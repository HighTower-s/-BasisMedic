---
doc_id: mem_tsv_tnew_page_alloc
category: memory_dump
title: TSV_TNEW_PAGE_ALLOC_FAILED - internal table cannot be extended (out of memory)
tcodes: [ST22, ST02, RZ11, SM37, SM21]
escalate_to: developer
references:
  - https://help.sap.com/saphelp_gbt10/helpdata/en/49/1805ac005338a1e10000000a421937/content.htm
  - https://archive.sap.com/discussions/thread/2107282
---

## Symptoms
An ABAP program terminates with the runtime error TSV_TNEW_PAGE_ALLOC_FAILED and the short text
"No more storage space available for extending an internal table". It often happens in large
reports, month-end jobs or mass data loads. In a background job, SM37 shows the job as Canceled and
the job log points to the ABAP runtime error. Users may say "the report crashed after running a long time".

## Cause
The work process could not allocate more memory for an internal table. ABAP memory is allocated
roughly in the order roll area -> extended memory (shared) -> heap memory (private). When the
quotas are used up (parameters such as ztta/roll_extension, abap/heap_area_dia,
abap/heap_area_nondia, abap/heap_area_total) the dump is written. The most common root cause is the
program reading far more data than intended: a very wide selection, data growth, or code that loads
a whole table without filtering. Less often the instance is simply short of memory at that moment.

## Check
1. ST22 - open the dump. Read "Error analysis" (how much memory was requested and already used),
   "Information on where terminated" (program, include, line), "User and Transaction" (user, job name)
   and "Chosen variables" (size of the internal table).
2. ST02 - look at extended memory and heap memory usage and their history: was the instance short
   of memory at that time?
3. RZ11 - check current values of the memory parameters mentioned in the dump.
4. SM37 - if it was a job, check the variant/selection and whether data volume grew.
5. SM21 - check the system log around the same time for related memory messages.

## Fix
First reduce the data volume: narrow the selection, split the run (for example by period or plant),
or schedule it outside peak hours. If the program is custom (Z/Y), ask the developer to process data
in packages and filter in the database. For standard SAP programs, search SAP Notes with the keywords
from "How to correct the error". Increase memory parameters only after analysis, considering the
physical memory of the host; profile changes may need an instance restart.
Do not keep re-running the same job unchanged - it will fail again.

## Escalate
Custom program -> ABAP developer (attach the dump, selection and data volume).
Standard program without a matching SAP Note -> SAP Support incident with dump, SM21 and ST02 data.

## References
- SAP Help Portal - ABAP Dump Analysis (background) - https://help.sap.com/saphelp_gbt10/helpdata/en/49/1805ac005338a1e10000000a421937/content.htm
- SAP Community - TSV_TNEW_PAGE_ALLOC_FAILED discussion - https://archive.sap.com/discussions/thread/2107282
