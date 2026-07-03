# Change Management — sample-2
_generated: 2026-07-03T02:01:20.816490+00:00 · model: claude:claude-opus-4-7_

## ❌ Every production change has a corresponding change request that documents scope, risk classification, and rollback plan
**Verdict**: `FAIL`  · confidence `0.90`

The change request documents scope, risk classification (Medium), rollback plan, requester, approver, planned window, ID (CHG-2026-0912), and category (Normal). However, the attribute requires that IF the change is Normal THEN a CAB review is recorded. This change is categorised as Normal but the CAB meeting reference is explicitly "(none — deployed under standing team autonomy waiver)" with a retroactive CAB scheduled after deployment. No CAB review is recorded, which fails the Normal-change criterion.

**Policy references:**
- `change-management-policy.md` § Change Categories: “Normal | Non-routine change with a defined risk assessment | 2 (Change Coordinator + Change Approver from CAB) | Yes”

**Evidence:**
- `change-request.md` @ `Header + Approval record section` — Category: Normal; CAB meeting reference: (none — deployed under standing team autonomy waiver); Approval decision: Self-approved; retroactive CAB scheduled 2026-07-02.
- `change-request.md` @ `System(s) affected / Repositories touched / Scope / Risk assessment / Rollback plan / Planned window` — Documents scope (reports-api, reports-worker, reports-db; repos northpeak/reports-service PR#47 and northpeak/infra-terraform PR#2438), risk Medium, rollback plan with 3 steps, planned window 2026-06-28 15:00–17:00 UTC.
- `change-request.md` @ `Title line` — Change request ID 'CHG-2026-0912' matches CHG-YYYY-NNNN format.

**Exceptions considered:**
- Documentation-only exception — rejected: this is a new production service deployment, not documentation.
- Emergency retrospective CAB — rejected: change is categorised Normal, not Emergency, so retrospective CAB is not a valid substitute.

## ❌ Production changes are approved by an authorised change approver prior to deployment
**Verdict**: `FAIL`  · confidence `0.99`

The change request lists Marcus Bell as both requester and approver, and the approval decision is explicitly "Self-approved". This violates the four-eyes principle criterion. Additionally, CHG-2026-0912 is categorised as Normal, which requires 2 approvers (Change Coordinator + Change Approver from CAB); only a single self-approval is recorded, and the CAB review was explicitly skipped. Retrospective CAB is scheduled but retrospective approval is only permitted for Emergency changes.

**Policy references:**
- `change-management-policy.md` § Approval Rules: “The approver must be a different named human from the requester (four-eyes principle).”
- `change-management-policy.md` § Change Categories: “Normal | Non-routine change with a defined risk assessment | 2 (Change Coordinator + Change Approver from CAB) | Yes”
- `change-management-policy.md` § Approval Rules: “Retrospective approvals are only valid for Emergency changes and must be documented as such.”

**Evidence:**
- `change-request.md` @ `Category field header` — Change is categorised as Normal, Risk Medium.
- `change-request.md` @ `Requester and Approver sections` — Both requester and approver are listed as Marcus Bell (marcus.bell@northpeakfinancial.com).
- `change-request.md` @ `Approval record section` — Approval decision recorded as 'Self-approved'; CAB meeting reference states '(none — deployed under standing team autonomy waiver)'; note states CAB was skipped to hit demo deadline with a retroactive CAB scheduled 2026-07-02.
- `deployment-log.txt` @ `approval verification line at 15:04:20 UTC` — Deployment runner logs 'approval OK — CHG-2026-0912 approved by marcus.bell at 2026-06-28T14:47:00Z (self-approved)'.

**Exceptions considered:**
- Retrospective/emergency exception: rejected because the change is documented as Normal, not Emergency, so retrospective CAB approval is not permitted.
- Documentation-only exception: rejected — this is a new production service and RDS provisioning, clearly in scope.

## ❌ Pre-deployment testing is completed and evidence retained before release
**Verdict**: `FAIL`  · confidence `0.97`

Change is Normal, so failed tests must block deployment. The test workbook shows TC-002 (Functional) and TC-004 (Regression) FAILED on 2026-06-28, yet the deployment log shows the change was deployed at 15:04–15:31 UTC with an explicit "override applied — accepting canary failure for demo". The change request itself admits "3 test cases failed on staging... Deployment proceeded pending post-deployment fix." This directly violates the criterion that failed tests block deployment for Standard/Normal changes.

**Policy references:**
- `change-management-policy.md` § Testing Requirements: “Failed tests block deployment for Standard/Normal changes; must be documented as accepted risk for Emergency changes.”
- `change-management-policy.md` § Testing Requirements: “Standard and Normal changes: pre-deployment testing evidence (test plan + test results) must be attached to the change request.”

**Evidence:**
- `pre-deployment-test-results.xlsx` @ `Test Cases!D3 (TC-002 Result)` — Functional test TC-002 'reports service returns Q2 aggregate correctly' Result = FAIL, executed 2026-06-28 09:03.
- `pre-deployment-test-results.xlsx` @ `Test Cases!D5 (TC-004 Result)` — Regression test TC-004 'legacy report export CSV columns unchanged' Result = FAIL, executed 2026-06-28 09:05.
- `change-request.md` @ `Category / Testing evidence sections` — Change is classified Normal; testing section states '3 test cases failed on staging (2 functional, 1 performance). Deployment proceeded pending post-deployment fix.'
- `deployment-log.txt` @ `Lines at 15:19:41–15:31:02 UTC` — Canary transactions failed; override applied to accept failure; deployment completed with status DEPLOYED despite known defects.

**Exceptions considered:**
- Emergency accepted-risk exception: rejected because the change is explicitly classified Normal, not Emergency.
- Documentation-only exception: rejected because the change deploys new production services and infrastructure.
