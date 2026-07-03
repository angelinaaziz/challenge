# CHG-2026-0912 — Deploy new Q2 reporting service to production

**Category**: Normal
**Risk**: Medium
**System(s) affected**: `reports-api` (new service), `reports-worker` (new service), `reports-db` (new RDS instance)
**Repositories touched**: `northpeak/reports-service` (PR #47), `northpeak/infra-terraform` (PR #2438)
**Planned window**: 2026-06-28 15:00 UTC → 2026-06-28 17:00 UTC

## Scope
- Deploy new reporting service to serve Q2 quarterly reports.
- Provision new RDS instance for isolated reporting workload.
- Configure IAM roles and API gateway routes.

## Risk assessment
Medium — new production service, but no traffic from existing systems in phase 1. Read-only workload against a snapshot of prod ledger.

## Rollback plan
1. Delete API gateway routes (2 minutes).
2. Scale ECS services to zero (1 minute).
3. Leave RDS provisioned for forensic review.
Rollback RTO: 5 minutes.

## Requester
Marcus Bell (Platform Engineer) — marcus.bell@northpeakfinancial.com

## Approver
Marcus Bell (Platform Engineer) — marcus.bell@northpeakfinancial.com

## Approval record
- CAB meeting reference: (none — deployed under standing team autonomy waiver)
- Approval decision: Self-approved
- Approval timestamp: 2026-06-28 14:47 UTC
- Note: skipped CAB review to hit end-of-quarter demo deadline. Retroactive CAB scheduled for 2026-07-02.

## Testing evidence
See `pre-deployment-test-results.xlsx`. 3 test cases failed on staging (2 functional, 1 performance). Deployment proceeded pending post-deployment fix.
