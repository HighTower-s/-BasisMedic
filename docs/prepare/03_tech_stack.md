# 03 — Tech Stack

หลักการเลือก: **ใช้ของเดียวกับที่วิชาสอน + reference app ใช้** (อาจารย์อ่านง่าย, เราตอบคำถามได้, ลดความเสี่ยงตอนรันจาก README) และ **ไม่ใช้ LLM framework** (LangChain/LlamaIndex) เพราะวิชาสอนเขียน loop เอง และ rubric ให้คะแนนการเข้าใจ loop

## 1. ตาราง stack

| ชั้น | เลือก | ใช้ทำอะไร | ทำไม / อ้างอิง |
|---|---|---|---|
| ภาษา | **Python 3.12** | ทั้งหมด | reference app `requires-python >=3.12` |
| จัดการ env/deps | **uv** | `uv sync`, `uv run --env-file .env …` | วิชาใช้ (L1 หน้า 17) |
| LLM client | **openai** SDK (`OpenAI()`) | chat + embeddings ผ่าน class proxy | ข้อกำหนดบังคับ |
| Chat model | **gemma-4-E4B-it** | agent + formatter | ข้อกำหนดบังคับ; ⚠ proxy **ไม่สนใจ** `response_format` (L2 หน้า 8, 10) → ต้อง validate+repair เอง |
| Embedding | **bge-m3** (1024-d, multilingual EN+TH) ผ่าน proxy เดียวกัน | dense retrieval | L5 หน้า 15, 18 — ใช้โมเดลเดียวทั้ง index และ query (L5 หน้า 41) |
| Keyword search | **rank-bm25** (`BM25Okapi`) + tokenizer เขียนเอง | sparse retrieval | L8 หน้า 30–33; ต้องการ exact match error code |
| Fusion | RRF เขียนเอง (~8 บรรทัด, k=60) | hybrid | L8 หน้า 34–38 |
| Vector store | **numpy** + ไฟล์ `chunks.jsonl` + `embeddings.npy` | brute-force cosine | ~100 chunks → ไม่ต้องใช้ DB (L5 หน้า 29, 31); เปลี่ยนเป็น SQLite แบบ reference ก็ได้ |
| Validation | **Pydantic v2** | request, `TriageResult`, tool args | L2 หน้า 11–13, 32; L3 หน้า 14 |
| Served interface | **FastAPI + uvicorn** | `POST /api/triage`, `POST /api/triage/stream` (SSE) | L3, L4; family #6 + layering |
| Frontend | **Next.js (App Router) + TypeScript + Tailwind** | หน้าแบบแชต | ดู `12_web_ui_nextjs.md`; L4 สอน SvelteKit แต่หลักเดียวกัน |
| Dev runner | `concurrently` / docker compose | รัน API + เว็บด้วยคำสั่งเดียว | ลดความเสี่ยงเกณฑ์ "รันได้จาก README" |
| Test | **pytest** | unit test (mock LLM) | L3 หน้า 26–28 — quality ใช้ eval ไม่ใช่ unit test |
| Eval | สคริปต์ Python เอง (`eval/`) | metrics + ตาราง | L8 หน้า 14 (pattern เดียวกับ reference `eval/eval.py`) |
| Report | Markdown → PDF (หรือ Google Docs/Word) | รายงาน 4–8 หน้า | |
| Diagram | Mermaid / draw.io | architecture diagram | |
| Demo | OBS Studio / Xbox Game Bar (Windows) | อัดจอ 3–6 นาที | |
| Repo | GitHub public | ส่งงาน | |

**ไม่ใช้ (และเหตุผลที่ตอบได้):** pgvector/Postgres (ไม่จำเป็นที่ขนาดนี้, เพิ่ม setup), LangChain (ซ่อน loop), web search/SQL/MCP (ไม่ช่วยโจทย์ เพิ่มความเสี่ยง)

## 2. Dependencies (`pyproject.toml`)
ดูไฟล์ตัวอย่าง `templates/pyproject.toml`
```
openai>=1.40, pydantic>=2.7, numpy>=1.26, rank-bm25>=0.2.2
[optional] fastapi>=0.115, uvicorn[standard]>=0.30
[dev] pytest>=8.0
```

## 3. Config (env) — ห้าม hard-code
| ตัวแปร | ค่าเริ่มต้น | หมายเหตุ |
|---|---|---|
| `OPENAI_BASE_URL` | `https://llm.nat-d.uk/v1` | ตามที่ reference app ใช้ — ตรวจกับหน้า Profile ของวิชาอีกครั้ง |
| `OPENAI_API_KEY` | (ของเรา) | **อยู่ใน `.env` เท่านั้น** |
| `CHAT_MODEL` | `gemma-4-E4B-it` | |
| `EMBED_MODEL` | `bge-m3` | |
| `RETRIEVAL_MODE` | `hybrid` | `dense` / `bm25` / `hybrid` — ใช้ทำ ablation |
| `CHUNK_STRATEGY` | `section` | `fixed` / `section` |
| `TOP_K` | `3` | |
| `MIN_SCORE` | จูนจาก dev set | reference ใช้ 0.40 สำหรับ corpus ของมัน — ของเราต้องวัดเอง |
| `MAX_STEPS` | `5` | |

## 4. โครงสร้าง repo (เป้าหมาย)
```
basis-medic/
├─ README.md                 # what/why/run/eval/results/limitations
├─ pyproject.toml  uv.lock
├─ .env.example   .gitignore
├─ app/
│  ├─ config.py              # อ่าน env ที่เดียว
│  ├─ llm.py                 # chat(), embed()  ← ที่เดียวที่เรียก proxy
│  ├─ schemas.py             # TriageRequest, TriageResult, Hit, ToolArgs
│  ├─ normalize.py           # ตัด noise + ดึง error code/RC/T-code ด้วย regex
│  ├─ retrieval/
│  │  ├─ chunk.py  ingest.py  bm25.py  search.py  store.py
│  ├─ agent/
│  │  ├─ tools.py            # registry + allow-list + validation
│  │  ├─ loop.py             # Phase 1
│  │  └─ formatter.py        # Phase 2 (JSON + repair)
│  ├─ triage_service.py      # service layer: orchestrate ทั้งหมด
│  ├─ cli.py                 # edge: python -m app.cli < log.txt
│  └─ api.py                 # edge: FastAPI router (REST + SSE)
├─ web/                      # Next.js chat UI (ดู 12_web_ui_nextjs.md)
├─ data/
│  ├─ runbooks/*.md          # corpus (เขียนเอง + URL อ้างอิง)  ← commit
│  ├─ tcodes.json            # allow-list T-code
│  └─ index/                 # สร้างจาก ingest (gitignore ได้ หรือ commit เพื่อ reproducibility)
├─ eval/
│  ├─ cases_dev.jsonl  cases_test.jsonl
│  ├─ metrics.py  run_retrieval.py  run_e2e.py  run_all.py
│  └─ results/               # json + markdown table ← commit
├─ tests/                    # pytest: tools validation, metrics, extract_json, normalize
└─ docs/  architecture.png  report.pdf  demo_inputs/
```

## 5. ทดสอบ proxy ก่อนเริ่ม (Day 1) — สำคัญ
1. `smoke_test.py` แบบ L1 หน้า 18 → ได้ "setup OK"
2. `embeddings.create(model="bge-m3", input=["a","b"])` → ได้ 2 เวกเตอร์ 1024 มิติ
3. ส่ง `tools=[search_runbook spec]` + log ตัวอย่าง → ดูว่ามี `message.tool_calls` จริงไหม, `arguments` เป็น JSON string ที่ parse ได้ไหม (L10 หน้า 7, 24)
   - ถ้าไม่เสถียร → ใช้ text protocol แบบ reference app (`agent/loop.py`) เป็นแผนสำรอง
