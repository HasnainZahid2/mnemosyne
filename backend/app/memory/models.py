"""Core data model: a Memory is a single atomic thing the agent remembers.

Memory is treated as a living object with a lifecycle (salience that decays,
access counts that grow, a status that can move to 'archived' or 'superseded').
This is the heart of the Track-1 differentiator.
"""
from __future__ import annotations

import time
import uuid
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Optional


class MemoryType(str, Enum):
    FACT = "fact"               # objective info: "user is a backend engineer"
    PREFERENCE = "preference"   # likes/dislikes: "prefers concise answers"
    EVENT = "event"             # something that happened: "shipped v2 on Tuesday"
    RELATIONSHIP = "relationship"  # people/orgs: "manager is Sarah"
    GOAL = "goal"               # intentions/aims: "wants to read more this year"

    @classmethod
    def coerce(cls, value: str) -> "MemoryType":
        """Map an arbitrary LLM-produced type to a known one; default to FACT.
        Keeps a single unexpected label from crashing the whole pipeline."""
        try:
            return cls(str(value).lower())
        except ValueError:
            return cls.FACT


class MemoryStatus(str, Enum):
    ACTIVE = "active"
    ARCHIVED = "archived"       # faded out by decay/forgetting
    SUPERSEDED = "superseded"   # replaced by a newer, contradicting memory


@dataclass
class Memory:
    content: str
    type: MemoryType = MemoryType.FACT
    salience: float = 0.5            # 0..1 importance; decays over time
    entities: list[str] = field(default_factory=list)
    embedding: Optional[list[float]] = None

    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    created_at: float = field(default_factory=time.time)
    last_accessed: float = field(default_factory=time.time)
    access_count: int = 0
    status: MemoryStatus = MemoryStatus.ACTIVE
    superseded_by: Optional[str] = None   # id of the memory that replaced this one
    source_session: Optional[str] = None

    def touch(self) -> None:
        """Record that this memory was recalled — strengthens it."""
        self.last_accessed = time.time()
        self.access_count += 1

    def to_dict(self) -> dict:
        d = asdict(self)
        d["type"] = self.type.value
        d["status"] = self.status.value
        return d

    @classmethod
    def from_dict(cls, d: dict) -> "Memory":
        d = dict(d)
        d["type"] = MemoryType.coerce(d.get("type", "fact"))
        try:
            d["status"] = MemoryStatus(d.get("status", "active"))
        except ValueError:
            d["status"] = MemoryStatus.ACTIVE
        return cls(**d)
