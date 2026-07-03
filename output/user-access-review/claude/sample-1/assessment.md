# User Access Review — sample-1
_generated: 2026-07-03T03:08:00.053243+00:00 · model: claude:claude-opus-4-7_

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

The evidence file uar-netsuite-q2-2026.xlsx documents a Q2 2026 Periodic (Quarterly) User Access Review for NetSuite (Production), completed on 2026-06-30 (within Q2 2026). All 334 rows on the Access Review sheet share a single review date of 2026-06-30, and the Cover sheet explicitly identifies the cadence ("Periodic (Quarterly) User Access Review") and completion date. This attribute concerns cadence and completion timing only; substantive issues (e.g., missed terminated user) are scoped to other attributes. Only limitation is that a single quarter's evidence is provided, so full-period cadence adherence across all quarters cannot be independently confirmed from this sample alone.

**Evidence:**
- `uar-netsuite-q2-2026.xlsx` @ `Cover!Review Period / Review Type / Review Completed` — Cover metadata states Review Period = 'Q2 2026', Review Type = 'Periodic (Quarterly) User Access Review', Review Completed = '2026-06-30', with Reviewer Sign-off 'Approved electronically by Priya Nadkarni on 2026-06-30.'
- `uar-netsuite-q2-2026.xlsx` @ `Access Review!H2:H335 (Review Date column)` — All 334 reviewer rows carry Review Date = 2026-06-30, evidencing a completed review within Q2 2026.
- `uar-netsuite-q2-2026.xlsx` @ `Deterministic reperformance: unique_review_dates` — Reperformance confirms exactly one unique review date (2026-06-30) across the population, consistent with a single quarterly cycle.

**Exceptions considered:**
- Only one quarter (Q2 2026) of evidence was provided in this sample; verdict is on the observed cycle. If the audit period spans multiple quarters, additional quarters' UAR packs would be needed to fully confirm no skipped cycles.

## ✅ Access is reviewed and approved by an appropriate system or data owner
**Verdict**: `SUCCESS`  · confidence `0.90`

The Cover sheet identifies Priya Nadkarni, Director, Finance Systems as the System Owner and Reviewer/Approver for NetSuite (Production), and the Access Review sheet consistently lists her as "Reviewed By" for all sampled rows on 2026-06-30. An electronic sign-off attestation is documented ("Approved electronically by Priya Nadkarni on 2026-06-30"). Priya is not present in the reviewed user population (she does not appear as a user in the NetSuite export), so she did not review her own access. The population reviewed (334 rows) reconciles to the system export (334 rows). Note: this attribute concerns reviewer appropriateness/independence/sign-off — the separate reconciliation finding (Kevin Lewis missed) belongs to a different attribute and is not held against this one.

**Evidence:**
- `uar-netsuite-q2-2026.xlsx` @ `Cover!Reviewer / Approver` — Reviewer / Approver identified as 'Priya Nadkarni, Director, Finance Systems (System Owner)' for NetSuite (Production).
- `uar-netsuite-q2-2026.xlsx` @ `Cover!Reviewer Sign-off` — 'Approved electronically by Priya Nadkarni on 2026-06-30.' — documented sign-off.
- `uar-netsuite-q2-2026.xlsx` @ `Access Review!G2:G6 (Reviewed By column, sampled rows)` — All sampled rows show 'Priya Nadkarni' as Reviewed By with Review Date 2026-06-30.
- `uar-netsuite-q2-2026.xlsx` @ `System Access Export (full user list)` — Priya Nadkarni does not appear as a user in the NetSuite access export — she did not review her own access.
- `uar-netsuite-q2-2026.xlsx` @ `Deterministic reperformance: reviewer_names, unique_review_dates` — Single reviewer 'Priya Nadkarni' and single review date '2026-06-30' across all 334 rows; reviewer_sheet_rows (334) equals system_export_rows (334).

**Exceptions considered:**
- Considered whether the reviewer might also be a user of the system (self-review) — she is not present in the system access export.
- Considered whether reconciliation gaps (Kevin Lewis missed, service account orphans) undermine this attribute — they pertain to review completeness/effectiveness, a separate attribute, and do not affect reviewer appropriateness/independence/sign-off.

## ⚠️ Inappropriate or excessive access identified during the review is remediated in a timely manner
**Verdict**: `FURTHER_EVIDENCE_REQUIRED`  · confidence `0.80`

The reviewer flagged one account (Danielle Goodwin) for revocation and the summary records remediation via ITSM ticket ITSM-48217 assigned to IT with a 5-business-day SLA. However, no evidence has been provided showing (a) the ticket itself, (b) that the access was actually revoked, or (c) post-remediation confirmation that the account is now inactive in NetSuite. Additionally, the reperformance identified a second terminated-but-active account (Kevin Lewis) that the reviewer incorrectly retained — this is a reviewer-completeness issue, not strictly a remediation-timeliness issue, but it means only 1 of 2 real findings entered the remediation workflow. To reach SUCCESS, provide the ITSM-48217 ticket record with closure date and a post-remediation NetSuite screenshot showing Danielle Goodwin's account is inactive/deleted.

**Evidence:**
- `uar-netsuite-q2-2026.xlsx` @ `Cover!Observation 1` — States Danielle Goodwin retains ACTIVE access despite HRIS termination effective 2021-12-03; access flagged for immediate revocation and deprovisioning ticket ITSM-48217 raised, assigned to IT Identity & Access, due within 5 business days.
- `uar-netsuite-q2-2026.xlsx` @ `Cover!Conclusion` — 'Review complete. 1 observation raised and remediated via ITSM-48217.' — narrative claims remediation but no supporting ticket artefact provided.
- `uar-netsuite-q2-2026.xlsx` @ `Access Review!E90 (Danielle Goodwin row)` — Reviewer Decision = 'revoke' for danielle.goodwin@northpeakfinancial.com — the flagged item is documented with a remediation action in the review workbook.
- `uar-netsuite-q2-2026.xlsx` @ `Access Review!E187 (Kevin Lewis row)` — Reviewer Decision = 'retain' for kevin.lewis@northpeakfinancial.com despite HRIS showing terminated — this account was not flagged for remediation, so no remediation was triggered.
- `deterministic reperformance` @ `reviewer_missed_findings / terminated_but_active_in_system` — Reperformance identifies 2 terminated-but-active accounts (Danielle Goodwin, Kevin Lewis); only Danielle Goodwin entered the remediation workflow.

**Exceptions considered:**
- Considered whether Kevin Lewis being missed by the reviewer belongs to a separate 'reviewer completeness' attribute rather than this timeliness attribute — it primarily does, but it is noted because remediation cannot be timely for a finding that was never raised.
- Considered whether the narrative statement 'remediated via ITSM-48217' on the Cover sheet is sufficient evidence — rejected because there is no independent artefact (ticket export or post-remediation system screenshot) confirming the revocation actually occurred.
