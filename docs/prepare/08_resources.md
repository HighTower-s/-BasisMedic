# 08 — Resources (แหล่งข้อมูลที่เตรียมไว้)

> ✔ = เปิดตรวจเนื้อหาแล้ว (6 พ.ย. 2026) · ○ = จากผลค้นหา ยังไม่ได้เปิดอ่านละเอียด
> URL แบบ `help.sap.com/saphelp_*` เป็นเอกสารรุ่นเก่าแต่ยังเปิดได้และเนื้อหาหลักยังใช้ได้กับ ABAP platform รุ่นใหม่ — ใช้เป็น reference ใน runbook ได้

## 1. SAP Help Portal (เอกสารทางการ)
| หัวข้อ | ใช้กับ runbook | URL | |
|---|---|---|---|
| ABAP Dump Analysis – Background (ST22 คืออะไร, short dump) | R01–R03, ส่วน ST22 | https://help.sap.com/saphelp_gbt10/helpdata/en/49/1805ac005338a1e10000000a421937/content.htm | ✔ |
| Analyzing ABAP Runtime Errors (มุม ADT/ST22) | ST22 | https://help.sap.com/saphelp_em92/helpdata/de/4e/c385946e391014adc9fffe4e204223/content.htm (ถ้าขึ้นภาษาเยอรมันให้เปลี่ยน `/de/` เป็น `/en/`) | ✔ |
| Analyzing the Job Status (job log, job details, check status) | R05, R06 | https://help.sap.com/saphelp_gbt10/helpdata/en/4b/272d08d1341780e10000000a42189c/content.htm | ✔ |
| Work Processes (DIA/UPD/BTC/ENQ/SPO + dispatcher) | primer, R02, R06, R08 | https://help.sap.com/saphelp_nw73/helpdata/en/fc/eb2e7d358411d1829f0000e829fbfe/content.htm | ✔ |
| Most Important Update Statuses (SM13: INIT, ERR, …) | R09, R10, R07 | https://help.sap.com/saphelp_470/helpdata/en/e5/de86ea35cd11d3acb00000e83539c3/content.htm | ✔ |
| Example Program: SAP Locking (enqueue/dequeue, SM12) | R07, R08 | https://help.sap.com/saphelp_nw73/helpdata/en/41/7af4c8a79e11d1950f0000e82de14a/content.htm | ✔ |
| Return Codes in the Transport Log (0/4/8/12) | R11, R12 | https://help.sap.com/saphelp_46c/helpdata/en/57/38e26c4eb711d182bf0000e829fbfe/content.htm | ✔ |
| tp Return Codes (combined RC, >200, `explainrc`) | R11, R12 | https://help.sap.com/saphelp_nwes72/helpdata/en/3a/58c2e9f47611d184850000e8a57770/content.htm | ✔ |
| Displaying, Maintaining and Testing Destinations (SM59) | R15, R16 | https://help.sap.com/saphelp_46c/helpdata/en/22/042638488911d189490000e829fbbd/content.htm | ✔ |
| ICM parameter (ระบุว่า `rdisp/max_wprun_time` default 600 วินาที) | R03 | https://help.sap.com/saphelp_snc700_ehp01/helpdata/en/48/6360918c4a31cbe10000000a42189d/content.htm | ✔ |

## 2. SAP Learning (learning.sap.com — อ่านบนเว็บได้)
คอร์สหลักสำหรับ Basis มือใหม่ (เทียบ ADM100): **Technical Implementation and Operation I of SAP S/4HANA and SAP Business Suite**
https://learning.sap.com/courses/technical-implementation-and-operation-i-of-sap-s-4hana-and-sap-business-suite ✔
บทที่ควรอ่าน (เรียงตามลำดับ):
1. Describing the Architecture of SAP Systems
2. Explaining the Basic Architecture of AS ABAP and AS Java / Describing AS ABAP
3. Describing Software Logistics for AS ABAP based SAP systems (transport)
4. Users and Authorizations in AS ABAP (ทั้งหมวด) — โดยเฉพาะ **Evaluate Users and Authorizations** ✔ https://learning.sap.com/courses/technical-implementation-and-operation-i-of-sap-s-4hana-and-sap-business-suite/evaluate-users-and-authorizations
5. Describing Remote Function Calls and BAPIs
6. System Monitoring and Troubleshooting: **Using Local Monitoring Tools** ✔ (RZ20, SMICM, SMGW) และ **Troubleshooting Procedures** ✔ (ขั้นตอน isolate → analyze → SAP Notes → compare → SAP Support) https://learning.sap.com/courses/technical-implementation-and-operation-i-of-sap-s-4hana-and-sap-business-suite/troubleshooting-procedures
7. Starting and Stopping AS ABAP / Configuring SAP Systems via Profile Parameters
เสริม: Troubleshooting Authorization Checks ○ https://learning.sap.com/courses/exploring-the-authorization-concept-for-sap-s-4hana-and-sap-business-suite/troubleshouting-authorization-checks

## 3. SAP Community / บทความ (มุมปฏิบัติจริง)
| หัวข้อ | URL | |
|---|---|---|
| Thread วิเคราะห์ TSV_TNEW_PAGE_ALLOC_FAILED (parameter, ST02, แนวแก้) | https://archive.sap.com/discussions/thread/2107282 | ✔ |
| SAP Basis daily tasks (DB12, SM51, SM13, SM21, SM37) | https://blogs.sap.com/2012/10/19/sap-basis-daily-tasks/ | ✔ |
| Basis daily monitoring T-codes | https://blogs.sap.com/t5/technology-blogs-by-members/basis-daily-monitoring-t-codes/bc-p/13593835 | ○ |
| SAP Basis Monitoring T-codes & Health Checks (17 T-codes อธิบายทีละตัว) | https://www.guru99.com/system-monitoring-performance-checks.html | ✔ |
| Checking the job log in SM37 | https://hicron.com/sap101/checking-the-job-log-in-sm37 | ○ |
| Troubleshooting canceled jobs (blog) | https://rakshitranjansingh.blogspot.com/p/troubleshooting-canceled-jobs.html | ○ |

## 4. ระบบ SAP สำหรับฝึก (ถ้าอยากลองของจริง — ไม่บังคับ)
- **ABAP Cloud Developer Trial** (Docker image ฟรีจาก SAP) https://hub.docker.com/r/sapse/abap-cloud-developer-trial ○ — ใช้ทรัพยากรเครื่องสูงมาก ตรวจ requirement ในหน้า Docker Hub ก่อน
- ประกาศ/วิธีติดตั้ง: https://community.sap.com/t5/technology-blog-posts-by-sap/abap-cloud-developer-trial-2022-available-now/ba-p/13598069 ○
> ถ้าได้รันจริง: เปิด ST22/SM37/SM12/SM50 ถ่ายภาพหน้าจอไว้ใช้ในรายงาน/สัมภาษณ์ และสร้าง dump จริงเพื่อนำรูปแบบ log มาใช้ใน eval (ระบุในรายงาน)

## 5. แหล่งของวิชา + เครื่องมือ
| อะไร | URL |
|---|---|
| Reference app (อ่าน `CODE_TOUR.md`, `eval/eval.py`, `agent/loop.py`, `app/store.py`) | https://github.com/Nat-D/kmitl-llm-app-demo |
| Course proxy (ตาม reference `.env.example`) | `https://llm.nat-d.uk/v1` |
| rank-bm25 | https://github.com/dorianbrown/rank_bm25 |
| Pydantic v2 | https://docs.pydantic.dev/ |
| OpenAI function calling (รูปแบบ `tools=` / `tool_calls`) | https://platform.openai.com/docs/guides/function-calling |
| FastAPI | https://fastapi.tiangolo.com/ |
| uv | https://docs.astral.sh/uv/ |
| Mermaid (diagram) | https://mermaid.js.org/ |

## 6. สิ่งที่ใช้ไม่ได้ / ต้องระวัง
- **SAP Notes / KBA** (`me.sap.com`, `userapps.support.sap.com`) ต้องใช้ S-user ของลูกค้า — นักศึกษาไม่มี; หน้า preview บางส่วนเห็นได้แต่ **อย่าคัดลอกลง corpus**
- **ลิขสิทธิ์**: เอกสาร SAP Help/Learning เป็นของ SAP → corpus ของเราต้องเป็น **บทสรุปที่เขียนเอง** + ใส่ URL ในหัวข้อ References ของแต่ละ runbook (ทำให้ "commit raw data" ได้โดยไม่ละเมิด)
- Scribd/เว็บรวมไฟล์ PDF ที่อัปโหลดโดยไม่ทราบที่มา → ไม่ใช้
- ข้อมูลใน forum เก่า (2008–2013) อาจล้าสมัย — ใช้เป็นแนวคิด ไม่ใช่ค่าพารามิเตอร์ตายตัว
