# User Access Review — sample-1
_generated: 2026-07-03T04:02:58.042871+00:00 · model: claude:claude-opus-4-7_

## ❌ Control conclusion: `CONTROL_FAIL`

### Reperformance summary
System export: 334 rows | HRIS roster: 720 rows | Reviewer sheet: 334 rows | Matched to HRIS: 332 | Orphans (no HRIS record): 2 | Terminated but active in system: 2 | On leave but active in system: 8 | Reviewer missed (terminated + retained): 1

### Evidence coverage — 100%
- All files provided: 2
- Cited in at least one verdict: 2

---

## Attribute-level verdicts

## ✅ Access reviews are performed on a periodic basis (e.g. quarterly)
**Verdict**: `SUCCESS`  · confidence `0.92`

The Cover sheet positively identifies the Review Type as "Periodic (Quarterly) User Access Review" for Review Period Q2 2026, with Review Completed 2026-06-30. All 334 reviewer decision rows on the Access Review sheet carry a single Review Date of 2026-06-30, consistent with a single quarterly cycle, and IPE checks reconcile the population (334 accounts; 332 in-scope + 2 service) to the Cover totals. The review covered the in-scope NetSuite Production user population as of the review date.

**Evidence:**
- `uar-netsuite-q2-2026.xlsx` @ `Cover!Review Type / Review Period / Review Completed` — Cover sheet declares Review Type: 'Periodic (Quarterly) User Access Review', Review Period: 'Q2 2026', Review Completed: '2026-06-30', System: 'NetSuite (Production)', Scope: 'All human user accounts with access to NetSuite Production.'
- `uar-netsuite-q2-2026.xlsx` @ `Access Review!H2:H335 (Review Date column)` — unique_review_dates = ['2026-06-30']; every one of the 334 reviewer decision rows is dated 2026-06-30, indicating a single quarterly review cycle.
- `uar-netsuite-q2-2026.xlsx` @ `Cover!Reviewer Sign-off` — 'Approved electronically by Priya Nadkarni on 2026-06-30.' — completion date documented and signed.
- `uar-netsuite-q2-2026.xlsx` @ `IPE checks (reperformance)` — IPE reconciliation passes: 334 export rows = 332 in-scope + 2 service accounts, matching Cover totals; population as of review date is fully covered.

## ✅ Access is reviewed and approved by an appropriate system or data owner
**Verdict**: `SUCCESS`  · confidence `0.90`

The reviewer is named as Priya Nadkarni, Director, Finance Systems (System Owner) on the Cover sheet, an appropriate owner role for NetSuite (Production). She is distinct from the preparer (Marcus Bell) and is not on the reviewed access list (she is not among the 334 usernames), so she is independent of the users reviewed. Sign-off is documented ("Approved electronically by Priya Nadkarni on 2026-06-30") and dated the same day as the Review Completed date, satisfying the documented, on-or-after approval criterion.

**Evidence:**
- `uar-netsuite-q2-2026.xlsx` @ `Cover!Reviewer / Approver` — Reviewer / Approver identified as 'Priya Nadkarni, Director, Finance Systems (System Owner)'.
- `uar-netsuite-q2-2026.xlsx` @ `Cover!Reviewer Sign-off and Review Completed` — 'Approved electronically by Priya Nadkarni on 2026-06-30.' with Review Completed 2026-06-30.
- `uar-netsuite-q2-2026.xlsx` @ `Access Review!G2:G335 (Reviewed By column)` — All 334 rows show 'Priya Nadkarni' as the reviewer with Review Date 2026-06-30.
- `uar-netsuite-q2-2026.xlsx` @ `Cover!Prepared By vs Reviewer` — Preparer (Marcus Bell) is distinct from Reviewer (Priya Nadkarni); Priya Nadkarni does not appear in the list of 334 in-scope usernames, confirming she is not reviewing her own access.

## ❌ Inappropriate or excessive access identified during the review is remediated in a timely manner
**Verdict**: `FAIL`  · confidence `0.90`

Deterministic reperformance identified a terminated employee, Kevin Lewis (HRIS status: terminated), whose NetSuite account remains Active and whom the reviewer marked "Retain" — inappropriate access exists that was neither flagged nor remediated. While the one item the reviewer did flag (Danielle Goodwin) has a documented remediation path via ITSM-48217, the reperformance surfaces at least one additional case of inappropriate access that was missed and left in place, contradicting the criterion that all flagged inappropriate access be remediated. Evidence of actual system removal (deprovisioning confirmation for Danielle Goodwin) is also not present — only a ticket reference.

**Evidence:**
- `uar-netsuite-q2-2026.xlsx` @ `Access Review!E187 (Kevin Lewis row)` — Reviewer Decision = 'Retain' for kevin.lewis@northpeakfinancial.com despite HRIS showing him terminated.
- `hris-employee-export.xlsx` @ `Employees!D127 (Kevin Lewis)` — HRIS record for Kevin Lewis shows employment status terminated, contradicting the retained decision.
- `uar-netsuite-q2-2026.xlsx` @ `Cover sheet — Observation 1 / Conclusion` — Only 1 observation raised (Danielle Goodwin) with remediation via ITSM-48217; no mention of Kevin Lewis or any other terminated-but-active user.
- `reperformance` @ `reviewer_missed_findings (count=1)` — Reconciliation flagged Kevin Lewis as terminated-in-HRIS but retained by the reviewer — a case of inappropriate access not identified and not remediated.
- `uar-netsuite-q2-2026.xlsx` @ `Cover sheet — Observation 1 remediation text` — Remediation for Danielle Goodwin is only a raised ticket (ITSM-48217, due within 5 business days); no evidence provided that the account was actually deprovisioned in NetSuite.

**Exceptions considered:**
- Considered whether the two service accounts (svc-bank-recon, svc-netsuite-integration) constitute inappropriate access — Cover sheet explicitly scopes them out as integration accounts, so they are not an exception issue for this attribute.
- Considered whether Danielle Goodwin's ticketed remediation alone satisfies the criterion — rejected because the reperformance surfaces an additional un-remediated case (Kevin Lewis) and no evidence confirms actual system removal for Danielle Goodwin.
