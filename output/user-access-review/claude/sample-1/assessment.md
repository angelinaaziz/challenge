# User Access Review — sample-1
_generated: 2026-07-03T04:23:01.968133+00:00 · model: claude:claude-opus-4-8_

## ❌ Control conclusion: `CONTROL_FAIL`

### Reperformance summary
Full-population reperformance — 100% of the 334 in-scope account(s) tested, not a sample | System export: 334 rows | HRIS roster: 720 rows | Reviewer sheet: 334 rows | Matched to HRIS: 332 | Orphans (no HRIS record): 2 | Terminated but active in system: 2 | On leave but active in system: 8 | Reviewer missed (terminated + retained): 1

### Evidence coverage — 50%
- All files provided: 2
- Cited in at least one verdict: 1
- **Uncited:** `hris-employee-export.xlsx`

---

## Attribute-level verdicts

## ✅ Access reviews are performed on a periodic basis (e.g. quarterly)
**Verdict**: `SUCCESS`  · confidence `0.90`

The Cover sheet declares the review as a "Periodic (Quarterly) User Access Review" for Review Period "Q2 2026", with "Review Completed: 2026-06-30" and an electronic sign-off dated 2026-06-30 — positively evidencing that a review was performed at the defined quarterly frequency with a documented date. All 334 reviewer decision rows carry a single Review Date of 2026-06-30, and the reperformance confirms exactly one unique review date, consistent with a single Q2 2026 cycle completed within the period. The reperformance findings about missed/inappropriate access relate to the review's accuracy, not its periodicity, so they do not bear on this attribute.

**Evidence:**
- `uar-netsuite-q2-2026.xlsx` @ `Cover sheet (Review Type / Review Period / Review Completed / Reviewer Sign-off)` — Review Type = 'Periodic (Quarterly) User Access Review'; Review Period = 'Q2 2026'; Review Completed = '2026-06-30'; Reviewer Sign-off = 'Approved electronically by Priya Nadkarni on 2026-06-30.'
- `uar-netsuite-q2-2026.xlsx` @ `Access Review!H2:H335 (Review Date column)` — Every reviewer decision row is dated 2026-06-30, consistent with a single quarterly review cycle.
- `reperformance (deterministic)` @ `unique_review_dates` — Exactly one unique review date across all rows: 2026-06-30T00:00:00, confirming a single Q2 2026 cycle.

## ✅ Access is reviewed and approved by an appropriate system or data owner
**Verdict**: `SUCCESS`  · confidence `0.85`

The Cover sheet identifies the reviewer/approver as Priya Nadkarni, Director, Finance Systems, explicitly designated "(System Owner)" for NetSuite Production, satisfying the identified-individual and appropriate-owner criteria. Documented approval exists via the sign-off line "Approved electronically by Priya Nadkarni on 2026-06-30," and all 334 review rows are attributed to Priya Nadkarni. Priya Nadkarni does not appear as a subject account in the NetSuite access export, so there is no self-approval concern. Note: reviewer-missed findings (e.g. Kevin Lewis) and remediation timeliness belong to separate attributes and do not bear on reviewer appropriateness/approval.

**Evidence:**
- `uar-netsuite-q2-2026.xlsx` @ `Cover!Reviewer / Approver` — Reviewer/Approver identified as 'Priya Nadkarni, Director, Finance Systems (System Owner)' for NetSuite (Production).
- `uar-netsuite-q2-2026.xlsx` @ `Cover!Reviewer Sign-off` — Documented approval: 'Approved electronically by Priya Nadkarni on 2026-06-30.'
- `uar-netsuite-q2-2026.xlsx` @ `Access Review!G2:G335 (Reviewed By)` — All in-scope review rows attributed to reviewer Priya Nadkarni, dated 2026-06-30.
- `reperformance` @ `reviewer_names / system_export subject list` — Sole reviewer is Priya Nadkarni; she does not appear as a subject account in the 334-row NetSuite access export, so no self-approval of her own access.

**Exceptions considered:**
- Self-approval check: Priya Nadkarni is not among the reviewed subject accounts, so four-eyes/independence is not compromised for this attribute.
- Reviewer-missed findings and remediation timeliness (Kevin Lewis, Danielle Goodwin) were considered but excluded as they pertain to separate attributes (review completeness / remediation), not reviewer appropriateness.

## ❌ Inappropriate or excessive access identified during the review is remediated in a timely manner
**Verdict**: `FAIL`  · confidence `0.85`

The deterministic reperformance surfaced a second terminated-but-still-active user, Kevin Lewis (A/P Clerk, terminated in HRIS, system account still Active), whom the reviewer marked "retain" — a reviewer_missed finding. This is inappropriate access identified by the audit that was neither flagged nor remediated, contradicting the criterion. Separately, the one case the reviewer did catch (Danielle Goodwin) was flagged with ITSM-48217 due within 5 business days, but no completed remediation date is evidenced (the account was still Active at export). Because at least one instance of inappropriate access exists with no evidence of remediation, this attribute fails.

**Evidence:**
- `uar-netsuite-q2-2026.xlsx (reperformance)` @ `reviewer_missed_findings / terminated_but_active_in_system — kevin.lewis@northpeakfinancial.com` — Kevin Lewis is terminated in HRIS but his NetSuite account is still Active, and the reviewer decision is 'retain'. Access should have been revoked but was not identified or remediated.
- `uar-netsuite-q2-2026.xlsx` @ `Access Review!E187 / System Access Export!C187 / HRIS Employees!D127` — Kevin Lewis row: Account Status Active, reviewer decision Retain — no revocation, no remediation ticket, no remediation date.
- `uar-netsuite-q2-2026.xlsx` @ `Cover sheet — Observation 1 / Conclusion` — Only Danielle Goodwin was flagged for revocation via ITSM-48217 (due within 5 business days). Ticket raised but no completed remediation date is provided, and the account remained Active at time of export.

**Exceptions considered:**
- Danielle Goodwin was flagged and a remediation ticket (ITSM-48217) raised, but this does not compensate for the missed Kevin Lewis case; and no evidence of a completed remediation date exists even for Danielle.
- On-leave-but-active users (8) treated as policy-dependent and not counted as clear inappropriate access; the terminated-but-active cases are the definitive finding.
