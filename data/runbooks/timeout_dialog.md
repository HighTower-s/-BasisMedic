---
doc_id: timeout_dialog
category: timeout
title: TIME_OUT - dialog step exceeded the maximum run time
tcodes: [ST22, SM50, SM66, ST05, ST12, RZ11]
escalate_to: developer
references:
  - https://help.sap.com/saphelp_snc700_ehp01/helpdata/en/48/6360918c4a31cbe10000000a42189d/content.htm
  - https://help.sap.com/saphelp_gbt10/helpdata/en/49/1805ac005338a1e10000000a421937/content.htm
---

## Symptoms
A short dump named TIME_OUT with the short text "Time limit exceeded" appears in ST22. The user ran
a report or transaction from the screen and it died after roughly ten minutes. Users describe it as
"it spun for ages and then threw me out". The dump names the program and the line where the system
cut it off, which is wherever it happened to be, not necessarily the slow part.

## Cause
A dialog work process may only run one step for a limited time, controlled by the profile parameter
rdisp/max_wprun_time, whose traditional default is 600 seconds. Newer kernels may expose this as
rdisp/scheduler/max_runtime, so check the current value rather than assuming. The limit exists to
stop a single user occupying a dialog process indefinitely. The real cause is almost always a slow
database access or a selection returning far more data than intended, not the limit itself.

## Check
1. ST22 - read the dump for the program, the include and the line where it was terminated.
2. SM50 - if the run is still in progress, look at the current action and the table being read.
3. SM66 - the same across instances, useful when several users run the same report.
4. ST05 - take an SQL trace of a smaller run to find the expensive statement.
5. ST12 - a combined ABAP and SQL trace when it is unclear whether time goes to code or database.
6. RZ11 - display the current timeout parameter value and its documentation.

## Fix
Run the work as a background job: batch work processes are not subject to this dialog limit, and
this is the normal answer for month-end reports. Narrow the selection so less data is read. Ask the
developer or DBA to improve the statement, add an index or refresh statistics. Raising the timeout
parameter is a last resort because it applies to the whole instance and lets one user hold a dialog
process for longer.

## Escalate
Slow custom code or a missing index goes to the developer or DBA with the trace attached. A standard
SAP program that is slow without explanation is worth searching SAP Notes for.

## References
- SAP Help Portal - ICM and dispatcher parameters including rdisp/max_wprun_time - https://help.sap.com/saphelp_snc700_ehp01/helpdata/en/48/6360918c4a31cbe10000000a42189d/content.htm
- SAP Help Portal - ABAP Dump Analysis (background) - https://help.sap.com/saphelp_gbt10/helpdata/en/49/1805ac005338a1e10000000a421937/content.htm
