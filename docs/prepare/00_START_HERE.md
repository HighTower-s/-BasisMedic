# BasisMedic — ชุดเตรียมโปรเจกต์ (เริ่มอ่านที่นี่)

> **BasisMedic**: วาง error log ของ SAP (dump, job ล้ม, transport ไม่ผ่าน ฯลฯ) → ได้ประเภทปัญหา, T-code ที่ควรเปิดตามลำดับ, ขั้นตอนตรวจ และแหล่งอ้างอิง runbook — เป็น RAG + tool-calling agent ที่ **วัดผลได้**

## ลำดับการอ่าน
| ลำดับ | ไฟล์ | อ่านเพื่อ | เวลา |
|---|---|---|---|
| 1 | `01_requirements_checklist.md` | รู้ว่าอาจารย์ต้องการอะไร + เราตอบทุกข้ออย่างไร | 15 นาที |
| 2 | `06_sap_basis_primer.md` | พื้นฐาน SAP/Basis (ไม่เคยรู้มาก่อนก็อ่านได้) | 45 นาที |
| 3 | `07_short_dump_and_incidents.md` | การจัดการ short dump (ST22) + incident 8 ประเภท = วัตถุดิบ runbook | 60 นาที |
| 4 | `02_design.md` | ออกแบบระบบละเอียด (scope, I/O schema, components, guardrails, design decisions) | 30 นาที |
| 5 | `04_system_flow.md` | flow ตั้งแต่ต้นจนจบ (indexing / runtime / eval) + diagram | 20 นาที |
| 6 | `03_tech_stack.md` | stack, config, โครงสร้าง repo, smoke test วันแรก | 10 นาที |
| 7 | `05_course_techniques_map.md` | เทคนิคแต่ละอย่างมาจาก lecture/หน้าไหน + คำถามที่อาจารย์น่าจะถาม | 30 นาที + อ่านสไลด์ |
| 8 | `09_eval_plan.md` | eval set, metrics, baselines, การทดลอง E1–E4 | 20 นาที |
| 9 | `10_timeline_and_checklist.md` | แผน 4 สัปดาห์, commit plan, README/report outline, demo script | 15 นาที |
| 10 | `08_resources.md` | ลิงก์ SAP Help / SAP Learning / community ที่ตรวจแล้ว | ใช้ตอนเขียน runbook |
| 11 | `11_proposal.md` | proposal ส่งอาจารย์ (EN + TH) | 5 นาที |
| 12 | `12_web_ui_nextjs.md` | หน้าเว็บ Next.js แบบแชต: API/SSE contract, UI spec, โครงโฟลเดอร์, ลำดับการทำ | 20 นาที |

## โฟลเดอร์ `templates/` (คัดลอกไปใช้ใน repo)
| ไฟล์ | ใช้เป็น |
|---|---|
| `runbook_TEMPLATE.md` | แม่แบบ runbook (หัวข้อตายตัว 6 หัวข้อ — chunker ตัดตามนี้) |
| `mem_tsv_tnew_page_alloc.example.md` | ตัวอย่าง runbook เต็ม 1 ไฟล์ (R01) |
| `tcodes.json` | allow-list T-code 51 ตัว พร้อมคำอธิบาย (ใช้กับ `lookup_tcode` และ post-check) |
| `eval_cases.example.jsonl` | ตัวอย่างเคส dev 8 ข้อ (ทุก format/ความยาก/ไทย/OOS) |
| `env.example` → `.env.example` | config ทั้งหมด (ห้าม commit `.env`) |
| `gitignore.txt` → `.gitignore` | |
| `pyproject.toml` | dependencies สำหรับ `uv sync` |

## สรุปการออกแบบใน 6 บรรทัด
1. Families: **#1 structured output, #2 RAG + citations, #3 retrieval eval, #4 agent loop, #6 FastAPI + SSE + หน้าเว็บ Next.js** — เกินขั้นต่ำ 3 และมี eval + agentic ครบ
2. Corpus: runbook ~16 ไฟล์ที่เขียนเอง (8 category × 2) + `tcodes.json`
3. Retrieval: hybrid BM25 + bge-m3 (RRF) เพราะ error code เป็นคำหายาก (L8 หน้า 31) + min_score gate สำหรับ out_of_scope
4. Agent: Phase 1 native tool calling (`search_runbook`, `lookup_tcode`, max 5 steps) → Phase 2 formatter JSON + Pydantic + repair (แยกเพราะ L10 หน้า 8)
5. Eval: dev 10 + test 30; recall@3, MRR, category accuracy, T-code recall; baselines BM25-only / dense-naive / LLM-no-RAG
6. Measured improvements: chunk fixed→section, dense→hybrid, min_score sweep (ทีละอย่าง)

## ควรทำอะไรเพิ่มอีก (นอกจากที่เตรียมไว้)
1. **ส่ง proposal + ถามอาจารย์ 4 ข้อ** (ใช้ synthetic log ได้ไหม, runbook เขียนเองถือเป็น raw data ไหม, CLI พอไหม, dev/test split) — ก่อนลงมือหนัก
2. **ทดสอบ proxy วันแรก** โดยเฉพาะ native tool calling ของ gemma — เป็นความเสี่ยงอันดับ 1 ของการออกแบบนี้
3. **สร้าง GitHub repo วันนี้และ commit บ่อยๆ** — history ถูกให้คะแนน
4. **เขียน eval set ก่อนโค้ด** — และให้เพื่อนช่วยเขียน 5 ข้อเพื่อลด bias
5. **เรียน SAP Learning บทที่ระบุใน 08** ระหว่างเขียน runbook — ได้ทั้งงานและความรู้สัมภาษณ์
6. (ไม่บังคับ) ลองรัน SAP trial (Docker) ถ้าเครื่องไหว — เก็บภาพ ST22/SM37 จริงไว้ใช้ในรายงาน/สัมภาษณ์
7. จด **decision log** สั้นๆ ทุกครั้งที่เปลี่ยนการออกแบบ (ใช้เขียนรายงาน + ตอบตอน demo)
8. หลังส่งงาน: ใส่โปรเจกต์ใน resume + pin repo (ดู `10_timeline_and_checklist.md` ส่วน 8)
