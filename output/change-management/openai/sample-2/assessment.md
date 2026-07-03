# Change Management — sample-2
_generated: 2026-07-03T01:56:25.509820+00:00 · model: openai:gpt-5.4_

## ❌ Every production change has a corresponding change request that documents scope, risk classification, and rollback plan
**Verdict**: `FAIL`  · confidence `0.98`

A corresponding change request exists and includes identifier CHG-2026-0912, documented scope, systems affected, repositories touched, risk Medium, rollback plan, requester/approver names, and a planned window in change-request.md. However, the documented scope does not explicitly include config surfaces as required; the scope mentions configuring IAM roles and API gateway routes, but there is no dedicated config surfaces field in the required documentation. The named approver also fails policy because the approver is the same named human as the requester (Marcus Bell), which contradicts the four-eyes requirement for named requester and named approver documentation under this attribute.

**Policy references:**
- `change-management-policy.md` § Required Documentation: “Every change (regardless of category) must include:
- A change request identifier (e.g. CHG-YYYY-NNNN)
- Scope: systems affected, code repositories, config surfaces
- Risk classification (Low / Medium / High)
- Rollback plan
- Named requester and named approver
- Planned start and end times”
- `change-management-policy.md` § Approval Rules: “- The approver must be a different named human from the requester (four-eyes principle).”

**Evidence:**
- `change-request.md` @ `Title heading` — The change request is titled 'CHG-2026-0912 — Deploy new Q2 reporting service to production', providing a change request record and identifier.
- `change-request.md` @ `Metadata block` — The metadata lists Category Normal, Risk Medium, affected systems reports-api, reports-worker, and reports-db, repositories northpeak/reports-service and northpeak/infra-terraform, and planned window 2026-06-28 15:00 UTC to 2026-06-28 17:00 UTC.
- `change-request.md` @ `## Scope` — The scope states deployment of a new reporting service, provisioning a new RDS instance, and configuring IAM roles and API gateway routes.
- `change-request.md` @ `## Risk assessment` — The risk assessment is documented as Medium.
- `change-request.md` @ `## Rollback plan` — A rollback plan is documented with steps to delete API gateway routes, scale ECS services to zero, and leave RDS provisioned, with rollback RTO of 5 minutes.
- `change-request.md` @ `## Requester` — The requester is identified as Marcus Bell (Platform Engineer).
- `change-request.md` @ `## Approver` — The approver is also identified as Marcus Bell (Platform Engineer), the same named human as the requester.
- `change-request.md` @ `## Approval record` — The approval record states 'Approval decision: Self-approved' and notes CAB meeting reference none.

**Exceptions considered:**
- Documentation-only change exception rejected because the change deploys new production services, provisions a new RDS instance, and creates API gateway routes.
- Break-fix hotfix / Incident Response exception rejected because the change request is categorized as Normal, not Incident Response.
- Development or staging-only exception rejected because the change request and deployment log both describe production deployment.

## ❌ Production changes are approved by an authorised change approver prior to deployment
**Verdict**: `FAIL`  · confidence `0.99`

The change request records an approval, but the requester and approver are both Marcus Bell, which violates the four-eyes requirement and the criterion that the approver be a different named human. This is a Normal change, yet the record says CAB meeting reference '(none)' and 'Self-approved,' so the required two approvers, including a Change Coordinator and a CAB Change Approver, are not present. Approval was timestamped before the deployment window opened, but that does not cure the failed independence and Normal-change approval criteria.

**Policy references:**
- `change-management-policy.md` § Change Categories: “| Normal | Non-routine change with a defined risk assessment | 2 (Change Coordinator + Change Approver from CAB) | Yes |”
- `change-management-policy.md` § Approval Rules: “- The approver must be a different named human from the requester (four-eyes principle).”
- `change-management-policy.md` § Approval Rules: “- Approvers must hold the Change Approver role in the identity provider.”
- `change-management-policy.md` § Approval Rules: “- Approval must occur **before** the deployment window opens.”

**Evidence:**
- `change-request.md` @ `## Requester` — The named requester is Marcus Bell (Platform Engineer) with email marcus.bell@northpeakfinancial.com.
- `change-request.md` @ `## Approver` — The named approver is also Marcus Bell (Platform Engineer) with the same email, showing self-approval.
- `change-request.md` @ `## Approval record` — The approval record states CAB meeting reference '(none — deployed under standing team autonomy waiver)', approval decision 'Self-approved', and approval timestamp '2026-06-28 14:47 UTC'.
- `change-request.md` @ `Top metadata block` — The change category is listed as Normal and the planned window is 2026-06-28 15:00 UTC to 2026-06-28 17:00 UTC.
- `deployment-log.txt` @ `window start header` — The deployment log shows window start at 2026-06-28 15:04:17 UTC.
- `deployment-log.txt` @ `2026-06-28 15:04:20 UTC line` — The deployment system records 'approval OK' and explicitly says the change was approved by marcus.bell at 2026-06-28T14:47:00Z '(self-approved)'.

**Exceptions considered:**
- Considered whether the policy exception for 'Break-fix hotfixes classified as Incident Response' applied, but the change is explicitly categorized as Normal in the change request, not Incident Response or Emergency.
- Considered whether retrospective approval rules for Emergency changes applied because the note mentions a retroactive CAB scheduled for 2026-07-02, but retrospective approvals are only valid for Emergency changes and this sample is documented as a Normal change.
- Considered whether 'standing team autonomy waiver' created an exception, but no such exception appears in the provided policy excerpt, so it was not accepted.

## ❌ Pre-deployment testing is completed and evidence retained before release
**Verdict**: `FAIL`  · confidence `0.98`

This is a Normal change, so pre-deployment testing evidence with both a test plan and test results was required before release. The change request links only `pre-deployment-test-results.xlsx`, and the workbook contains executed test cases/results but no separate test plan artefact is evidenced; additionally, the change request states 3 staging test failures and the workbook shows failed functional/regression tests before deployment. For a Normal change, failed tests block deployment, so the criterion 'there is no failed test result at the time of deployment' failed.

**Policy references:**
- `change-management-policy.md` § Testing Requirements: “Standard and Normal changes: pre-deployment testing evidence (test plan + test results) must be attached to the change request.”
- `change-management-policy.md` § Testing Requirements: “Testing must include, at minimum, functional smoke tests of the affected surfaces.”
- `change-management-policy.md` § Testing Requirements: “Failed tests block deployment for Standard/Normal changes; must be documented as accepted risk for Emergency changes.”

**Evidence:**
- `change-request.md` @ `Testing evidence section` — The change is marked Category: Normal and the testing evidence says to see `pre-deployment-test-results.xlsx`; it also states that 3 test cases failed on staging and deployment proceeded pending post-deployment fix.
- `pre-deployment-test-results.xlsx` @ `Test Cases!A2:F6` — The workbook shows executed test results for multiple cases, including functional tests and at least two failures: TC-002 marked FAIL and TC-004 marked FAIL, with execution timestamps on 2026-06-28 before deployment.
- `pre-deployment-test-results.xlsx` @ `Workbook structure / Summary sheet` — Only a `Test Cases` sheet with results is populated; the `Summary` sheet is empty and no test plan content is evidenced in the provided workbook.
- `deployment-log.txt` @ `Deployment log lines 1-4 and completion line` — Deployment window ran on 2026-06-28 from 15:04:17 UTC to 15:31:02 UTC, after the pre-deployment test executions recorded around 09:02-09:06 UTC.
- `deployment-log.txt` @ `Canary verification lines near 15:19:41-15:20:00 UTC` — Post-deployment canary transactions failed with 5xx responses and an override was applied accepting the canary failure for a demo, confirming deployment proceeded despite known test failures.

**Exceptions considered:**
- Documentation-only change exception rejected because the change request describes deployment of new production services, infrastructure, IAM roles, and API gateway routes.
- Incident-response / break-fix hotfix exception rejected because the change is explicitly categorized as Normal, not Incident Response or Emergency.
- Emergency-change accepted-risk allowance rejected because the sample is a Normal change; accepted risk for failed tests applies only to Emergency changes under policy.
