---
doc_id: <snake_case_id เช่น job_cancelled>
category: <memory_dump | timeout | job_failure | lock_issue | update_error | transport_error | user_auth | rfc_error>
title: <ชื่อสั้น มี error code/อาการหลัก>
tcodes: [<T-code เรียงตามลำดับที่ควรเปิด>]
escalate_to: <basis | developer | security | dba | network | sap_support>
references:
  - <URL แหล่งที่ใช้สรุป 1>
  - <URL 2>
---
<!--
กติกา:
- เขียนเป็นภาษาอังกฤษ (log ส่วนใหญ่เป็นอังกฤษ; โมเดลเล็กทำงานกับอังกฤษได้ดีกว่า; bge-m3 ยังจับคำค้นภาษาไทยข้ามภาษาได้)
- ใช้หัวข้อ 6 อันนี้ "ตรงตัว" ทุกไฟล์ เพราะ chunker ตัดตาม "## " (1 หัวข้อ = 1 chunk)
- แต่ละหัวข้อ 40–150 คำ — สั้นพอให้ chunk คม ยาวพอให้มีบริบท
- ใส่ error code / ข้อความ error ที่พบจริงใน Symptoms (ช่วย BM25)
- เขียนด้วยภาษาตัวเอง ห้ามคัดลอกเอกสาร SAP ยาวๆ
-->

## Symptoms
<ข้อความ error ที่ผู้ใช้เห็น / ที่อยู่ใน log, ชื่อ runtime error, สถานะใน T-code, อาการที่ผู้ใช้บ่น>

## Cause
<สาเหตุที่พบบ่อย เรียงจากบ่อยสุด>

## Check
1. <T-code> — <ดูอะไร หาอะไร>
2. ...

## Fix
<วิธีแก้ตามสาเหตุ + ข้อควรระวัง (อะไรที่ห้ามทำ)>

## Escalate
<เมื่อไรต้องส่งต่อ และส่งให้ใคร พร้อมข้อมูลอะไร>

## References
- <ชื่อเอกสาร> — <URL>
