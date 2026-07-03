# Change Management — sample-2
_generated: 2026-07-03T04:16:36.535799+00:00 · model: claude:claude-opus-4-8_

## ❌ Control conclusion: `CONTROL_FAIL`

### Evidence coverage — 100%
- All files provided: 3
- Cited in at least one verdict: 3

---

## Attribute-level verdicts

## ✅ Every production change has a corresponding change request that documents scope, risk classification, and rollback plan
**Verdict**: `SUCCESS`  · confidence `0.88`

A change request exists (CHG-2026-0912, correct CHG-YYYY-NNNN format) and documents scope (systems affected, repositories touched, config surfaces), a Medium risk classification, a rollback plan with RTO, a named requester, a named approver, and a planned window with start/end times. The change is in scope — it deploys new production services (reports-api/worker/db), not a documentation-only, incident-response hotfix, or dev/staging change. Note: the requester and approver are the same person (Marcus Bell), which violates four-eyes, but that is a separate approval-independence attribute and does not defeat this documentation-completeness attribute.

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
- `change-request.md` @ `Title + header block (CHG-2026-0912, Category/Risk/System(s) affected/Repositories touched/Planned window)` — Identifier CHG-2026-0912 in CHG-YYYY-NNNN format; Risk: Medium; systems reports-api/reports-worker/reports-db; repos northpeak/reports-service PR#47 and infra-terraform PR#2438; planned window 2026-06-28 15:00→17:00 UTC.
- `change-request.md` @ `## Scope and ## Rollback plan sections` — Scope lists deploying reporting service, provisioning RDS, configuring IAM/API gateway routes. Rollback plan enumerates 3 steps with a 5-minute RTO.
- `change-request.md` @ `## Requester and ## Approver sections` — Requester named as Marcus Bell (Platform Engineer); Approver also named as Marcus Bell — same person, satisfying the 'names requester/approver' criteria though not independence.
- `deployment-log.txt` @ `Header + provisioning/deploy lines` — Confirms this is a production deployment of new services (reports-api ECS rev 4, reports-worker, reports-db RDS), establishing the change is in scope for change management.

**Exceptions considered:**
- Documentation-only / incident-response hotfix / dev-staging exception rejected — evidence shows a production deployment of new services (reports-api, reports-worker, RDS reports-db), so the change is in scope.
- Same-person requester and approver noted, but this is an approval-independence concern belonging to a separate attribute; per attribute isolation it does not fail this documentation-completeness attribute, which requires only that requester and approver be named (both are).

## ❌ Production changes are approved by an authorised change approver prior to deployment
**Verdict**: `FAIL`  · confidence `0.97`

This is a Normal change (per the change request), which requires 2 approvers (Change Coordinator + CAB Change Approver) and CAB approval — instead it was self-approved by the requester Marcus Bell with no CAB review, violating the four-eyes principle. The approver and requester are the same named human (marcus.bell), and the note explicitly states "skipped CAB review to hit end-of-quarter demo deadline." Retrospective approval is only valid for Emergency changes, but this is classified Normal, so the retroactive CAB scheduled for 2026-07-02 does not cure the defect. Multiple criteria fail.

**Policy references:**
- `change-management-policy.md` § Approval Rules: “The approver must be a different named human from the requester (four-eyes principle).”
- `change-management-policy.md` § Change Categories: “Normal | Non-routine change with a defined risk assessment | 2 (Change Coordinator + Change Approver from CAB) | Yes”
- `change-management-policy.md` § Approval Rules: “Retrospective approvals are only valid for Emergency changes and must be documented as such.”

**Evidence:**
- `change-request.md` @ `Category / Requester / Approver fields` — Category is 'Normal'; both Requester and Approver are listed as the same person, Marcus Bell (marcus.bell@northpeakfinancial.com).
- `change-request.md` @ `Approval record section` — CAB meeting reference is '(none — deployed under standing team autonomy waiver)', decision is 'Self-approved', with a note that CAB review was skipped to hit an end-of-quarter deadline and a retroactive CAB scheduled for 2026-07-02.
- `deployment-log.txt` @ `approval verification line at 15:04:20 UTC` — Log records 'approval OK — CHG-2026-0912 approved by marcus.bell at 2026-06-28T14:47:00Z (self-approved)', confirming the deployer/approver/requester are the same individual.

**Exceptions considered:**
- Retrospective approval exception — rejected: retrospective approvals are only valid for Emergency changes, but this change is classified Normal, so the retroactive CAB does not validate it.
- Standard-change single-approver path — rejected: the change request explicitly classifies this as a Normal change requiring 2 approvers plus CAB.

## ❌ Pre-deployment testing is completed and evidence retained before release
**Verdict**: `FAIL`  · confidence `0.95`

This is a Normal change (per change-request.md), so failed tests must block deployment. The pre-deployment test results show TC-002 (functional) and TC-004 (regression) both FAIL, and the change request itself admits "3 test cases failed on staging... Deployment proceeded pending post-deployment fix." The deployment log further shows two canary transactions FAILED (5xx) yet an override was applied ("accepting canary failure for demo") and the change completed as DEPLOYED. The criterion "IF Standard or Normal AND tests failed THEN was deployment blocked?" is positively contradicted — tests failed and deployment was not blocked.

**Policy references:**
- `change-management-policy.md` § Testing Requirements: “Failed tests block deployment for Standard/Normal changes; must be documented as accepted risk for Emergency changes.”
- `change-management-policy.md` § Testing Requirements: “Standard and Normal changes: pre-deployment testing evidence (test plan + test results) must be attached to the change request.”

**Evidence:**
- `change-request.md` @ `Category / Testing evidence sections` — Change is categorized 'Normal'; the Testing evidence section states '3 test cases failed on staging (2 functional, 1 performance). Deployment proceeded pending post-deployment fix.'
- `pre-deployment-test-results.xlsx` @ `Test Cases!Result column (TC-002, TC-004)` — TC-002 (Functional — Q2 aggregate) result FAIL and TC-004 (Regression — legacy CSV columns) result FAIL, confirming failed tests among pre-deployment results.
- `deployment-log.txt` @ `2026-06-28 15:19:41–15:20:00 UTC lines` — Two canary transactions FAILED (5xx), then 'override applied — accepting canary failure for demo'; deployment completed with status DEPLOYED despite failures.

**Exceptions considered:**
- Documentation-only / staging-only exceptions rejected — this deploys new production services (reports-api, reports-worker, reports-db) to production, so no exception applies.
- Emergency post-deployment verification path rejected — change is explicitly categorized 'Normal', not Emergency, so the deployment-blocking rule (not the 24-hour verification rule) governs.
