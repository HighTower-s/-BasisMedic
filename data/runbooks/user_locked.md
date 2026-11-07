---
doc_id: user_locked
category: user_auth
title: User is locked - failed logons, administrator lock or expired validity
tcodes: [SU01, SUIM, SU10, SM20, SM21]
escalate_to: security
references:
  - https://learning.sap.com/courses/technical-implementation-and-operation-i-of-sap-s-4hana-and-sap-business-suite/evaluate-users-and-authorizations
  - https://www.guru99.com/system-monitoring-performance-checks.html
---

## Symptoms
The user cannot log on and sees a message such as "User is locked. Please notify the person
responsible". The same lock also breaks anything else running under that account: background jobs
whose step user is locked fail, and RFC connections using it stop working. So the first report may
come from a failed job rather than from a person, which is a useful clue that an account, not a
program, is the problem.

## Cause
Either the system locked the account after too many wrong passwords, counted against the parameter
login/fails_to_user_lock, or an administrator locked it deliberately, or a central user
administration lock applies, or the account's validity period has simply expired. Expired validity
is easy to miss because it is not shown as a lock in the usual sense but has the same effect.

## Check
1. SU01 - open the user and read the lock status and the logon data, including validity dates and
   user type.
2. SUIM - list locked users, useful when several accounts are affected at once.
3. SM20 - if the security audit log is active, see where the failed logon attempts came from.
4. SM21 - the system log around the same time, as a cross-check.

## Fix
Verify who is asking before unlocking anything, through an established channel and not just by
email. Then unlock or reset the password in SU01, or use SU10 for several accounts. For a system or
communication account, also correct the stored password wherever it is used, such as in RFC
destinations, otherwise the retries will lock it again within minutes and you will be back where you
started.

## Escalate
Repeated failed logons from unexpected sources go to the security team before you unlock. Deliberate
administrative locks should be queried with whoever set them.

## References
- SAP Learning - Evaluate Users and Authorizations - https://learning.sap.com/courses/technical-implementation-and-operation-i-of-sap-s-4hana-and-sap-business-suite/evaluate-users-and-authorizations
- Guru99 - SAP system monitoring and security audit log - https://www.guru99.com/system-monitoring-performance-checks.html
