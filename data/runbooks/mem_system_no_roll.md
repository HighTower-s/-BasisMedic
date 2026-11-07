---
doc_id: mem_system_no_roll
category: memory_dump
title: SYSTEM_NO_ROLL / MEMORY_NO_MORE_PAGING - instance is out of shared memory
tcodes: [ST02, SM50, SM66, SM04, ST06, SM21]
escalate_to: basis
references:
  - https://help.sap.com/saphelp_nw73/helpdata/en/fc/eb2e7d358411d1829f0000e829fbfe/content.htm
  - https://help.sap.com/saphelp_gbt10/helpdata/en/49/1805ac005338a1e10000000a421937/content.htm
---

## Symptoms
Short dumps named SYSTEM_NO_ROLL or MEMORY_NO_MORE_PAGING appear in ST22, often several at once and
from different users. Unlike a single large report failing, this pattern usually hits many sessions
in the same few minutes. Users report the system is slow, sessions drop, or saving suddenly fails.
The dumps may name different programs each time, which is the clue that the shortage is
instance-wide rather than caused by one bad program.

## Cause
The instance could not reserve memory for a user context. Roll area, extended memory or the paging
area is exhausted at that moment. The common reasons are many large user contexts active at the same
time, one session or background job consuming far more memory than expected, or memory parameters
sized smaller than the workload needs. A work process that switched to PRIV mode holds its memory
until it finishes, so a few runaway sessions can starve everyone else.

## Check
1. ST02 - look at roll area, paging and extended memory, especially the "max used" column rather
   than only the current value.
2. SM50 - check for work processes in PRIV mode and how much memory each holds.
3. SM66 - the same view across all instances, to see whether one instance or all are affected.
4. SM04 - identify the users and sessions holding the largest contexts.
5. ST06 - confirm the host itself still has physical memory and is not swapping.
6. SM21 - read the system log around the same time for related memory messages.

## Fix
Find the session or job consuming abnormal memory and agree with its owner to stop or reschedule it.
Move large reports to background processing and outside peak hours. If PRIV work processes are
stuck, restart them only after checking what they are doing. Review the memory parameters against
the physical memory of the host before changing anything; profile changes need an instance restart,
so plan them. Do not simply raise quotas on a host that is already swapping - that makes the whole
system slower.

## Escalate
Repeated shortages with no single culprit are a sizing question for Basis. If one custom program is
always the cause, hand it to the developer with the ST02 and SM50 evidence attached.

## References
- SAP Help Portal - Work Processes - https://help.sap.com/saphelp_nw73/helpdata/en/fc/eb2e7d358411d1829f0000e829fbfe/content.htm
- SAP Help Portal - ABAP Dump Analysis (background) - https://help.sap.com/saphelp_gbt10/helpdata/en/49/1805ac005338a1e10000000a421937/content.htm
