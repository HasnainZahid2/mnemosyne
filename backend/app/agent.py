"""Chat orchestrator: wires the memory engine into a conversation.

Flow per user turn:
  1. RETRIEVE relevant memories (token-budgeted) and inject as context.
  2. Generate the assistant reply with Qwen, grounded in those memories.
  3. ENCODE new memories from the user's message (async-ish, after reply).

This is what makes the agent "get smarter across sessions": memory persists in
the store, so a brand-new session still recalls everything from before.
"""
from __future__ import annotations

from app.llm import qwen_client
from app.memory.engine import MemoryEngine, RetrievalResult

_SYSTEM = """You are Mnemosyne, a personal assistant with persistent memory.
Use the REMEMBERED CONTEXT below to personalize your answer. If it contradicts
what the user now says, trust the user's latest message. Be concise and natural.
Do not say "based on my memory" unless it's genuinely relevant."""


class Agent:
    def __init__(self, engine: MemoryEngine) -> None:
        self.engine = engine

    def respond(self, user_message: str, session_id: str) -> dict:
        retrieval: RetrievalResult = self.engine.retrieve(user_message)
        recalled = retrieval.memories

        context_block = ""
        if recalled:
            lines = "\n".join(f"- ({m.type.value}) {m.content}" for m in recalled)
            context_block = f"\n\nREMEMBERED CONTEXT:\n{lines}"

        reply = qwen_client.chat([
            {"role": "system", "content": _SYSTEM + context_block},
            {"role": "user", "content": user_message},
        ])

        # Learn from this turn after replying.
        new_memories = self.engine.encode(user_message, session_id)

        def slim(m) -> dict:
            d = m.to_dict()
            d.pop("embedding", None)
            return d

        return {
            "reply": reply,
            "recalled": [slim(m) for m in recalled],
            "new_memories": [slim(m) for m in new_memories],
            "tokens_used": retrieval.used_tokens,
            "considered": retrieval.considered,
        }
