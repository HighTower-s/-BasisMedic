---
doc_id: rfc_connection_failed
category: rfc_error
title: RFC connection test fails - partner not reached or logon rejected
tcodes: [SM59, SU01, SMGW, SM21]
escalate_to: network
references:
  - https://help.sap.com/saphelp_46c/helpdata/en/22/042638488911d189490000e829fbbd/content.htm
  - https://learning.sap.com/courses/technical-implementation-and-operation-i-of-sap-s-4hana-and-sap-business-suite/troubleshooting-procedures
---

## Symptoms
Short dumps named CALL_FUNCTION_COMMUNICATION_FAILURE or CALL_FUNCTION_SYSTEM_FAILURE appear in
ST22. The connection test in SM59 fails with a message such as "partner not reached", "Name or
password is incorrect", "user is locked", or a timeout during allocate. Interfaces to the named
system stop working, and the error text itself usually tells you whether the problem is the network
or the credentials.

## Cause
Three groups of cause, and the message distinguishes them. Partner not reached means the target
system or instance is down, the host and instance number in the destination are wrong, or a firewall
blocks the route. Logon failures mean the RFC user's password is wrong, the account is locked, or it
lacks the right authorisations in the target. Gateway rejections mean the target's gateway security
rules refuse the connection or the expected registered program is not there.

## Check
1. SM59 - run the connection test first, then the authorization or logon test separately; they fail
   for different reasons.
2. SU01 - in the target system, check the RFC user's lock status and validity.
3. SMGW - on the target, look at the gateway monitor for connections, registered programs and
   rejections.
4. SM21 - the system log on both sides around the same time.

## Fix
Correct whichever layer the message pointed at: fix the host, instance number or service in the
destination; unlock the RFC user and align its password in both the destination and the target; or
adjust the gateway security configuration. Test again from SM59 after each single change, so you
know which one actually fixed it.

## Escalate
Network routes and firewalls go to the network team. If the target system is down, that is its own
team's incident and not something to fix from this side.

## References
- SAP Help Portal - Displaying, Maintaining and Testing Destinations - https://help.sap.com/saphelp_46c/helpdata/en/22/042638488911d189490000e829fbbd/content.htm
- SAP Learning - Troubleshooting Procedures - https://learning.sap.com/courses/technical-implementation-and-operation-i-of-sap-s-4hana-and-sap-business-suite/troubleshooting-procedures
