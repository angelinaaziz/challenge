# User Access Review — sample-1
_generated: 2026-07-03T01:24:52.422306+00:00 · model: openai:gpt-5.4_

## Reperformance
System export: 334 rows | HRIS roster: 720 rows | Reviewer sheet: 334 rows | Matched to HRIS: 332 | Orphans (no HRIS record): 2 | Terminated but active in system: 2 | On leave but active in system: 8 | Reviewer missed (terminated + retained): 1

## ✅ Access reviews are performed on a periodic basis (e.g. quarterly)
**Verdict**: `SUCCESS`  · confidence `0.74`

The evidence shows a recurring quarterly cadence because the cover sheet identifies the review as "Periodic (Quarterly) User Access Review" for review period "Q2 2026." The review for the period under examination was completed, with the cover sheet showing "Review Completed: 2026-06-30" and electronic reviewer sign-off on the same date. The access review tab also shows completed reviewer decisions across reviewed accounts, each populated with reviewer name "Priya Nadkarni" and review date "2026-06-30," supporting that the Q2 2026 review was executed.

**Evidence:**
- `uar-netsuite-q2-2026.xlsx` @ `Cover sheet` — The cover sheet states Review Period is Q2 2026 and Review Type is Periodic (Quarterly) User Access Review.
- `uar-netsuite-q2-2026.xlsx` @ `Cover sheet` — The cover sheet states Review Completed on 2026-06-30 and Reviewer Sign-off approved electronically by Priya Nadkarni on 2026-06-30.
- `uar-netsuite-q2-2026.xlsx` @ `Access Review sheet` — Reviewed account rows include populated Reviewer Decision, Reviewed By as Priya Nadkarni, and Review Date as 2026-06-30.
- `deterministic reperformance` @ `cover_sheet` — Reperformance extracted the cover sheet fields showing Review Type as Periodic (Quarterly) User Access Review, Review Period as Q2 2026, and Review Completed as 2026-06-30.
- `deterministic reperformance` @ `unique_review_dates` — Reperformance identified a single review date of 2026-06-30 across the review sheet.
- `deterministic reperformance` @ `reviewer_sheet_rows` — Reperformance found 334 rows on the reviewer sheet, indicating the review worksheet was populated for the period.

**Exceptions considered:**
- Service accounts were marked out of scope on the cover sheet and in reperformance (2 accounts), but this does not affect the attribute of whether the review occurred periodically and was completed for Q2 2026.

## ✅ Access is reviewed and approved by an appropriate system or data owner
**Verdict**: `SUCCESS`  · confidence `0.94`

The workbook evidences an approval decision because the cover sheet states "Reviewer Sign-off: Approved electronically by Priya Nadkarni on 2026-06-30," and the Access Review sheet contains reviewer decisions for the reviewed population. The approver’s identity and role are verifiable from the cover sheet, which lists "Priya Nadkarni, Director, Finance Systems (System Owner)" as "Reviewer / Approver." This role is appropriate for the reviewed system because the same cover sheet identifies the system under review as "NetSuite (Production)," directly tying the approval to the named system owner.

**Evidence:**
- `uar-netsuite-q2-2026.xlsx` @ `Cover sheet` — The cover information identifies the system as NetSuite (Production), names the Reviewer / Approver as Priya Nadkarni, Director, Finance Systems (System Owner), and states Reviewer Sign-off was approved electronically by Priya Nadkarni on 2026-06-30.
- `uar-netsuite-q2-2026.xlsx` @ `Access Review sheet` — The review sheet contains decision fields including Reviewer Decision, Reviewed By, and Review Date, and sampled rows show decisions such as Retain reviewed by Priya Nadkarni on 2026-06-30.
- `uar-netsuite-q2-2026.xlsx` @ `Cover sheet` — The cover sheet states the review scope is all human user accounts with access to NetSuite Production, supporting that the named system owner approval applies to the reviewed system.

**Exceptions considered:**
- Service/integration accounts were explicitly marked out of scope on the cover sheet and in deterministic reperformance; this does not affect the owner-approval attribute for the in-scope human-user review population.

## ❌ Inappropriate or excessive access identified during the review is remediated in a timely manner
**Verdict**: `FAIL`  · confidence `0.95`

The evidence shows one inappropriate active account was identified during the review: Danielle Goodwin was flagged for revocation and the cover sheet states remediation was initiated via ITSM-48217 with a 5-business-day due date. However, deterministic reperformance found a second terminated user, Kevin Lewis, still active in NetSuite while the reviewer marked the account "retain," so not every identified inappropriate/excessive access exception was initiated for remediation. Because criterion 1 failed for Kevin Lewis, the attribute fails even though Danielle Goodwin appears to have been raised and tracked for remediation.

**Evidence:**
- `uar-netsuite-q2-2026.xlsx` @ `Cover sheet / Observation 1` — The review conclusion states Danielle Goodwin retained active access despite termination, and remediation was to raise deprovisioning ticket ITSM-48217 assigned to IT with a due date within 5 business days.
- `uar-netsuite-q2-2026.xlsx` @ `Access Review!E90` — Danielle Goodwin's reviewer decision is recorded as revoke.
- `uar-netsuite-q2-2026.xlsx` @ `System Access Export!C90` — Danielle Goodwin appears in the system access export as an active NetSuite account.
- `uar-netsuite-q2-2026.xlsx` @ `System Access Export!C187` — Kevin Lewis appears in the system access export as an active account.
- `hris-employee-export.xlsx` @ `Employees!D127` — Deterministic reperformance identifies Kevin Lewis as terminated in HRIS at the cited row.
- `uar-netsuite-q2-2026.xlsx` @ `Access Review!E187` — Kevin Lewis's reviewer decision is recorded as retain, not revoke.
- `Deterministic reperformance` @ `reviewer_missed_findings` — Reperformance states Kevin Lewis was a terminated-but-active account that should have been revoked, but the reviewer missed the finding.
- `Deterministic reperformance` @ `terminated_but_active_in_system` — Reperformance lists two terminated-but-active accounts: Danielle Goodwin and Kevin Lewis.

**Exceptions considered:**
- Service/integration accounts were considered and rejected as exceptions for this attribute because the cover sheet marks them out of scope and the reperformance lists them separately as service accounts without HRIS records.
- On-leave users were considered and not treated as failures for this attribute because the reperformance explicitly notes they are not necessarily findings and are policy-dependent.
- Accounts already inactive in the system were considered and not treated as remediation exceptions because reperformance states no further action was needed for those terminated-but-inactive accounts.
