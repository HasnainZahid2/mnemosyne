# Proof of Alibaba Cloud Deployment

Mnemosyne runs entirely on Alibaba Cloud infrastructure. This document is the
submission's "Proof of Alibaba Cloud Deployment" writeup.

## 1. Qwen Cloud (DashScope) — the model layer

Every LLM and embedding call goes through Qwen Cloud, which is Alibaba Cloud's
model-serving platform. See [`backend/app/llm/qwen_client.py`](../backend/app/llm/qwen_client.py).

- Endpoint: `https://dashscope-intl.aliyuncs.com/compatible-mode/v1`
- Models: `qwen-plus` (chat, memory extraction, conflict judge), `text-embedding-v3` (1024-d)

## 2. Alibaba Cloud OSS — memory persistence

The agent's memory store is persisted to an Alibaba Cloud OSS bucket using the
official `oss2` SDK. **This is the code file demonstrating use of Alibaba Cloud
services and APIs:**

➡️ [`backend/app/storage/oss_client.py`](../backend/app/storage/oss_client.py)

It calls `oss2.Auth`, `oss2.Bucket`, `bucket.put_object`, and `bucket.get_object`.
When the `OSS_*` environment variables are set, every memory write is synced to
OSS, so a redeployed backend restores its full memory from the cloud.

## 3. Alibaba Cloud ECS — the backend host

The FastAPI backend is deployed on an Alibaba Cloud ECS instance.

### Deployment steps (reproducible)

```bash
# On a fresh Alibaba Cloud ECS Ubuntu instance:
sudo apt update && sudo apt install -y python3-venv python3-pip
git clone <your-repo-url> mnemosyne && cd mnemosyne/backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# Set secrets (Qwen key + OSS credentials) in the environment or .env
export DASHSCOPE_API_KEY=sk-...
export OSS_ACCESS_KEY_ID=...  OSS_ACCESS_KEY_SECRET=...
export OSS_ENDPOINT=https://oss-ap-southeast-1.aliyuncs.com  OSS_BUCKET=mnemosyne-memories

# Run (bind to 0.0.0.0 so the instance's public IP serves it)
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Open the ECS security group to inbound TCP 8000 (or put it behind nginx on 80/443).

### What the proof recording shows
- `curl http://<ECS_PUBLIC_IP>:8000/health` returning `{"status":"ok","oss_enabled":true}`
- A `/chat` call creating a memory, then the new object appearing in the OSS bucket
  in the Alibaba Cloud console.

> Replace `<ECS_PUBLIC_IP>` and `<your-repo-url>` with your actual values before recording.
