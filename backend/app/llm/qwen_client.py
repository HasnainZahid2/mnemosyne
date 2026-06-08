"""Qwen Cloud client (OpenAI-compatible). All LLM + embedding calls go through here.

Qwen Cloud / DashScope is Alibaba Cloud infrastructure, so every call in this
module is an Alibaba Cloud API call (see docs/ALIBABA_CLOUD.md for the deployment
proof). We use the OpenAI SDK pointed at the DashScope-compatible endpoint.
"""
from __future__ import annotations

import json
import os
from typing import Any

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

_BASE_URL = os.getenv("QWEN_BASE_URL", "https://dashscope-intl.aliyuncs.com/compatible-mode/v1")
_CHAT_MODEL = os.getenv("QWEN_CHAT_MODEL", "qwen-plus")
_EMBED_MODEL = os.getenv("QWEN_EMBED_MODEL", "text-embedding-v3")


def _client() -> OpenAI:
    api_key = os.getenv("DASHSCOPE_API_KEY")
    if not api_key:
        raise RuntimeError(
            "DASHSCOPE_API_KEY is not set. Copy backend/.env.example to backend/.env "
            "and fill in your Qwen Cloud key."
        )
    return OpenAI(api_key=api_key, base_url=_BASE_URL)


def chat(messages: list[dict[str, str]], temperature: float = 0.3) -> str:
    """Plain chat completion. Returns the assistant's text."""
    resp = _client().chat.completions.create(
        model=_CHAT_MODEL,
        messages=messages,
        temperature=temperature,
    )
    return resp.choices[0].message.content or ""


def chat_json(messages: list[dict[str, str]], temperature: float = 0.1) -> Any:
    """Chat completion constrained to JSON output. Returns parsed JSON.

    Used by the memory engine for structured extraction / conflict detection.
    """
    resp = _client().chat.completions.create(
        model=_CHAT_MODEL,
        messages=messages,
        temperature=temperature,
        response_format={"type": "json_object"},
    )
    raw = resp.choices[0].message.content or "{}"
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        # Last-resort salvage: grab the outermost JSON object/array.
        start = min((raw.find("{") if "{" in raw else len(raw)),
                    (raw.find("[") if "[" in raw else len(raw)))
        end = max(raw.rfind("}"), raw.rfind("]"))
        if start < len(raw) and end > start:
            return json.loads(raw[start:end + 1])
        raise


def embed(texts: list[str]) -> list[list[float]]:
    """Embed a batch of texts. Returns a list of vectors."""
    if not texts:
        return []
    resp = _client().embeddings.create(model=_EMBED_MODEL, input=texts)
    return [d.embedding for d in resp.data]
