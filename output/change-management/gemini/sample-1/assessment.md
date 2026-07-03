# Change Management — sample-1
_generated: 2026-07-03T01:56:46.131962+00:00 · model: gemini:gemini-3.1-pro-preview_

## ✅ Every production change has a corresponding change request that documents scope, risk classification, and rollback plan
**Verdict**: `SUCCESS`  · confidence `1.00`

The change request contains all required documentation according to policy. It includes a standard change identifier (CHG-2026-0847), defines the scope with affected systems and repositories, and explicitly lists the risk classification as 'Medium'. Additionally, the rollback plan, named requester/approver, and planned start/end times are all clearly documented.

**Policy references:**
- `change-management-policy.md` § Required Documentation: “Every change (regardless of category) must include:
- A change request identifier (e.g. CHG-YYYY-NNNN)
- Scope: systems affected, code repositories, config surfaces
- Risk classification (Low / Medium / High)
- Rollback plan
- Named requester and named approver
- Planned start and end times”

**Evidence:**
- `change-request.md` @ `Header and metadata section` — Identified change request CHG-2026-0847, classified as 'Medium' risk, with systems 'payments-primary' and 'payments-api' and repository 'northpeak/infra-terraform' in scope, along with a planned window of 2026-06-24 20:00 UTC to 22:00 UTC.
- `change-request.md` @ `## Rollback plan` — Found a documented 3-step rollback plan detailing the restoration of a point-in-time snapshot.
- `change-request.md` @ `## Requester and ## Approver sections` — Explicitly names Marcus Bell as the requester and Priya Nadkarni as the approver.

## ❌ Production changes are approved by an authorised change approver prior to deployment
**Verdict**: `FAIL`  · confidence `1.00`

The change CHG-2026-0847 is categorized as a 'Normal' change, which requires a minimum of two approvers (a Change Coordinator and a Change Approver from CAB). However, both the change request and the deployment log explicitly record only one approver (Priya Nadkarni). Because it falls short of the required approver count, this attribute fails.

**Policy references:**
- `change-management-policy.md` § Change Categories: “| Normal | Non-routine change with a defined risk assessment | 2 (Change Coordinator + Change Approver from CAB) | Yes |”

**Evidence:**
- `change-request.md` @ `Approver section` — Only a single approver, Priya Nadkarni, is listed for the change request.
- `deployment-log.txt` @ `Lines 8-9 (approval status verification)` — The deployment log only confirms approval by a single individual (priya.nadkarni) with no indication of a second approver.

**Exceptions considered:**
- The policy exception for documentation-only or development changes does not apply, as this was a major database upgrade on a production payments cluster.

## ✅ Pre-deployment testing is completed and evidence retained before release
**Verdict**: `SUCCESS`  · confidence `1.00`

The change is categorized as a Normal change, and pre-deployment testing evidence is explicitly attached to the change request. The attached testing evidence includes functional smoke tests targeting the affected payments API, and all executed test cases are marked as passing with zero failures blocking deployment.

**Policy references:**
- `change-management-policy.md` § Testing Requirements: “Standard and Normal changes: pre-deployment testing evidence (test plan + test results) must be attached to the change request.”
- `change-management-policy.md` § Testing Requirements: “Testing must include, at minimum, functional smoke tests of the affected surfaces.”
- `change-management-policy.md` § Testing Requirements: “Failed tests block deployment for Standard/Normal changes; must be documented as accepted risk for Emergency changes.”

**Evidence:**
- `change-request.md` @ `Lines 3-4 (Category)` — The change is classified as a Normal change category.
- `change-request.md` @ `Testing evidence section` — References the attached pre-deployment-test-results.xlsx and confirms that all planned test cases passed on staging.
- `pre-deployment-test-results.xlsx` @ `Test Cases!A1:F6` — The test results document includes functional smoke tests for the payments API (e.g., '/healthz' response, ledger inserts/reads), with all sampled tests showing a 'PASS' result.
