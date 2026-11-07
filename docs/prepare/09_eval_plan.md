# 09 — Evaluation Plan (ส่วนที่ได้คะแนนมากที่สุด)

> หลัก: "สร้าง eval ก่อนเขียนระบบ" (Tips ของอาจารย์ + L8 หน้า 2–7) · วัด retrieval แยกจาก answer (L8 หน้า 5) · เปลี่ยนทีละอย่าง (L8 หน้า 40) · ซื่อสัตย์

## 1. ชุดข้อมูลทดสอบ

### 1.1 รูปแบบ (`eval/cases_*.jsonl` หนึ่งบรรทัดต่อหนึ่งเคส)
```json
{"id": "t07", "split": "test", "format": "sm37_joblog", "difficulty": "hard",
 "log": "Job ZSD_BILLING_DAILY ... Job cancelled after system exception ERROR_MESSAGE ...",
 "gold_category": "job_failure",
 "gold_docs": ["job_cancelled"],
 "acceptable_docs": ["user_locked"],
 "gold_tcodes": ["SM37", "ST22"],
 "notes": "step user locked เป็นต้นเหตุ — ต้องค้น 2 รอบ"}
```
- `gold_docs` = runbook ที่ "ต้อง" เจอ (ใช้คิด recall/MRR) · `acceptable_docs` = เจอแล้วไม่ผิด (ไม่นับเป็น relevant)
- `gold_tcodes` = T-code **ที่ต้องมี** อย่างน้อย (2–3 ตัวสำคัญ) ไม่ใช่ทุกตัว
- OOS: `gold_category="out_of_scope"`, `gold_docs=[]`, `gold_tcodes=[]`

### 1.2 จำนวนและการกระจาย
| ชุด | จำนวน | องค์ประกอบ | ใช้ทำอะไร |
|---|---|---|---|
| **dev** | 10 | 8 in-scope (1/category) + 2 OOS | จูน `MIN_SCORE`, เลือก chunk strategy, แก้ prompt |
| **test** | 30 | 24 in-scope (3/category: easy, medium, hard; ทุก runbook ถูกใช้ ≥ 1 ครั้ง) + 4 OOS + 2 mixed (2 ปัญหาใน log เดียว) | **รายงานผลเท่านั้น ห้ามจูน** |

### 1.3 กฎการเขียนเคส (กัน "ตัวเลขสวยเกินจริง")
- **easy** = มี error code ตรง (เช่น `TIME_OUT`) · **medium** = รูปแบบ log อื่น (SM21 line, job log, STMS log) · **hard** = ไม่มี code ตรง เป็นคำบ่นของ user / paraphrase / **ภาษาไทย 2–3 ข้อ** (bge-m3 รองรับไทย — ทดสอบจริงว่าได้ไหม)
- ห้ามคัดลอกประโยคจาก runbook มาเป็น log (L8 หน้า 7: คำถามที่ลอก keyword ทำให้ BM25 ดูดีเกินจริง)
- ใช้รูปแบบ (format) หลากหลาย: `st22_header`, `sm37_joblog`, `sm21_syslog`, `stms_log`, `sm59_test`, `user_email`, `chat_thai`
- เขียน log ก่อน แล้วค่อยติด label จาก runbook · ถ้าได้ ให้เพื่อนเขียน 5 ข้อ (ลด bias ว่าคนเขียน runbook = คนเขียนข้อสอบ) และบันทึกไว้ในรายงาน
- dev กับ test ห้ามเป็น log เดียวกันที่เปลี่ยนแค่ชื่อโปรแกรม

## 2. Metrics
| ระดับ | Metric | นิยาม | คิดบน |
|---|---|---|---|
| Retrieval | **recall@3** ⭐ | \|gold_docs ∩ top-3 docs\| / \|gold_docs\| (ยุบ chunk เป็น doc ก่อน แบบ reference) | in-scope 26 ข้อ |
| Retrieval | **MRR** | 1/rank ของ gold doc ตัวแรก (ไม่เจอ = 0) | in-scope |
| Retrieval | OOS gate accuracy | สัดส่วน OOS ที่ถูก gate ตัดทิ้ง (คืน []) | OOS 4 ข้อ |
| Retrieval | false-refusal rate | สัดส่วน in-scope ที่ถูก gate ตัดทิ้งผิดๆ | in-scope |
| End-to-end | **category accuracy** ⭐ | predicted == gold_category | ทั้ง 30 |
| End-to-end | **T-code recall** | \|gold_tcodes ∩ pred_tcodes\| / \|gold_tcodes\| เฉลี่ย | in-scope |
| End-to-end | hallucinated T-code rate | T-code ที่ทำนาย แต่ไม่อยู่ใน `tcodes.json` / ทั้งหมด | ทั้งหมด (ก่อน post-check) |
| End-to-end | valid-JSON rate | ผ่าน Pydantic โดยไม่ต้อง fallback | ทั้งหมด |
| End-to-end | avg tool calls / steps | ประสิทธิภาพ agent | ทั้งหมด |
| (optional) | faithfulness 1–5 (LLM-judge) | steps อ้างจาก evidence จริงไหม — ต้อง validate กับ label มือ ~10 ข้อก่อน (L8 หน้า 21–24) | ทั้งหมด |

โค้ด metric (เหมือน L8 หน้า 14 / reference `eval/eval.py`):
```python
def recall_at_k(ranked, relevant, k):  return len(set(ranked[:k]) & set(relevant)) / len(relevant)
def mrr(ranked, relevant):
    for i, d in enumerate(ranked, 1):
        if d in relevant: return 1 / i
    return 0.0
```

## 3. Baselines (ต้องตั้งชื่อชัด)
| ชื่อ | คืออะไร | เทียบกับ |
|---|---|---|
| **R-BM25** | BM25-only retrieval | retrieval ของเรา |
| **R-Dense-naive** | bge-m3 + fixed 800-char chunks (= naive default แบบ reference) | ใช้เป็น "before" |
| **E-NoRAG** | gemma ตอบ category + T-code จาก log เลย ไม่มี retrieval/tools (formatter prompt เดียวกัน) | ระบบเต็ม |
| **E-ClassicRAG** (แนะนำ) | ค้น 1 ครั้งด้วย normalized log → ตอบ (ไม่มี agent loop) | ตอบว่า "agent ช่วยจริงไหม" — ถ้าไม่ช่วย ก็รายงานตรงๆ |

## 4. การทดลอง (ทีละตัวแปร)
| # | ตัวแปรที่เปลี่ยน | ค่าคงที่ | ใช้ชุด | ผลที่ต้องการ |
|---|---|---|---|---|
| E1 | chunk: `fixed-800/150` → `section` | dense, k=3 | dev → test | **measured improvement #1** (ข้อบังคับ B3) |
| E2 | retrieval: `bm25` vs `dense` vs `hybrid(RRF k=60)` | chunk ที่ดีที่สุดจาก E1 | dev → test | เหตุผลของ hybrid |
| E3 | `MIN_SCORE` 0.30→0.60 ทีละ 0.05 | config จาก E2 | **dev เท่านั้น** แล้วรายงานค่าที่เลือกบน test | กราฟ: in-scope recall vs OOS gate accuracy |
| E4 | E-NoRAG vs E-ClassicRAG vs BasisMedic | config สุดท้าย | test | ตาราง e2e |
| E5 (opt) | k = 1, 3, 5 | config สุดท้าย | dev | เลือก k |

## 5. ตารางผล (template สำหรับรายงาน — เติมจากผลรันจริงเท่านั้น)
**Retrieval (test, in-scope n=26)**
| Config | recall@3 | MRR | OOS gate acc (n=4) | false refusal |
|---|---|---|---|---|
| R-Dense-naive (fixed-800) | | | | |
| Dense + section | | | | |
| R-BM25 + section | | | | |
| **Hybrid + section + min_score=?** | | | | |

**End-to-end (test, n=30)**
| System | category acc | T-code recall | halluc. T-code | valid JSON | avg steps |
|---|---|---|---|---|---|
| E-NoRAG | | | | | – |
| E-ClassicRAG | | | | | 1 |
| **BasisMedic** | | | | | |

**แยกตามความยาก** (easy / medium / hard / Thai / mixed) — ใส่ด้วย จะเห็นจุดอ่อนจริง

## 6. Reproducibility
- `temperature=0` ทุกที่ · บันทึก config (model, mode, chunk, k, min_score, git commit) ลงใน `results/*.json`
- **cache embedding** ลงดิสก์ (key = sha1 ของข้อความ) → รันซ้ำได้ตัวเลขเดิมและประหยัด
- คำสั่งเดียว: `uv run python -m eval.run_all` → เขียน `eval/results/results.md`
- e2e ขึ้นกับโมเดล: รัน 2 รอบเช็คว่าตัวเลขเท่าเดิมไหม ถ้าต่างให้รายงาน mean ± range

## 7. Failure analysis (สำหรับรายงาน + demo)
บันทึกทุกข้อที่ผิดลง `eval/results/failures.jsonl` แล้วจัดกลุ่ม:
| id | expected | got | top-3 retrieved | ชนิดความผิดพลาด | แนวแก้ |
|---|---|---|---|---|---|
| t29 | lock_issue | update_error | update_terminated, lock_old… | mixed log — schema รับ category เดียว | multi-label / ถาม user |
ชนิด: (a) retrieval miss (b) retrieval ถูกแต่ category ผิด (c) formatter/JSON (d) agent loop (ค้นซ้ำ/ไม่ค้น) (e) gate ผิด
> เลือก failure 1 ข้อที่อธิบายได้ชัดไปโชว์ใน demo video

## 8. Checklist
- [ ] เขียน dev 10 + test 30 **ก่อน** เขียน retrieval
- [ ] `run_retrieval.py` รันได้กับ BM25 (ไม่ต้องใช้ proxy) ตั้งแต่วันแรก
- [ ] E1 → E2 → E3 → E4 ตามลำดับ บันทึกผลทุกครั้ง (commit ผล)
- [ ] ตารางผล + กราฟ min_score + failure table อยู่ใน README และรายงาน
