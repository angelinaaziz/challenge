# User Access Review — sample-1
_generated: 2026-07-03T02:14:59.978046+00:00 · model: claude:claude-opus-4-7_

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

The evidence shows a Q2 2026 quarterly UAR for NetSuite (Production) was completed on 2026-06-30, matching the documented quarterly cadence. The review date is within the Q2 review window and all 334 accounts from the system export (332 in-scope + 2 service accounts marked out of scope) appear in the Access Review sheet, so the complete user population at time of review was covered. Source of access is the NetSuite Users/Roles export dated 26 Jun 2026, reconciled to the Workday HCM roster, supporting completeness of the review population.

**Evidence:**
- `uar-netsuite-q2-2026.xlsx` @ `Cover sheet — Review Period / Review Type / Review Completed` — Cover identifies 'Review Period: Q2 2026', 'Review Type: Periodic (Quarterly) User Access Review', 'Review Completed: 2026-06-30', for System 'NetSuite (Production)'.
- `uar-netsuite-q2-2026.xlsx` @ `Access Review!H2:H335 (Review Date column)` — unique_review_dates = ['2026-06-30'] — every reviewed row is dated 2026-06-30, within the Q2 2026 window.
- `uar-netsuite-q2-2026.xlsx` @ `System Access Export sheet row count vs Access Review sheet row count` — System Access Export has 334 rows and Access Review sheet has 334 rows; reperformance confirms all in-scope accounts (332) plus 2 service accounts appear in the review population.
- `uar-netsuite-q2-2026.xlsx` @ `Cover — Source of Access` — 'Source of Access: NetSuite > Setup > Users/Roles export (26 Jun 2026)' — access population extracted from the system at time of review.

**Exceptions considered:**
- Two service accounts (svc-bank-recon, svc-netsuite-integration) marked out of scope — acceptable for this attribute since they are still listed on the Access Review sheet and explicitly noted on the Cover as out of scope, so the population is complete even though decisions are 'n/a'.

## ✅ Access is reviewed and approved by an appropriate system or data owner
**Verdict**: `SUCCESS`  · confidence `0.90`

The reviewer is identified by name (Priya Nadkarni) across all 334 rows of the Access Review sheet, and the Cover sheet documents her as "Director, Finance Systems (System Owner)" for NetSuite Production. Formal sign-off is retained ("Approved electronically by Priya Nadkarni on 2026-06-30"). Priya does not appear as a reviewed user in the access export, so there is no self-review issue. All four testable criteria are met.

**Evidence:**
- `uar-netsuite-q2-2026.xlsx` @ `Cover!Reviewer/Approver` — Reviewer/Approver listed as 'Priya Nadkarni, Director, Finance Systems (System Owner)' for NetSuite (Production).
- `uar-netsuite-q2-2026.xlsx` @ `Cover!Reviewer Sign-off` — 'Approved electronically by Priya Nadkarni on 2026-06-30.' — formal sign-off retained.
- `uar-netsuite-q2-2026.xlsx` @ `Access Review!G2:G335 (Reviewed By column)` — Deterministic reperformance confirms a single reviewer name 'Priya Nadkarni' populated for all 334 rows.
- `uar-netsuite-q2-2026.xlsx` @ `System Access Export (full user list)` — Priya Nadkarni does not appear in the list of reviewed users, so she is not reviewing her own access (independence satisfied).

## ⚠️ Inappropriate or excessive access identified during the review is remediated in a timely manner
**Verdict**: `FURTHER_EVIDENCE_REQUIRED`  · confidence `0.80`

The reviewer flagged one account (Danielle Goodwin) for revocation and the cover sheet documents that ITSM-48217 was raised to deprovision within 5 business days — but no ticket closure evidence, deprovisioning confirmation, or post-remediation system export was provided to confirm the access was actually removed within the defined timeframe. Additionally, the deterministic reperformance identified a missed finding (Kevin Lewis — terminated in HRIS but retained by the reviewer) which was never tracked for remediation, meaning not all inappropriate access items were identified and remediated. To flip to SUCCESS, evidence would need: (a) proof ITSM-48217 was closed with the account deprovisioned within the SLA, (b) a post-remediation system query showing Danielle Goodwin is inactive, and (c) remediation of the Kevin Lewis exception.

**Evidence:**
- `uar-netsuite-q2-2026.xlsx` @ `Cover!Observation 1` — States Danielle Goodwin's access was flagged for immediate revocation; ITSM-48217 raised, due within 5 business days. No confirmation of ticket closure or actual deprovisioning provided.
- `uar-netsuite-q2-2026.xlsx` @ `Access Review!E90 (Danielle Goodwin row)` — Reviewer decision = 'revoke' — flagged item is tracked, but no post-remediation evidence in workbook.
- `uar-netsuite-q2-2026.xlsx` @ `System Access Export!C187 / Access Review!E187 (Kevin Lewis)` — HRIS shows Kevin Lewis terminated but system account still Active; reviewer decision = 'retain'. Reperformance flagged this as a missed finding — not identified, tracked, or remediated.
- `uar-netsuite-q2-2026.xlsx` @ `Cover!Accounts Flagged for Revocation / Observations Raised` — Only 1 account flagged for revocation and 1 observation raised, whereas deterministic reperformance identified 2 terminated-but-active accounts.

**Exceptions considered:**
- Inactive-but-retained accounts (12) were not treated as findings because the accounts are already inactive in the system — no remediation needed; accepted this as not-an-exception.
- On-leave-but-active accounts (8) are policy-dependent and reviewer retained; not a clear inappropriate-access finding, so excluded from remediation scope.
