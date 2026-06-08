"""Naive-RAG baseline: embed every user turn, retrieve top-k by cosine, no
reconcile, no forgetting, no salience. This is what most 'memory' agents do —
the thing Track 1 asks you to do better.
"""
from __future__ import annotations

import math

from app.llm import qwen_client


def _cosine(a, b):
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a)); nb = math.sqrt(sum(y * y for y in b))
    return dot / (na * nb) if na and nb else 0.0


class NaiveRAG:
    """Stores raw turns, retrieves top-k. No lifecycle."""

    def __init__(self, top_k: int = 5, token_budget: int | None = None) -> None:
        self.turns: list[dict] = []   # {text, embedding}
        self.top_k = top_k
        self.token_budget = token_budget   # if set, pack by budget like Mnemosyne

    def add_turn(self, text: str) -> None:
        vec = qwen_client.embed([text])[0]
        self.turns.append({"text": text, "embedding": vec})

    def answer(self, question: str) -> tuple[str, int, str]:
        if not self.turns:
            return qwen_client.chat([{"role": "user", "content": question}]), 0, ""
        qvec = qwen_client.embed([question])[0]
        ranked = sorted(self.turns,
                        key=lambda t: _cosine(qvec, t["embedding"]), reverse=True)
        if self.token_budget is not None:
            # Same constraint as Mnemosyne: greedily pack top matches into budget.
            ctx, used = [], 0
            for t in ranked:
                cost = max(1, len(t["text"]) // 4)
                if used + cost > self.token_budget:
                    continue
                ctx.append(t["text"]); used += cost
        else:
            ctx = [t["text"] for t in ranked[: self.top_k]]
        ctx_text = "\n".join(f"- {c}" for c in ctx)
        tokens = len(ctx_text) // 4
        reply = qwen_client.chat([
            {"role": "system",
             "content": "Answer using this remembered context:\n" + ctx_text},
            {"role": "user", "content": question},
        ])
        return reply, tokens, ctx_text
