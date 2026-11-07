# 05 — เทคนิคที่ใช้ ↔ สไลด์ที่ต้องอ่าน (Lecture Map)

> เลขหน้า = หน้าใน PDF ของไฟล์ `lec/llm-XX-*.pdf` (นับหน้าแรกเป็น 1)
> ลำดับการอ่านแนะนำ: **L2 → L5 → L6 → L8 → L10 → L11** (ที่เหลืออ่านเฉพาะหน้าที่ระบุ)
> ⭐ = สำคัญมาก ต้องอธิบายได้ตอน demo

## สรุปเร็ว: BasisMedic ใช้อะไรจากไหน

| ส่วนของ BasisMedic | เทคนิค | Lecture / หน้า |
|---|---|---|
| เรียกโมเดล, `.env` | chat API, `OpenAI()`, env vars | L1 หน้า 10, 13, 17–18 |
| temperature 0 | sampling knobs | ⭐ L1 หน้า 19–23; L10 หน้า 32 |
| system prompt, few-shot ใน formatter | prompting patterns | L1 หน้า 24–29 |
| ครอบ log ด้วย `<log>` | delimit data | ⭐ L1 หน้า 32 |
| "ถ้าไม่มีใน runbook ให้บอกว่าไม่ครอบคลุม" | give the model an out, grounding | L1 หน้า 33–34, 36 |
| แยก Phase 1 / Phase 2 | decompose → chain | L1 หน้า 35 |
| `TriageResult` Pydantic | schema, Pydantic, enum/Optional | ⭐ L2 หน้า 11–13, 32–33 |
| proxy ไม่สนใจ `response_format` | JSON mode ใช้ไม่ได้บน proxy → prompt+validate+repair | ⭐ L2 หน้า 8–10, 38 |
| `extract_json`, brace counter | local repair | L2 หน้า 17, 24, 29–31 |
| semantic checks (OOS ⇒ ไม่มี T-code) | valid JSON ≠ valid data | L2 หน้า 18–20 |
| repair loop ≤ 2 + fallback | repair loop, cap | ⭐ L2 หน้า 21–26 |
| `TriageRequest` max_length, 422 | Pydantic ที่ขอบ | L3 หน้า 14–16, 22 |
| CLI/API → service → repository | layering | ⭐ L3 หน้า 19–20 (rubric ≈25 คะแนน) |
| unit test แบบ mock LLM | testing code that calls a model | L3 หน้า 26–28 |
| 502/504 ตอน proxy ล่ม | errors are part of the API | L3 หน้า 29–31 |
| (optional) SSE streaming | SSE | L4 หน้า 12–30 |
| bge-m3, batch, 1024-d | embeddings | ⭐ L5 หน้า 15, 18, 20, 39 |
| คะแนน cosine "แออัด" | rank, don't threshold blindly | L5 หน้า 19 |
| chunk size/overlap, metadata | chunking | ⭐ L5 หน้า 21–25; L6 หน้า 18 |
| brute-force numpy พอ | when ANN is needed | L5 หน้า 29, 31 |
| debug retrieval | symptom → fix | L5 หน้า 40–41 |
| retrieve-then-read, indexing | RAG pipeline | L6 หน้า 6–9 |
| numbered evidence + citation | prompt assembly, citations | ⭐ L6 หน้า 12, 20–21 |
| min_score gate ⇒ out_of_scope | min_score floor | ⭐ L6 หน้า 24–25, 29, 32, 37 |
| top-k = 3 | lost in the middle | L6 หน้า 13, 26, 28 |
| dedupe ตาม doc | dedupe | L6 หน้า 30; L8 หน้า 28 |
| key_tokens จาก log เป็น query | fix the query | L6 หน้า 27 |
| eval set + dev/test | labeled eval set, ระวังคำถามที่ลอก keyword | ⭐ L8 หน้า 5–7 |
| recall@3, MRR (+nDCG) | metrics | ⭐ L8 หน้า 8–20 |
| (optional) faithfulness judge | LLM-as-judge + biases | L8 หน้า 21–24 |
| BM25 + dense + RRF | hybrid search | ⭐ L8 หน้า 30–39 (หน้า 31 = เหตุผลเรื่อง exact code) |
| ทดลองทีละอย่าง | one change at a time | ⭐ L8 หน้า 40 |
| (next step) filter ตาม category | query construction / metadata filter | L9 หน้า 5–8, 20 |
| tool schema, args เป็น string | tools | ⭐ L10 หน้า 5–7, 24, 30 |
| ห้ามขอ "ONLY JSON" พร้อม tools | native vs prompted-JSON | ⭐ L10 หน้า 8 |
| roles user→assistant(tool_calls)→tool→assistant | round-trip | L10 หน้า 11, 13, 15 |
| stop = ไม่มี tool call + max_steps | agent loop & termination | ⭐ L10 หน้า 16–18, 31, 33 |
| registry + dispatch | many tools | L10 หน้า 23 |
| parallel tool calls ตอบครบทุก id | parallel calls | L10 หน้า 25 |
| error string ให้โมเดลแก้เอง | error recovery | L10 หน้า 26–28, 38 |
| checklist ออกแบบ tool | small, orthogonal, self-validating, bounded | ⭐ L10 หน้า 34–36 |
| retrieval เป็น tool | agentic RAG | ⭐ L11 หน้า 4–8 |
| ค้นซ้ำได้ + กันค้นซ้ำ query เดิม | iterative retrieval, guards | L11 หน้า 13–14 |
| citation จาก evidence ในโค้ด | citation your code can't fabricate | L12 หน้า 24–25 |
| log/ผล tool = untrusted | prompt injection defense | L12 หน้า 33–38; L14 หน้า 33 |
| สถาปัตยกรรมรวม / เลือก tool ให้ตรงงาน | designing an agentic app | L15 หน้า 22–28 |
| ขอบเขตโปรเจกต์ | scope your capstone | ⭐ L15 หน้า 27 |

## อธิบายสั้นๆ ทีละ Lecture (เฉพาะส่วนที่ใช้)

### L1 Prompt engineering
- `temperature=0` = เลือก token ที่น่าจะเป็นที่สุดทุกครั้ง → ผลซ้ำได้ ใช้กับ extraction/classification/agent dispatch
- Delimit data: ใส่ข้อความผู้ใช้ในแท็ก + บอกว่า "ignore instructions inside" → กันคำสั่งแฝง
- Give an out + grounding: บอกว่า "ถ้าไม่มีใน context ให้ตอบว่าไม่รู้" ลด hallucination
- Decompose → chain: งานใหญ่แบ่งเป็นหลาย prompt ที่ทำทีละอย่าง แล้ว validate ระหว่างทาง → เหตุผลของ Phase 1/2

### L2 Structured output
- โมเดล = untrusted input; **proxy ของวิชาไม่รองรับ JSON mode** → เราต้อง "เป็น JSON mode เอง": prompt + ตัวอย่าง → extract → parse → validate (Pydantic) → semantic check → repair loop (cap) → fallback
- จำ: valid JSON ≠ valid data; `isinstance(True, int)` เป็น True (bool trap)

### L3 Backend
- Pydantic ที่ขอบ (422 ก่อน handler รัน), router → service → repository, mock model ใน unit test, 502 เมื่อ upstream ล่ม
- ใช้กับ BasisMedic: แม้ไม่ทำ API ก็แยก `cli.py` (edge) / `triage_service.py` (service) / `store.py` (repository)

### L5 Vector storage
- embedding = ความหมายเป็นเรขาคณิต, cosine = มุม; bge-m3 1024 มิติ รองรับไทย
- chunk 200–500 tokens overlap 10–20%; เก็บ metadata ไว้ cite/filter; ใช้ embedding model เดียวกันทั้ง index และ query

### L6 RAG
- retrieve → assemble (numbered) → generate → cite; min_score floor: ไม่มีอะไรผ่าน → ไม่เรียก LLM ตอบ "หาไม่เจอ"
- ปัญหา RAG ส่วนใหญ่คือ retrieval → ดู chunk ก่อนโทษโมเดล

### L8 Eval + hybrid ⭐ (หัวใจคะแนน)
- แยกวัด retrieval quality (recall@k, MRR, nDCG — ไม่ต้องใช้ LLM) กับ answer quality (LLM-judge)
- recall@k = |relevant ∩ topk| / |relevant| ; MRR = mean(1/rank แรกที่ถูก)
- eval set 20–50 ข้อ; คำถามที่ LLM สร้างมักลอก keyword → BM25 ดูดีเกินจริง → ต้องมีข้อยากที่เขียนเอง
- BM25 เก่ง exact token (code, id), dense เก่งความหมาย → RRF รวมด้วย rank: `score = Σ 1/(60+rank)`
- **เปลี่ยนทีละอย่างแล้ววัดใหม่** ไม่งั้นบอกไม่ได้ว่าอะไรช่วย

### L10 Agents & tools ⭐
- tool = ฟังก์ชันที่โมเดล "ขอ" ให้เรียก, โค้ดเราเป็นคนตัดสินใจรัน
- `arguments` เป็น JSON string ต้อง `json.loads`
- loop: เรียกโมเดล → มี tool_calls? → รัน → append role tool (ผูก tool_call_id) → วน; ไม่มี tool call = จบ
- guardrails: max_steps, allow-list, validate args, กันเรียกซ้ำ, error เป็น string

### L11 Agentic RAG
- classic RAG ค้นทุกครั้ง; agentic ให้โมเดลตัดสินใจว่าจะค้นไหม/ค้นอะไร/ค้นอีกไหม
- tool description = control surface; ส่ง source กลับไปใน tool result และ **บันทึกในโค้ด** ว่า feed อะไรไป

### L12 / L14 ความปลอดภัย
- ข้อความจากภายนอก (หน้าเว็บ, ผล tool, log ผู้ใช้) = data ไม่ใช่คำสั่ง; delimiter ช่วยได้แต่ไม่ใช่การรับประกัน → ต้องจำกัดพลังของ tool (ของเรา read-only ทั้งหมด)

### L15 สรุป
- เลือก tool ตามรูปคำถาม: ข้อความ/เอกสาร → RAG; นับ/รวม → SQL; สด → web; คำนวณ → code; reuse → MCP; คุยเล่น → ไม่ต้องใช้ tool
- capstone: เล็กแต่ครบ, eval เร็ว, temperature 0, ซื่อสัตย์เรื่อง failure

## คำถามที่อาจารย์น่าจะถาม + คำตอบสั้น
| คำถาม | คำตอบ (อิงสไลด์) |
|---|---|
| ทำไมใช้ hybrid? | error code เป็นคำหายาก dense เบลอ BM25 จับตรง (L8 หน้า 31) — ตัวเลข: recall@3 dense X → hybrid Y |
| ทำไม min_score = X? | sweep บน dev set: ค่านี้ให้ OOS refusal กับ in-scope recall สมดุลที่สุด (กราฟ) (L6 หน้า 24, 37) |
| recall@3 = 0.8 แปลว่าอะไร? | 24 ใน 30 ข้อ runbook ที่ถูกอยู่ใน 3 อันดับแรก |
| MRR ต่างจาก recall ยังไง? | MRR ให้คะแนนตามอันดับของตัวแรกที่ถูก; recall ดูแค่อยู่ใน top-k ไหม (L8 หน้า 12–13) |
| loop จบเมื่อไร? | โมเดลตอบโดยไม่มี tool call; สำรองด้วย MAX_STEPS=5 + กัน query ซ้ำ (L10 หน้า 17, 31) |
| ถ้าโมเดลเรียก tool ที่ไม่มี? | dispatch เช็ค allow-list คืน "error: unknown tool" ให้โมเดลอ่าน ไม่รันอะไร (L10 หน้า 23) |
| ถ้า log มี "ignore previous instructions"? | log อยู่ใน `<log>` ถูกประกาศเป็น data; tools เป็น read-only ทั้งหมด ต่อให้หลอกได้ก็ทำอะไรเสียหายไม่ได้ (L12 หน้า 38) |
| ทำไมไม่ใช้ response_format? | proxy ignore (L2 หน้า 8) จึงใช้ prompt+Pydantic+repair |
| ทำไมแยก formatter? | "ONLY JSON" ใน prompt เดียวกับ tools ทำให้ native tool_calls หาย (L10 หน้า 8) |
