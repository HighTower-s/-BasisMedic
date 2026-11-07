# 06 — SAP Basis สำหรับมือใหม่ (Primer)

> เป้าหมาย: อ่านจบแล้ว (1) เขียน runbook ได้ถูก (2) คุยกับผู้สัมภาษณ์ตำแหน่ง Basis ได้รู้เรื่อง
> แหล่งอ้างอิงทั้งหมดอยู่ใน `08_resources.md`

---

## 1. SAP คืออะไร
- **SAP** = บริษัทซอฟต์แวร์เยอรมัน ผลิตระบบ **ERP** (Enterprise Resource Planning) ที่บริษัทใหญ่ใช้ทำบัญชี จัดซื้อ ขาย ผลิต HR ฯลฯ ในระบบเดียว
- โมดูลธุรกิจที่จะได้ยินบ่อย: **FI** (บัญชี), **CO** (ต้นทุน), **MM** (จัดซื้อ/คลัง), **SD** (ขาย), **PP** (ผลิต), **HCM** (บุคคล)
- รุ่น: **SAP ECC** (รุ่นเก่า รันบน DB หลายยี่ห้อ) → **SAP S/4HANA** (รุ่นใหม่ รันบน SAP HANA เท่านั้น)
- โปรแกรมของ SAP เขียนด้วยภาษา **ABAP** และรันบน **Application Server ABAP (AS ABAP)** ซึ่งเป็นส่วนหนึ่งของ "SAP NetWeaver / ABAP Platform"
- โปรแกรมที่บริษัทเขียนเพิ่มเอง ชื่อจะขึ้นต้นด้วย **Z** หรือ **Y** (เช่น `ZFI_MONTHLY_REPORT`) — สำคัญมากตอน triage: dump ใน Z-program มักต้องส่งต่อ developer

## 2. SAP Basis คือใคร ทำอะไร
**Basis** = ทีมดูแล "ระบบ" ของ SAP (คล้าย sysadmin + DBA + middleware admin) ไม่ใช่คนตั้งค่าธุรกิจ (functional) หรือคนเขียน ABAP (developer)

งานหลัก:
| กลุ่มงาน | ตัวอย่าง |
|---|---|
| Monitoring ประจำวัน | ดู dump, system log, job, update, lock, work process, backup |
| Incident / troubleshooting | ระบบช้า, job ล้ม, user เข้าไม่ได้, interface (RFC) ล่ม |
| Transport management | ย้ายของจาก DEV → QAS → PRD ด้วย STMS |
| User & security (บางที่แยกทีม) | สร้าง/ล็อก user, role, ตรวจสิทธิ์ |
| Installation / upgrade / patch | ติดตั้งระบบ, kernel upgrade, support package, OS/DB patch |
| Performance tuning | memory parameter, buffer, SQL ช้า |
| Start/stop, backup, system copy, client copy | งาน operation |

## 3. สถาปัตยกรรม 3 ชั้น (3-tier)
```
 Presentation   : SAP GUI / Fiori (browser)        ← ผู้ใช้
        │
 Application    : AS ABAP instances (ทำงานจริง)      ← Basis ดูแลเยอะสุด
        │          - Dispatcher + Work Processes
        │          - Gateway (RFC), ICM (HTTP)
        │          - ASCS: Message Server + Enqueue Server
 Database       : SAP HANA / Oracle / SQL Server / DB2 ...
```
คำศัพท์:
- **SID** = รหัส 3 ตัวอักษรของระบบ เช่น `PRD`, `QAS`, `DEV`
- **Instance** = กลุ่ม process บนเครื่องหนึ่ง มี instance number 2 หลัก (00–97)
- **ASCS** (ABAP Central Services) = Message Server (ประสานงานหลาย app server, load balancing) + **Enqueue Server** (ถือ lock table)
- **PAS/AAS** = Primary/Additional Application Server
- **Client** = "บริษัทเสมือน" ภายในระบบเดียว ข้อมูลแยกกันด้วยฟิลด์ `MANDT` (เช่น client 000 = SAP standard, 100 = production client)
- **Landscape**: DEV (พัฒนา) → QAS (ทดสอบ) → PRD (ใช้งานจริง) — ห้ามแก้ใน PRD ตรงๆ ต้องผ่าน transport

## 4. Work Process — ต้องเข้าใจให้แม่น
**Dispatcher** รับ request แล้วส่งให้ work process (WP) ที่ว่างตาม "ประเภท"

| Type | ชื่อเต็ม | ทำอะไร | ปัญหาที่เจอบ่อย |
|---|---|---|---|
| **DIA** | Dialog | งานที่ user กดหน้าจอ (dialog step) | **TIME_OUT** เมื่อ dialog step นานเกิน `rdisp/max_wprun_time`; WP เต็ม ระบบค้าง |
| **BTC** | Background | background job (ไม่ต้องมีคนกด) | job ค้าง Ready เพราะ BTC ไม่ว่าง |
| **UPD** | Update (V1) | เขียน DB แบบ asynchronous ส่วนสำคัญ | update terminated (SM13 ERR) |
| **UP2** | Update V2 | update ส่วนรอง (เช่น statistics) | |
| **ENQ** | Enqueue | จัดการ lock table (ปกติอยู่ใน ASCS) | lock ค้าง, lock table overflow |
| **SPO** | Spool | ส่งงานพิมพ์ | spool ค้าง (SP01) |

ดูสถานะ WP: **SM50** (instance ที่ login อยู่), **SM66** (ทุก instance), **SM51** (รายการ app server)
สถานะ WP: `Waiting` (ว่าง), `Running`, `Stopped`, `On hold`, `PRIV` (ใช้ heap memory ส่วนตัว → ผูกกับ user)

## 5. Memory ของ ABAP (พอให้เข้าใจ dump memory)
ลำดับการจองหน่วยความจำของ dialog WP (ภาพรวม): **roll area** → **extended memory (EM)** (ใช้ร่วมกัน) → **heap memory** (ส่วนตัว, WP เข้าโหมด PRIV)
พารามิเตอร์ที่จะเจอใน dump/forum (ดูค่าจริงด้วย **RZ11**, ดูการใช้ด้วย **ST02**):
| parameter | ความหมาย |
|---|---|
| `ztta/roll_area` | roll area ต่อ user context |
| `ztta/roll_extension` | EM สูงสุดต่อ user context |
| `em/initial_size_MB` | ขนาด EM ทั้ง instance (ใช้ร่วมกัน) |
| `abap/heap_area_dia` / `abap/heap_area_nondia` | heap สูงสุดต่อ dialog / non-dialog (background) WP |
| `abap/heap_area_total` | heap รวมทั้ง instance |
> ⚠ หลักคิด Basis ที่ดี: dump memory ส่วนใหญ่เกิดจาก **โปรแกรมดึงข้อมูลมากเกิน** (selection กว้าง, ข้อมูลโต) — แก้ที่ต้นเหตุก่อน (ลด selection, แบ่งรัน, ให้ dev แก้) เพิ่ม parameter เป็นทางเลือกท้ายๆ และต้องดูหน่วยความจำเครื่องด้วย

## 6. Transport (Change and Transport System)
- การแก้ไขใน DEV ถูกเก็บใน **transport request** (เช่น `DEVK900123`) ประเภท Workbench (โปรแกรม/object) หรือ Customizing (ค่าตั้ง)
- release ใน **SE01/SE09/SE10** → ไฟล์ถูก export ไปที่ `/usr/sap/trans` (`cofiles/`, `data/`) → import เข้า QAS/PRD ด้วย **STMS** (Transport Management System) โดยโปรแกรม `tp` และ `R3trans`
- **Return code** ของ import:
  | RC | ความหมาย |
  |---|---|
  | 0 | สำเร็จ |
  | 4 | สำเร็จแต่มี warning (ควรอ่าน) |
  | 8 | บาง object import ไม่ได้ (เช่น syntax error, object ที่พึ่งพายังไม่มา) — ต้องแก้ |
  | 12 ขึ้นไป | error ร้ายแรง มักไม่ใช่เนื้อหาใน request (tp/R3trans/ไฟล์/สิทธิ์/DB) — แจ้ง Basis |
- background job **RDDIMPDP** ต้องทำงาน ไม่งั้น import บางขั้นไม่เดิน

## 7. User & Authorization
- **SU01** สร้าง/แก้/ล็อก/ปลดล็อก user, reset password · **SU10** ทำทีละหลายคน · **SUIM** รายงาน (user ที่ล็อก, ใครมีสิทธิ์อะไร)
- **PFCG** สร้าง role (ชุดสิทธิ์) → profile
- **SU53** ดูว่า "สิทธิ์ที่ขาด" ของการเช็คครั้งล่าสุดคืออะไร · **STAUTHTRACE / ST01** trace สิทธิ์ทั้งหมด
- user ถูกล็อกเพราะใส่รหัสผิดเกินค่า `login/fails_to_user_lock` (ดูค่าจริงใน RZ11) หรือแอดมินล็อก
- ประเภท user: Dialog (คน), System (ใช้ใน RFC/background ระหว่างระบบ), Communication, Service, Reference — **system/communication user โดนล็อก = RFC/job ล้มทั้งชุด** (เชื่อมกับ incident rfc_error, job_failure)

## 8. RFC (คุยกันระหว่างระบบ)
- **RFC** = Remote Function Call; ตั้งปลายทางใน **SM59** (type 3 = ABAP system, T = TCP/IP program, H/G = HTTP)
- ทดสอบ: SM59 → Connection Test / Authorization (logon) test
- **tRFC** (transactional) ดู error ใน **SM58**; **qRFC** queue ใน **SMQ1** (outbound) / **SMQ2** (inbound); gateway **SMGW**
- dump ที่เกี่ยว: `CALL_FUNCTION_COMMUNICATION_FAILURE`, `CALL_FUNCTION_SYSTEM_FAILURE`, `CALL_FUNCTION_REMOTE_ERROR`

## 9. Background job
- สร้าง **SM36**, ดู/จัดการ **SM37**
- สถานะ: **Scheduled** (ยังไม่ release) → **Released** (รอเวลา/เงื่อนไข) → **Ready** (ถึงเวลาแล้ว รอ BTC ว่าง) → **Active** → **Finished** / **Canceled**
- job Canceled → อ่าน **Job log** ก่อนเสมอ → มักเจอ dump (ST22) หรือ message error ของโปรแกรม; ดู Job details ว่ารันบน server/WP ไหน; ดู SM21 ช่วงเวลานั้น
- สาเหตุพบบ่อย: dump ในโปรแกรม, variant ผิด, **step user ถูกล็อก/หมดอายุ**, สิทธิ์ไม่พอ, ไฟล์ไม่มี, ระบบ restart ระหว่างรัน

## 10. Update & Lock (คู่กัน — ระวัง!)
- SAP เขียน DB หลายขั้นแบบ asynchronous ผ่าน **update task**; ถ้าล้ม user ได้ express mail "Update was terminated" → ดู **SM13** (สถานะ ERR) → ดู dump ที่ผูกกับ update ใน ST22
- **Lock (enqueue)** = lock แบบ logical ของ SAP (ไม่ใช่ DB lock) ดู/ลบใน **SM12**
- ⚠ **lock ที่ถูกส่งต่อให้ update task จะค้างจนกว่า update เสร็จ** → ก่อนลบ lock ใน SM12 ต้องเช็ค SM13 และเช็คว่า user ยังทำงานอยู่ไหม (SM04/AL08) — ลบผิดอาจทำข้อมูลไม่สอดคล้อง

## 11. Monitoring ประจำวัน (daily checklist ของ Basis)
| T-code | ดูอะไร |
|---|---|
| SM51 / SM50 / SM66 | app server, work process, งานที่รันนาน |
| SM21 | system log (error/warning) |
| ST22 | ABAP dump ของเมื่อวาน/วันนี้ |
| SM37 | job ที่ Canceled |
| SM13 | update ที่ล้ม |
| SM12 | lock เก่าค้าง (เช่น เกิน 1 วัน) |
| SM58 / SMQ1 / SMQ2 | RFC/queue ค้าง |
| SP01 | spool error |
| ST02 / ST06 | buffer/memory, OS CPU/memory |
| DB02 / DB12 (หรือ DBACOCKPIT) | ขนาด DB/tablespace, ผล backup |
| AL08 / SM04 | user ที่ login |
| RZ20 | CCMS alert monitor |

## 12. SAP HANA (พอรู้)
- in-memory column-store database ของ SAP; S/4HANA บังคับใช้
- เครื่องมือ: HANA Cockpit / HANA Studio, `DBACOCKPIT` ใน SAP GUI; ปัญหาที่เจอ: memory เต็ม, log volume เต็ม, backup ล้ม (ใน BasisMedic ถือเป็น out_of_scope)

## 13. ศัพท์ที่ควรรู้ (glossary)
| คำ | ความหมาย |
|---|---|
| T-code | Transaction code — ทางลัดเปิดหน้าจอ เช่น SM37 |
| Short dump / ABAP dump | บันทึกตอนโปรแกรม ABAP ล้มด้วย runtime error (ดูใน ST22) |
| Kernel | โปรแกรม C ระดับล่าง (disp+work, tp, R3trans) ที่รัน SAP |
| Profile | ไฟล์ตั้งค่า (DEFAULT.PFL, instance profile) แก้ผ่าน RZ10, ดูค่าปัจจุบัน RZ11 |
| SAP Note / KBA | เอกสารแก้ปัญหาของ SAP (ต้องมี S-user) |
| S-user | บัญชีลูกค้าสำหรับเข้า SAP Support Portal / SAP for Me |
| Solution Manager | ระบบกลางสำหรับ monitor หลายระบบ |
| LUW | Logical Unit of Work — หน่วยการทำธุรกรรม |
| Dev trace | ไฟล์ trace ระดับ OS เช่น `dev_w0`, `dev_disp` (ดูผ่าน ST11 หรือ SM50) |

## 14. เตรียมสัมภาษณ์ฝึกงาน Basis (ฝึกตอบ)
1. Basis ต่างจาก ABAP developer / functional ยังไง?
2. อธิบาย 3-tier architecture และ work process types
3. เจอ dump `TIME_OUT` จะทำยังไง? (ST22 → ดูโปรแกรม/user → SM50/SM66 → แนะนำรันเป็น background หรือให้ dev ปรับ SQL → ไม่รีบเพิ่ม `rdisp/max_wprun_time`)
4. job Canceled ตอนตี 2 จะเริ่มดูตรงไหน? (SM37 job log → ST22 → SM21 → เช็ค step user)
5. transport RC=8 แปลว่าอะไร?
6. ทำไมต้องระวังการลบ lock ใน SM12?
7. DEV/QAS/PRD คืออะไร ทำไมห้ามแก้ใน PRD?
8. (ใช้โปรเจกต์) "ผมทำ BasisMedic ซึ่งบังคับให้ผมศึกษา incident 8 ประเภท… วัดผลได้ recall@3 = …"
