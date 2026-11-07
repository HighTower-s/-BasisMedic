# 07 — การจัดการ Short Dump (ST22) + คู่มือ Incident 8 ประเภท

> ไฟล์นี้คือ **วัตถุดิบสำหรับเขียน `data/runbooks/*.md`** (16 ไฟล์) และใช้เรียน Basis ไปพร้อมกัน
> ⚠ ก่อน commit เป็น runbook: อ่านแหล่งอ้างอิง (08_resources.md) แล้ว **เรียบเรียงด้วยภาษาตัวเอง** + ใส่ URL ในหัวข้อ References — อย่าคัดลอกเอกสาร SAP ยาวๆ

---

# ส่วนที่ 1 — การจัดการ ABAP Short Dump ด้วย ST22

## 1.1 Short dump คืออะไร
เมื่อโปรแกรม ABAP เจอ **runtime error ที่ไม่ถูกดักจับ** (unhandled exception) โปรแกรมจะหยุดทันที และระบบบันทึก **short dump** (log รายละเอียดของความผิดพลาด) ไว้ในระบบ ถ้าเกิดในงาน dialog ผู้ใช้จะเห็นหน้าจอ dump ทันที ถ้าเกิดใน background job/update task ผู้ใช้จะไม่เห็น ต้องไปดูใน **ST22 (ABAP Dump Analysis)** (ref: SAP Help "ABAP Dump Analysis – Background")

## 1.2 เปิด ST22 แล้วดูอะไร
1. เลือกช่วงเวลา: Today / Yesterday หรือกำหนดเอง (วันที่, เวลา, user, ชื่อ runtime error, program)
2. รายการแสดง: วันที่/เวลา, application server, user, client, **runtime error**, exception, program, สถานะ "keep"
3. เปิด dump → ส่วนที่ต้องอ่าน (ชื่อหัวข้อมาตรฐานใน ST22):

| หัวข้อใน dump | ใช้ตอบคำถาม | หมายเหตุสำหรับ triage |
|---|---|---|
| **Short Text** | เกิดอะไรขึ้น (1 บรรทัด) | ใช้เป็น query ค้นได้ดี |
| **What happened?** | อธิบายเพิ่ม | |
| **What can you do?** | สิ่งที่ผู้ใช้ทำได้ | มักบอกให้แจ้ง admin + จดเวลา |
| **Error analysis** | สาเหตุเชิงเทคนิค | เช่น ขนาดตาราง, เวลาที่ใช้ |
| **How to correct the error** | แนวทางแก้ + **keywords สำหรับค้น SAP Notes** | ใช้ค้นต่อใน SAP for Me (ต้องมี S-user) |
| **System environment** | kernel, DB, OS, เครื่อง | ใช้ตอนเปิด incident กับ SAP |
| **User and Transaction** | client, user, transaction, **job name** | บอกว่าเป็น dialog หรือ background |
| **Information on where terminated** | program, include, **บรรทัด** | Z/Y program → developer; standard → หา SAP Note |
| **Source Code Extract** | โค้ดรอบจุดที่ล้ม (มี `>>>>>` ชี้) | |
| **Active Calls/Events** | call stack | ดูว่าเรียกมาจากไหน |
| **Chosen variables** | ค่าตัวแปรตอนล้ม | เช่น ขนาด internal table |

4. ปุ่มที่ควรรู้: **Keep/Release** (กันไม่ให้ dump ถูกลบอัตโนมัติ — ปกติ dump เก่าถูกลบโดย reorg job), ดาวน์โหลด/พิมพ์, เปิด debugger (เฉพาะกรณี dialog ที่ยังอยู่ใน context)

## 1.3 ขั้นตอน triage dump แบบ Basis (ใช้เป็นโครง runbook ได้)
1. **ขอบเขต**: เกิดครั้งเดียวหรือซ้ำ? กี่ user? เริ่มเมื่อไร? (เรียง ST22 ตามชื่อ error/จำนวน)
2. **ใคร/อะไร**: user, client, transaction หรือ job (User and Transaction)
3. **อะไร**: ชื่อ runtime error + exception class
4. **ที่ไหน**: program/include/line — **standard SAP หรือ Z?**
5. **ทำไม**: Error analysis + How to correct the error → keyword ค้น SAP Notes/KBA
6. **บริบทระบบ**: SM21 ช่วงเวลาเดียวกัน, SM50/SM66 (WP), ST02 (memory), DB ล่มหรือไม่
7. **ตัดสินใจเจ้าของงาน**:
   | สาเหตุ | ส่งต่อ |
   |---|---|
   | ทรัพยากร/parameter/ระบบ (memory, timeout, WP) | Basis |
   | logic ใน Z-program | ABAP developer |
   | ข้อมูล/การตั้งค่าธุรกิจ | Functional consultant |
   | error ฐานข้อมูล | DBA / Basis |
   | bug ใน standard ที่ไม่มี SAP Note | SAP Support (เปิด incident แนบ dump + SM21 + trace) |
8. **Keep dump** ที่ต้องใช้วิเคราะห์ต่อ, บันทึก ticket, เฝ้าดูว่าซ้ำไหม

## 1.4 Dump ที่พบบ่อย (ใช้สร้าง eval case และ out-of-scope)
| Runtime error | ความหมายโดยย่อ | กลุ่มใน BasisMedic | มักเป็นงานของ |
|---|---|---|---|
| `TSV_TNEW_PAGE_ALLOC_FAILED` | internal table ขยายไม่ได้ memory ไม่พอ | memory_dump | Basis + Dev |
| `SYSTEM_NO_ROLL` | จอง roll/memory ให้ user context ไม่ได้ | memory_dump | Basis |
| `MEMORY_NO_MORE_PAGING` | paging area เต็ม | memory_dump | Basis |
| `TIME_OUT` | dialog step นานเกินขีดจำกัด | timeout | Basis + Dev |
| `DBIF_RSQL_SQL_ERROR` | SQL error จาก DB (เช่น พื้นที่เต็ม) | (out_of_scope / DB) | DBA/Basis |
| `DBSQL_DUPLICATE_KEY_ERROR`, `SAPSQL_ARRAY_INSERT_DUPREC` | insert key ซ้ำ | (out_of_scope) | Dev/Functional |
| `CONVT_NO_NUMBER` | แปลงข้อความเป็นตัวเลขไม่ได้ | (out_of_scope) | Dev/ข้อมูล |
| `MESSAGE_TYPE_X` | โปรแกรมตั้งใจหยุดเพราะสถานะผิด | (out_of_scope) | ดูข้อความ/SAP Note |
| `CALL_FUNCTION_NOT_FOUND` | function module ไม่มี (transport ไม่ครบ?) | (เชื่อม transport) | Dev/Basis |
| `CALL_FUNCTION_COMMUNICATION_FAILURE` / `..._SYSTEM_FAILURE` | RFC ล้ม | rfc_error | Basis |
| `OBJECTS_OBJREF_NOT_ASSIGNED` | ใช้ object reference ที่ว่าง | (out_of_scope) | Dev |
| `LOAD_PROGRAM_NOT_FOUND`, `SYNTAX_ERROR` | โปรแกรมไม่มี/มี syntax error (หลัง transport) | transport_error (เกี่ยว RC 8) | Dev/Basis |

---

# ส่วนที่ 2 — Incident catalog (วัตถุดิบ 16 runbook)

รูปแบบทุกเรื่อง: **Symptoms → Cause → Check (T-code ตามลำดับ) → Fix → Escalate → References** (ตรงกับหัวข้อที่ chunker ตัด)

## memory_dump

### R01 `mem_tsv_tnew_page_alloc` — TSV_TNEW_PAGE_ALLOC_FAILED
- **Symptoms**: dump "No more storage space available for extending an internal table"; job ล้มกลางทาง; มักเกิดกับรายงานใหญ่/สิ้นเดือน
- **Cause**: internal table ใช้ memory เกินที่ WP จองได้ (roll → extended memory → heap หมด) ส่วนใหญ่เพราะ **ดึงข้อมูลมากเกิน** (selection กว้าง, ข้อมูลโต, โค้ดไม่ได้กรอง) บางครั้งเพราะ parameter ตั้งต่ำหรือ instance memory เต็มขณะนั้น
- **Check**: ST22 (Error analysis: ขนาดที่ขอ/ใช้ไปแล้ว, Chosen variables, program, job) → ST02 (EM/heap, ประวัติการใช้) → RZ11 (`ztta/roll_extension`, `abap/heap_area_dia`/`_nondia`, `abap/heap_area_total`, `em/initial_size_MB`) → SM37 (variant/selection ของ job) → SM21
- **Fix**: ลด selection / แบ่งรันเป็นช่วง (เช่น ตาม plant/period), ให้ dev ปรับโค้ด (กรอง/ประมวลผลเป็น package), ค้น SAP Note สำหรับ standard program; ปรับ parameter เฉพาะเมื่อวิเคราะห์แล้ว และคำนึง RAM ของเครื่อง
- **Escalate**: Z-program → developer; standard → SAP Note/SAP Support
- **Refs**: SAP Help ABAP Dump Analysis; SAP Community thread TSV_TNEW_PAGE_ALLOC_FAILED (archive.sap.com/discussions/thread/2107282)

### R02 `mem_system_no_roll` — SYSTEM_NO_ROLL / MEMORY_NO_MORE_PAGING
- **Symptoms**: dump SYSTEM_NO_ROLL หรือ MEMORY_NO_MORE_PAGING; หลาย user ล้มพร้อมกัน; ระบบช้า
- **Cause**: memory ส่วนกลางของ instance หมด (EM/roll/paging) — มักเพราะมี user context ใหญ่หลายตัวพร้อมกัน หรือ parameter ตั้งเล็กเกิน
- **Check**: ST02 (สถานะ roll/paging/EM, ดู "max used") → SM50/SM66 (WP ที่อยู่ในโหมด PRIV, ใครกิน memory) → SM04 (session ของ user) → ST06 (RAM/swap ของ OS) → SM21
- **Fix**: หา session/job ที่กิน memory ผิดปกติ, ย้ายงานใหญ่ไป background/นอกเวลา, ทบทวน memory parameter กับ RAM จริง (ต้อง restart instance ถ้าแก้ profile)
- **Escalate**: Basis (sizing); dev ถ้าเป็นโปรแกรมเฉพาะ
- **Refs**: SAP Help Work Processes; ST02

## timeout

### R03 `timeout_dialog` — TIME_OUT
- **Symptoms**: dump TIME_OUT "Time limit exceeded"; ผู้ใช้รันรายงานจากหน้าจอแล้วล้มหลังประมาณ 10 นาที
- **Cause**: dialog step ใช้เวลาเกินขีดจำกัดของ dialog WP (`rdisp/max_wprun_time`, ค่า default เดิม 600 วินาที; เคอร์เนลรุ่นใหม่บางรุ่นใช้ `rdisp/scheduler/max_runtime` — ตรวจใน RZ11) เพื่อกันไม่ให้ dialog WP ถูกยึดนาน; สาเหตุจริงมักเป็น SQL ช้า/ข้อมูลเยอะ
- **Check**: ST22 (program, ตำแหน่งที่ค้าง) → SM50/SM66 (ถ้ายังรันอยู่ ดู action/table) → ST05 หรือ ST12 (SQL trace) → RZ11 (ค่า timeout)
- **Fix**: รันเป็น **background job** (BTC ไม่มีขีดจำกัดนี้), จำกัด selection, ให้ dev/DBA ปรับ SQL/index; เพิ่ม timeout เป็นทางเลือกท้ายและกระทบทั้งระบบ
- **Escalate**: developer (SQL/โค้ด), DBA (index/statistics)
- **Refs**: SAP Help (ICM/rdisp parameters); SAP Community threads TIME_OUT

### R04 `timeout_long_running_wp` — WP ค้าง/ระบบช้า
- **Symptoms**: ผู้ใช้บ่นระบบช้า, SM50 เห็น dialog WP สถานะ Running นาน, ไม่มี WP ว่าง
- **Cause**: งานหนัก/SQL ไม่มี index ยึด WP หลายตัว, lock รอกัน, DB ช้า
- **Check**: SM66 (ทุก instance: เวลา, action เช่น "Sequential read", ตาราง) → SM50 (รายละเอียด, dev trace) → ST05/ST12 → ST06 (CPU/IO) → DB monitor (DBACOCKPIT/ST04)
- **Fix**: ประสาน user ให้หยุดงาน / cancel WP เฉพาะเมื่อจำเป็น (cancel without core), ย้ายงานไป background, ปรับ SQL/index/statistics
- **Escalate**: DBA, developer
- **Refs**: guru99 SAP Basis monitoring (SM50/SM66); SAP Help Work Processes

## job_failure

### R05 `job_cancelled` — Job สถานะ Canceled
- **Symptoms**: SM37 สถานะ **Canceled**; ข้อความ "Job cancelled after system exception ERROR_MESSAGE" หรือ "ABAP/4 processor: <ชื่อ dump>"
- **Cause**: dump ในโปรแกรม, message error ของโปรแกรม, variant ผิด, **step user ถูกล็อก/หมดอายุ/สิทธิ์ไม่พอ**, ไฟล์/ปลายทางไม่มี, instance restart ระหว่างรัน
- **Check**: SM37 → **Job log** (อ่านก่อนเสมอ) → Job details (server, WP, step user) → ST22 (เวลาเดียวกัน) → SM21 → SU01 (step user)
- **Fix**: แก้ตามต้นเหตุ (ส่ง dump ให้ dev, ปลดล็อก step user, แก้ variant) แล้ว **ทำสำเนา job/รันใหม่** หลังยืนยันว่ารันซ้ำปลอดภัย (บาง job ห้ามรันซ้ำ เช่น posting)
- **Escalate**: เจ้าของ job/functional ก่อนรันซ้ำ
- **Refs**: SAP Help "Analyzing the Job Status"; hicron.com "Checking the job log in SM37"

### R06 `job_stuck_ready_released` — Job ค้าง Released / Ready
- **Symptoms**: job ถึงเวลาแล้วแต่ไม่เริ่ม; ค้าง **Ready** นาน หรือ **Released** ไม่ขยับ
- **Cause**: Ready = ถึงเวลาแล้วแต่ **ไม่มี BTC WP ว่าง** (BTC เต็ม/จำนวนน้อย/target server ที่กำหนดไว้ล่ม); Released = รอเวลา/event/job ก่อนหน้า (predecessor) ยังไม่จบ
- **Check**: SM37 (start condition, target server) → SM50/SM66 (BTC ว่างไหม) → SM51 (server ยังอยู่ไหม) → RZ04 (operation mode/จำนวน BTC) → SM62 (event)
- **Fix**: รอ/ยกเลิก job ที่ยึด BTC นาน, เอา target server ที่ล่มออก, ปรับจำนวน BTC (rdisp/wp_no_btc หรือ operation mode), trigger event ที่รออยู่
- **Escalate**: Basis
- **Refs**: SAP Help Work Processes; SAP Help "Analyzing the Job Status"

## lock_issue

### R07 `lock_old_entries` — Lock ค้าง / "locked by user"
- **Symptoms**: ข้อความ "<object> is locked by user XXX"; SM12 มี lock อายุเกิน 1 วัน
- **Cause**: session ของ user ค้าง/หลุด, โปรแกรมไม่ปล่อย lock, **lock ถูกส่งต่อให้ update task ที่ยังไม่เสร็จหรือ error**
- **Check**: SM12 (owner, เวลา, table/argument) → SM04/AL08 (user ยัง login อยู่ไหม) → **SM13 (มี update ค้าง/ERR ของ user นั้นไหม)** → SM50 (WP ของ user)
- **Fix**: ให้ user ปิดงาน/ออกจากระบบก่อน; ปิด session ใน SM04; **ลบ lock ใน SM12 เฉพาะเมื่อยืนยันแล้วว่าไม่มี update ค้างและ user ไม่ได้ทำงานอยู่** และบันทึกไว้
- **Escalate**: functional (ตรวจความถูกต้องของข้อมูลหลังลบ)
- **Refs**: SAP Help Example: SAP Locking (SM12); SAP Help Update statuses

### R08 `lock_table_overflow` — Lock table overflow
- **Symptoms**: SM21/dump "lock table overflow", ผู้ใช้หลายคนบันทึกไม่ได้ (enqueue fail)
- **Cause**: lock table (ใน enqueue server) เต็ม — โปรแกรม/job ล็อกจำนวนมาก หรือขนาด `enque/table_size` เล็กเกิน
- **Check**: SM12 → Extras → Statistics (max fill/overflow) → SM12 list (ใครถือ lock เยอะ) → SM21 → RZ11 `enque/table_size`
- **Fix**: หา job/โปรแกรมที่ล็อกเยอะเกิน (ให้ dev ปรับ), เพิ่มขนาด lock table ใน profile (ต้อง restart enqueue/ASCS) ตามที่วิเคราะห์
- **Escalate**: developer, Basis
- **Refs**: SAP Help Work Processes (Enqueue)

## update_error

### R09 `update_terminated` — Update terminated (SM13 ERR)
- **Symptoms**: ผู้ใช้ได้ express mail "Update was terminated"; SM13 มีรายการสถานะ **ERR**
- **Cause**: update module (V1/V2) ล้ม — dump ใน update task, ข้อมูลผิด, key ซ้ำ, DB error
- **Check**: SM13 (สถานะ, user, เวลา, function module ที่ล้ม) → ST22 (dump ของ update task เวลาเดียวกัน) → SM21
- **Fix**: แก้ต้นเหตุก่อน (dev/functional), แล้วจึง **Repeat update** ใน SM13 ได้เฉพาะเมื่อมั่นใจว่าไม่ทำให้ข้อมูลซ้ำ; รายการที่แก้ไม่ได้ให้ลบตามขั้นตอน + แจ้ง functional ให้บันทึกธุรกรรมใหม่
- **Escalate**: functional/dev (ข้อมูลธุรกิจหาย/ไม่ครบ)
- **Refs**: SAP Help "Most Important Update Statuses" (SM13)

### R10 `update_deactivated` — Update deactivated
- **Symptoms**: ผู้ใช้บันทึกไม่ได้ทั้งระบบ, SM13/SM14 แสดงว่า update ถูก deactivate, SM21 มีข้อความเกี่ยวกับ update
- **Cause**: ระบบปิด update อัตโนมัติเมื่อเจอปัญหาร้ายแรง (มักเป็น DB error เช่น พื้นที่เต็ม/เชื่อมต่อไม่ได้)
- **Check**: SM14 (สถานะ update) → SM21 (สาเหตุ) → DB02/DB monitor (พื้นที่/การเชื่อมต่อ) → SM13
- **Fix**: แก้ต้นเหตุ (เช่น เพิ่มพื้นที่ DB) → activate update ใน SM14 → ตรวจรายการค้างใน SM13
- **Escalate**: DBA
- **Refs**: SAP Help Update Management

## transport_error

### R11 `transport_rc8` — Import RC = 8
- **Symptoms**: STMS import history แสดง RC 8 (สีแดง); หลัง import โปรแกรมมี syntax error หรือ object ไม่ active
- **Cause**: บาง object import/activate ไม่ได้ — syntax error, **object ที่พึ่งพายังไม่ถูก import (ลำดับผิด)**, ตาราง/โครงสร้างแปลงไม่ได้
- **Check**: STMS → import queue/history → **Logs ของ request** (ดูขั้นที่ RC 8 เช่น activation, import, generation) → SE01/SE09 (object ใน request) → SE80/SE38 (syntax check)
- **Fix**: ให้ dev แก้ใน DEV แล้วปล่อย request ใหม่ หรือ import request ที่ขาดก่อนแล้ว re-import ตามลำดับ; RC 4 อ่าน warning แต่ไม่ต้องหยุด
- **Escalate**: developer เจ้าของ request
- **Refs**: SAP Help "Return Codes in the Transport Log"; SAP Help "tp Return Codes"

### R12 `transport_rc12_or_stuck` — RC ≥ 12 / import ค้าง
- **Symptoms**: RC 12 / 16 หรือสูงกว่า, import ค้างสถานะ running นาน, "tp error"
- **Cause**: ปัญหานอกเนื้อหา request: tp/R3trans เชื่อม DB ไม่ได้, ไฟล์ใน `/usr/sap/trans` (cofiles/data) หายหรือสิทธิ์ไม่พอ, **job RDDIMPDP ไม่ทำงาน**, พื้นที่ดิสก์เต็ม
- **Check**: STMS import monitor + tp log (ALOG/SLOG) → SM37 (`RDDIMPDP` ใน client 000/client ปลายทาง) → OS: สิทธิ์และพื้นที่ `/usr/sap/trans` → SM21
- **Fix**: แก้สาเหตุ (permission/disk/DB), schedule RDDIMPDP ใหม่ (report RDDNEWPP), แล้ว re-import
- **Escalate**: Basis (มักต้องสิทธิ์ OS)
- **Refs**: SAP Help "tp Return Codes"

## user_auth

### R13 `user_locked` — User locked
- **Symptoms**: "User is locked. Please notify the person responsible"; login ไม่ได้; job/RFC ที่ใช้ user นี้ล้มด้วย
- **Cause**: ใส่รหัสผิดเกิน `login/fails_to_user_lock`, แอดมินล็อก (lock by administrator / CUA global lock), validity date หมด
- **Check**: SU01 (Lock status / Logon data: validity, user type) → SUIM (รายการ user ที่ล็อก) → SM21 / SM20 (security audit log ถ้าเปิดไว้) เพื่อดูว่ามีความพยายาม login ผิดจากที่ไหน
- **Fix**: ยืนยันตัวตนผู้ขอก่อน → ปลดล็อก/รีเซ็ตรหัส (SU01, หลายคนใช้ SU10) → ถ้าเป็น system/communication user ให้ตรวจว่ารหัสใน SM59/โปรแกรมปลายทางตรงกัน ไม่งั้นจะโดนล็อกซ้ำ
- **Escalate**: security team (ถ้าสงสัยการโจมตี)
- **Refs**: SAP Learning "Evaluate Users and Authorizations"

### R14 `auth_missing` — ไม่มีสิทธิ์
- **Symptoms**: "You are not authorized to use transaction XXX" / "No authorization for ..."; job ล้มด้วย authority check
- **Cause**: role ของ user ขาด authorization object/ค่า field ที่โปรแกรมเช็ค
- **Check**: **SU53** (ให้ user เปิดทันทีหลังเจอ error) → STAUTHTRACE / ST01 (trace การเช็คสิทธิ์ทั้งหมด) → SUIM (role ไหนมีสิทธิ์นั้น) → PFCG
- **Fix**: เพิ่มสิทธิ์ใน role ที่เหมาะสมผ่านกระบวนการอนุมัติ (แก้ใน DEV + transport), หลัก least privilege — ห้ามแก้ด้วยการให้ SAP_ALL
- **Escalate**: security/GRC team
- **Refs**: SAP Learning "Evaluate Users and Authorizations"; "Troubleshooting Authorization Checks"

## rfc_error

### R15 `rfc_connection_failed` — RFC/SM59 ล้ม
- **Symptoms**: dump CALL_FUNCTION_COMMUNICATION_FAILURE / SYSTEM_FAILURE; SM59 Connection Test ล้ม: "partner not reached", "Name or password is incorrect", "user locked", "timeout"
- **Cause**: ระบบปลายทางล่ม/host-instance ผิด/network-firewall, RFC user ล็อกหรือรหัสผิด, gateway ปฏิเสธ (registered program/ security rules)
- **Check**: SM59 (Connection Test → แล้ว Authorization/logon test) → ปลายทาง: SU01 RFC user → SMGW (gateway, registered programs) → SM21 / dev_rfc trace → ping/OS network
- **Fix**: แก้ข้อมูล destination, ปลดล็อก/ตั้งรหัส RFC user ให้ตรง, ประสาน network, ตรวจ gateway security
- **Escalate**: network team, ทีมระบบปลายทาง
- **Refs**: SAP Help "Displaying, Maintaining and Testing Destinations"

### R16 `rfc_trfc_queue` — tRFC/qRFC ค้าง
- **Symptoms**: ข้อมูล interface ไม่ไปถึงปลายทาง; SM58 มีรายการ error; SMQ1/SMQ2 queue สถานะ SYSFAIL / CPICERR / STOP
- **Cause**: ปลายทางล่มช่วงหนึ่ง (connection), error ใน function ปลายทาง, queue ถูก stop
- **Check**: SM58 (status text ของแต่ละ LUW) → SMQ1 (outbound) / SMQ2 (inbound) → SM59 (destination ยังใช้ได้ไหม) → ST22 ฝั่งปลายทาง
- **Fix**: แก้ต้นเหตุ → execute LUW ใหม่ใน SM58 (หรือ report RSARFCEX สำหรับจำนวนมาก) / unlock-activate queue ใน SMQ1/SMQ2; ระวังลำดับข้อมูลใน qRFC
- **Escalate**: ทีม interface/ระบบปลายทาง
- **Refs**: guru99 monitoring (SM58, SMQ1, SMQ2)

## out_of_scope (ไม่มี runbook — ใช้ทดสอบ min_score)
ตัวอย่าง log: spool request error (SP01), HANA log volume full, SSL certificate หมดอายุใน STRUST, Fiori launchpad tile ไม่ขึ้น, OS disk `/usr/sap` เต็ม, `DBSQL_DUPLICATE_KEY_ERROR` จาก Z-program, printer ไม่พิมพ์ → ระบบต้องตอบ `out_of_scope`
