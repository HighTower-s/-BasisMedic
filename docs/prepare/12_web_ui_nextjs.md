# 12 — Web UI (Next.js) แบบหน้าแชต

> เป้าหมาย: หน้าตาแนวเดียวกับ Gemini / ChatGPT / Claude (sidebar ซ้าย + ช่องพิมพ์ตรงกลาง + ข้อความเป็น bubble) แต่ **ใช้ธีมของ BasisMedic เอง** ไม่ใช้โลโก้หรือแบรนด์ของใคร
> ได้ family **#6 served interface** แบบเต็ม (REST + SSE streaming) — ตอนนี้ใช้ครบ 5 กลุ่ม: #1 #2 #3 #4 #6

## 1. สิ่งที่เพิ่ม และสิ่งที่ไม่เปลี่ยน
| | รายการ |
|---|---|
| **เพิ่ม** | `app/api.py` (FastAPI: REST + SSE) · `web/` (Next.js) · callback `on_event` ใน service/agent loop เพื่อส่งความคืบหน้า · test ของ API |
| **แก้เล็กน้อย** | `triage_service.triage(log, on_event=None)` และ `agent/loop.py` เรียก `on_event(...)` ทุกครั้งที่มี tool call, tool result, หรือเริ่ม/จบแต่ละ phase (ถ้า `on_event` เป็น None ทุกอย่างทำงานเหมือนเดิม → CLI/eval ไม่กระทบ) |
| **ไม่เปลี่ยน** | retrieval, tools, guardrails, formatter, schema, eval ทั้งหมด (eval ยังเรียก service ตรง ไม่ผ่านเว็บ) |

## 2. สถาปัตยกรรม
```
Browser (Next.js page)
   │  fetch POST /api/triage/stream   (same-origin)
   ▼
Next.js dev server ── rewrites /api/* ──► FastAPI :8000 (app/api.py)   ← edge (router)
                                              │
                                              ▼
                                      triage_service.triage(log, on_event)  ← service
                                              │
                                   agent loop / store / tcodes             ← repository
                                              │
                                     class LLM proxy (key อยู่ฝั่งนี้เท่านั้น)
```
- **API key อยู่ใน FastAPI เท่านั้น** browser ไม่เคยเห็น key และไม่เรียก proxy ตรง (L3 หน้า 2–4)
- ใช้ `rewrites` ใน `next.config.js` → `/api/:path*` ไป `http://localhost:8000/api/:path*` (เรียกแบบ same-origin ไม่ต้องตั้ง CORS)

## 3. API contract
### 3.1 `POST /api/triage` (ไม่ stream — ใช้กับ test/CLI แบบ HTTP)
- request: `{"log": "..."}` (Pydantic `TriageRequest`: 10–4000 ตัวอักษร) → ผิด = **422** (detail เป็น list ตาม field — L3 หน้า 31)
- response: `TriageResult` JSON
- proxy ล่ม: **502** `{"detail":"upstream error"}` · timeout: **504** (L3 หน้า 29–30) · ไม่ส่ง stack trace/key ออกไป

### 3.2 `POST /api/triage/stream` (SSE — ใช้กับหน้าเว็บ)
`Content-Type: text/event-stream` · **1 frame = 1 บรรทัด `data: {JSON}\n\n`** (กัน newline ใน token ทำ frame แตก — L4 หน้า 19–20, 29–30)

| `type` | ส่งเมื่อ | payload ตัวอย่าง |
|---|---|---|
| `status` | เริ่มแต่ละ phase | `{"type":"status","phase":"searching"}` / `"formatting"` |
| `tool_call` | agent เรียก tool | `{"type":"tool_call","tool":"search_runbook","args":{"query":"TSV_TNEW_PAGE_ALLOC_FAILED"}}` |
| `tool_result` | tool คืนผล | `{"type":"tool_result","tool":"search_runbook","hits":["mem_tsv_tnew_page_alloc#check", "..."]}` (ส่งแค่ id/สรุป ไม่ส่งข้อความเต็ม) |
| `result` | ได้ `TriageResult` ที่ validate แล้ว | `{"type":"result","data":{...TriageResult...}}` |
| `error` | มีปัญหากลางทาง | `{"type":"error","detail":"upstream error"}` — **ต้องส่ง frame นี้ ไม่ปล่อยให้ stream เงียบหาย** (L4 หน้า 33) |
| `done` | จบ | `{"type":"done"}` |

> ทำไมไม่ stream คำตอบทีละ token แบบ ChatGPT: ผลลัพธ์ต้องผ่าน Pydantic ทั้งก้อนก่อน (structured output) จึง stream "ขั้นตอนการทำงาน" แทน — ผู้ใช้เห็นว่าระบบกำลังค้นอะไร (โปร่งใส + ดูดีตอน demo)

โครง FastAPI (ย่อ):
```python
@router.post("/api/triage/stream")
async def triage_stream(req: TriageRequest):
    queue: asyncio.Queue = asyncio.Queue()
    def on_event(ev: dict): queue.put_nowait(ev)

    async def run():
        try:
            result = await asyncio.to_thread(triage_service.triage, req.log, on_event)  # ไม่บล็อก event loop (L3 หน้า 18)
            on_event({"type": "result", "data": result.model_dump()})
        except UpstreamError:
            on_event({"type": "error", "detail": "upstream error"})
        finally:
            on_event({"type": "done"})

    async def frames():
        task = asyncio.create_task(run())
        while True:
            ev = await queue.get()
            yield f"data: {json.dumps(ev, ensure_ascii=False)}\n\n"
            if ev["type"] == "done": break
        await task
    return StreamingResponse(frames(), media_type="text/event-stream")
```
⚠ `on_event` ถูกเรียกจาก thread อื่น → ในโค้ดจริงใช้ `loop.call_soon_threadsafe(queue.put_nowait, ev)`

### 3.3 ฝั่ง client อ่าน stream
- ใช้ `fetch` + `response.body.getReader()` (ไม่ใช้ `EventSource` เพราะ EventSource ส่งได้แค่ GET — L4 หน้า 31)
- เก็บ **buffer** แล้วตัดด้วย `"\n\n"` เพราะ chunk ที่ได้ ≠ frame (L4 หน้า 28, 32)
- ปุ่ม **Stop** ใช้ `AbortController` (L4 หน้า 38)
```ts
// web/lib/sse.ts
export async function streamTriage(log: string, onEvent: (e: TriageEvent) => void, signal: AbortSignal) {
  const res = await fetch("/api/triage/stream", {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ log }), signal,
  });
  if (!res.ok) throw await res.json();          // 422 → {detail: [...]} , 502 → {detail: "..."}
  const reader = res.body!.getReader(); const dec = new TextDecoder(); let buf = "";
  while (true) {
    const { value, done } = await reader.read(); if (done) break;
    buf += dec.decode(value, { stream: true });
    let i; while ((i = buf.indexOf("\n\n")) >= 0) {
      const frame = buf.slice(0, i); buf = buf.slice(i + 2);
      if (frame.startsWith("data: ")) onEvent(JSON.parse(frame.slice(6)));
    }
  }
}
```

## 4. หน้าตา (UI spec)
```
┌───────────────┬──────────────────────────────────────────────────────┐
│ 🩺 BasisMedic  │                                                      │
│ [+ Triage ใหม่] │   (หน้าว่าง)  "วาง error log ของ SAP ที่นี่"               │
│               │   [TSV dump] [Job cancelled] [Transport RC 8] [HANA]  │ ← ปุ่มตัวอย่าง
│ ประวัติ          │   ┌──────────────────────────────────────────────┐   │
│  • TSV_TNEW…  │   │ วาง log …                          0/4000  ➤ │   │ ← composer
│  • RC=8 QAS   │   └──────────────────────────────────────────────┘   │
│  • User lock  │                                                      │
│               │  (มีบทสนทนาแล้ว)                                         │
│               │   [user bubble: log แบบ monospace, พับได้ถ้ายาว]           │
│               │   ▸ ขั้นตอนการทำงาน (3)   ← พับ/กางได้                     │
│               │      🔍 search_runbook("TSV_TNEW…") → 3 hits          │
│               │      🔎 lookup_tcode("ST02")                           │
│               │   ┌ TriageCard ─────────────────────────────────┐    │
│               │   │ [memory_dump] confidence: high               │    │
│               │   │ เปิด: (ST22)→(ST02)→(SM37)  ← chip มี tooltip   │    │
│               │   │ 1. ST22: …  2. ST02: …                        │    │
│ ⚙ เกี่ยวกับ      │   │ ส่งต่อ: developer   แหล่งอ้างอิง: mem_tsv…#check   │    │
│               │   └──────────────────────────────────────────────┘    │
└───────────────┴──────────────────────────────────────────────────────┘
```
| Component | หน้าที่ |
|---|---|
| `Sidebar` | ปุ่ม Triage ใหม่, รายการประวัติ (ชื่อ = error code แรกที่เจอ), ลบรายการ |
| `EmptyState` | หัวข้อ + ปุ่ม log ตัวอย่าง 4 อัน (สำเร็จ / OOS / failure — ใช้ตอน demo ได้เลย) |
| `Composer` | textarea ขยายอัตโนมัติ, Enter = ส่ง, Shift+Enter = ขึ้นบรรทัด, ตัวนับ 4000, ปุ่ม Stop ระหว่างทำงาน, แสดง error 422 ใต้ช่อง |
| `UserBubble` | แสดง log แบบ monospace, ยาวเกิน 12 บรรทัดให้พับ |
| `StepTimeline` | แสดง event `tool_call`/`tool_result` แบบเรียลไทม์, พับได้ (คล้ายกล่อง "กำลังคิด") |
| `TriageCard` | badge category + สี, confidence, T-code chip (tooltip จาก `tcodes.json` ผ่าน `GET /api/tcodes`), steps, escalate, sources, ปุ่ม "คัดลอก JSON" |
| `OutOfScopeCard` | แสดงเมื่อ `category=out_of_scope`: "ไม่อยู่ใน runbook" + คำแนะนำทั่วไป |
| `ErrorToast` | 502/504/stream error |

ธีม: dark (พื้นน้ำเงินเข้ม/เทา), สีประจำ category 8 สี, ฟอนต์ไทย **IBM Plex Sans Thai** หรือ **Noto Sans Thai**, log ใช้ **JetBrains Mono**

## 5. State และประวัติ
- **v1 (แนะนำ):** เก็บประวัติใน `localStorage` (wrap ด้วย try/catch) — แต่ละ "แชต" = 1 log + ผล triage · ไม่ต้องมี DB
- **v2 (optional):** SQLite ผ่าน repository layer + `GET /api/history` (L3 หน้า 20) — ได้คะแนน layering เพิ่ม
- **Follow-up หลายรอบ:** v1 ทุกข้อความใหม่ = triage ใหม่ (บอกผู้ใช้ชัดในหน้าเว็บ) · ถ้าจะทำ v2 ต้องส่ง history เข้า agent และเพิ่มเคส eval หลายรอบ — **อย่าทำจนกว่าทุกอย่างอื่นจะเสร็จ**

## 6. Tech stack ฝั่งเว็บ
| | เลือก |
|---|---|
| Framework | **Next.js (App Router) + TypeScript** |
| Style | **Tailwind CSS** |
| Icon | lucide-react |
| Markdown (ถ้า steps มี format) | react-markdown |
| รันพร้อมกันสองฝั่ง | `concurrently` (npm script) หรือ `docker compose` |
> หมายเหตุ: L4 สอนด้วย SvelteKit — ใช้ Next.js ได้ แต่ต้องอธิบายหลัก (state, fetch, stream reader) ได้เอง

## 7. โครงสร้างโฟลเดอร์ `web/`
```
web/
├─ package.json            # scripts: dev, build, dev:all (concurrently uvicorn + next)
├─ next.config.js          # rewrites /api/* → http://localhost:8000
├─ app/
│  ├─ layout.tsx           # ฟอนต์, ธีม
│  └─ page.tsx             # หน้าแชตหลัก
├─ components/  Sidebar.tsx  EmptyState.tsx  Composer.tsx  UserBubble.tsx
│               StepTimeline.tsx  TriageCard.tsx  OutOfScopeCard.tsx  ErrorToast.tsx
├─ lib/  sse.ts  types.ts (TriageResult/TriageEvent ให้ตรงกับ Pydantic)  history.ts  samples.ts
└─ public/  logo.svg       # โลโก้ของเราเอง
```

## 8. การรัน (ต้องอยู่ใน README)
```bash
uv sync --extra api
uv run python -m app.retrieval.ingest
uv run uvicorn app.api:app --port 8000          # terminal 1
cd web && npm install && npm run dev             # terminal 2 → http://localhost:3000
# หรือคำสั่งเดียว:  cd web && npm run dev:all
```
**CLI ต้องยังใช้ได้** (`uv run python -m app.cli ...`) เป็นทางสำรองตอน demo สดถ้าเว็บมีปัญหา

## 9. Test ที่ควรเพิ่ม (model ถูก mock — L3 หน้า 26–28)
- `POST /api/triage` log ว่าง → 422 · ยาวเกิน → 422
- service โยน `UpstreamError` → 502 และ body ไม่มี stack trace
- `/api/triage/stream` → ทุก frame เป็น `data: {json}\n\n` parse ได้, จบด้วย `done`, กรณี error มี frame `error` ก่อน `done`

## 10. Demo (ใช้หน้าเว็บแทน CLI)
1. กดปุ่มตัวอย่าง "TSV dump" → ให้คนดูเห็น StepTimeline ขึ้นทีละขั้น → TriageCard (success)
2. กด "HANA" → OutOfScopeCard (min_score gate)
3. วาง log ที่มี 2 ปัญหา → ผลผิด → อธิบาย failure
4. สลับไป terminal รัน `eval.run_all` แสดงตาราง

## 11. ลำดับการทำ + สิ่งที่ตัดได้ถ้าเวลาไม่พอ
1. `on_event` ใน service/loop → 2. `POST /api/triage` + tests → 3. `/api/triage/stream` → 4. Next.js หน้าเดียว (Composer + TriageCard) → 5. StepTimeline → 6. Sidebar + localStorage → 7. ตกแต่ง
**ถ้าเวลาไม่พอ ตัดจากท้ายขึ้นมา:** sidebar → streaming (ใช้ `POST /api/triage` ธรรมดา + spinner) → Next.js ทั้งหมด (กลับไปใช้ CLI) — แกนและ eval ต้องเสร็จก่อนเสมอ
