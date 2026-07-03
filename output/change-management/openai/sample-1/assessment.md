# Change Management — sample-1
_generated: 2026-07-03T01:56:08.222804+00:00 · model: openai:gpt-5.4_

## ❌ Every production change has a corresponding change request that documents scope, risk classification, and rollback plan
**Verdict**: `FAIL`  · confidence `0.93`

A corresponding change request exists and includes the required identifier, scope, risk classification, rollback plan, named requester/approver, and planned window in `change-request.md`. The scope documents affected systems and repository, and the request records Risk as Medium and a detailed rollback procedure. However, the documented scope does not identify any config surfaces, which fails the criterion requiring scope to include systems affected, code repositories, and config surfaces.

**Policy references:**
- `change-management-policy.md` § Required Documentation: “Every change (regardless of category) must include:
- A change request identifier (e.g. CHG-YYYY-NNNN)
- Scope: systems affected, code repositories, config surfaces
- Risk classification (Low / Medium / High)
- Rollback plan
- Named requester and named approver
- Planned start and end times”
- `change-management-policy.md` § Exceptions: “The following are out of scope:
- Documentation-only changes (README, comments)
- Break-fix hotfixes classified as Incident Response (see Incident Response Policy)
- Changes to development or staging environments”

**Evidence:**
- `change-request.md` @ `Title heading` — The change request is identified as CHG-2026-0847 for upgrading Postgres 15 to 16 on the payments-primary cluster.
- `change-request.md` @ `Header fields` — The document lists Category as Normal, Risk as Medium, affected systems as payments-primary and payments-api, repository touched as northpeak/infra-terraform (PR #2411), and a planned window of 2026-06-24 20:00 UTC to 22:00 UTC.
- `change-request.md` @ `## Scope` — The scope states the Postgres upgrade on payments-primary, an update to the payments-api connection library from pg@8.11 to pg@8.13, and that there are no schema changes.
- `change-request.md` @ `## Rollback plan` — The rollback plan includes restoring a point-in-time snapshot, redeploying payments-api pinned to pg@8.11, and verifying with /healthz and a canary transaction.
- `change-request.md` @ `## Requester` — The requester is named as Marcus Bell, Platform Engineer.
- `change-request.md` @ `## Approver` — The approver is named as Priya Nadkarni, Change Approver, CAB.
- `deployment-log.txt` @ `Log header` — The deployment log references CHG-2026-0847 for payments-primary and payments-api, linking the production deployment to the same change request.

**Exceptions considered:**
- Documentation-only exception rejected because the change request and deployment log describe a production database major version upgrade and application dependency deployment, not README/comments only.
- Incident Response / break-fix hotfix exception rejected because the change is categorized as Normal in the change request, not Incident Response.
- Development or staging exception rejected because the evidence describes deployment to production systems payments-primary and payments-api.

## ⚠️ Production changes are approved by an authorised change approver prior to deployment
**Verdict**: `FURTHER_EVIDENCE_REQUIRED`  · confidence `0.89`

I agree with the first pass. On re-read, the evidence clearly supports several criteria: CHG-2026-0847 is explicitly marked as a Normal change; the change request records an approval decision of Approved; the named approver (Priya Nadkarni) is different from the requester (Marcus Bell); Priya is identified on the record as 'Change Approver, CAB'; and the approval timestamp (2026-06-23 15:42 UTC) is before the deployment window opened (2026-06-24 20:00:02 UTC). However, for a Normal change, the policy requires at least 2 approvers, specifically one Change Coordinator and one CAB Change Approver. The evidence bundle only names one approver anywhere in the provided records, and the attached CAB minutes that might establish additional approval are expressly not included. The deployment log's 'approval OK' line also references only Priya. Because the record on hand does not show the required second approver or identify any Change Coordinator approval, SUCCESS is not defensible from current evidence. Evidence that would resolve this would be the missing CAB minutes, a fuller approval history/export from the change system, or another included record showing a second pre-deployment approval and confirming one approver was the Change Coordinator and one was the CAB Change Approver.

**Policy references:**
- `change-management-policy.md` § Change Categories: “| Normal | Non-routine change with a defined risk assessment | 2 (Change Coordinator + Change Approver from CAB) | Yes |”
- `change-management-policy.md` § Approval Rules: “- The approver must be a different named human from the requester (four-eyes principle).”
- `change-management-policy.md` § Approval Rules: “- Approvers must hold the Change Approver role in the identity provider.”
- `change-management-policy.md` § Approval Rules: “- Approval must occur **before** the deployment window opens.”

**Evidence:**
- `change-request.md` @ `Header / metadata` — The change is categorized as Normal and the planned window is 2026-06-24 20:00 UTC to 2026-06-24 22:00 UTC.
- `change-request.md` @ `Requester section` — The requester is Marcus Bell (Platform Engineer) with email marcus.bell@northpeakfinancial.com.
- `change-request.md` @ `Approver section` — The only named approver shown is Priya Nadkarni, labeled Change Approver, CAB, with email priya.nadkarni@northpeakfinancial.com.
- `change-request.md` @ `Approval record section` — The record states CAB-2026-W25 approval decision Approved with timestamp 2026-06-23 15:42 UTC, and says signed CAB minutes are attached separately but are not included in this evidence bundle.
- `deployment-log.txt` @ `window start header` — The deployment window start is 2026-06-24 20:00:02 UTC, which is after the recorded approval timestamp.
- `deployment-log.txt` @ `log line 'approval OK'` — The deployment log confirms approval by priya.nadkarni at 2026-06-23T15:42:00Z and does not mention any second approver or Change Coordinator approval.

**Exceptions considered:**
- Not a Standard change, so the Standard-change single-approver rule does not apply.
- Not an Emergency change, so emergency retrospective-approval criteria do not apply.
- I considered whether the CAB meeting reference itself could imply multiple approvers, but without the missing CAB minutes or explicit approval history that would be inference rather than evidence.

## ⚠️ Pre-deployment testing is completed and evidence retained before release
**Verdict**: `FURTHER_EVIDENCE_REQUIRED`  · confidence `0.94`

I agree with the first-pass hedge. On re-read, the record is strong for several criteria: this is a Normal change; the change request explicitly references attached pre-deployment evidence; the attached workbook clearly contains test results; visible executed timestamps (2026-06-23 14:12–14:14) are before the 2026-06-24 deployment window; and the visible tests include functional smoke checks of affected surfaces such as /healthz and ledger read/write, all marked PASS. However, the evidence still does not actually show a test plan artifact, despite the change request text claiming '42 planned test cases.' Also, the workbook summary only exposes sample rows from a 12-row sheet and an empty Summary sheet, so we cannot directly verify from the attachment itself that the full attached evidence contains all planned cases or that there were no failed results anywhere in the retained test evidence at the time of deployment. What would resolve this: either (a) a complete view/export of `pre-deployment-test-results.xlsx` showing the full planned set and all results with no FAILs, and a visible test-plan section/sheet, or (b) a separate attached test-plan artifact referenced by the change request.

**Policy references:**
- `change-management-policy.md` § Testing Requirements: “Standard and Normal changes: pre-deployment testing evidence (test plan + test results) must be attached to the change request.”
- `change-management-policy.md` § Testing Requirements: “Testing must include, at minimum, functional smoke tests of the affected surfaces.”
- `change-management-policy.md` § Testing Requirements: “Failed tests block deployment for Standard/Normal changes; must be documented as accepted risk for Emergency changes.”

**Evidence:**
- `change-request.md` @ `Header / metadata block` — The change is explicitly categorized as Normal.
- `change-request.md` @ `## Testing evidence` — The change request says to see `pre-deployment-test-results.xlsx` in the evidence bundle and asserts that all 42 planned test cases pass on staging, including 12 functional smoke, 24 regression, and 6 rollback validation cases.
- `pre-deployment-test-results.xlsx` @ `Test Cases!A1:F12` — The attached workbook contains a 'Test Cases' sheet with result-oriented columns: Test ID, Category, Description, Result, Executed By, and Executed At.
- `pre-deployment-test-results.xlsx` @ `Test Cases sample rows TC-001 to TC-005` — Visible sample test cases are Functional and PASS, covering affected-surface smoke checks including payments API `/healthz`, ledger insert, ledger read, transaction monotonic constraint, and currency conversion.
- `pre-deployment-test-results.xlsx` @ `Summary sheet` — The Summary sheet is empty in the provided workbook summary, so no visible plan/coverage summary or aggregate pass/fail status is available there.
- `deployment-log.txt` @ `window start and deployment steps` — Deployment began on 2026-06-24 20:00:02 UTC, after the visible test execution timestamps in the workbook, confirming the shown tests predate release.

**Exceptions considered:**
- Documentation-only exception not applicable because the scope is a production Postgres major upgrade plus application dependency update.
- Emergency-change exception not applicable because the change is explicitly Normal, so pre-deployment evidence requirements apply.
- Post-deployment success indicators in the deployment log (/healthz and canary passes) were considered corroborating but do not substitute for missing direct evidence of a retained pre-deployment test plan or complete no-fail results set.
