# Change Management — sample-2
_generated: 2026-07-03T03:14:09.627588+00:00 · model: claude:claude-opus-4-7_

## ❌ Control conclusion: `CONTROL_FAIL`

### Evidence coverage — 100%
- All files provided: 3
- Cited in at least one verdict: 3

---

## Attribute-level verdicts

## ✅ Every production change has a corresponding change request that documents scope, risk classification, and rollback plan
**Verdict**: `SUCCESS`  · confidence `0.95`

The change request exists with identifier CHG-2026-0912 (correct format), documents scope (systems, repositories, config surfaces), risk classification (Medium), a rollback plan with steps and RTO, a named requester and named approver, a planned window (2026-06-28 15:00–17:00 UTC), and categorises the change as Normal. All documentation-completeness criteria for this attribute are met. Note: the requester and approver being the same person is a separate approval/independence attribute and is not judged here.

**Policy references:**
- `change-management-policy.md` § Required Documentation: “Every change (regardless of category) must include: A change request identifier (e.g. CHG-YYYY-NNNN); Scope: systems affected, code repositories, config surfaces; Risk classification (Low / Medium / High); Rollback plan; Named requester and named approver; Planned start and end times”
- `change-management-policy.md` § Change Categories: “Standard | Normal | Emergency”

**Evidence:**
- `change-request.md` @ `Title line` — Change request identifier 'CHG-2026-0912' matches CHG-YYYY-NNNN format.
- `change-request.md` @ `Header block (Category, Risk, System(s) affected, Repositories touched, Planned window)` — Category: Normal; Risk: Medium; systems reports-api/reports-worker/reports-db listed; repositories northpeak/reports-service PR #47 and northpeak/infra-terraform PR #2438 listed; planned window 2026-06-28 15:00 UTC → 17:00 UTC.
- `change-request.md` @ `Scope section` — Documents scope: deploy reporting service, provision RDS, configure IAM roles and API gateway routes (config surfaces).
- `change-request.md` @ `Rollback plan section` — Three-step rollback plan with timings and 5-minute RTO documented.
- `change-request.md` @ `Requester and Approver sections` — Named requester Marcus Bell and named approver Marcus Bell are both documented (independence is a separate attribute).

**Exceptions considered:**
- Documentation-only change exception — rejected: this deploys a new production service and RDS instance, not documentation.
- Dev/staging exception — rejected: deployment targets production per deployment-log.txt.

## ❌ Production changes are approved by an authorised change approver prior to deployment
**Verdict**: `FAIL`  · confidence `0.99`

The change is self-approved: requester and approver are both Marcus Bell, violating the four-eyes principle. Additionally, this is a Normal change which requires 2 approvers (Change Coordinator + CAB Approver) with CAB review evidenced — the record explicitly states CAB was skipped and only a retroactive CAB was scheduled. Retrospective approval is only valid for Emergency changes, but this change is documented as Normal.

**Policy references:**
- `change-management-policy.md` § Approval Rules: “The approver must be a different named human from the requester (four-eyes principle).”
- `change-management-policy.md` § Change Categories: “Normal | Non-routine change with a defined risk assessment | 2 (Change Coordinator + Change Approver from CAB) | Yes”
- `change-management-policy.md` § Approval Rules: “Retrospective approvals are only valid for Emergency changes and must be documented as such.”

**Evidence:**
- `change-request.md` @ `Requester and Approver sections` — Both Requester and Approver are listed as 'Marcus Bell (Platform Engineer) — marcus.bell@northpeakfinancial.com' — same human.
- `change-request.md` @ `Category header` — Category is 'Normal' with Risk 'Medium'.
- `change-request.md` @ `Approval record section` — 'CAB meeting reference: (none — deployed under standing team autonomy waiver)', 'Approval decision: Self-approved', note states CAB skipped and retroactive CAB scheduled for 2026-07-02.
- `deployment-log.txt` @ `approval verification line at 15:04:20 UTC` — Log records 'approved by marcus.bell at 2026-06-28T14:47:00Z (self-approved)' confirming self-approval was accepted by the deployment runner.

**Exceptions considered:**
- Considered whether a 'standing team autonomy waiver' could substitute for CAB approval — rejected, no such exception exists in the Change Management Policy.
- Considered whether retrospective CAB could cure the deficiency — rejected because retrospective approvals per policy are only valid for Emergency changes, and this is documented as Normal.

## ❌ Pre-deployment testing is completed and evidence retained before release
**Verdict**: `FAIL`  · confidence `0.98`

This is a Normal change with failed pre-deployment tests, yet deployment proceeded. Test Cases sheet shows TC-002 (Functional) and TC-004 (Regression) with Result=FAIL on 2026-06-28 09:02–09:06, and the change request itself acknowledges "3 test cases failed on staging... Deployment proceeded pending post-deployment fix". The deployment log confirms deployment completed at 15:31:02 UTC with status DEPLOYED. Per policy, "Failed tests block deployment for Standard/Normal changes" — this criterion is directly violated.

**Policy references:**
- `change-management-policy.md` § Testing Requirements: “Failed tests block deployment for Standard/Normal changes; must be documented as accepted risk for Emergency changes.”
- `change-management-policy.md` § Testing Requirements: “Standard and Normal changes: pre-deployment testing evidence (test plan + test results) must be attached to the change request.”

**Evidence:**
- `change-request.md` @ `Header — Category` — Change is classified Category: Normal, Risk: Medium.
- `pre-deployment-test-results.xlsx` @ `Test Cases!D3 (TC-002 Result)` — TC-002 functional test 'reports service returns Q2 aggregate correctly' Result = FAIL, executed 2026-06-28 09:03.
- `pre-deployment-test-results.xlsx` @ `Test Cases!D5 (TC-004 Result)` — TC-004 regression test 'legacy report export CSV columns unchanged' Result = FAIL, executed 2026-06-28 09:05.
- `change-request.md` @ `Testing evidence section` — Requester notes: '3 test cases failed on staging (2 functional, 1 performance). Deployment proceeded pending post-deployment fix.'
- `deployment-log.txt` @ `Final line — status` — Deployment completed 2026-06-28 15:31:02 UTC — 'status: DEPLOYED (with known post-deploy defects to be fixed 2026-06-29)', confirming release proceeded despite failed tests.

**Exceptions considered:**
- Emergency post-deployment testing allowance — rejected because the change request explicitly classifies this as Normal, not Emergency.
- Documentation-only exception — rejected; this deploys new services and infrastructure.
