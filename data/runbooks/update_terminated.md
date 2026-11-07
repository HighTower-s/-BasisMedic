---
doc_id: update_terminated
category: update_error
title: Update was terminated - SM13 entries with status ERR
tcodes: [SM13, ST22, SM21]
escalate_to: developer
references:
  - https://help.sap.com/saphelp_470/helpdata/en/e5/de86ea35cd11d3acb00000e83539c3/content.htm
  - https://help.sap.com/saphelp_gbt10/helpdata/en/49/1805ac005338a1e10000000a421937/content.htm
---

## Symptoms
The user receives an express message in their SAP inbox saying "Update was terminated", usually a
minute or two after saving. SM13 lists one or more update requests with status ERR for that user.
From the user's point of view the save appeared to succeed but the data is not in the system, which
makes this more confusing to them than an outright error on screen.

## Cause
The user's dialog step finished and handed the database work to the update task, which then failed.
Common reasons are a short dump inside the update function module, data that violates a check only
evaluated at update time, a duplicate key, or a database error such as a full tablespace. Because
the failure happens asynchronously, the dump belongs to the update work process rather than to the
user's session.

## Check
1. SM13 - open the failed entry: status, user, time, and the function module that failed.
2. ST22 - find the dump from the same timestamp, which carries the real technical reason.
3. SM21 - the system log, which shows database-level problems around the same time.

## Fix
Correct the cause before touching the queue. Once it is genuinely fixed, SM13 can repeat the update,
but only do that when you are confident the transaction has not already been posted in part, or you
will create duplicates. Entries that cannot be repaired should be deleted following your local
procedure, and the functional team must then be told to re-enter the business transaction, because
the data is simply missing until they do.

## Escalate
Dumps inside update modules go to the developer. Missing or incomplete business data is a functional
matter. Repeated failures caused by database space belong to the DBA.

## References
- SAP Help Portal - Most Important Update Statuses - https://help.sap.com/saphelp_470/helpdata/en/e5/de86ea35cd11d3acb00000e83539c3/content.htm
- SAP Help Portal - ABAP Dump Analysis (background) - https://help.sap.com/saphelp_gbt10/helpdata/en/49/1805ac005338a1e10000000a421937/content.htm
