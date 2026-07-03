# Change Management — sample-2
_generated: 2026-07-03T01:57:33.800757+00:00 · model: gemini:gemini-3.1-pro-preview_

## ❌ Every production change has a corresponding change request that documents scope, risk classification, and rollback plan
**Verdict**: `FAIL`  · confidence `1.00`

While the change request successfully documents an identifier (CHG-2026-0912), scope, risk classification (Medium), rollback plan, and planned times, it fails the independent approval requirement. The criterion requiring the requester and approver to be explicitly named is not satisfied because both roles are fulfilled by the same person (Marcus Bell), which violates the policy's four-eyes principle.

**Policy references:**
- `change-management-policy.md` § Approval Rules: “The approver must be a different named human from the requester (four-eyes principle).”

**Evidence:**
- `change-request.md` @ `## Requester and ## Approver` — Marcus Bell is explicitly listed as both the Requester and the Approver for the change request.
- `change-request.md` @ `## Approval record` — The record notes the change was 'Self-approved' by Marcus Bell.
- `deployment-log.txt` @ `Lines 8-9 (timestamps 15:04:20 UTC)` — The deployment script explicitly verified that the change was self-approved by marcus.bell.

**Exceptions considered:**
- The change request mentions deploying under a 'standing team autonomy waiver' to hit a quarter-end demo deadline. This exception was rejected because it is not listed among the permitted exceptions (e.g., documentation-only changes, break-fix hotfixes) in the Change Management Policy.

## ❌ Production changes are approved by an authorised change approver prior to deployment
**Verdict**: `FAIL`  · confidence `1.00`

The change was self-approved by the requester, violating the four-eyes principle. Additionally, as a Normal change, it failed to obtain the mandatory minimum of two approvals and lacked required CAB approval prior to deployment.

**Policy references:**
- `change-management-policy.md` § Approval Rules: “The approver must be a different named human from the requester (four-eyes principle).”
- `change-management-policy.md` § Change Categories: “2 (Change Coordinator + Change Approver from CAB)”

**Evidence:**
- `change-request.md` @ `Requester and Approver sections` — Marcus Bell is listed as both the requester and the sole approver.
- `change-request.md` @ `Approval record section` — CAB review was explicitly skipped and the change was self-approved, despite being categorized as a Normal change.
- `deployment-log.txt` @ `Line 10` — The runner log confirms approval was checked and noted as self-approved by marcus.bell.

**Exceptions considered:**
- The change request mentions a 'standing team autonomy waiver' to bypass CAB, but this is not a recognized exception under the Exceptions section of the Change Management Policy (which only permits documentation, break-fix incidents, or non-production changes).

## ❌ Pre-deployment testing is completed and evidence retained before release
**Verdict**: `FAIL`  · confidence `1.00`

The change was categorized as a Normal change, which requires zero failed tests to proceed with deployment according to policy. However, the testing evidence indicates multiple functional and regression test failures prior to deployment, and the change request explicitly notes that deployment proceeded despite these 3 failed tests.

**Policy references:**
- `change-management-policy.md` § Testing Requirements: “Failed tests block deployment for Standard/Normal changes; must be documented as accepted risk for Emergency changes.”

**Evidence:**
- `change-request.md` @ `Category and Testing evidence sections` — Classifies the change as Normal and explicitly states that 3 test cases failed on staging but deployment proceeded pending a post-deployment fix.
- `pre-deployment-test-results.xlsx` @ `Test Cases!A1:F7` — Lists multiple test cases, including TC-002 and TC-004, with a result of 'FAIL'.

**Exceptions considered:**
- Considered whether the change qualified as an Emergency change where failed tests could be documented as an accepted risk, but the change request explicitly categorized it as 'Normal'.
