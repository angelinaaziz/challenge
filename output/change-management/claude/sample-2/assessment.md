# Change Management — sample-2
_generated: 2026-07-03T03:49:13.309498+00:00 · model: claude:claude-opus-4-7_

## ❌ Control conclusion: `CONTROL_FAIL`

### Evidence coverage — 100%
- All files provided: 3
- Cited in at least one verdict: 3

---

## Attribute-level verdicts

## ✅ Every production change has a corresponding change request that documents scope, risk classification, and rollback plan
**Verdict**: `SUCCESS`  · confidence `0.95`

The change request CHG-2026-0912 exists and follows the CHG-YYYY-NNNN format. It documents scope (systems affected: reports-api/worker/db; repositories: reports-service PR #47, infra-terraform PR #2438), risk classification (Medium), rollback plan (3 steps with 5-min RTO), a named requester and named approver (both Marcus Bell — note: independence is a separate attribute), planned window (2026-06-28 15:00–17:00 UTC), and category (Normal). The change is a new production service deployment, not an out-of-scope exception. All documentation-completeness criteria for this attribute are met.

**Policy references:**
- `change-management-policy.md` § Required Documentation: “Every change (regardless of category) must include: A change request identifier (e.g. CHG-YYYY-NNNN); Scope: systems affected, code repositories, config surfaces; Risk classification (Low / Medium / High); Rollback plan; Named requester and named approver; Planned start and end times”
- `change-management-policy.md` § Exceptions: “The following are out of scope: Documentation-only changes (README, comments); Break-fix hotfixes classified as Incident Response (see Incident Response Policy); Changes to development or staging environments”

**Evidence:**
- `change-request.md` @ `Title line` — Change request identifier CHG-2026-0912 in required CHG-YYYY-NNNN format, titled 'Deploy new Q2 reporting service to production'.
- `change-request.md` @ `Header block (Category/Risk/Systems/Repositories/Planned window)` — Category: Normal; Risk: Medium; Systems: reports-api, reports-worker, reports-db; Repositories: northpeak/reports-service PR #47, northpeak/infra-terraform PR #2438; Planned window: 2026-06-28 15:00–17:00 UTC.
- `change-request.md` @ `Scope section` — Scope enumerated: deploy reporting service, provision RDS, configure IAM/API gateway routes.
- `change-request.md` @ `Rollback plan section` — Rollback plan with 3 numbered steps and 5-minute RTO documented.
- `change-request.md` @ `Requester and Approver sections` — Requester: Marcus Bell; Approver: Marcus Bell (independence is out of scope for this attribute but noted).
- `deployment-log.txt` @ `Header (system line)` — Deployment targets production reports-api/worker/db — confirms this is a production change, not dev/staging or docs-only, so no exception applies.

**Exceptions considered:**
- Documentation-only exception: rejected — deployment provisions new production services and RDS instance.
- Dev/staging exception: rejected — deployment log shows production ECS/RDS resources.
- Incident Response break-fix: rejected — CR is categorised Normal for an end-of-quarter feature launch, not an IR hotfix.

## ❌ Production changes are approved by an authorised change approver prior to deployment
**Verdict**: `FAIL`  · confidence `0.98`

The change is classified Normal, which requires 2 approvers (Change Coordinator + CAB Change Approver) and evidenced CAB review. The change request records only a self-approval by Marcus Bell, who is also the requester — this violates the four-eyes principle. CAB review was explicitly skipped ("standing team autonomy waiver") and only scheduled retroactively; retrospective approval is only valid for Emergency changes per policy. Multiple criteria fail: same-person approver, single approver on a Normal change, and no CAB evidence.

**Policy references:**
- `change-management-policy.md` § Change Categories: “Normal | Non-routine change with a defined risk assessment | 2 (Change Coordinator + Change Approver from CAB) | Yes”
- `change-management-policy.md` § Approval Rules: “The approver must be a different named human from the requester (four-eyes principle).”
- `change-management-policy.md` § Approval Rules: “Retrospective approvals are only valid for Emergency changes and must be documented as such.”

**Evidence:**
- `change-request.md` @ `Category line` — Category: Normal, Risk: Medium — triggers 2-approver + CAB requirements.
- `change-request.md` @ `Requester and Approver sections` — Both requester and approver are listed as 'Marcus Bell (Platform Engineer) — marcus.bell@northpeakfinancial.com' — same human, violating four-eyes.
- `change-request.md` @ `Approval record section` — CAB meeting reference '(none — deployed under standing team autonomy waiver)'; Approval decision 'Self-approved'; note states CAB was skipped to hit demo deadline and retroactive CAB scheduled for 2026-07-02.
- `deployment-log.txt` @ `Line 2026-06-28 15:04:20 UTC approval verification` — Log confirms 'approved by marcus.bell at 2026-06-28T14:47:00Z (self-approved)' — deployment proceeded on a self-approval.

**Exceptions considered:**
- Retrospective/Emergency exception: rejected — the change is classified Normal, not Emergency, so the retrospective-CAB pathway does not apply.
- Documentation-only exception: rejected — this is a production service deployment with new infra.

## ❌ Pre-deployment testing is completed and evidence retained before release
**Verdict**: `FAIL`  · confidence `0.95`

This is a Normal change. A test plan and results workbook is attached and dated 2026-06-28 09:02–09:06 UTC, prior to the 15:04 UTC deployment — so those criteria are met. However, the Test Cases sheet shows two functional tests (TC-002) and one regression test (TC-004) with Result=FAIL, and the change request itself acknowledges "3 test cases failed on staging ... Deployment proceeded pending post-deployment fix." Policy states "Failed tests block deployment for Standard/Normal changes" — deployment proceeded anyway (deployment-log confirms DEPLOYED status), directly contradicting the criterion "if any tests failed, deployment did not proceed."

**Policy references:**
- `change-management-policy.md` § Testing Requirements: “Standard and Normal changes: pre-deployment testing evidence (test plan + test results) must be attached to the change request.”
- `change-management-policy.md` § Testing Requirements: “Failed tests block deployment for Standard/Normal changes; must be documented as accepted risk for Emergency changes.”

**Evidence:**
- `pre-deployment-test-results.xlsx` @ `Test Cases!D2:D6 (Result column)` — TC-002 (functional, Q2 aggregate) = FAIL and TC-004 (regression, CSV columns) = FAIL; executed 2026-06-28 09:03 and 09:05 UTC by test-bot.
- `change-request.md` @ `## Testing evidence section` — States '3 test cases failed on staging (2 functional, 1 performance). Deployment proceeded pending post-deployment fix.'
- `deployment-log.txt` @ `Final line 2026-06-28 15:31:02 UTC` — 'CHG-2026-0912 complete — status: DEPLOYED (with known post-deploy defects to be fixed 2026-06-29)' — confirms deployment proceeded despite failed pre-deployment tests.
- `pre-deployment-test-results.xlsx` @ `Test Cases!F2:F6 (Executed At)` — All test executions dated 2026-06-28 09:02–09:06 UTC, i.e. before deployment window start of 15:04 UTC — dating criterion met.

**Exceptions considered:**
- Emergency-change accepted-risk exception: rejected because the change request explicitly classifies this as Category=Normal, not Emergency, so the 'accepted risk' carve-out for failed tests does not apply.
- Documentation-only / dev-or-staging scope exception: rejected — this deploys a new production service (reports-api, reports-worker, reports-db).
