"""Run this FIRST to confirm your Qwen Cloud key works before building anything.

    cd backend
    python -m venv .venv && .venv\\Scripts\\activate   (Windows)
    pip install -r requirements.txt
    copy .env.example .env   # then edit .env, paste your key
    python check_connection.py
"""
from app.llm import qwen_client


def main() -> None:
    print("1/2  Testing chat completion ...")
    reply = qwen_client.chat(
        [{"role": "user", "content": "Reply with exactly: Mnemosyne online."}]
    )
    print("     Qwen says:", reply.strip())

    print("2/2  Testing embeddings ...")
    vecs = qwen_client.embed(["hello world"])
    print(f"     Got embedding of dimension {len(vecs[0])}")

    print("\nAll good. Key works. You're cleared to build.")


if __name__ == "__main__":
    main()
