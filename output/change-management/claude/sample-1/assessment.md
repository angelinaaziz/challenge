# Change Management — sample-1
_generated: 2026-07-03T03:13:27.899520+00:00 · model: claude:claude-opus-4-7_

## ⚠️ Control conclusion: `CONTROL_INCONCLUSIVE`

### Evidence coverage — 100%
- All files provided: 3
- Cited in at least one verdict: 3

---

## Attribute-level verdicts

## ✅ Every production change has a corresponding change request that documents scope, risk classification, and rollback plan
**Verdict**: `SUCCESS`  · confidence `0.97`

The change request CHG-2026-0847 satisfies every testable criterion: identifier follows CHG-YYYY-NNNN format; scope enumerates affected systems (payments-primary RDS, payments-api) and repository (infra-terraform PR #2411); risk is classified Medium; a three-step rollback plan with RTO is documented; named requester (Marcus Bell) and approver (Priya Nadkarni) are given; planned start/end window is 2026-06-24 20:00–22:00 UTC; and the change is categorised as Normal. This attribute concerns documentation completeness only — approval validity/independence is judged separately.

**Policy references:**
- `change-management-policy.md` § Required Documentation: “Every change (regardless of category) must include: A change request identifier (e.g. CHG-YYYY-NNNN); Scope: systems affected, code repositories, config surfaces; Risk classification (Low / Medium / High); Rollback plan; Named requester and named approver; Planned start and end times”
- `change-management-policy.md` § Change Categories: “Standard | Normal | Emergency”

**Evidence:**
- `change-request.md` @ `Title line` — Identifier 'CHG-2026-0847' present, matching CHG-YYYY-NNNN format.
- `change-request.md` @ `Header block (Category/Risk/Systems/Repositories/Planned window)` — Category: Normal; Risk: Medium; Systems affected: payments-primary (RDS), payments-api; Repositories touched: northpeak/infra-terraform PR #2411; Planned window: 2026-06-24 20:00 UTC → 22:00 UTC.
- `change-request.md` @ `Scope section` — Enumerates Postgres 15.7→16.3 upgrade, pg library bump 8.11→8.13, no schema changes.
- `change-request.md` @ `Rollback plan section` — Three-step rollback: PITR snapshot restore, redeploy pinned pg@8.11, verify via /healthz and canary. RTO 25 min, validated in staging drill 2026-06-19.
- `change-request.md` @ `Requester section` — Named requester: Marcus Bell (Platform Engineer).
- `change-request.md` @ `Approver section` — Named approver: Priya Nadkarni (Change Approver, CAB).

**Exceptions considered:**
- Documentation-only exception rejected — this is a Postgres major version upgrade on a production cluster, not documentation.

## ⚠️ Production changes are approved by an authorised change approver prior to deployment
**Verdict**: `FURTHER_EVIDENCE_REQUIRED`  · confidence `0.70`

The change request records approval by Priya Nadkarni (a different named human from requester Marcus Bell) at 2026-06-23 15:42 UTC, before the 2026-06-24 20:00 UTC deployment window, and cites CAB-2026-W25. However, this is a Normal change requiring 2 approvers (Change Coordinator + Change Approver from CAB); only one approver (the CAB Change Approver) is named — no Change Coordinator approval is evidenced. Additionally, the signed CAB minutes (`cab-minutes-w25.pdf`) and IdP role membership confirming Priya holds the Change Approver role are not included in this bundle. Providing the CAB minutes showing a second approver / Change Coordinator sign-off, and an IdP export confirming Priya's Change Approver role, would resolve to SUCCESS.

**Policy references:**
- `change-management-policy.md` § Change Categories: “Normal | Non-routine change with a defined risk assessment | 2 (Change Coordinator + Change Approver from CAB) | Yes”
- `change-management-policy.md` § Approval Rules: “The approver must be a different named human from the requester (four-eyes principle). Approvers must hold the Change Approver role in the identity provider. Approval must occur before the deployment window opens.”

**Evidence:**
- `change-request.md` @ `Category / Requester / Approver / Approval record sections` — Category = Normal; Requester = Marcus Bell; Approver = Priya Nadkarni (Change Approver, CAB); Approval timestamp 2026-06-23 15:42 UTC; CAB reference CAB-2026-W25; signed CAB minutes noted as not included in bundle.
- `change-request.md` @ `Planned window` — Deployment window 2026-06-24 20:00 UTC → 22:00 UTC — approval timestamp precedes window opening by ~28 hours.
- `deployment-log.txt` @ `line at 2026-06-24 20:00:15 UTC` — Runner verified 'approval OK — CHG-2026-0847 approved by priya.nadkarni at 2026-06-23T15:42:00Z (CAB-2026-W25)'; only a single approver identity referenced.

**Exceptions considered:**
- Documentation-only / dev-staging exception — rejected: this change modifies production payments-primary RDS and payments-api.
- Emergency retrospective approval — not applicable: change is categorised Normal and approval is pre-deployment.

## ✅ Pre-deployment testing is completed and evidence retained before release
**Verdict**: `SUCCESS`  · confidence `0.90`

Change is Normal category. A test plan and test results are attached via pre-deployment-test-results.xlsx, referenced in the change request. Test execution timestamps (2026-06-23 14:12–14:14) predate the deployment window start (2026-06-24 20:00 UTC). Functional smoke tests of the affected payments API surface (healthz, ledger insert/read, monotonic constraint, currency conversion) are present and all PASS, so the failed-test-blocks-deployment criterion is not triggered. Emergency criteria are N/A.

**Policy references:**
- `change-management-policy.md` § Testing Requirements: “Standard and Normal changes: pre-deployment testing evidence (test plan + test results) must be attached to the change request.”
- `change-management-policy.md` § Testing Requirements: “Testing must include, at minimum, functional smoke tests of the affected surfaces.”
- `change-management-policy.md` § Testing Requirements: “Failed tests block deployment for Standard/Normal changes; must be documented as accepted risk for Emergency changes.”

**Evidence:**
- `change-request.md` @ `Header — Category` — Change is classified as Normal, Risk Medium — invokes Standard/Normal testing criteria.
- `change-request.md` @ `Testing evidence section` — References pre-deployment-test-results.xlsx with 42 test cases including 12 functional smoke, 24 regression, 6 rollback validation — all pass on staging.
- `pre-deployment-test-results.xlsx` @ `Test Cases!A1:F13` — 12 test rows with Test ID, Category=Functional, Description, Result=PASS, Executed By, Executed At. Sample rows TC-001..TC-005 cover payments API /healthz, ledger insert/read, transaction id monotonic constraint, and currency-conversion — functional smoke of affected surfaces.
- `pre-deployment-test-results.xlsx` @ `Test Cases!F2:F6 (Executed At)` — Test execution timestamps 2026-06-23 14:12–14:14 UTC, which predate the deployment window start of 2026-06-24 20:00 UTC.
- `deployment-log.txt` @ `window start line` — Deployment window began 2026-06-24 20:00:02 UTC — confirms tests (2026-06-23) predate deployment.

**Exceptions considered:**
- Emergency post-deployment testing clause: not applicable — change is Normal, not Emergency.
- Documentation-only exception: not applicable — change involves Postgres major version upgrade and library bump.
