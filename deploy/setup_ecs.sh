#!/bin/bash
# ============================================================
# Mnemosyne — one-shot ECS deploy script
# Run on a fresh Alibaba Cloud ECS Ubuntu 22.04/24.04 instance
#
# Usage:
#   1. SSH into your ECS instance
#   2. Copy-paste this entire script (or scp it over)
#   3. Run: bash setup_ecs.sh
#   4. When prompted, paste your DASHSCOPE_API_KEY
#   5. (Optional) paste OSS credentials if you have them
# ============================================================
set -e

echo "=== Mnemosyne ECS Deploy ==="

# 1. System deps
echo "[1/5] Installing system dependencies..."
sudo apt-get update -qq
sudo apt-get install -y -qq python3 python3-venv python3-pip git curl > /dev/null

# 2. Clone repo
echo "[2/5] Cloning repository..."
cd ~
if [ -d "mnemosyne" ]; then
    cd mnemosyne && git pull --ff-only
else
    git clone https://github.com/HasnainZahid2/mnemosyne.git
    cd mnemosyne
fi

# 3. Python venv + deps
echo "[3/5] Setting up Python environment..."
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -q -r requirements.txt

# 4. Configure environment
echo "[4/5] Configuring environment..."
if [ ! -f .env ]; then
    cp .env.example .env
    echo ""
    echo ">>> Enter your DASHSCOPE_API_KEY (Qwen Cloud key):"
    read -r QWEN_KEY
    sed -i "s|sk-your-key-here|${QWEN_KEY}|" .env
    echo ""
    echo ">>> Enter OSS_ACCESS_KEY_ID (or press Enter to skip OSS):"
    read -r OSS_KEY_ID
    if [ -n "$OSS_KEY_ID" ]; then
        echo ">>> Enter OSS_ACCESS_KEY_SECRET:"
        read -r OSS_KEY_SECRET
        echo ">>> Enter OSS_BUCKET name:"
        read -r OSS_BUCKET
        sed -i "s|^OSS_ACCESS_KEY_ID=.*|OSS_ACCESS_KEY_ID=${OSS_KEY_ID}|" .env
        sed -i "s|^OSS_ACCESS_KEY_SECRET=.*|OSS_ACCESS_KEY_SECRET=${OSS_KEY_SECRET}|" .env
        sed -i "s|^OSS_BUCKET=.*|OSS_BUCKET=${OSS_BUCKET}|" .env
    fi
    echo ".env configured."
else
    echo ".env already exists, skipping configuration."
fi

# 5. Start the server
echo "[5/5] Starting Mnemosyne backend..."
echo ""

# Kill any existing instance
pkill -f "uvicorn app.main:app" 2>/dev/null || true

# Run in background with nohup so it survives SSH disconnect
nohup .venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000 \
    > ~/mnemosyne.log 2>&1 &

sleep 2

# Verify
if curl -s http://localhost:8000/health | grep -q "ok"; then
    PUBLIC_IP=$(curl -s http://checkip.amazonaws.com 2>/dev/null || echo "<YOUR_ECS_IP>")
    echo ""
    echo "============================================"
    echo "  Mnemosyne is LIVE!"
    echo "  Local:  http://localhost:8000/health"
    echo "  Public: http://${PUBLIC_IP}:8000/health"
    echo "============================================"
    echo ""
    echo "Next steps:"
    echo "  1. Open ECS security group: allow inbound TCP 8000"
    echo "  2. Test: curl http://${PUBLIC_IP}:8000/health"
    echo "  3. Record the proof video showing the public URL"
    echo ""
    echo "Logs: tail -f ~/mnemosyne.log"
else
    echo "ERROR: Server didn't start. Check logs: cat ~/mnemosyne.log"
fi
