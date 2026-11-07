---
doc_id: transport_rc12_or_stuck
category: transport_error
title: Transport return code 12 or higher, or an import that never finishes
tcodes: [STMS, SM37, SM21]
escalate_to: basis
references:
  - https://help.sap.com/saphelp_nwes72/helpdata/en/3a/58c2e9f47611d184850000e8a57770/content.htm
  - https://help.sap.com/saphelp_46c/helpdata/en/57/38e26c4eb711d182bf0000e829fbfe/content.htm
---

## Symptoms
The import ends with return code 12 or 16, or reports a "tp error", or sits in status running far
longer than such a request should take. The difference from return code 8 is that the request's
content was never really processed: the transport tooling itself could not do its work, so the logs
talk about files and connections rather than about objects and activation.

## Cause
The problem is outside the request. The tp or R3trans programs could not reach the database, files
in the transport directory are missing or unreadable because cofiles and data files were not copied
or have wrong permissions, the transport filesystem is full, or the import background job RDDIMPDP
is not scheduled so nothing picks the request up. Return codes above 200 are combined values and
need the explainrc utility to decode.

## Check
1. STMS - open the import monitor and read the tp system log and action log for the request.
2. SM37 - check whether RDDIMPDP is scheduled and running in the target client and in client 000.
3. SM21 - look for database or filesystem messages at the same time.

## Fix
Repair the environment, then re-import. Restore missing cofiles and data files from the source
system, correct ownership and permissions on the transport directory, or free disk space. If
RDDIMPDP is missing, reschedule it with the standard report RDDNEWPP and confirm it starts picking
up the queue. Only after the tooling works again does re-importing make sense.

## Escalate
This usually needs operating-system access to the transport directory, so it is Basis work and often
needs the platform team as well. Involve the DBA if the logs point at the database connection.

## References
- SAP Help Portal - tp Return Codes - https://help.sap.com/saphelp_nwes72/helpdata/en/3a/58c2e9f47611d184850000e8a57770/content.htm
- SAP Help Portal - Return Codes in the Transport Log - https://help.sap.com/saphelp_46c/helpdata/en/57/38e26c4eb711d182bf0000e829fbfe/content.htm
