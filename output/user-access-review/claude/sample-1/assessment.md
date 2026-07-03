# User Access Review — sample-1
_generated: 2026-07-03T03:35:51.819219+00:00 · model: claude:claude-opus-4-7_

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
**Verdict**: `SUCCESS`  · confidence `0.85`

The evidence shows a Q2 2026 quarterly access review for NetSuite (Production) was performed and completed on 2026-06-30, with a documented review date on every reviewed row and a Cover sheet declaring the review type as "Periodic (Quarterly) User Access Review". This directly evidences that a review occurred in the audit period, at the defined quarterly cadence, with the review date documented. The interval between consecutive reviews cannot be fully assessed from a single quarter's file, but the cadence declaration and dated Q2 2026 completion satisfy the criteria for this sample.

**Evidence:**
- `uar-netsuite-q2-2026.xlsx` @ `Cover!Review Type / Review Period / Review Completed` — Cover sheet declares Review Period 'Q2 2026', Review Type 'Periodic (Quarterly) User Access Review', and Review Completed '2026-06-30'.
- `uar-netsuite-q2-2026.xlsx` @ `Access Review!H2:H6 (Review Date column)` — All sampled Access Review rows show Review Date 2026-06-30; deterministic reperformance found a single unique review date (2026-06-30) across all 334 rows.
- `uar-netsuite-q2-2026.xlsx` @ `Cover!Reviewer Sign-off` — 'Approved electronically by Priya Nadkarni on 2026-06-30' — confirms review completion date is documented and signed off.

**Exceptions considered:**
- Interval-between-consecutive-reviews criterion: only Q2 2026 is in evidence; no prior quarter's UAR file was provided, so interval cannot be directly measured. Accepted as satisfied for this sample based on the documented quarterly cadence declaration, but would require prior-period UAR to fully verify.

## ✅ Access is reviewed and approved by an appropriate system or data owner
**Verdict**: `SUCCESS`  · confidence `0.90`

The reviewer is identified by name and role on the Cover sheet as "Priya Nadkarni, Director, Finance Systems (System Owner)" and is the sole "Reviewed By" name across all 332 in-scope Access Review rows. Reviewer sign-off is documented ("Approved electronically by Priya Nadkarni on 2026-06-30"). IPE checks reconcile the 334-row export to 332 in-scope + 2 service accounts, and reviewer decisions (331 retain / 1 revoke) tie to Cover totals, evidencing that the approval covers the complete in-scope population.

**Evidence:**
- `uar-netsuite-q2-2026.xlsx` @ `Cover!Reviewer / Approver` — Reviewer/Approver identified as 'Priya Nadkarni, Director, Finance Systems (System Owner)'.
- `uar-netsuite-q2-2026.xlsx` @ `Cover!Reviewer Sign-off` — Sign-off recorded: 'Approved electronically by Priya Nadkarni on 2026-06-30.'
- `uar-netsuite-q2-2026.xlsx` @ `Access Review!G2:G335 (Reviewed By column)` — All 334 rows show 'Priya Nadkarni' as Reviewed By with Review Date 2026-06-30 (single reviewer, single date).
- `uar-netsuite-q2-2026.xlsx` @ `IPE checks / Cover totals` — Reperformance confirms 332 in-scope accounts fully covered (331 retain + 1 revoke reconciles to Cover); 2 service accounts appropriately scoped out.

**Exceptions considered:**
- Service-account carve-out (2 orphan accounts marked 'n/a - out of scope') was considered; this does not undermine population completeness because the carve-out is explicit and reconciles to IPE checks.

## ⚠️ Inappropriate or excessive access identified during the review is remediated in a timely manner
**Verdict**: `FURTHER_EVIDENCE_REQUIRED`  · confidence `0.80`

The reviewer documented one exception (Danielle Goodwin) and evidenced a remediation action — ITSM-48217 was raised and assigned to IT with a 5-business-day SLA. However, the workbook only shows the ticket was raised; there is no evidence that the access was actually revoked in NetSuite (e.g., closed ticket, deprovisioning confirmation, or updated system export showing status=Inactive). Additionally, the reperformer independently identified a second exception (Kevin Lewis — terminated in HRIS but reviewer decided "retain"), which the reviewer missed entirely and therefore no remediation was undertaken; however that gap belongs to the "completeness of exception identification" attribute rather than "timeliness of remediation of identified exceptions." To flip this to SUCCESS, evidence is needed that ITSM-48217 was closed and Danielle Goodwin's NetSuite account is now Inactive, along with the closure date to assess timeliness against the 5-business-day SLA.

**Evidence:**
- `uar-netsuite-q2-2026.xlsx` @ `Cover!Observation 1` — States Danielle Goodwin retains ACTIVE access despite HRIS termination 2021-12-03; remediation: access flagged for immediate revocation; deprovisioning ticket ITSM-48217 raised, assigned to IT Identity & Access, due within 5 business days.
- `uar-netsuite-q2-2026.xlsx` @ `Access Review!E90 (Danielle Goodwin row)` — Reviewer Decision = 'revoke' — the exception is documented on the reviewer sheet.
- `uar-netsuite-q2-2026.xlsx` @ `System Access Export!C90` — Danielle Goodwin account still shows Account Status = Active in the export dated 26 Jun 2026 — no post-remediation export provided to confirm the access was actually revoked.
- `uar-netsuite-q2-2026.xlsx` @ `Cover!Conclusion` — States '1 observation raised and remediated via ITSM-48217' but provides no ticket closure date or confirmation of actual deprovisioning in NetSuite.
- `reperformance (deterministic)` @ `reviewer_missed_findings` — Reperformer identified Kevin Lewis (terminated in HRIS, still active in system) — reviewer decision was 'retain' so no remediation initiated. Not an in-scope failure for this attribute (belongs to identification-completeness), but noted.

**Exceptions considered:**
- Considered whether the ticket number ITSM-48217 alone constitutes sufficient evidence of remediation. Rejected — a ticket being raised evidences a remediation request, not that access was actually revoked in the target system. The attribute explicitly requires 'evidence confirms the access was actually revoked or adjusted in the target system (not just requested).'
- Considered whether Kevin Lewis (missed by reviewer) should cause this attribute to FAIL. Rejected — Kevin Lewis was not 'identified during the review' by the reviewer, so remediation timeliness for identified exceptions is not directly impugned. That gap belongs to the exception-identification attribute.
