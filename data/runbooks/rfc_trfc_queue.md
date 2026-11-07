---
doc_id: rfc_trfc_queue
category: rfc_error
title: tRFC and qRFC entries stuck - SM58 errors, SMQ1 and SMQ2 queues blocked
tcodes: [SM58, SMQ1, SMQ2, SM59, ST22]
escalate_to: basis
references:
  - https://help.sap.com/saphelp_46c/helpdata/en/22/042638488911d189490000e829fbbd/content.htm
  - https://www.guru99.com/system-monitoring-performance-checks.html
---

## Symptoms
Data stops arriving at the receiving system while this system reports no error to users. SM58 lists
entries with error status. SMQ1 or SMQ2 show queues in status SYSFAIL, CPICERR or STOP. Unlike a
failed connection test, the connection may now work again - the entries simply stayed behind after an
earlier outage and nothing has retried them.

## Cause
The target was briefly unreachable and the calls were parked for retry, or the function module in
the target raised an error so the entry stayed in the queue, or a queue was stopped manually or by a
previous error and never released. For qRFC the order of entries matters: one blocked entry at the
head holds everything behind it, which is why one stuck record can stop an entire interface.

## Check
1. SM58 - read the status text of each failed logical unit of work; it names the real reason.
2. SMQ1 - check outbound queues and their status.
3. SMQ2 - check inbound queues on the receiving side.
4. SM59 - confirm the destination works now, so you know whether the cause has gone.
5. ST22 - look for dumps in the target system at the time the entries failed.

## Fix
Fix the cause first, then re-execute. SM58 can run a single unit again, and the standard report
RSARFCEX processes many at once. Unlock and activate stopped queues in SMQ1 or SMQ2. With qRFC,
respect the sequence: do not skip a blocked entry to clear the backlog, because later entries may
depend on the one you skipped and the receiving data will be inconsistent.

## Escalate
Errors raised inside the target's function modules belong to the interface or receiving-system team.
Recurring queue stoppages are worth raising as a design question rather than clearing by hand daily.

## References
- SAP Help Portal - Displaying, Maintaining and Testing Destinations - https://help.sap.com/saphelp_46c/helpdata/en/22/042638488911d189490000e829fbbd/content.htm
- Guru99 - SAP monitoring (SM58, SMQ1, SMQ2) - https://www.guru99.com/system-monitoring-performance-checks.html
