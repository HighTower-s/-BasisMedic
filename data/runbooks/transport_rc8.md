---
doc_id: transport_rc8
category: transport_error
title: Transport import ended with return code 8 - objects did not activate
tcodes: [STMS, SE01, SE09, SE38, SE80]
escalate_to: developer
references:
  - https://help.sap.com/saphelp_46c/helpdata/en/57/38e26c4eb711d182bf0000e829fbfe/content.htm
  - https://help.sap.com/saphelp_nwes72/helpdata/en/3a/58c2e9f47611d184850000e8a57770/content.htm
---

## Symptoms
The STMS import history shows the request in red with return code 8. After the import, a program may
have a syntax error, a table may not be active, or a function module may be reported as missing. The
import did finish - unlike a hanging import - but part of its content did not come across usable.
Users in the target system notice it as a transaction that suddenly dumps.

## Cause
Some objects in the request could not be imported or activated. The usual reasons are a syntax error
in the transported code, a dependent object that lives in another request which has not been
imported yet, so the import order is wrong, or a table or structure conversion that could not be
performed. Return code 4 is different: it means warnings only, and does not require this procedure.

## Check
1. STMS - open the import queue and history, then the logs for the failing request.
2. STMS - inside the log, identify which step returned 8: import, activation, or generation.
3. SE01 - list the objects contained in the request.
4. SE09 - look for sibling requests that should have gone first.
5. SE38 - run a syntax check on the affected program in the target system.
6. SE80 - inspect the object and whether it is active.

## Fix
If an object depends on something not yet imported, import the missing request and then re-import
this one in the correct order. If the code itself is wrong, it must be corrected in the development
system and released as a new request; do not try to repair objects directly in the target. Check
afterwards that the previously broken objects are active, and tell the affected users once they are.

## Escalate
The developer who owns the request fixes the content. Decisions about import order and whether to
re-import belong with Basis and the release manager together.

## References
- SAP Help Portal - Return Codes in the Transport Log - https://help.sap.com/saphelp_46c/helpdata/en/57/38e26c4eb711d182bf0000e829fbfe/content.htm
- SAP Help Portal - tp Return Codes - https://help.sap.com/saphelp_nwes72/helpdata/en/3a/58c2e9f47611d184850000e8a57770/content.htm
