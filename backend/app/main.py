"""FastAPI app for Mnemosyne.

Endpoints:
  POST /chat               -> {reply, recalled, new_memories, tokens_used}
  GET  /memories           -> all memories (for the live inspector panel)
  POST /decay              -> run the forgetting pass, returns #archived
  GET  /health             -> liveness
"""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from app.agent import Agent
from app.memory.engine import MemoryEngine
from app.storage.oss_client import make_oss_client
from app.storage.store import MemoryStore

app = FastAPI(title="Mnemosyne — MemoryAgent")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

_store = MemoryStore(oss_client=make_oss_client())
_engine = MemoryEngine(_store)
_agent = Agent(_engine)


class ChatIn(BaseModel):
    message: str
    session_id: str = "default"


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "oss_enabled": _store._oss is not None}


@app.post("/chat")
def chat(body: ChatIn) -> dict:
    return _agent.respond(body.message, body.session_id)


def _slim(m) -> dict:
    """Memory dict without the embedding vector — for the inspector UI/API."""
    d = m.to_dict()
    d.pop("embedding", None)
    return d


@app.get("/memories")
def memories() -> dict:
    items = [_slim(m) for m in _store.all()]
    items.sort(key=lambda m: m["last_accessed"], reverse=True)
    return {"memories": items, "count": len(items)}


@app.post("/decay")
def decay() -> dict:
    archived = _engine.decay()
    return {"archived": archived}


@app.post("/reset")
def reset() -> dict:
    """Wipe all memories (in-process AND on disk). For clean demos/tests."""
    _store._memories.clear()
    _store.save_all()
    return {"status": "reset", "count": 0}
