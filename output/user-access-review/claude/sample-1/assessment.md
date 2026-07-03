# User Access Review — sample-1
_generated: 2026-07-03T03:38:45.338277+00:00 · model: claude:claude-opus-4-7_

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

Evidence shows a Q2 2026 quarterly UAR was performed for NetSuite Production, completed on 2026-06-30 by Priya Nadkarni. The review covered all 334 users from the system access export (332 in-scope humans + 2 service accounts flagged out of scope), matching the population as of the review date. IPE checks reconcile system export row counts to the Cover sheet and reviewer decisions. Frequency labelled quarterly and completion date is documented; no prior-quarter review date is in evidence but the review type and completion are clearly stated.

**Evidence:**
- `uar-netsuite-q2-2026.xlsx` @ `Cover!Review Period / Review Type / Review Completed` — Review Period = Q2 2026; Review Type = Periodic (Quarterly) User Access Review; Review Completed = 2026-06-30; Reviewer/Approver = Priya Nadkarni.
- `uar-netsuite-q2-2026.xlsx` @ `Access Review sheet (334 rows) Review Date column` — All rows carry Review Date 2026-06-30, reviewed by Priya Nadkarni.
- `uar-netsuite-q2-2026.xlsx` @ `System Access Export sheet (334 rows)` — Population of 334 accounts covered by the Access Review sheet (332 in-scope + 2 service accounts marked out of scope).
- `deterministic reperformance` @ `ipe_checks` — All three IPE checks pass: export row count reconciles to Cover, service-account carve-out matches, and reviewer decision counts (331 retain / 1 revoke) tie to Cover.

**Exceptions considered:**
- Prior-quarter review date not directly evidenced; however the review is explicitly designated as Quarterly and completed 2026-06-30, satisfying the periodicity criterion for the period under review.

## ✅ Access is reviewed and approved by an appropriate system or data owner
**Verdict**: `SUCCESS`  · confidence `0.90`

The reviewer is identified on the Cover sheet as "Priya Nadkarni, Director, Finance Systems (System Owner)" — name and role are documented, and she is designated as the NetSuite system owner. All 334 rows on the Access Review sheet show "Reviewed By: Priya Nadkarni" with a review date, and the Cover sheet records electronic sign-off on 2026-06-30. Independence is satisfied: the reviewer's name does not appear as an in-scope user being reviewed (she is not among the listed NetSuite user accounts), and the workbook was prepared by a separate individual (Marcus Bell). Documented approval is captured via the signed workbook and per-line reviewer attribution.

**Evidence:**
- `uar-netsuite-q2-2026.xlsx` @ `Cover!Reviewer / Approver` — Reviewer / Approver identified as 'Priya Nadkarni, Director, Finance Systems (System Owner)'.
- `uar-netsuite-q2-2026.xlsx` @ `Cover!Reviewer Sign-off` — 'Approved electronically by Priya Nadkarni on 2026-06-30.'
- `uar-netsuite-q2-2026.xlsx` @ `Access Review!G2:G335 (Reviewed By column)` — All 334 rows attributed to 'Priya Nadkarni' with Review Date 2026-06-30; reperformance confirms only one unique reviewer name.
- `uar-netsuite-q2-2026.xlsx` @ `Cover!Prepared By` — Prepared by Marcus Bell, IT Compliance Analyst — separate individual from reviewer.
- `uar-netsuite-q2-2026.xlsx` @ `System Access Export (Username list)` — Priya Nadkarni does not appear in the list of in-scope NetSuite user accounts being reviewed — reviewer is not reviewing her own access.

**Exceptions considered:**
- Considered whether reviewer independence is compromised by self-review; Priya Nadkarni is not in the in-scope user list, so she did not self-approve.

## ⚠️ Inappropriate or excessive access identified during the review is remediated in a timely manner
**Verdict**: `FURTHER_EVIDENCE_REQUIRED`  · confidence `0.80`

The reviewer flagged one account (Danielle Goodwin) for revocation and a deprovisioning ticket ITSM-48217 was raised and assigned to IT with a 5-business-day SLA, but no evidence of actual ticket closure/completion or a system screenshot confirming the account was deprovisioned has been provided. Additionally, the reperformance identified a second terminated-but-active account (Kevin Lewis) that the reviewer incorrectly marked "retain" — this is a completeness issue for identifying flagged items, but for THIS attribute (timeliness of remediation of items that were flagged), we can only assess the one item that was flagged. To flip to SUCCESS, provide evidence that ITSM-48217 was closed (deprovisioning log, ticket resolution timestamp, or NetSuite screenshot showing the account inactive) within the SLA window following the 2026-06-30 review completion.

**Evidence:**
- `uar-netsuite-q2-2026.xlsx` @ `Cover!Observation 1` — States Danielle Goodwin's access was flagged for immediate revocation and deprovisioning ticket ITSM-48217 was raised and assigned to IT Identity & Access with due date within 5 business days. No evidence of ticket closure or actual deprovisioning provided.
- `uar-netsuite-q2-2026.xlsx` @ `Cover!Review Completed / Reviewer Sign-off` — Review completed 2026-06-30; conclusion states '1 observation raised and remediated via ITSM-48217' but no supporting ticket closure artefact is included in the workbook.
- `uar-netsuite-q2-2026.xlsx` @ `Access Review!E90 (Danielle Goodwin row)` — Reviewer decision recorded as 'revoke' — this is the sole flagged item requiring remediation.
- `reperformance` @ `terminated_but_active_in_system / system_status for danielle.goodwin` — As of the reperformance snapshot, Danielle Goodwin's system_status is still 'active' in the NetSuite export, indicating the revocation may not yet have been executed at the point the export was taken.

**Exceptions considered:**
- Kevin Lewis (terminated but active, reviewer marked 'retain') was NOT flagged by the reviewer, so it does not fall within this attribute's scope (timeliness of remediation of flagged items) — it is a reviewer-completeness issue belonging to a different attribute. Noted but not used as a basis for this verdict.
