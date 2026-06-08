"""Alibaba Cloud OSS client — the deployment-proof artifact.

THIS FILE is the "link to a code file that demonstrates use of Alibaba Cloud
services and APIs" required by the submission. It uses the official `oss2` SDK
to persist the agent's memory store to an Alibaba Cloud OSS bucket.

If OSS env vars are absent, the factory returns None and the app falls back to
local-only storage, so development never requires cloud credentials.
"""
from __future__ import annotations

import os
from typing import Optional

try:
    import oss2  # Alibaba Cloud OSS SDK
except ImportError:  # pragma: no cover
    oss2 = None

_OBJECT_KEY = "mnemosyne/memories.json"


class OSSClient:
    def __init__(self, key_id: str, key_secret: str, endpoint: str, bucket: str) -> None:
        if oss2 is None:
            raise RuntimeError("oss2 not installed; run pip install -r requirements.txt")
        auth = oss2.Auth(key_id, key_secret)
        self._bucket = oss2.Bucket(auth, endpoint, bucket)

    def save(self, payload: str) -> None:
        """Upload the serialized memory store to Alibaba Cloud OSS."""
        self._bucket.put_object(_OBJECT_KEY, payload.encode("utf-8"))

    def try_load(self) -> Optional[str]:
        """Fetch the memory store from OSS, or None if it doesn't exist yet."""
        try:
            obj = self._bucket.get_object(_OBJECT_KEY)
            return obj.read().decode("utf-8")
        except Exception:
            return None


def make_oss_client() -> Optional[OSSClient]:
    """Build an OSSClient from env, or None if not configured."""
    key_id = os.getenv("OSS_ACCESS_KEY_ID")
    key_secret = os.getenv("OSS_ACCESS_KEY_SECRET")
    endpoint = os.getenv("OSS_ENDPOINT")
    bucket = os.getenv("OSS_BUCKET")
    if all([key_id, key_secret, endpoint, bucket]):
        return OSSClient(key_id, key_secret, endpoint, bucket)
    return None
