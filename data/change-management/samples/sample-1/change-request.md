# CHG-2026-0847 — Upgrade Postgres 15 → 16 on payments-primary cluster

**Category**: Normal
**Risk**: Medium
**System(s) affected**: `payments-primary` (RDS), `payments-api` (dependency)
**Repositories touched**: `northpeak/infra-terraform` (PR #2411)
**Planned window**: 2026-06-24 20:00 UTC → 2026-06-24 22:00 UTC

## Scope
- Upgrade payments-primary Postgres from 15.7 to 16.3
- Update PG connection library in payments-api from `pg@8.11` → `pg@8.13`
- No schema changes; wire-protocol compatible

## Risk assessment
Medium — production payments cluster, but well-established Postgres major upgrade. Full test suite passes on staging (see attached results). Blast radius contained by pg-bouncer connection pool; rollback validated.

## Rollback plan
1. Restore point-in-time snapshot taken 5 minutes before upgrade (RDS automated snapshot ID snap-payments-2026-06-24-1955).
2. Redeploy payments-api pinned to `pg@8.11`.
3. Verify with `/healthz` and a canary transaction.
Rollback RTO: 25 minutes; validated in staging drill on 2026-06-19.

## Requester
Marcus Bell (Platform Engineer) — marcus.bell@northpeakfinancial.com

## Approver
Priya Nadkarni (Change Approver, CAB) — priya.nadkarni@northpeakfinancial.com

## Approval record
- CAB meeting reference: CAB-2026-W25
- Approval decision: **Approved**
- Approval timestamp: **2026-06-23 15:42 UTC** (before deployment window)
- Approval evidence: signed CAB minutes attached separately (`cab-minutes-w25.pdf` — not included in this evidence bundle)

## Testing evidence
See `pre-deployment-test-results.xlsx` in this evidence bundle. All 42 planned test cases pass on staging. Includes:
- Functional smoke: 12 cases
- Regression: 24 cases
- Rollback validation: 6 cases
