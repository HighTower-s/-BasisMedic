---
doc_id: job_stuck_ready_released
category: job_failure
title: Job stuck in Ready or Released - scheduled but never starts
tcodes: [SM37, SM50, SM66, SM51, RZ04, SM62]
escalate_to: basis
references:
  - https://help.sap.com/saphelp_gbt10/helpdata/en/4b/272d08d1341780e10000000a42189c/content.htm
  - https://help.sap.com/saphelp_nw73/helpdata/en/fc/eb2e7d358411d1829f0000e829fbfe/content.htm
---

## Symptoms
The start time has passed but the job has not run. SM37 shows it as Ready, or as Released and not
moving. There is no job log to read yet and no dump anywhere, because the program never started.
Nothing failed - the job is simply waiting, which is why this looks alarming but is often benign.

## Cause
The two statuses mean different things and should not be treated alike. Ready means the scheduler
wants to run it but no background work process is available: batch processes are all busy, there are
too few of them, or the job is pinned to a target server that is down. Released means the start
condition itself has not been met: the clock time has not arrived, an awaited event has not been
raised, or a predecessor job has not finished.

## Check
1. SM37 - open the job's start condition and target server, and note which status it is in.
2. SM50 - are the background work processes on this instance all occupied?
3. SM66 - the same question across all instances.
4. SM51 - is the target server named in the job still registered and alive?
5. RZ04 - how many background processes the current operation mode allows.
6. SM62 - for event-driven jobs, whether the awaited event has been raised.

## Fix
For Ready, free capacity: let long runners finish, or stop one that is holding a process
unnecessarily. If the target server is gone, remove the server restriction so any instance can take
the job. Adjusting the number of background processes, through the profile or the operation mode, is
the structural fix when this recurs. For Released, raise the awaited event or fix the predecessor
job; nothing is wrong with the job itself.

## Escalate
Capacity and operation-mode changes are Basis work. A predecessor that keeps failing belongs to its
own owner, and that is the job to investigate instead.

## References
- SAP Help Portal - Analyzing the Job Status - https://help.sap.com/saphelp_gbt10/helpdata/en/4b/272d08d1341780e10000000a42189c/content.htm
- SAP Help Portal - Work Processes - https://help.sap.com/saphelp_nw73/helpdata/en/fc/eb2e7d358411d1829f0000e829fbfe/content.htm
