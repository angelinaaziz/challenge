# Change Management — sample-1
_generated: 2026-07-03T03:42:20.433666+00:00 · model: claude:claude-opus-4-7_

## ⚠️ Control conclusion: `CONTROL_INCONCLUSIVE`

### Evidence coverage — 100%
- All files provided: 3
- Cited in at least one verdict: 3

---

## Attribute-level verdicts

## ✅ Every production change has a corresponding change request that documents scope, risk classification, and rollback plan
**Verdict**: `SUCCESS`  · confidence `0.95`

Change request CHG-2026-0847 exists and satisfies every documentation criterion: identifier follows CHG-YYYY-NNNN format; scope lists systems (payments-primary RDS, payments-api) and repo (northpeak/infra-terraform PR #2411); risk classified Medium; rollback plan has three concrete steps with validated RTO; named requester (Marcus Bell) and named approver (Priya Nadkarni); planned window 2026-06-24 20:00–22:00 UTC; category Normal. Change targets production payments cluster, so no out-of-scope exception applies.

**Policy references:**
- `change-management-policy.md` § Required Documentation: “Every change (regardless of category) must include: A change request identifier (e.g. CHG-YYYY-NNNN); Scope: systems affected, code repositories, config surfaces; Risk classification (Low / Medium / High); Rollback plan; Named requester and named approver; Planned start and end times”
- `change-management-policy.md` § Exceptions: “The following are out of scope: Documentation-only changes (README, comments); Break-fix hotfixes classified as Incident Response; Changes to development or staging environments”

**Evidence:**
- `change-request.md` @ `Header line` — Title reads 'CHG-2026-0847 — Upgrade Postgres 15 → 16 on payments-primary cluster' — identifier matches CHG-YYYY-NNNN format.
- `change-request.md` @ `Category/Risk/Systems header block` — Category: Normal; Risk: Medium; Systems affected: payments-primary (RDS), payments-api; Repositories touched: northpeak/infra-terraform PR #2411; Planned window 2026-06-24 20:00–22:00 UTC.
- `change-request.md` @ `Scope section` — Documents Postgres 15.7→16.3 upgrade and pg library bump 8.11→8.13, no schema changes.
- `change-request.md` @ `Rollback plan section` — Three-step rollback with snapshot ID snap-payments-2026-06-24-1955, redeploy pinned pg@8.11, health verification; RTO 25 min validated in staging drill 2026-06-19.
- `change-request.md` @ `Requester and Approver sections` — Named requester Marcus Bell (Platform Engineer); named approver Priya Nadkarni (Change Approver, CAB).

**Exceptions considered:**
- Documentation-only exception: rejected — change alters production Postgres cluster and application code.
- Dev/staging exception: rejected — target is payments-primary production RDS.
- Incident Response hotfix: rejected — planned Normal change with CAB approval, not break-fix.

## ⚠️ Production changes are approved by an authorised change approver prior to deployment
**Verdict**: `FURTHER_EVIDENCE_REQUIRED`  · confidence `0.70`

The change request names Priya Nadkarni (Change Approver, CAB) as approver, separate from requester Marcus Bell, with an approval timestamp of 2026-06-23 15:42 UTC — before the 2026-06-24 20:00 UTC deployment window. The deployment log independently corroborates this approval. However, this is a Normal change requiring 2 approvers (Change Coordinator + Change Approver from CAB); only Priya (CAB Approver) is documented — no Change Coordinator approval is shown. Additionally, the signed CAB minutes (`cab-minutes-w25.pdf`) evidencing CAB review are explicitly not included in the bundle, and the IdP role assignment for Priya as Change Approver is not provided. Providing the CAB minutes, an IdP role listing confirming Priya's Change Approver role, and evidence of a second Change Coordinator approval would resolve this to SUCCESS.

**Policy references:**
- `change-management-policy.md` § Change Categories: “Normal | Non-routine change with a defined risk assessment | 2 (Change Coordinator + Change Approver from CAB) | Yes”
- `change-management-policy.md` § Approval Rules: “The approver must be a different named human from the requester (four-eyes principle). Approvers must hold the Change Approver role in the identity provider. Approval must occur before the deployment window opens.”

**Evidence:**
- `change-request.md` @ `Category / Approver / Approval record sections` — Category is 'Normal'; approver named as Priya Nadkarni (Change Approver, CAB); approval timestamp 2026-06-23 15:42 UTC noted as before deployment window; CAB reference CAB-2026-W25 cited; signed CAB minutes referenced as `cab-minutes-w25.pdf` but explicitly 'not included in this evidence bundle'. Only one approver is listed — no Change Coordinator approval documented.
- `change-request.md` @ `Requester section` — Requester is Marcus Bell (Platform Engineer), distinct human from approver Priya Nadkarni — four-eyes principle satisfied on the recorded approver.
- `deployment-log.txt` @ `Line at 2026-06-24 20:00:15 UTC` — Runner logs 'approval OK — CHG-2026-0847 approved by priya.nadkarni at 2026-06-23T15:42:00Z (CAB-2026-W25)', corroborating the approval timestamp precedes the 20:00:02 UTC deployment window start.

**Exceptions considered:**
- Documentation-only exception — rejected; this is a Postgres major-version upgrade on a production cluster, clearly in-scope.
- Emergency retrospective approval — not applicable; change is classified Normal and approval is pre-deployment.

## ✅ Pre-deployment testing is completed and evidence retained before release
**Verdict**: `SUCCESS`  · confidence `0.90`

Change is Normal category and has both a test plan and test results attached (pre-deployment-test-results.xlsx referenced in the change request, listing 42 planned test cases including 12 functional smoke tests). All sampled functional smoke tests executed on 2026-06-23, prior to the deployment window opening on 2026-06-24 20:00 UTC. All sampled results show PASS; no failed tests observed that would block deployment. Emergency-change criteria are not applicable.

**Policy references:**
- `change-management-policy.md` § Testing Requirements: “Standard and Normal changes: pre-deployment testing evidence (test plan + test results) must be attached to the change request.”
- `change-management-policy.md` § Testing Requirements: “Testing must include, at minimum, functional smoke tests of the affected surfaces.”
- `change-management-policy.md` § Testing Requirements: “Failed tests block deployment for Standard/Normal changes; must be documented as accepted risk for Emergency changes.”

**Evidence:**
- `change-request.md` @ `Testing evidence section` — References pre-deployment-test-results.xlsx with 42 planned test cases: 12 functional smoke, 24 regression, 6 rollback validation — all pass on staging.
- `change-request.md` @ `Header — Category / Planned window` — Change is Normal category; planned deployment window 2026-06-24 20:00–22:00 UTC.
- `pre-deployment-test-results.xlsx` @ `Test Cases!A1:F13` — Sheet contains 12 rows of test cases with columns Test ID, Category, Description, Result, Executed By, Executed At. Sampled rows TC-001 through TC-005 are Functional smoke tests covering payments API /healthz, ledger insert/read, transaction id constraint, and currency conversion — all Result=PASS, executed 2026-06-23 14:12–14:14 by test-bot.
- `deployment-log.txt` @ `window start line` — Deployment began 2026-06-24 20:00:02 UTC, which is after test execution on 2026-06-23 — testing dated prior to deployment.

**Exceptions considered:**
- Emergency-change post-deployment verification (within 24h) criterion — rejected as inapplicable because the change is categorised Normal.
- Failed-test / accepted-risk criterion — not triggered; all sampled test results are PASS.
