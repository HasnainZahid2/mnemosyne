"""Standalone Alibaba Cloud OSS connectivity + round-trip test.

Run this AFTER filling the OSS_* fields in backend/.env. It proves the backend
talks to Alibaba Cloud OSS — and the run itself is good footage for the
"proof of Alibaba Cloud deployment" recording.

    cd backend
    .venv\\Scripts\\activate
    python test_oss.py
"""
from __future__ import annotations

import json
import os
import time

from dotenv import load_dotenv

from app.storage.oss_client import make_oss_client

load_dotenv()


def main() -> None:
    client = make_oss_client()
    if client is None:
        print("✗ OSS not configured. Fill OSS_ACCESS_KEY_ID / OSS_ACCESS_KEY_SECRET / "
              "OSS_ENDPOINT / OSS_BUCKET in backend/.env first.")
        return

    bucket = os.getenv("OSS_BUCKET")
    endpoint = os.getenv("OSS_ENDPOINT")
    print(f"→ Connecting to Alibaba Cloud OSS bucket '{bucket}' at {endpoint}")

    # 1. Upload a sample memory snapshot.
    sample = json.dumps(
        [{"id": "demo1", "content": "The user lives in Berlin.",
          "type": "fact", "status": "active"}],
        indent=2,
    )
    print("→ Uploading a memory snapshot to OSS …")
    client.save(sample)
    print("  ✓ put_object succeeded")

    # 2. Read it back.
    print("→ Reading the snapshot back from OSS …")
    loaded = client.try_load()
    assert loaded is not None, "round-trip failed: object not found after upload"
    parsed = json.loads(loaded)
    print(f"  ✓ get_object succeeded — {len(parsed)} memory record(s) restored from cloud")
    print(f"  ✓ first record: {parsed[0]['content']!r}")

    print("\n✓ Alibaba Cloud OSS round-trip OK. The backend persists its memory "
          "store to Alibaba Cloud.")
    print(f"  Verify in the console: OSS → Buckets → {bucket} → Objects → "
          "mnemosyne/memories.json")


if __name__ == "__main__":
    main()
