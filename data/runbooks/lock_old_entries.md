---
doc_id: lock_old_entries
category: lock_issue
title: Object is locked by user - stale lock entries in SM12
tcodes: [SM12, SM04, AL08, SM13, SM50]
escalate_to: basis
references:
  - https://help.sap.com/saphelp_nw73/helpdata/en/41/7af4c8a79e11d1950f0000e82de14a/content.htm
  - https://help.sap.com/saphelp_470/helpdata/en/e5/de86ea35cd11d3acb00000e83539c3/content.htm
---

## Symptoms
A user cannot edit a document and gets a message naming someone else, such as "Purchase order
4500001234 is locked by user JSMITH". Often the named user left hours or days ago. SM12 shows lock
entries older than a day. Sometimes several users are blocked on the same object, and the request
arrives as "please remove this lock" rather than as an error log.

## Cause
A session ended without releasing its lock, usually because a client crashed or a connection
dropped. A program may hold a lock longer than intended. Importantly, the lock may have been handed
to the update task: when a user saves, the lock is inherited by the update process and is only
released when that update completes. If the update failed or is still queued, the lock is doing its
job and deleting it would be wrong.

## Check
1. SM12 - find the entry and note the owner, the time it was created, and the table and argument.
2. SM04 - is that user still logged on to this instance?
3. AL08 - the same question across all instances, since the session may live elsewhere.
4. SM13 - the decisive check: does that user have an open or failed update request?
5. SM50 - is a work process still active for that user?

## Fix
Prefer the gentle route: ask the user to close the transaction or log off, which releases the lock
cleanly. If the session is genuinely dead, end it in SM04. Delete the entry in SM12 only after
confirming that there is no pending or failed update for that user and that the user is not working,
and record what you deleted and why. Deleting a lock that belongs to a queued update can leave the
document half-posted.

## Escalate
After deleting a lock, ask the functional team to verify the document is consistent. If stale locks
appear daily from the same program, hand it to the developer.

## References
- SAP Help Portal - Example Program: SAP Locking (enqueue and dequeue, SM12) - https://help.sap.com/saphelp_nw73/helpdata/en/41/7af4c8a79e11d1950f0000e82de14a/content.htm
- SAP Help Portal - Most Important Update Statuses - https://help.sap.com/saphelp_470/helpdata/en/e5/de86ea35cd11d3acb00000e83539c3/content.htm
