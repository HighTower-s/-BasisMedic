---
doc_id: job_cancelled
category: job_failure
title: Background job status Canceled - read the job log first
tcodes: [SM37, ST22, SM21, SU01]
escalate_to: basis
references:
  - https://help.sap.com/saphelp_gbt10/helpdata/en/4b/272d08d1341780e10000000a42189c/content.htm
  - https://hicron.com/sap101/checking-the-job-log-in-sm37
---

## Symptoms
SM37 shows the job with status Canceled, usually in red. The job log ends with a message such as
"Job cancelled after system exception ERROR_MESSAGE", or names an ABAP runtime error with
"ABAP/4 processor: <dump name>". Downstream work that depended on the job is missing its data, and
the first sign is often a user asking why a report or interface file is empty this morning.

## Cause
Several very different things end up looking the same here, which is why the job log must be read
before anything else. A dump inside the program, an error message raised deliberately by the
program, a wrong or deleted variant, a step user that is locked, expired or short of authorisations,
a missing file or unreachable target directory, or an instance restart while the job was running.

## Check
1. SM37 - open the Job log before forming any theory; it names the actual failure.
2. ST22 - if the log mentions the ABAP processor, find the dump from the same timestamp.
3. SM21 - the system log around that time, for restarts and resource messages.
4. SU01 - check the step user shown in the job details for lock status and validity.

## Fix
Repair the underlying cause first: pass the dump to the developer, unlock or renew the step user,
correct the variant, or restore the missing file. Only then repeat the job, normally by copying it
from SM37 rather than editing history. Confirm with the job owner that a rerun is safe before
starting it. Some jobs must not run twice, especially posting and payment runs, because the first
partial run may already have created documents.

## Escalate
Ask the functional owner before any rerun of a job that posts data. Dumps go to the developer. If
the job failed because the instance restarted, that is a Basis question.

## References
- SAP Help Portal - Analyzing the Job Status - https://help.sap.com/saphelp_gbt10/helpdata/en/4b/272d08d1341780e10000000a42189c/content.htm
- Hicron SAP101 - Checking the job log in SM37 - https://hicron.com/sap101/checking-the-job-log-in-sm37
