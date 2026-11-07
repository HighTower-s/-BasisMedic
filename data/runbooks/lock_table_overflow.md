---
doc_id: lock_table_overflow
category: lock_issue
title: Lock table overflow - the enqueue table is full
tcodes: [SM12, SM21, RZ11, SM50]
escalate_to: developer
references:
  - https://help.sap.com/saphelp_nw73/helpdata/en/41/7af4c8a79e11d1950f0000e82de14a/content.htm
  - https://help.sap.com/saphelp_nw73/helpdata/en/fc/eb2e7d358411d1829f0000e829fbfe/content.htm
---

## Symptoms
Many users suddenly cannot save at once, and the messages mention that a lock could not be set or
that the lock table has overflowed. SM21 contains lock table overflow entries. Short dumps about
failed enqueue operations may appear in the same minutes. The breadth is the signal: a single stale
lock blocks one document, whereas an overflow blocks everyone.

## Cause
The lock table lives in the enqueue server's shared memory and holds a finite number of entries,
sized by the profile parameter enque/table_size. It fills up when a program or mass job takes an
unusually large number of locks and holds them inside one long transaction, or when the table is
simply sized smaller than the workload needs. A mass update written to lock every record before
committing is the classic cause.

## Check
1. SM12 - use Extras then Statistics to see peak fill and whether an overflow was recorded.
2. SM12 - list current entries and sort by owner to find who holds thousands of them.
3. SM21 - confirm the overflow messages and their exact timing.
4. RZ11 - read the current value of enque/table_size.
5. SM50 - identify the work process and program responsible.

## Fix
Deal with the cause first: find the job or program taking excessive locks and have it changed to
commit in smaller packages instead of locking everything at once. That is usually a code change, not
a parameter change. Enlarging the lock table in the profile is legitimate once the real demand is
understood, but it needs a restart of the enqueue service, so plan it rather than doing it mid-day.

## Escalate
A program locking in bulk goes to the developer with the SM12 statistics attached. Sizing and the
restart are Basis work and need a maintenance window.

## References
- SAP Help Portal - Example Program: SAP Locking (enqueue and dequeue) - https://help.sap.com/saphelp_nw73/helpdata/en/41/7af4c8a79e11d1950f0000e82de14a/content.htm
- SAP Help Portal - Work Processes, including the enqueue work process - https://help.sap.com/saphelp_nw73/helpdata/en/fc/eb2e7d358411d1829f0000e829fbfe/content.htm
