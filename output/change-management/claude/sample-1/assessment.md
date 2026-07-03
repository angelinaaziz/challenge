# Change Management — sample-1
_generated: 2026-07-03T04:15:54.855353+00:00 · model: claude:claude-opus-4-8_

## ⚠️ Control conclusion: `CONTROL_INCONCLUSIVE`

### Evidence coverage — 100%
- All files provided: 3
- Cited in at least one verdict: 3

---

## Attribute-level verdicts

## ✅ Every production change has a corresponding change request that documents scope, risk classification, and rollback plan
**Verdict**: `SUCCESS`  · confidence `0.92`

The change request CHG-2026-0847 exists and uses the CHG-YYYY-NNNN format. It documents scope (systems affected: payments-primary RDS + payments-api; repository northpeak/infra-terraform PR #2411; the Postgres 15.7→16.3 upgrade and pg library bump), a Medium risk classification, a detailed rollback plan (PITR snapshot, redeploy pinned library, canary verification, 25-min RTO), names requester Marcus Bell and approver Priya Nadkarni, and includes a planned window (2026-06-24 20:00→22:00 UTC). It is a Normal production change to the payments-primary cluster — not documentation-only, not an Incident Response hotfix, and not a dev/staging change — so it is in scope. Every criterion for this attribute is directly satisfied.

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
- `change-request.md` @ `Header + metadata block (CHG-2026-0847, Category/Risk/System(s) affected/Repositories touched/Planned window)` — CR identifier CHG-2026-0847 in correct format; Category Normal; Risk Medium; systems payments-primary (RDS) and payments-api; repo northpeak/infra-terraform PR #2411; planned window 2026-06-24 20:00→22:00 UTC.
- `change-request.md` @ `Scope and Rollback plan sections` — Scope lists the Postgres 15.7→16.3 upgrade, pg@8.11→8.13 bump, no schema changes. Rollback plan gives PITR snapshot snap-payments-2026-06-24-1955, redeploy pinned to pg@8.11, canary verification, 25-min RTO validated in staging drill.
- `change-request.md` @ `Requester and Approver sections` — Requester named Marcus Bell (Platform Engineer); Approver named Priya Nadkarni (Change Approver, CAB) — both distinct named humans.
- `deployment-log.txt` @ `Header (system / executor)` — Deployment targets production payments-primary + payments-api, confirming this is an in-scope production change, not dev/staging or documentation-only.

**Exceptions considered:**
- Documentation-only exception — rejected: change is a production Postgres major upgrade with infra code changes, not README/comment edits.
- Break-fix hotfix / Incident Response exception — rejected: CR is categorised Normal with pre-approved CAB window, not an emergency incident response.
- Dev/staging exception — rejected: deployment log and CR target production payments-primary cluster.

## ⚠️ Production changes are approved by an authorised change approver prior to deployment
**Verdict**: `FURTHER_EVIDENCE_REQUIRED`  · confidence `0.72`

Four-eyes is satisfied (requester Marcus Bell vs approver Priya Nadkarni are different named humans) and approval (2026-06-23 15:42 UTC) preceded the deployment window (2026-06-24 20:00 UTC), consistent with the deployment log. However, this is a Normal change, which requires at least 2 approvers (Change Coordinator + Change Approver from CAB); the change request names only one approver (Priya Nadkarni). The mandatory second Change Coordinator approver is not evidenced, and the CAB minutes proving CAB approval and Priya's Change Approver IdP role (cab-minutes-w25.pdf) are explicitly not in the bundle. Providing the signed CAB minutes showing a distinct Change Coordinator approval plus Priya's Change Approver role would resolve this to SUCCESS.

**Policy references:**
- `change-management-policy.md` § Change Categories: “| Normal | Non-routine change with a defined risk assessment | 2 (Change Coordinator + Change Approver from CAB) | Yes |”
- `change-management-policy.md` § Approval Rules: “The approver must be a different named human from the requester (four-eyes principle). Approvers must hold the Change Approver role in the identity provider. Approval must occur before the deployment window opens.”

**Evidence:**
- `change-request.md` @ `Category / Requester / Approver headings` — Category is 'Normal'; requester is Marcus Bell, approver is Priya Nadkarni (Change Approver, CAB) — two different named humans, but only one approver is listed where a Normal change requires two (Change Coordinator + Change Approver).
- `change-request.md` @ `Approval record section` — Approval timestamp 2026-06-23 15:42 UTC (before window); CAB reference CAB-2026-W25; approval evidence is signed CAB minutes 'cab-minutes-w25.pdf' explicitly noted as NOT included in this evidence bundle.
- `deployment-log.txt` @ `window start line and 20:00:15 approval-OK line` — Deployment window opened 2026-06-24 20:00:02 UTC; runner logged 'approval OK — approved by priya.nadkarni at 2026-06-23T15:42:00Z (CAB-2026-W25)', confirming approval preceded deployment but referencing only a single approver.

**Exceptions considered:**
- Policy 'Documentation-only' / dev-staging / incident-response exceptions — rejected, this is a production RDS upgrade classified Normal, not an exception case.
- Retrospective approval clause — not applicable; approval occurred before the window, so the change is not retrospective.

## ✅ Pre-deployment testing is completed and evidence retained before release
**Verdict**: `SUCCESS`  · confidence `0.85`

The change is classified Normal, so pre-deployment testing evidence (test plan + results) is required. The evidence bundle contains pre-deployment-test-results.xlsx with functional smoke test cases (TC-001–TC-005: /healthz, ledger insert/read, currency conversion) all marked PASS, satisfying the functional-smoke-of-affected-surfaces criterion. All tests passed (no failures to block deployment), and the test results were executed 2026-06-23 14:12–14:14 UTC — before the 2026-06-24 20:00 UTC deployment window — so evidence was retained before release. No tests failed, so the failure/accepted-risk criteria are not triggered.

**Policy references:**
- `change-management-policy.md` § Testing Requirements: “Standard and Normal changes: pre-deployment testing evidence (test plan + test results) must be attached to the change request.”
- `change-management-policy.md` § Testing Requirements: “Testing must include, at minimum, functional smoke tests of the affected surfaces.”
- `change-management-policy.md` § Testing Requirements: “Failed tests block deployment for Standard/Normal changes; must be documented as accepted risk for Emergency changes.”

**Evidence:**
- `change-request.md` @ `Header / Category field` — CHG-2026-0847 is classified Category: Normal, Risk: Medium — triggering the pre-deployment test evidence requirement.
- `change-request.md` @ `Testing evidence section` — References pre-deployment-test-results.xlsx in the bundle; states 42 planned cases pass on staging including 12 functional smoke, 24 regression, 6 rollback validation.
- `pre-deployment-test-results.xlsx` @ `Test Cases!A2:F6 (TC-001 through TC-005)` — Functional smoke tests of the payments API surface (healthz 200, ledger insert/read, monotonic constraint, currency conversion) all show Result=PASS, executed 2026-06-23 14:12–14:14 UTC.
- `deployment-log.txt` @ `window start line` — Deployment window started 2026-06-24 20:00:02 UTC — after the 2026-06-23 test execution timestamps, confirming testing evidence existed and was retained before release.

**Exceptions considered:**
- Emergency post-deployment verification (24h) and accepted-risk criteria — rejected: change is Normal, not Emergency, and no tests failed.
- Documentation-only / staging-environment exception — rejected: this is a production Postgres major upgrade on the payments-primary cluster.
