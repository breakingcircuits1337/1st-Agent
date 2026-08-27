# 1st Agent Multi‑Agent Framework Plan

## 1. Overview
Build a lightweight orchestrator that delegates user intent to specialized **Needle** agents that run fine‑tuned models.  The high‑level strategy is produced by Moonshot Kimi‑K2.6 via its API key.  Everything stays open‑source, runs CPU‑only on the user’s device, and keeps model weights local.

## 2. Folder structure
```
1st agent/
├─ orchestrator.py          # Main orchestration logic
├─ agents/
│  ├─ __init__.py
│  ├─ weather_agent.py    # Specialized Needle + tools
│  ├─ news_agent.py
│  └─ db_agent.py
├─ datasets/
│  ├─ weather.jsonl
│  ├─ news.jsonl
│  └─ db.jsonl
├─ models/
│  ├─ weather.cact        # Fine‑tuned Needle weights
│  ├─ news.cact
│  └─ db.cact
├─ README.md
└─ requirements.txt
```

## 3. Development steps
1. **Environment** – Ensure pip, Python 3.10+, NVidia driver, and `cactus‑needle[gpu]` installed.
2. **Base repo** – Clone the 1st‑Agent repo locally and install it as an editable package.
3. **Tools** – For each domain write a small set of `@tool`‑decorated functions (beautiful as in `tests/test_tools.py`).
4. **Fine‑tune** – Use the CLI:
   ```bash
   needle finetune datasets/weather.jsonl --epochs 10 --lora-rank 16 --out models/weather.cact
   needle finetune datasets/news.jsonl --... --out models/news.cact
   needle finetune datasets/db.jsonl    --... --out models/db.cact
   ```
5. **Orchestrator** – Code `orchestrator.py`:
   * Load Moonshot Kimi via `mimiai` API key.
   * Very simple dispatch (keyword or LLM classifier) picks an agent.
   * Pass the user query to the chosen `Needle` agent; gather the JSON output.
   * Wrap the JSON in a system prompt and ask Kimi to produce a natural‑language answer.
6. **Run** – `python orchestrator.py`.  Optional: expose a tiny HTTP API (FastAPI) for a token‑based UI.
7. **Test** – Write unit tests for dispatch logic and end‑to‑end flows.

## 4. Important details
* **Process isolation** – Spin each `Needle` instance in a separate process if you anticipate high concurrency.  The compiled library keeps a global state; separate processes avoid race conditions.
* **Dynamic loading** – Load the `.cact` files at runtime; no need to rebuild the binary.  Expose `models/` folder under the project.
* **Security** – Store the Kimi key in `~/.kimi_secret` or as an environment variable; never commit it.
* **Extensibility** – Add a new domain by adding a new `*_agent.py`, JSONL dataset, fine‑tune command, and a small entry in the dispatch table.

## 5. Deliverables
* The folder structure above, ready to run locally.
* `requirements.txt`: `cactus-needle[gpu]`, `mimiai`, `pydantic`.
* Example datasets and demo fine‑tuned weights.
* Minimal unit tests in `tests/`.

---
*Prepared by Hermes Agent, now powered by Moonshot Kimi‑K2.6.*
