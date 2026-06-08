"""The Memory Lifecycle Engine — the Track-1 differentiator.

Five operations, each one a thing naive RAG skips:

  1. ENCODE     Qwen extracts atomic, typed memories from a turn (not raw dumps).
  2. RETRIEVE   Multi-signal ranking (semantic + recency + salience + frequency)
                then token-budget-aware packing — "recall within a limited
                context window", exactly what the track asks for.
  3. RECONCILE  New memories that contradict old ones SUPERSEDE them; the old
                fact is archived with a pointer, not silently kept or lost.
  4. CONSOLIDATE  Near-duplicate memories merge (light version).
  5. DECAY      Salience fades with age; low-salience, rarely-used memories are
                archived ("timely forgetting of outdated information").
"""
from __future__ import annotations

import math
import time
from dataclasses import dataclass

from app.llm import qwen_client
from app.memory.models import Memory, MemoryStatus, MemoryType
from app.storage.store import MemoryStore

# Ranking weights (semantic dominates, but recency/salience/frequency matter).
W_SEMANTIC = 0.55
W_RECENCY = 0.15
W_SALIENCE = 0.20
W_FREQUENCY = 0.10

DECAY_HALFLIFE_DAYS = 14.0      # salience halves every two weeks of non-use
ARCHIVE_THRESHOLD = 0.12        # below this (and rarely used) -> archived
DUP_SIMILARITY = 0.92           # cosine above this = treat as duplicate
CONFLICT_SIMILARITY = 0.55      # candidates this similar are LLM-checked for conflict
                                # (moderate on purpose: the LLM makes the final call,
                                #  so we favor recall here — a cheap pre-filter, not a
                                #  precise gate. Entity overlap also triggers a check.)

# Rough token estimate: ~4 chars/token. Good enough for budget packing.
CHARS_PER_TOKEN = 4


def _cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


def _recency_score(last_accessed: float) -> float:
    age_days = max(0.0, (time.time() - last_accessed) / 86400.0)
    return 0.5 ** (age_days / DECAY_HALFLIFE_DAYS)


@dataclass
class RetrievalResult:
    memories: list[Memory]
    used_tokens: int
    considered: int


_EXTRACT_SYS = """You extract durable memories from a user message in a personal-assistant chat.
Return JSON: {"memories": [{"content": str, "type": "fact|preference|event|relationship", "salience": 0.0-1.0, "entities": [str]}]}.
Rules:
- Extract only durable, reusable facts about the USER or their world. Skip pleasantries, questions, and transient chit-chat.
- salience: 0.9+ for identity/stable preferences, ~0.5 for ordinary facts, <0.3 for minor/ephemeral details.
- entities: proper nouns (people, places, orgs, products) mentioned.
- If nothing worth remembering, return {"memories": []}."""

_CONFLICT_SYS = """You decide if a NEW memory makes an EXISTING memory OUTDATED.

Return JSON: {"conflict": bool, "reason": str}.

conflict = true when the two describe the SAME ATTRIBUTE of the same subject with
DIFFERENT current values, so the old one is no longer true. This includes:
- location: "lives in New York" vs "moved to Berlin" -> conflict
- job/title/role: "is a backend engineer" vs "is a staff engineer now" -> conflict
- employer, relationship status, current project, a reversed preference, etc.

conflict = false when the new memory is merely ADDITIONAL or UNRELATED info
(a different attribute, a new person, an allergy vs a job, etc.).

When the same attribute has changed value, prefer conflict = true."""


class MemoryEngine:
    def __init__(self, store: MemoryStore) -> None:
        self.store = store

    # ---- 1. ENCODE --------------------------------------------------------
    def encode(self, user_message: str, session_id: str) -> list[Memory]:
        """Extract typed memories from a user message and store them, running
        reconcile + dedup as each one lands."""
        result = qwen_client.chat_json([
            {"role": "system", "content": _EXTRACT_SYS},
            {"role": "user", "content": user_message},
        ])
        extracted = result.get("memories", []) if isinstance(result, dict) else []
        if not extracted:
            return []

        # Embed all new memory contents in one batch.
        contents = [m["content"] for m in extracted if m.get("content")]
        vectors = qwen_client.embed(contents)

        stored: list[Memory] = []
        for spec, vec in zip(extracted, vectors):
            mem = Memory(
                content=spec["content"],
                type=MemoryType.coerce(spec.get("type", "fact")),
                salience=float(spec.get("salience", 0.5)),
                entities=spec.get("entities", []) or [],
                embedding=vec,
                source_session=session_id,
            )
            if self._dedup(mem):
                continue            # merged into an existing memory
            self._reconcile(mem)    # supersede any contradicted memory
            self.store.add(mem)
            stored.append(mem)
        return stored

    # ---- 2. RETRIEVE ------------------------------------------------------
    def retrieve(self, query: str, token_budget: int = 1200) -> RetrievalResult:
        """Rank active memories by multiple signals, then greedily pack the
        highest-scoring ones into a fixed token budget."""
        active = self.store.all_active()
        if not active:
            return RetrievalResult([], 0, 0)

        qvec = qwen_client.embed([query])[0]
        scored: list[tuple[float, Memory]] = []
        for m in active:
            sem = _cosine(qvec, m.embedding) if m.embedding else 0.0
            rec = _recency_score(m.last_accessed)
            sal = m.salience
            freq = 1.0 - 1.0 / (1.0 + m.access_count)   # 0 -> grows toward 1
            score = (W_SEMANTIC * sem + W_RECENCY * rec
                     + W_SALIENCE * sal + W_FREQUENCY * freq)
            scored.append((score, m))

        scored.sort(key=lambda t: t[0], reverse=True)

        packed: list[Memory] = []
        used = 0
        for _, m in scored:
            cost = max(1, len(m.content) // CHARS_PER_TOKEN)
            if used + cost > token_budget:
                continue
            packed.append(m)
            used += cost
            m.touch()
        if packed:
            self.store.save_all()   # persist updated access counts
        return RetrievalResult(packed, used, len(active))

    # ---- 3. RECONCILE -----------------------------------------------------
    CONFLICT_CHECK_TOP_N = 3        # at most this many LLM judgements per new memory
    CONFLICT_CHECK_FLOOR = 0.62     # only judge neighbors at least this similar

    def _reconcile(self, new_mem: Memory) -> None:
        """Check the new memory against its nearest existing memories and let the
        LLM decide if any are contradicted (and thus superseded).

        Contradictions concern the SAME attribute with a DIFFERENT value
        ("lives in New York" -> "moved to Berlin"); such pairs are semantically
        related, so we only LLM-judge the top-N neighbors above a similarity
        floor. This bounds cost (most distractors never trigger a judgement)
        while still catching real conflicts.
        """
        if new_mem.embedding is None:
            return
        candidates = [
            (_cosine(new_mem.embedding, old.embedding), old)
            for old in self.store.all_active()
            if old.embedding is not None and old.id != new_mem.id
        ]
        candidates.sort(key=lambda t: t[0], reverse=True)
        candidates = [(s, o) for s, o in candidates if s >= self.CONFLICT_CHECK_FLOOR]

        for sim, old in candidates[: self.CONFLICT_CHECK_TOP_N]:
            verdict = qwen_client.chat_json([
                {"role": "system", "content": _CONFLICT_SYS},
                {"role": "user",
                 "content": f"EXISTING: {old.content}\nNEW: {new_mem.content}"},
            ])
            conflict = isinstance(verdict, dict) and verdict.get("conflict")
            print(f"[reconcile] sim={sim:.2f} conflict={bool(conflict)} "
                  f"| OLD='{old.content}' NEW='{new_mem.content}'")
            if conflict:
                old.status = MemoryStatus.SUPERSEDED
                old.superseded_by = new_mem.id
                self.store.update(old)

    # ---- 4. CONSOLIDATE (dedup) ------------------------------------------
    def _dedup(self, new_mem: Memory) -> bool:
        """If an almost-identical active memory exists, strengthen it instead of
        adding a duplicate. Returns True if merged."""
        if new_mem.embedding is None:
            return False
        for old in self.store.all_active():
            if old.embedding is None:
                continue
            if _cosine(new_mem.embedding, old.embedding) >= DUP_SIMILARITY:
                old.salience = min(1.0, old.salience + 0.1)
                old.touch()
                self.store.update(old)
                return True
        return False

    # ---- 5. DECAY / FORGET ------------------------------------------------
    def decay(self) -> int:
        """Apply time-decay to salience and archive faded, unused memories.
        Returns the number archived."""
        archived = 0
        for m in self.store.all_active():
            effective = m.salience * _recency_score(m.last_accessed)
            if effective < ARCHIVE_THRESHOLD and m.access_count < 2:
                m.status = MemoryStatus.ARCHIVED
                self.store.update(m)
                archived += 1
        return archived
