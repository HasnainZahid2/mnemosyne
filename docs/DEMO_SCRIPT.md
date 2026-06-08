# 3-Minute Demo Video Script — Mnemosyne

Target: **under 3:00** (judges stop watching at 3:00). Record at 1080p. Have the
chat UI (left) and memory inspector (right) both visible. Reset memory before you
start (the Reset button).

---

### 0:00–0:20 — Hook + problem
> "Most AI assistants forget you the moment a chat ends — or worse, they remember
> everything forever and can't tell what's still true. This is Mnemosyne, a
> MemoryAgent built on Qwen Cloud that treats memory as a living lifecycle:
> it learns, recalls, forgets, and reconciles contradictions."

Show: the app, both panels, empty memory inspector.

### 0:20–1:00 — Encode + cross-session recall
Type: `I live in New York and I prefer short answers.`
> "It doesn't dump raw text. Qwen extracts structured memories — a *fact* and a
> *preference* — each with a type, salience, and entities."

Show: two cards appear and flash in the inspector. Point at the type tags.

Type: `Where do I live?`
> "New session, no chat history — but it answers from memory."

Show: reply "New York", the card flashes (recalled ×1). Point at the metadata line
("recalled 1").

### 1:00–1:40 — Reconcile (the hero moment)
Type: `Actually I just moved to Berlin.`
> "Here's what naive RAG can't do. The new fact *contradicts* the old one. Qwen
> detects the conflict, and Mnemosyne **supersedes** the outdated memory —
> archived, not deleted, with a pointer to what replaced it."

Show: the "New York" card turns **red and strikes through**; a green "Berlin"
card appears. Let this land — it's the visual climax.

### 1:40–2:20 — The benchmark (proof, not vibes)
Cut to terminal. Run `python ..\benchmark\run_benchmark.py` (or show pre-recorded output).
> "We benchmarked it against naive RAG — same 120-token budget, 32 facts, two
> contradictions. Both answer correctly today. But look at the memory layer:
> naive RAG leaves **2 stale facts** sitting in the context window, betting the
> LLM untangles them. Mnemosyne resolves them at write-time — **zero stale facts
> reach the context** — using 13% fewer tokens."

Show: the results table, highlight the "0 vs 2" row.

### 2:20–2:50 — Architecture + Alibaba Cloud
Show: `docs/architecture.svg`.
> "It's built entirely on Alibaba Cloud — Qwen-plus for reasoning and the
> contradiction judge, text-embedding-v3 for retrieval, and Alibaba OSS to
> persist the memory store across restarts. FastAPI backend, single-file React
> inspector."

### 2:50–3:00 — Close
> "Mnemosyne — memory that knows what's still true. Track 1, MemoryAgent.
> Code's open-source on GitHub."

Show: the repo URL on screen.

---

## Tips
- Reset memory right before recording so the inspector starts clean.
- Pre-run the benchmark once so the numbers are warm (avoids dead air on API latency).
- Keep narration tight — practice once to land under 3:00.
- No copyrighted music. Use silence or royalty-free audio.
