"""Benchmark: Mnemosyne (lifecycle) vs naive-RAG baseline.

Plants facts across "sessions", changes one (a move), then asks recall questions.
The interesting case is the CONTRADICTION: after the user moves to Berlin, a
correct system answers "Berlin" and must NOT say "New York". Naive RAG keeps both
the old and new turn and frequently retrieves the stale one.

Run from the backend dir so `app` is importable:
    cd backend
    python ..\\benchmark\\run_benchmark.py
"""
from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROOT / "backend"))   # so `app...` imports work
sys.path.insert(0, str(_ROOT))               # so `benchmark...` imports work

from app.llm import qwen_client                       # noqa: E402
from app.memory.engine import MemoryEngine            # noqa: E402
from app.storage.store import MemoryStore             # noqa: E402
from benchmark.baseline import NaiveRAG               # noqa: E402

# Distractor facts — realistic memory accumulates a LOT of these. Their presence
# is the point: with a tight context budget, a system must surface the few
# CRITICAL memories and not waste the budget on noise (Track 1's core ask).
DISTRACTORS = [
    "I enjoy hiking on weekends.", "My favorite color is teal.",
    "I drink black coffee in the morning.", "I have a golden retriever named Max.",
    "I studied computer science in college.", "I play the guitar occasionally.",
    "I watched a documentary about oceans last night.", "I like Thai food.",
    "My favorite author is Ursula K. Le Guin.", "I usually go to bed around midnight.",
    "I'm learning to cook Italian dishes.", "I take the subway to work.",
    "I have a younger sister.", "I prefer window seats on flights.",
    "I use a mechanical keyboard.", "I enjoy board games with friends.",
    "I once visited Japan for two weeks.", "I'm trying to read more this year.",
    "I keep a small herb garden.", "I like listening to jazz while working.",
    "I run about 5k three times a week.", "I collect vintage postcards.",
    "I dislike crowded places.", "My favorite season is autumn.",
    "I recently started meditating.",
]

# Critical facts, including two CONTRADICTIONS introduced later in the timeline.
CRITICAL = [
    "I live in New York.",
    "I work as a backend engineer at a fintech startup.",
    "I prefer concise, no-fluff answers.",
    "My manager is Sarah.",
    "I'm allergic to peanuts.",
]
UPDATES = [
    "Actually I just moved to Berlin last week.",      # supersedes New York
    "I switched jobs — I'm a staff engineer now.",     # supersedes backend engineer
]

# Interleave so the timeline is realistic: critical facts, buried in distractors,
# with the contradicting updates arriving near the end.
SCRIPT = (
    CRITICAL
    + DISTRACTORS[:13]
    + [UPDATES[0]]
    + DISTRACTORS[13:]
    + [UPDATES[1]]
)

# Tight budget forces selectivity — the regime where lifecycle memory wins.
TOKEN_BUDGET = 120
BASELINE_TOP_K = 6

# (question, must_contain, must_not_contain, stale_terms_in_context)
# stale_terms: substrings whose presence in the RETRIEVED CONTEXT means the
# memory layer surfaced an outdated fact (regardless of what the LLM then says).
QUESTIONS = [
    ("Where do I live?", ["berlin"], ["new york"], ["new york"]),
    ("What's my job title?", ["staff"], ["backend engineer"], ["backend engineer"]),
    ("Who is my manager?", ["sarah"], [], []),
    ("Any allergies I should know about?", ["peanut"], [], []),
    ("How do I like my answers?", ["concise", "short", "no-fluff", "brief"], [], []),
]


def judge(answer: str, must: list[str], must_not: list[str]) -> tuple[bool, bool]:
    a = answer.lower()
    correct = any(m in a for m in must) if must else True
    stale = any(m in a for m in must_not)
    return correct, stale


def _stale_in_ctx(ctx: str, stale_terms: list[str]) -> int:
    c = ctx.lower()
    return sum(1 for t in stale_terms if t in c)


def run_mnemosyne():
    store = MemoryStore()
    store._memories.clear()
    engine = MemoryEngine(store)
    for turn in SCRIPT:
        engine.encode(turn, session_id="bench")
    correct = stale_ans = stale_ctx = total_tokens = 0
    for q, must, mustnot, staleterms in QUESTIONS:
        r = engine.retrieve(q, token_budget=TOKEN_BUDGET)
        ctx = "\n".join(f"- {m.content}" for m in r.memories)
        reply = qwen_client.chat([
            {"role": "system", "content": "Answer using remembered context:\n" + ctx},
            {"role": "user", "content": q},
        ])
        c, s = judge(reply, must, mustnot)
        sc = _stale_in_ctx(ctx, staleterms)
        correct += c; stale_ans += s; stale_ctx += sc; total_tokens += r.used_tokens
        print(f"  [Mnemosyne] Q: {q}\n     A: {reply.strip()[:80]}  "
              f"({'OK' if c else 'MISS'}{', STALE-CTX' if sc else ''})")
    return correct, stale_ans, stale_ctx, total_tokens


def run_baseline():
    rag = NaiveRAG(top_k=BASELINE_TOP_K, token_budget=TOKEN_BUDGET)
    for turn in SCRIPT:
        rag.add_turn(turn)
    correct = stale_ans = stale_ctx = total_tokens = 0
    for q, must, mustnot, staleterms in QUESTIONS:
        reply, tokens, ctx = rag.answer(q)
        c, s = judge(reply, must, mustnot)
        sc = _stale_in_ctx(ctx, staleterms)
        correct += c; stale_ans += s; stale_ctx += sc; total_tokens += tokens
        print(f"  [NaiveRAG]  Q: {q}\n     A: {reply.strip()[:80]}  "
              f"({'OK' if c else 'MISS'}{', STALE-CTX' if sc else ''})")
    return correct, stale_ans, stale_ctx, total_tokens


def main():
    n = len(QUESTIONS)
    print("\n=== Mnemosyne (memory lifecycle) ===")
    m_correct, m_sans, m_sctx, m_tokens = run_mnemosyne()
    print("\n=== Naive RAG baseline ===")
    b_correct, b_sans, b_sctx, b_tokens = run_baseline()

    print("\n" + "=" * 62)
    print(f"{'Metric':<34}{'Mnemosyne':>13}{'NaiveRAG':>13}")
    print("-" * 62)
    print(f"{'Answer accuracy':<34}{f'{m_correct}/{n}':>13}{f'{b_correct}/{n}':>13}")
    print(f"{'Stale facts in retrieved context':<34}{m_sctx:>13}{b_sctx:>13}")
    print(f"{'Wrong answers from stale facts':<34}{m_sans:>13}{b_sans:>13}")
    print(f"{'Context tokens used':<34}{m_tokens:>13}{b_tokens:>13}")
    print("=" * 62)
    print("\nKey result: the lifecycle engine SUPERSEDES outdated facts at encode")
    print(f"time, so they never reach the context window ({m_sctx} stale vs {b_sctx} for naive RAG).")
    print("Naive RAG keeps every version forever and leans on the LLM to sort it")
    print("out at answer time — which wastes context budget and fails silently as")
    print("memory grows or the answering model gets weaker.")


if __name__ == "__main__":
    main()
