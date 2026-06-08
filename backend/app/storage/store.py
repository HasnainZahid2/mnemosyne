"""Pluggable memory store.

Default backend is a local JSON file (zero setup, works offline). If Alibaba
Cloud OSS credentials are present in the environment, every save is also synced
to an OSS object — that sync is the "backend runs on Alibaba Cloud" proof.

The store is deliberately simple (load-all into memory); for a hackathon-scale
personal assistant the memory set is small, and keeping it in-process makes the
ranking/decay logic trivial to reason about.
"""
from __future__ import annotations

import json
import os
import threading
from pathlib import Path
from typing import Optional

from app.memory.models import Memory

_DATA_DIR = Path(__file__).resolve().parents[2] / "data"
_DATA_DIR.mkdir(exist_ok=True)
_LOCAL_PATH = _DATA_DIR / "memories.json"


class MemoryStore:
    def __init__(self, oss_client: Optional["OSSClient"] = None) -> None:
        self._lock = threading.Lock()
        self._memories: dict[str, Memory] = {}
        self._oss = oss_client
        self._load()

    # ---- persistence -------------------------------------------------------
    def _load(self) -> None:
        # Prefer OSS if available (so a redeployed container restores state).
        raw = None
        if self._oss is not None:
            raw = self._oss.try_load()
        if raw is None and _LOCAL_PATH.exists():
            raw = _LOCAL_PATH.read_text(encoding="utf-8")
        if raw:
            data = json.loads(raw)
            self._memories = {m["id"]: Memory.from_dict(m) for m in data}

    def _persist(self) -> None:
        payload = json.dumps([m.to_dict() for m in self._memories.values()],
                             ensure_ascii=False, indent=2)
        _LOCAL_PATH.write_text(payload, encoding="utf-8")
        if self._oss is not None:
            self._oss.save(payload)

    # ---- CRUD --------------------------------------------------------------
    def add(self, memory: Memory) -> None:
        with self._lock:
            self._memories[memory.id] = memory
            self._persist()

    def update(self, memory: Memory) -> None:
        with self._lock:
            self._memories[memory.id] = memory
            self._persist()

    def all_active(self) -> list[Memory]:
        from app.memory.models import MemoryStatus
        return [m for m in self._memories.values() if m.status == MemoryStatus.ACTIVE]

    def all(self) -> list[Memory]:
        return list(self._memories.values())

    def get(self, mem_id: str) -> Optional[Memory]:
        return self._memories.get(mem_id)

    def save_all(self) -> None:
        with self._lock:
            self._persist()
