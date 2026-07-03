# User Access Review — sample-1
_generated: 2026-07-03T02:55:59.982905+00:00 · model: claude:claude-opus-4-7_

## ⚠️ Control conclusion: `CONTROL_INCONCLUSIVE`

### Reperformance summary
System export: 334 rows | HRIS roster: 720 rows | Reviewer sheet: 334 rows | Matched to HRIS: 332 | Orphans (no HRIS record): 2 | Terminated but active in system: 2 | On leave but active in system: 8 | Reviewer missed (terminated + retained): 1

### Evidence coverage — 50%
- All files provided: 2
- Cited in at least one verdict: 1
- **Uncited:** `hris-employee-export.xlsx`

---

## Attribute-level verdicts

## ✅ Access reviews are performed on a periodic basis (e.g. quarterly)
**Verdict**: `SUCCESS`  · confidence `0.90`

The evidence shows a Q2 2026 quarterly UAR was performed for NetSuite (Production), completed 2026-06-30, covering the complete population of 334 accounts from the system export (332 in-scope human users + 2 service accounts flagged out of scope). The Cover sheet explicitly identifies the review as "Periodic (Quarterly) User Access Review" for Q2 2026 with review completion date documented. The reviewer sheet contains 334 rows matching the system export 1:1, and all Review Dates are 2026-06-30, evidencing completeness of population coverage at the time of review. Note: this attribute assesses cadence/timeliness/completeness only; separate attributes cover reviewer independence, accuracy, and remediation of findings.

**Evidence:**
- `uar-netsuite-q2-2026.xlsx` @ `Cover sheet (Review Period / Review Type / Review Completed)` — Review Period: Q2 2026; Review Type: Periodic (Quarterly) User Access Review; Review Completed: 2026-06-30; Scope: All human user accounts with access to NetSuite Production.
- `uar-netsuite-q2-2026.xlsx` @ `System Access Export sheet (row count)` — 334 rows in the NetSuite user/roles export (dated 26 Jun 2026 per Cover).
- `uar-netsuite-q2-2026.xlsx` @ `Access Review sheet (row count, Review Date column)` — 334 review rows, each with Review Date 2026-06-30 — full population covered at review time.
- `reperformance` @ `unique_review_dates and reviewer_sheet_rows` — Deterministic reperformance confirms reviewer_sheet_rows=334 matches system_export_rows=334; unique_review_dates = ['2026-06-30'].

**Exceptions considered:**
- Only one review period is in evidence, so gap-between-consecutive-reviews cannot be directly verified; however the Q2 2026 review being labelled 'Periodic (Quarterly)' and completed within Q2 2026 is consistent with a quarterly cadence for this sample.

## ✅ Access is reviewed and approved by an appropriate system or data owner
**Verdict**: `SUCCESS`  · confidence `0.90`

The Cover sheet identifies the reviewer/approver by name and role as "Priya Nadkarni, Director, Finance Systems (System Owner)", and the Access Review sheet consistently shows Priya Nadkarni as the "Reviewed By" party across the sampled rows. The Cover records explicit sign-off ("Approved electronically by Priya Nadkarni on 2026-06-30"). Priya is not present in the list of reviewed users, so there is no self-review. All four criteria are satisfied.

**Evidence:**
- `uar-netsuite-q2-2026.xlsx` @ `Cover!Reviewer / Approver` — Reviewer/Approver identified as 'Priya Nadkarni, Director, Finance Systems (System Owner)'.
- `uar-netsuite-q2-2026.xlsx` @ `Cover!Reviewer Sign-off` — 'Approved electronically by Priya Nadkarni on 2026-06-30.' — explicit sign-off retained.
- `uar-netsuite-q2-2026.xlsx` @ `Access Review!G2:G6 (Reviewed By)` — Every sampled row shows 'Priya Nadkarni' as the Reviewed By party with Review Date 2026-06-30.
- `uar-netsuite-q2-2026.xlsx` @ `Access Review sheet — user list` — Priya Nadkarni does not appear in the reviewed user population, so there is no self-approval.
- `reperformance` @ `reviewer_names` — Deterministic reperformance confirms single reviewer: ['Priya Nadkarni'].

**Exceptions considered:**
- Considered whether the reviewer might also be a user in the reviewed population (self-approval risk) — Priya Nadkarni does not appear among the 334 accounts reviewed, so this exception does not apply.

## ⚠️ Inappropriate or excessive access identified during the review is remediated in a timely manner
**Verdict**: `FURTHER_EVIDENCE_REQUIRED`  · confidence `0.80`

The reviewer flagged one account for revocation (Danielle Goodwin) and the summary states remediation was tracked via ITSM ticket ITSM-48217 with a 5 business day SLA, which addresses tracking. However, no evidence has been provided showing the ticket was actually closed and access revoked in NetSuite (e.g., ticket closure record, updated system export, or deprovisioning screenshot), so criteria 2 (evidence access was actually revoked) and 3 (remediation within SLA) cannot be confirmed. Additionally, the reperformance identified a second terminated-but-active account (Kevin Lewis) that the reviewer decided to "retain" with no documented justification — this is a reviewer-missed finding rather than a remediation-attribute failure, but it does mean at least one flagged/should-have-been-flagged item lacks either a remediation trail or a documented risk acceptance. Evidence that would flip to SUCCESS: closure record of ITSM-48217 and an updated NetSuite export showing danielle.goodwin's account inactive/removed within the 5-business-day SLA.

**Evidence:**
- `uar-netsuite-q2-2026.xlsx` @ `Cover!Observation 1 / Conclusion` — States Danielle Goodwin's access flagged for immediate revocation; deprovisioning ticket ITSM-48217 raised and assigned to IT with 5 business day SLA. Conclusion says '1 observation raised and remediated via ITSM-48217' but no ticket closure evidence attached.
- `uar-netsuite-q2-2026.xlsx` @ `System Access Export!C90 (danielle.goodwin row)` — System export dated 26 Jun 2026 shows danielle.goodwin account status = Active. No later export provided to confirm the account was subsequently deactivated.
- `uar-netsuite-q2-2026.xlsx` @ `Access Review!E187 (kevin.lewis row)` — Kevin Lewis (HRIS terminated) marked Reviewer Decision = Retain with no documented risk acceptance or justification — reperformer flagged as a missed finding; no remediation tracked because reviewer did not flag it.
- `uar-netsuite-q2-2026.xlsx` @ `Cover!'Accounts Flagged for Revocation' and 'Observations raised'` — Both = 1, confirming only one flagged item was tracked for remediation.

**Exceptions considered:**
- Inactive-but-retained accounts (12 rows): these accounts were already inactive in the system, so no remediation action is required — reviewer's 'retain' decision is acceptable and does not affect this attribute.
- On-leave-but-active accounts (8 rows): reviewer explicitly retained; policy-dependent and not treated as flagged access requiring remediation.
- Service accounts (2 orphans): marked out of scope on the Cover sheet, not requiring remediation under this review.
