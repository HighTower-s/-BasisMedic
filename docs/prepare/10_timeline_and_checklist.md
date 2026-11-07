# 10 — แผนงาน, Commit plan, README/Report outline, Demo script

## 1. แผน 4 สัปดาห์ (ปรับตาม deadline จริงของวิชา)
| สัปดาห์ | งาน | ผลลัพธ์ที่ต้องได้ |
|---|---|---|
| **1 — Setup + Knowledge + Eval** | ส่ง proposal (11_proposal.md) · สร้าง GitHub repo · ทดสอบ proxy (chat, bge-m3, **native tool calling**) · อ่าน primer + เรียน SAP Learning บทที่ระบุ · เขียน runbook 16 ไฟล์ · เขียน `tcodes.json` · **เขียน eval dev 10 + test 30** | repo มี data + eval set; รู้แล้วว่า tool calling ใช้ได้ไหม |
| **2 — Retrieval** | chunk (2 แบบ) · ingest + embed cache · BM25 · hybrid RRF · `run_retrieval.py` · ทำ E1, E2, E3 | ตาราง retrieval + กราฟ min_score |
| **3 — Agent + Structured output** | tools + dispatch + guardrails · loop (Phase 1) · formatter + repair (Phase 2) · post-check · CLI · unit tests · `run_e2e.py` + baselines (E4) | ตาราง e2e + failures.jsonl |
| **4 — Web + Deliver** | วัน 1–2: `on_event` + FastAPI REST/SSE + tests · วัน 3–5: Next.js (Composer → TriageCard → StepTimeline → Sidebar) · วัน 6–7: README, รายงาน 4–8 หน้า, อัด demo บนหน้าเว็บ, ซ้อมตอบ, ตรวจ 01 checklist | ส่ง 3 ชิ้น |

### Day 1 (ทำวันนี้ได้เลย)
1. ส่ง proposal ให้อาจารย์ + ถามคำถาม 4 ข้อใน `01_requirements_checklist.md` ส่วน E
2. สร้าง repo `basis-medic` (public) → commit `README.md` สั้นๆ + `.gitignore` + `.env.example` (จาก `templates/`)
3. `uv init` + `uv add openai pydantic numpy rank-bm25` → รัน smoke test 3 ข้อใน `03_tech_stack.md` ส่วน 5
4. อ่าน `06_sap_basis_primer.md` + เปิด ST22/SM37 ใน resource

## 2. Commit plan (history ต้องแสดงงานทีละขั้น — rubric ดู)
```
chore: project skeleton, env example, gitignore
data: add runbooks R01-R04 (memory, timeout)
data: add runbooks R05-R16 + tcodes allow-list
eval: add dev/test cases (40) + metrics module
feat(retrieval): fixed & section chunking + ingest with embedding cache
feat(retrieval): BM25 tokenizer + hybrid RRF search + min_score gate
eval: E1 chunking ablation results
eval: E2 retrieval mode results, E3 min_score sweep
feat(agent): tool registry, arg validation, dispatch
feat(agent): agent loop with max_steps + repeat guard
feat: formatter with Pydantic validation + repair loop + fallback
feat: CLI + triage service layer
test: unit tests (tools, extract_json, metrics, normalize)
eval: end-to-end eval + baselines + failure log
feat: on_event progress callback in service + agent loop
feat(api): FastAPI /api/triage + 422/502/504 handling + tests
feat(api): SSE /api/triage/stream with error frames
feat(web): Next.js scaffold + rewrites + composer + triage card
feat(web): streaming step timeline + stop button
feat(web): sidebar history (localStorage) + sample logs
docs: README results, architecture diagram, limitations
```

## 3. README outline (≈15 + 25 คะแนน)
1. **BasisMedic** — 1 ประโยค + GIF/ภาพ CLI
2. Problem & users
3. Quickstart (คัดลอกแล้วรันได้): `uv sync` → `cp .env.example .env` → `uv run python -m app.retrieval.ingest` → `uv run python -m app.cli examples/tsv_dump.log` → `uv run python -m eval.run_all`
4. Architecture diagram + ตาราง "course family → ไฟล์"
5. Data: runbooks (เขียนเอง + refs), tcodes, eval set (synthetic — บอกตรงๆ)
6. Evaluation: ตารางผล retrieval + e2e + baseline + min_score plot
7. Design decisions (3–5 ข้อ)
8. Safety (allow-list, validation, untrusted log, no secrets)
9. Limitations & next steps
10. Course/credits: reference app (cite), แหล่งข้อมูล SAP

## 4. Report outline (PDF 4–8 หน้า, 70 คะแนน)
| ส่วน | หน้า | เนื้อหา |
|---|---|---|
| 1. Problem & users | 0.5 | ปัญหา on-call Basis มือใหม่, user story |
| 2. Design | 1.5–2 | architecture diagram, 2 phases, tools, hybrid retrieval, guardrails, **ทำไม** (อ้างอิง lecture) |
| 3. Data | 0.5 | runbook 16 ไฟล์, tcodes, eval set (การแบ่ง easy/medium/hard/Thai/OOS/mixed, dev/test, การกัน bias) |
| 4. Evaluation method | 1 | metrics, baselines, การทดลอง E1–E4 ทีละตัวแปร |
| 5. Results | 1.5 | ตาราง + กราฟ + **วิเคราะห์ตรงไปตรงมา** + failure cases 2–3 ข้อ |
| 6. Limitations & next steps | 0.5 | synthetic, corpus เล็ก, โมเดลเล็ก, single-label |
| 7. References | 0.25 | lecture, reference app, SAP Help/Learning |

## 5. Demo video script (4–5 นาที)
| เวลา | ฉาก | พูด |
|---|---|---|
| 0:00–0:30 | สไลด์/README | ปัญหา + ผู้ใช้ + BasisMedic ทำอะไร |
| 0:30–1:00 | diagram | 2 phases, hybrid retrieval, tools 2 ตัว |
| 1:00–2:15 | **Success** `--trace` กับ dump TSV_TNEW | ชี้ tool calls, evidence, JSON, sources, T-code |
| 2:15–3:00 | **OOS** (HANA log volume full) | min_score gate → out_of_scope ไม่เดา |
| 3:00–3:45 | **Failure** (mixed lock+update หรือ Thai hard case) | อธิบายว่าทำไมผิด (retrieval หรือ schema) + จะแก้อย่างไร |
| 3:45–4:30 | `eval.run_all` + ตาราง | 1 ตัวเลขสำคัญ (เช่น hybrid vs dense recall@3) + 1 design choice |

## 6. ซ้อมตอบตอน demo สด (in-person)
- อาจารย์ให้ input ใหม่ → รัน `--trace` แล้วอ่าน trace ให้ฟังว่าโมเดลค้นอะไร ได้อะไร
- "อธิบาย 1 design choice" → hybrid search (มีตัวเลข E2) หรือ 2 phases (L10 หน้า 8)
- "อธิบาย 1 ตัวเลข" → recall@3 / MRR / category accuracy: นิยาม + คิดยังไง + n เท่าไร + baseline เท่าไร
- เตรียมเปิด `app/agent/tools.py` ชี้ allow-list + validation

## 7. Risk register
| ความเสี่ยง | สัญญาณ | แผนรับมือ |
|---|---|---|
| gemma ไม่เรียก tool / args เพี้ยน | smoke test วันแรก | text protocol แบบ reference / tool_choice / prompt ชัดขึ้น |
| proxy ล่มช่วงใกล้ส่ง | | embedding cache, อัด demo ล่วงหน้า, eval ผลเก็บใน repo |
| runbook ไม่ทัน | สัปดาห์ 1 ยังไม่ครบ | ลดเหลือ 8 runbook + เขียน limitation |
| ตัวเลขสูงเกินจริง (เช่น recall 1.0) | ผล E2 | เพิ่ม hard/Thai cases, ให้เพื่อนเขียนเคส |
| scope บวม | อยากเพิ่ม UI/MCP | ทำหลัง 01 checklist ครบเท่านั้น |
| หน้าเว็บไม่ทัน | สัปดาห์ 4 วันที่ 5 ยังไม่เสร็จ | ตัด sidebar → ตัด streaming (ใช้ REST + spinner) → กลับไปใช้ CLI; แกนและ eval ต้องเสร็จก่อน |

## 8. สำหรับสมัครฝึกงาน (หลังส่งงาน)
- Resume: *"BasisMedic — RAG + tool-calling agent that maps SAP error logs (ST22/SM37/STMS…) to T-codes and runbook steps; hybrid BM25+embedding retrieval, evaluated on 30 hand-written incidents (recall@3 = __ vs BM25 __)."*
- Pin repo บน GitHub, ใส่ภาพ diagram + ตารางผลใน README
- เตรียมเล่า: ศึกษา incident 8 ประเภท → ทำ runbook → วัดผล → เจอ failure อะไร เรียนรู้อะไรเกี่ยวกับ Basis
