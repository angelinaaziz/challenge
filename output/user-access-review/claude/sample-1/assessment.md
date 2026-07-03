# User Access Review — sample-1
_generated: 2026-07-03T02:48:39.054214+00:00 · model: claude:claude-opus-4-7_

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

The evidence shows a completed Q2 2026 UAR performed on a quarterly cadence: the Cover sheet identifies the artefact as a "Periodic (Quarterly) User Access Review" for Review Period "Q2 2026", completed 2026-06-30, and the Access Review sheet contains 334 dated review decisions all signed by Priya Nadkarni on 2026-06-30. The review artefact is dated, retained, and clearly falls within the audit period. Only one prior review is not evidenced here, so interval-vs-cadence cannot be directly measured from a single sample, but the defined cadence and a dated in-period execution are established.

**Evidence:**
- `uar-netsuite-q2-2026.xlsx` @ `Cover!Review Type / Review Period / Review Completed` — Cover sheet states Review Type = 'Periodic (Quarterly) User Access Review', Review Period = 'Q2 2026', Review Completed = '2026-06-30', Reviewer Sign-off = 'Approved electronically by Priya Nadkarni on 2026-06-30.'
- `uar-netsuite-q2-2026.xlsx` @ `Access Review!H2:H6 (Review Date column)` — All sampled review rows carry Review Date 2026-06-30 with Reviewed By 'Priya Nadkarni', evidencing a dated, retained review artefact.
- `uar-netsuite-q2-2026.xlsx` @ `Access Review sheet (row_count=334)` — 334 in-scope accounts reviewed with reviewer decisions recorded — a completed review artefact.

**Exceptions considered:**
- Interval between consecutive reviews: only the Q2 2026 review is in evidence for this sample; cadence conformance across periods would require prior-period UAR artefacts, but the attribute is satisfied by evidencing an in-period review executed on the defined quarterly cadence.

## ✅ Access is reviewed and approved by an appropriate system or data owner
**Verdict**: `SUCCESS`  · confidence `0.90`

The reviewer is named and titled as the system owner: "Priya Nadkarni, Director, Finance Systems (System Owner)" on the Cover sheet, and she is the sole reviewer recorded across all 334 rows of the Access Review sheet. Her sign-off is documented ("Approved electronically by Priya Nadkarni on 2026-06-30"). The population reviewed (334 rows) matches the system access export (334 rows), covering the full population of NetSuite users.

**Evidence:**
- `uar-netsuite-q2-2026.xlsx` @ `Cover!Reviewer / Approver` — Reviewer / Approver identified as 'Priya Nadkarni, Director, Finance Systems (System Owner)'.
- `uar-netsuite-q2-2026.xlsx` @ `Cover!Reviewer Sign-off` — 'Approved electronically by Priya Nadkarni on 2026-06-30.' documents the sign-off.
- `uar-netsuite-q2-2026.xlsx` @ `Access Review!G2:G335 (Reviewed By column)` — All 334 rows show 'Priya Nadkarni' as the Reviewed By value; reviewer_names list contains only her.
- `uar-netsuite-q2-2026.xlsx` @ `System Access Export vs Access Review row counts` — System export has 334 rows and Access Review sheet has 334 rows — full population included in review.

**Exceptions considered:**
- Service accounts (2) were listed as out-of-scope on the cover sheet; this is consistent with the reviewer scoping human accounts, and does not undermine population completeness for the human-user scope.

## ⚠️ Inappropriate or excessive access identified during the review is remediated in a timely manner
**Verdict**: `FURTHER_EVIDENCE_REQUIRED`  · confidence `0.80`

The reviewer documented only 1 exception (Danielle Goodwin) with remediation via ticket ITSM-48217 assigned to IT with a 5-business-day SLA, but no evidence was provided that the ticket was closed or that access was actually removed in NetSuite — so timeliness and completion of remediation cannot be confirmed. Additionally, the reperformance identified a second terminated-but-active account (Kevin Lewis) that the reviewer marked "retain" and therefore has no remediation action documented at all, meaning not every exception has a corresponding remediation. To flip to SUCCESS we would need: (a) ticket closure evidence / system screenshot showing Danielle Goodwin's access revoked within the SLA, and (b) treatment of the Kevin Lewis exception.

**Evidence:**
- `uar-netsuite-q2-2026.xlsx` @ `Cover!Observation 1` — States Danielle Goodwin remained ACTIVE despite HRIS termination effective 2021-12-03; remediation is 'deprovisioning ticket ITSM-48217 raised and assigned to IT (owner: IT Identity & Access; due within 5 business days).' No closure/confirmation evidence provided.
- `uar-netsuite-q2-2026.xlsx` @ `Cover!Conclusion` — 'Review complete. 1 observation raised and remediated via ITSM-48217.' Assertion of remediation with no supporting ticket-closure or system screenshot attached.
- `uar-netsuite-q2-2026.xlsx` @ `Access Review!E187 (Kevin Lewis)` — Reviewer decision recorded as 'Retain' for kevin.lewis@northpeakfinancial.com despite HRIS status = terminated per reperformance; no exception documented and no remediation action assigned.
- `deterministic reperformance` @ `reviewer_missed_findings / terminated_but_active_in_system` — Reperformance found 2 terminated-but-still-active accounts (Danielle Goodwin, Kevin Lewis); only Danielle Goodwin was flagged for revocation by the reviewer. Kevin Lewis has no remediation.

**Exceptions considered:**
- On-leave accounts remaining active were considered — reviewer retained these and this may be acceptable per policy for active employees on leave, so not treated as an un-remediated exception here.
- Service/integration accounts flagged as out-of-scope on the Cover sheet — accepted as scoping, not a remediation gap for this attribute.
