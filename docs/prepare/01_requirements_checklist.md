# 01 — ตรวจความครบตามข้อกำหนดของอาจารย์ (Requirements Checklist)

> ใช้ไฟล์นี้เป็น "ตาราง checklist" ตลอดโปรเจกต์ ทุกข้อต้องมี **หลักฐาน** (ไฟล์/คำสั่ง/ตัวเลข) ที่ชี้ได้ตอน demo
> อ้างอิงข้อกำหนดจากเอกสาร Project ของวิชา (Capstone 200 คะแนน)

## A. ขั้นต่ำที่ต้องมี (ถ้าขาด = โดน cap คะแนน)

| # | ข้อกำหนด | BasisMedic ทำอย่างไร | หลักฐาน |
|---|---|---|---|
| A1 | เรียก LLM ผ่าน class proxy `from openai import OpenAI`, `OpenAI()`, `model="gemma-4-E4B-it"` | `app/llm.py` เป็นที่เดียวที่เรียกโมเดล; อ่าน `OPENAI_API_KEY`/`OPENAI_BASE_URL` จาก env | โค้ด + `.env.example` |
| A2 | ≥ 3 capability families | ใช้ **5 กลุ่ม**: #1 structured output, #2 RAG + citations, #3 retrieval eval, #4 agent loop, #6 served interface (FastAPI REST + SSE + หน้าเว็บ Next.js — ดู `12_web_ui_nextjs.md`) | ตารางใน README |
| A3 | ต้องมี **#3 evaluation** | `eval/run_retrieval.py` (recall@3, MRR) + `eval/run_e2e.py` (category acc, T-code recall, OOS refusal) | `eval/results/*.json` |
| A4 | ต้องมี agentic family อย่างน้อย 1 (#4 หรือ #5) | **#4** agent loop: native function calling, tools = `search_runbook`, `lookup_tcode`; stop = ไม่มี tool call + `MAX_STEPS=5` + กันเรียกซ้ำ | `app/agent/loop.py` + trace log |
| A5 | Evaluation จริง: test set + metric เชิงปริมาณ ≥ 1 + **baseline** | 30 test cases (+10 dev), metric: recall@3, MRR, category accuracy, T-code recall; baseline: BM25-only และ LLM-no-retrieval | `eval/cases_test.jsonl`, ตารางผล |

## B. เงื่อนไข "ต้องต่างจาก reference app" (kmitl-llm-app-demo)

| # | ข้อกำหนด | BasisMedic | หลักฐาน |
|---|---|---|---|
| B1 | ใช้ corpus ที่ reference ตอบไม่ได้ (โดเมนของเราเอง) + **commit raw data** | runbook SAP Basis ~16 ไฟล์ ที่เราเขียนเอง (สรุปจากเอกสารสาธารณะ + ใส่ URL อ้างอิง) อยู่ใน `data/runbooks/` | ไฟล์ใน repo |
| B2 | eval set ของเราเอง ~30 ข้อ + **ชนะ baseline ที่ระบุชื่อ** + reproducible | log 30 ข้อเขียนเอง (มี easy/medium/hard/out-of-scope); รันซ้ำได้ด้วย `uv run python -m eval.run_all` | `eval/results/` |
| B3 | **หนึ่ง measured improvement** เทียบ naive default (min_score / chunk size / retrieval choice) พร้อมตัวเลขก่อน/หลัง | ทำ 3 การทดลอง (ทีละอย่าง): (1) chunk 800-char (ค่า default ของ reference) → chunk ตามหัวข้อ, (2) dense-only → hybrid BM25+dense (RRF), (3) min_score sweep สำหรับ OOS | ตาราง ablation ในรายงาน |
| B4 | Defend live: รันกับ input ใหม่ที่อาจารย์ให้ + อธิบาย 1 design choice + 1 ตัวเลข eval | เตรียม "คำตอบ 30 วินาที" ไว้ใน `10_timeline_and_checklist.md` | ซ้อมพูด |

**จุดต่างที่ต้องพูดให้ชัด (ใช้ตอบอาจารย์):**
1. Input ของเราเป็น **error log/dump** ไม่ใช่คำถาม → ต้องมี normalize + query construction จาก log
2. ใช้ **hybrid search (BM25 + bge-m3, RRF)** เพราะ error code เช่น `TSV_TNEW_PAGE_ALLOC_FAILED`, `RC=8` เป็น "exact rare token" (L8 หน้า 30–31) — reference ใช้ dense อย่างเดียว
3. ใช้ **native tool calling** + เครื่องมือ 2 ตัว (reference ใช้ text protocol ACTION/ANSWER และ tool เดียว)
4. Output เป็น **structured triage JSON** (category / T-codes / steps / sources) ผ่าน Pydantic + repair loop — reference ตอบเป็น prose
5. Eval ของเรามี **end-to-end** (ถูก category ไหม, แนะนำ T-code ถูกไหม, ปฏิเสธ out-of-scope ได้ไหม) ไม่ใช่แค่ retrieval

## C. Deliverables และคะแนน

### Q1 — GitHub repo (90 คะแนน)
| เกณฑ์ (คะแนนโดยประมาณ) | สิ่งที่ต้องทำ | ✔ |
|---|---|---|
| รันได้จาก README (≈25) | README มี: ติดตั้ง (`uv sync`, `npm install`), ตั้ง `.env`, `ingest`, รัน API + เว็บ (มีคำสั่งเดียว `npm run dev:all`), รัน CLI, รัน eval — คนอื่น clone แล้วรันตามได้ภายใน 5–10 นาที | ☐ |
| Code quality & layering (≈25) | แยกชั้น: edge (CLI/FastAPI router) → service (`triage_service`) → repository (`store`, `runbooks`); ไม่มี logic ปนใน router (L3 หน้า 19) | ☐ |
| ใช้ LLM/tools อย่างถูกและปลอดภัย (≈25) | env-based config, **validated structured output** (Pydantic + repair), **allow-listed tool calls**, validate args, max_steps, ไม่มี secret ใน repo | ☐ |
| README/repo clarity (≈15) | README มีแผนภาพ, ตาราง family→ไฟล์, ตารางผล eval, ข้อจำกัด; commit history ค่อยๆ เพิ่ม (ห้าม commit ก้อนเดียวตอนท้าย) | ☐ |

### Q2 — Report PDF 4–8 หน้า (70 คะแนน)
☐ ปัญหา + ใครใช้ ☐ architecture diagram + เทคนิคที่ใช้และ "ทำไม" ☐ test set / metric / baseline ☐ ตารางผล + วิเคราะห์ตรงไปตรงมา + **failure case ≥ 1** ☐ limitations / next steps
> "An honest, well-analysed evaluation scores higher than an inflated one" — อย่าแต่งตัวเลข ใส่ข้อที่ผิดด้วย

### Q3 — Demo video 3–6 นาที (40 คะแนน)
☐ รันกับ input จริง ☐ success 1 เคส ☐ **failure 1 เคส** ☐ มีเสียงบรรยาย ☐ unlisted YouTube/Drive

## D. Safety / quality checklist (rubric ข้อ "correct & safe use")

- [ ] ไม่มี API key ใน repo (`.env` อยู่ใน `.gitignore`; มี `.env.example`)
- [ ] `temperature=0` ทุกจุดที่ประเมินผลหรือควบคุม flow (L1 หน้า 19–23, L10 หน้า 32)
- [ ] tool name ต้องอยู่ใน allow-list; args ผ่าน Pydantic/regex ก่อนรัน; error คืนเป็น string ให้โมเดลอ่าน (L10 หน้า 31, 36)
- [ ] `MAX_STEPS` + ตรวจ query ซ้ำ (L10 หน้า 34, L11 หน้า 14)
- [ ] log ของผู้ใช้ถูกครอบ `<log>…</log>` และบอกว่าเป็น data ไม่ใช่คำสั่ง (L1 หน้า 32, L12 หน้า 34–36)
- [ ] ผล tool ถูก fence เป็น untrusted data (L14 หน้า 33)
- [ ] citation สร้างจากโค้ด (chunk ที่ tool คืนจริง) ไม่เชื่อ model (L11 หน้า 8, L12 หน้า 24)
- [ ] T-code ทุกตัวในผลลัพธ์ต้องอยู่ใน `tcodes.json` ไม่งั้นติด `unverified`
- [ ] JSON ผ่าน Pydantic; ถ้าพัง → local repair → re-ask ≤ 2 ครั้ง → fallback ที่ชัดเจน (L2 หน้า 22–25)
- [ ] min_score floor: ไม่มีอะไรผ่าน → ตอบ out_of_scope โดย **ไม่เรียก LLM ให้เดา** (L6 หน้า 24–25, 29)

## E. คำถามที่ควรถามอาจารย์ตอนส่ง proposal (sanity-check)
1. ใช้ log ที่ **สร้างขึ้นเอง (synthetic)** ตามรูปแบบจริงได้ไหม (เพราะไม่มีระบบ SAP จริง) — เราจะระบุในรายงานชัดเจน
2. Corpus เป็น runbook ที่ **เขียนเองโดยสรุปจากเอกสารสาธารณะ** + ลิงก์อ้างอิง ถือว่าเป็น "raw data" ได้ไหม
3. แจ้งว่าจะมีหน้าเว็บ Next.js + FastAPI (SSE) — โอเคไหมที่ฝั่งเว็บใช้ Next.js แทน SvelteKit ที่สอนใน L4
4. Eval 30 test + 10 dev (ใช้ dev จูน min_score) โอเคไหม

## F. หน้าเว็บ (เพิ่ม 7 พ.ย.)
- [ ] API key อยู่ใน FastAPI เท่านั้น browser ไม่เรียก proxy ตรง (L3 หน้า 2–4)
- [ ] `POST /api/triage` คืน 422/502/504 ถูกต้อง, ไม่ leak stack trace (L3 หน้า 29–31)
- [ ] SSE: 1 frame = 1 JSON, มี error frame, client ใช้ buffer (L4 หน้า 19–20, 28–33)
- [ ] CLI ยังใช้ได้ (ทางสำรองตอน demo สด)
- [ ] ไม่ใช้โลโก้/แบรนด์ของ Gemini, ChatGPT, Claude
