---
doc_id: timeout_long_running_wp
category: timeout
title: Work processes running too long - no free processes, system feels slow
tcodes: [SM66, SM50, ST05, ST12, ST06, ST04]
escalate_to: dba
references:
  - https://help.sap.com/saphelp_nw73/helpdata/en/fc/eb2e7d358411d1829f0000e829fbfe/content.htm
  - https://www.guru99.com/system-monitoring-performance-checks.html
---

## Symptoms
No dump is written, which is what distinguishes this from TIME_OUT. Instead users report the whole
system is slow or unresponsive. SM50 shows dialog work processes in status Running for a long time,
and few or no processes are free. New logons are slow or rejected. The action column often shows
"Sequential Read" against the same large table for several processes at once.

## Cause
Heavy work is holding work processes. Typical reasons are a report with no suitable index scanning a
large table, several users starting the same expensive report, database lock waits where sessions
queue behind each other, or the database itself being slow because of its own load or missing
statistics. Because the dispatcher has a fixed number of processes, a handful of long runners is
enough to make the instance look down to everyone else.

## Check
1. SM66 - the global view first: how many processes, how long, which action, which table.
2. SM50 - drill into one instance for details and the developer trace of a specific process.
3. ST05 - trace SQL for a representative session to find the statement that is slow.
4. ST12 - combined ABAP and SQL trace when the split between code and database is unclear.
5. ST06 - check host CPU, memory and disk, to separate "SAP is busy" from "the host is saturated".
6. ST04 - look at database performance and wait situations.

## Fix
Identify the owning users and agree to stop or postpone the heavy work. Cancelling a work process is
possible but should be a considered decision, not a reflex, and "cancel without core" is the gentler
option. Move recurring heavy reports to background jobs at quiet times. The durable fix is usually an
index, better statistics, or code that filters in the database rather than in ABAP.

## Escalate
Database waits, missing indexes and statistics go to the DBA. Inefficient custom reports go to the
developer with the trace. If it recurs daily at the same hour, treat it as a capacity question.

## References
- SAP Help Portal - Work Processes - https://help.sap.com/saphelp_nw73/helpdata/en/fc/eb2e7d358411d1829f0000e829fbfe/content.htm
- Guru99 - SAP system monitoring and performance checks (SM50, SM66) - https://www.guru99.com/system-monitoring-performance-checks.html
