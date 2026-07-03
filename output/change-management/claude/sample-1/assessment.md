# Change Management — sample-1
_generated: 2026-07-03T03:36:18.315306+00:00 · model: claude:claude-opus-4-7_

## ⚠️ Control conclusion: `CONTROL_INCONCLUSIVE`

### Evidence coverage — 100%
- All files provided: 3
- Cited in at least one verdict: 3

---

## Attribute-level verdicts

## ✅ Every production change has a corresponding change request that documents scope, risk classification, and rollback plan
**Verdict**: `SUCCESS`  · confidence `0.97`

The change request CHG-2026-0847 exists with the correct CHG-YYYY-NNNN identifier format and documents all required elements: scope (payments-primary RDS, payments-api, repo northpeak/infra-terraform PR #2411, config surfaces), risk classification (Medium), rollback plan (3-step PITR + redeploy + verify), named requester (Marcus Bell), named approver (Priya Nadkarni), planned start/end times (2026-06-24 20:00→22:00 UTC), and change category (Normal). The change is a Postgres major upgrade on production — not a documentation-only, hotfix, or dev/staging change, so no exception applies.

**Policy references:**
- `change-management-policy.md` § Required Documentation: “Every change (regardless of category) must include: A change request identifier (e.g. CHG-YYYY-NNNN); Scope: systems affected, code repositories, config surfaces; Risk classification (Low / Medium / High); Rollback plan; Named requester and named approver; Planned start and end times”
- `change-management-policy.md` § Exceptions: “The following are out of scope: Documentation-only changes (README, comments); Break-fix hotfixes classified as Incident Response; Changes to development or staging environments”

**Evidence:**
- `change-request.md` @ `Title line` — Change request identifier 'CHG-2026-0847' present in CHG-YYYY-NNNN format, titled 'Upgrade Postgres 15 → 16 on payments-primary cluster'.
- `change-request.md` @ `Header metadata block (Category/Risk/Systems/Repos/Window)` — Category: Normal; Risk: Medium; systems affected payments-primary (RDS) and payments-api; repository northpeak/infra-terraform PR #2411; planned window 2026-06-24 20:00 UTC → 22:00 UTC.
- `change-request.md` @ `Scope section` — Documents Postgres 15.7→16.3 upgrade and pg library bump from 8.11 to 8.13, no schema changes.
- `change-request.md` @ `Rollback plan section` — Three-step rollback: PITR snapshot restore (snap-payments-2026-06-24-1955), redeploy payments-api pinned to pg@8.11, verify via /healthz and canary; RTO 25 min, validated in staging drill 2026-06-19.
- `change-request.md` @ `Requester and Approver sections` — Named requester Marcus Bell (Platform Engineer); named approver Priya Nadkarni (Change Approver, CAB).
- `deployment-log.txt` @ `Deployment log header` — Confirms target is production payments-primary + payments-api — not dev/staging, not documentation-only, not an incident-response hotfix.

**Exceptions considered:**
- Documentation-only exception rejected: change is a Postgres major version upgrade with code and infra changes.
- Dev/staging exception rejected: deployment log shows target is payments-primary production cluster.
- Incident-response hotfix exception rejected: change is a planned Normal category change with CAB approval, not a break-fix.

## ⚠️ Production changes are approved by an authorised change approver prior to deployment
**Verdict**: `FURTHER_EVIDENCE_REQUIRED`  · confidence `0.70`

The change request records approval by Priya Nadkarni (Change Approver, CAB), a different named human from requester Marcus Bell, timestamped 2026-06-23 15:42 UTC — before the 2026-06-24 20:00 UTC window. However, this is a Normal change requiring TWO approvers (Change Coordinator + Change Approver from CAB); only one approver (Priya) is named on the change request. Additionally, the CAB minutes (`cab-minutes-w25.pdf`) that would document CAB review and any second approver are explicitly not included in the evidence bundle, and there is no IdP role assignment evidence confirming Priya holds the Change Approver role. Providing the CAB minutes (showing CAB review and Change Coordinator approval) plus an IdP role screenshot for Priya would resolve this to SUCCESS.

**Policy references:**
- `change-management-policy.md` § Change Categories: “Normal | Non-routine change with a defined risk assessment | 2 (Change Coordinator + Change Approver from CAB) | Yes”
- `change-management-policy.md` § Approval Rules: “The approver must be a different named human from the requester (four-eyes principle). Approvers must hold the Change Approver role in the identity provider. Approval must occur before the deployment window opens.”

**Evidence:**
- `change-request.md` @ `Category / Requester / Approver / Approval record sections` — Category = Normal; Requester = Marcus Bell; Approver = Priya Nadkarni (Change Approver, CAB); approval timestamp 2026-06-23 15:42 UTC; only one approver listed; CAB minutes referenced as CAB-2026-W25 but attached file cab-minutes-w25.pdf is explicitly not included in the evidence bundle.
- `change-request.md` @ `Planned window line` — Deployment window planned 2026-06-24 20:00 UTC to 22:00 UTC — approval at 2026-06-23 15:42 UTC precedes window opening.
- `deployment-log.txt` @ `line 'approval OK — CHG-2026-0847 approved by priya.nadkarni at 2026-06-23T15:42:00Z (CAB-2026-W25)'` — Runner verified approval by priya.nadkarni tied to CAB-2026-W25 prior to deployment start at 2026-06-24 20:00:02 UTC. Only one approver named; no second Change Coordinator approval logged.

**Exceptions considered:**
- Emergency retrospective-approval clause — not applicable; change is classified Normal and approval is prospective.
- Documentation-only exception — not applicable; change is a Postgres major version upgrade affecting production.

## ✅ Pre-deployment testing is completed and evidence retained before release
**Verdict**: `SUCCESS`  · confidence `0.90`

The change is categorised Normal, and the change request references an attached test results workbook. pre-deployment-test-results.xlsx contains 12 test cases including functional smoke tests (e.g., /healthz, ledger insert/read) all with PASS results, executed 2026-06-23 (before the 2026-06-24 20:00 UTC deployment window). No failed tests, so the deployment-block criterion is not triggered. Testing evidence is retained and linked from the change request.

**Policy references:**
- `change-management-policy.md` § Testing Requirements: “Standard and Normal changes: pre-deployment testing evidence (test plan + test results) must be attached to the change request.”
- `change-management-policy.md` § Testing Requirements: “Testing must include, at minimum, functional smoke tests of the affected surfaces.”
- `change-management-policy.md` § Testing Requirements: “Failed tests block deployment for Standard/Normal changes; must be documented as accepted risk for Emergency changes.”

**Evidence:**
- `change-request.md` @ `Header — Category` — Change categorised as Normal, Risk Medium.
- `change-request.md` @ `Testing evidence section` — References pre-deployment-test-results.xlsx with 42 test cases passing on staging, including 12 functional smoke, 24 regression, 6 rollback validation.
- `pre-deployment-test-results.xlsx` @ `Test Cases!A1:F13` — 12 test cases listed; sampled rows TC-001..TC-005 all Functional smoke (payments API /healthz, ledger insert/read, monotonic constraint, currency-conversion) with Result=PASS, executed 2026-06-23 14:12–14:14, i.e., before deployment window start of 2026-06-24 20:00 UTC.
- `deployment-log.txt` @ `window start line` — Deployment window began 2026-06-24 20:00:02 UTC, after test execution on 2026-06-23; deployment ultimately status SUCCESS with no failed tests triggering block.

**Exceptions considered:**
- Documentation-only exception — not applicable; this is a Postgres major-version upgrade with code dependency changes.
- Emergency post-deployment testing branch — not applicable; change is Normal, not Emergency.
