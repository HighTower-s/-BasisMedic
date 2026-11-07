---
doc_id: update_deactivated
category: update_error
title: Update deactivated - nobody in the system can save
tcodes: [SM14, SM21, DB02, SM13]
escalate_to: dba
references:
  - https://help.sap.com/saphelp_470/helpdata/en/e5/de86ea35cd11d3acb00000e83539c3/content.htm
  - https://blogs.sap.com/2012/10/19/sap-basis-daily-tasks/
---

## Symptoms
Saving fails across the whole system rather than for one user, and the calls arrive quickly from
everywhere. SM14 shows the update system as deactivated. SM21 carries messages about the update
being switched off. SM13 accumulates requests that are waiting rather than failing. The scope is
what separates this from a single terminated update: everyone is affected at once.

## Cause
The system deactivates updating by itself when it meets a serious, repeated problem, to avoid
losing data silently. The trigger is usually underneath SAP rather than in it: the database is out
of space, a tablespace is full, the database connection broke, or the filesystem holding the data
filled up. Treating it as an SAP problem and simply reactivating will fail again within minutes.

## Check
1. SM14 - confirm the update system status and when it was deactivated.
2. SM21 - find the first message in the sequence; that one names the real cause.
3. DB02 - check database and tablespace space, and recent growth.
4. SM13 - see how many requests are queued and waiting to be processed.

## Fix
Fix the underlying problem first - add space, restore the database connection, clear the filesystem.
Only then reactivate updating in SM14. Afterwards work through SM13 and confirm the queued requests
process cleanly, because some may still fail for their own reasons. Reactivating before the cause is
fixed simply repeats the outage and adds more queued work.

## Escalate
Database space and connectivity belong to the DBA, and this is usually their incident rather than
yours. Inform the functional teams that postings between the outage and the fix may need checking.

## References
- SAP Help Portal - Most Important Update Statuses - https://help.sap.com/saphelp_470/helpdata/en/e5/de86ea35cd11d3acb00000e83539c3/content.htm
- SAP Community Blogs - SAP Basis daily tasks (SM13, SM21, DB12) - https://blogs.sap.com/2012/10/19/sap-basis-daily-tasks/
