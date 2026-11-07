---
doc_id: auth_missing
category: user_auth
title: You are not authorized - missing authorization object in the role
tcodes: [SU53, STAUTHTRACE, ST01, SUIM, PFCG]
escalate_to: security
references:
  - https://learning.sap.com/courses/technical-implementation-and-operation-i-of-sap-s-4hana-and-sap-business-suite/evaluate-users-and-authorizations
  - https://learning.sap.com/courses/exploring-the-authorization-concept-for-sap-s-4hana-and-sap-business-suite/troubleshouting-authorization-checks
---

## Symptoms
The user gets "You are not authorized to use transaction XXX" or a message that there is no
authorization for a particular activity. They can log on normally, which distinguishes this from a
locked account: the account works, one specific action does not. A background job can fail the same
way when its step user lacks a right that the program checks at runtime.

## Cause
The role assigned to the user is missing an authorization object, or has the object but not the
field value the program checks - a plant, a company code, an activity. Partially correct
authorisation is the common case and the reason guessing does not work: the user often has the
transaction but not the data behind it.

## Check
1. SU53 - have the user run it immediately after the error; it shows the exact failed check while it
   is still in their session.
2. STAUTHTRACE - trace all authorization checks for that user when SU53 is not conclusive.
3. ST01 - the older system trace, an alternative when STAUTHTRACE is unavailable.
4. SUIM - find which roles already contain the needed authorization.
5. PFCG - inspect and maintain the role itself.

## Fix
Add the missing authorization to an appropriate role through the normal approval process, change it
in the development system, and transport it. Keep to least privilege: grant the specific object and
field values the trace showed, not a broad profile. Never resolve this by assigning SAP_ALL, even
temporarily in production - it is the fastest fix and the one that turns a small ticket into an audit
finding.

## Escalate
Role design and approval belong to the security or GRC team. If the user is asking for access they
have no business reason for, that is a conversation for their manager, not a technical fix.

## References
- SAP Learning - Evaluate Users and Authorizations - https://learning.sap.com/courses/technical-implementation-and-operation-i-of-sap-s-4hana-and-sap-business-suite/evaluate-users-and-authorizations
- SAP Learning - Troubleshooting Authorization Checks - https://learning.sap.com/courses/exploring-the-authorization-concept-for-sap-s-4hana-and-sap-business-suite/troubleshouting-authorization-checks
