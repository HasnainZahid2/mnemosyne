# Proof-of-Alibaba-Cloud Recording Checklist

A short (30–60s) screen recording, **separate from the 3-min demo**, that proves
the backend uses Alibaba Cloud. Record these shots in order:

## Shot list

1. **The code file** — open [`backend/app/storage/oss_client.py`](../backend/app/storage/oss_client.py)
   on screen. Scroll slowly over the `oss2.Auth`, `oss2.Bucket`, `put_object`,
   `get_object` calls. (This is the required "link to a code file demonstrating
   Alibaba Cloud APIs".)

2. **The Qwen client** — open [`backend/app/llm/qwen_client.py`](../backend/app/llm/qwen_client.py)
   and show the `dashscope-intl.aliyuncs.com` base URL. Say: "All model calls go
   to Qwen Cloud, which is Alibaba Cloud."

3. **Live OSS round-trip** — run `python test_oss.py` in the terminal. Show the
   output: "put_object succeeded" → "get_object succeeded — memory restored from cloud."

4. **The Alibaba Cloud console** — log into the OSS console in the browser, open
   your bucket → Objects, and show `mnemosyne/memories.json` sitting there with a
   recent "Last Modified" timestamp. This is the smoking gun: real data, in a
   real Alibaba Cloud bucket, written by the backend.

5. (Optional, if you did the ECS deploy) `curl http://<ECS_PUBLIC_IP>:8000/health`
   returning `{"status":"ok","oss_enabled":true}`.

## What the narration should assert
- "The backend's memory store is persisted to Alibaba Cloud OSS."
- "Every reasoning and embedding call runs on Qwen Cloud (Alibaba Cloud)."
- "Here is the object in the Alibaba Cloud console, written by the running backend."

Upload this clip (or link the file) per the submission form's "Proof of Alibaba
Cloud Deployment" field.
