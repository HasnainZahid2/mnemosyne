# Deploy Mnemosyne to Alibaba Cloud ECS — Step by Step

Total time: ~15 minutes. No Docker needed — we run directly with Python.

## Step 1 — Create an ECS instance (Alibaba Console)

1. Go to **https://ecs.console.aliyun.com** → **Create Instance**
2. Settings:
   - **Region**: Singapore (ap-southeast-1) — same region as your OSS bucket
   - **Instance Type**: `ecs.t6-c1m1.large` (1 vCPU, 1 GB) or any small type — the app is tiny. Use **Preemptible** if available (cheapest, ~$0.01/hr)
   - **Image**: Ubuntu 22.04 or 24.04 (64-bit)
   - **System disk**: 20 GB SSD (default is fine)
   - **Network**: default VPC, assign **Public IP** (essential!)
   - **Bandwidth**: Pay-by-traffic, 1–5 Mbps is enough
   - **Security Group**: note the name — you'll edit it in Step 2
   - **Login**: set a **root password** or upload your SSH key
3. Confirm and create. Wait ~1 minute for it to start.

## Step 2 — Open port 8000 in the Security Group

1. Go to **ECS Console → Instances** → click your instance → **Security Groups**
2. Click the security group → **Inbound Rules** → **Add Rule**
3. Add:
   - Protocol: **Custom TCP**
   - Port: **8000**
   - Source: **0.0.0.0/0** (allows all IPs — fine for the hackathon demo)
   - Action: **Allow**
4. Save.

## Step 3 — SSH into the instance and deploy

Find your instance's **Public IP** on the ECS console.

```bash
ssh root@<YOUR_ECS_PUBLIC_IP>
```

Then run the deploy script (copy-paste the entire thing):

```bash
curl -sL https://raw.githubusercontent.com/HasnainZahid2/mnemosyne/main/deploy/setup_ecs.sh | bash
```

Or manually:

```bash
apt update && apt install -y git curl python3 python3-venv
git clone https://github.com/HasnainZahid2/mnemosyne.git
cd mnemosyne/backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env — paste your DASHSCOPE_API_KEY (and OSS keys if you have them)
nano .env
# Start the server
nohup .venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000 > ~/mnemosyne.log 2>&1 &
```

## Step 4 — Verify

From your local machine:

```bash
curl http://<YOUR_ECS_PUBLIC_IP>:8000/health
# Should return: {"status":"ok","oss_enabled":false}
# (oss_enabled will be true if you filled in the OSS keys)
```

```bash
curl -X POST http://<YOUR_ECS_PUBLIC_IP>:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message":"I live in Berlin","session_id":"proof"}'
```

## Step 5 — Record the proof

Record a short screen clip showing:
1. The ECS console with your running instance (public IP visible)
2. `curl http://<IP>:8000/health` returning OK
3. A `/chat` call working

This is your "Proof of Alibaba Cloud Deployment" for the submission.

## Cost

- Smallest preemptible instance: ~$0.01/hr (~$0.24/day)
- Your $40 hackathon voucher covers weeks of this
- **Remember to release the instance after the hackathon** to stop charges
