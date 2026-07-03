"""Tests for the IPE (Information Produced by the Entity) validator.

IPE checks reconcile the source evidence against its own declared numbers
before we ever ask the LLM to judge anything. Bead markets this as
"IPE completeness testing" — none of the other public forks have it.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from openpyxl import Workbook

from audit_agent.evidence.reconciler import reconcile_user_access_review
from audit_agent.evidence.xlsx_parser import load_xlsx


def _write(path: Path, sheets: dict[str, list[list]]) -> Path:
    wb = Workbook()
    default = wb.active
    wb.remove(default)
    for name, rows in sheets.items():
        ws = wb.create_sheet(title=name)
        for row in rows:
            ws.append(row)
    wb.save(path)
    return path


def _uar_and_hris_with_cover(tmp_path, declared_total, declared_service, declared_retained, declared_revoked, extra_export_row=False):
    """Build a UAR + HRIS fixture pair where the Cover sheet declares specific
    totals. The rest of the workbook is the same shape as Bead's real UAR."""
    uar = tmp_path / "uar.xlsx"

    export_rows = [
        ["Username", "Full Name", "Email", "Role", "Account Status"],
        [],
        ["alice.smith", "Alice Smith", "alice@corp.com", "Analyst", "Active"],
        ["bob.jones",   "Bob Jones",   "bob@corp.com",   "Analyst", "Active"],
        ["svc-integration", "Service Account", "svc-integration@corp.com", "Integration", "Active"],
    ]
    if extra_export_row:
        export_rows.append(
            ["ghost.user", "Ghost User", "ghost@corp.com", "Analyst", "Active"]
        )

    _write(uar, {
        "Cover": [
            ["User Access Review"],
            [],
            ["System", "NetSuite (Production)"],
            ["Accounts In Scope", declared_total],
            ["Service accounts (out of scope)", declared_service],
            ["Accounts Retained", declared_retained],
            ["Accounts Flagged for Revocation", declared_revoked],
        ],
        "System Access Export": export_rows,
        "Access Review": [
            ["Email", "Name", "Role", "Account Status", "Reviewer Decision", "Reviewed By", "Review Date"],
            [],
            ["alice@corp.com", "Alice Smith", "Analyst", "Active", "Retain", "Priya", datetime(2026, 6, 30)],
            ["bob@corp.com", "Bob Jones", "Analyst", "Active", "Retain", "Priya", datetime(2026, 6, 30)],
            ["svc-integration@corp.com", "Service Account", "Integration", "Active", "Retain", "Priya", datetime(2026, 6, 30)],
        ],
    })
    hris = tmp_path / "hris.xlsx"
    _write(hris, {
        "Employees": [
            ["Employee ID", "Work Email", "Employment Status", "Job Title"],
            [],
            ["EMP-1", "alice@corp.com", "Active", "Analyst"],
            ["EMP-2", "bob@corp.com", "Active", "Analyst"],
        ],
    })
    return load_xlsx(uar), load_xlsx(hris)


def test_ipe_pass_when_all_declared_numbers_reconcile(tmp_path):
    """Cover: 2 in-scope + 1 service = 3 export rows. Retained: 3, Revoked: 0.
    Actual reperformance also finds 3 export rows, 1 orphan (svc), 3 retain."""
    uar, hris = _uar_and_hris_with_cover(
        tmp_path, declared_total=2, declared_service=1,
        declared_retained=3, declared_revoked=0,
    )
    d = reconcile_user_access_review(uar, hris).to_summary_dict()
    assert d["ipe_failures_count"] == 0
    checks = {c["check"]: c["status"] for c in d["ipe_checks"]}
    assert checks["Total export row count matches Cover sheet declaration"] == "pass"
    assert checks["Service-account carve-out matches reperformance orphans"] == "pass"
    assert checks["Reviewer decision counts match Cover sheet totals"] == "pass"


def test_ipe_fail_when_export_row_count_mismatches_cover(tmp_path):
    """Cover claims 2 in-scope + 1 service = 3 export rows, but the actual
    export has 4 rows. That's an integrity finding — the reviewer may have
    worked from a different snapshot."""
    uar, hris = _uar_and_hris_with_cover(
        tmp_path, declared_total=2, declared_service=1,
        declared_retained=3, declared_revoked=0,
        extra_export_row=True,  # actual export has 4 rows, not 3
    )
    d = reconcile_user_access_review(uar, hris).to_summary_dict()
    assert d["ipe_failures_count"] >= 1
    failing = [c for c in d["ipe_checks"] if c["status"] == "fail"]
    assert any("Total export row count" in c["check"] for c in failing)


def test_ipe_fail_when_service_account_carve_out_mismatches_orphans(tmp_path):
    """Cover claims 5 service accounts but reperformance finds only 1 orphan."""
    uar, hris = _uar_and_hris_with_cover(
        tmp_path, declared_total=2, declared_service=5,
        declared_retained=3, declared_revoked=0,
    )
    d = reconcile_user_access_review(uar, hris).to_summary_dict()
    failing = [c for c in d["ipe_checks"] if c["status"] == "fail"]
    assert any("Service-account carve-out" in c["check"] for c in failing)


def test_ipe_fail_when_reviewer_decision_counts_mismatch_cover(tmp_path):
    """Cover says 99 retained and 0 revoked, but Access Review sheet only has
    3 retain decisions."""
    uar, hris = _uar_and_hris_with_cover(
        tmp_path, declared_total=2, declared_service=1,
        declared_retained=99, declared_revoked=0,  # Cover wildly wrong
    )
    d = reconcile_user_access_review(uar, hris).to_summary_dict()
    failing = [c for c in d["ipe_checks"] if c["status"] == "fail"]
    assert any("Reviewer decision counts" in c["check"] for c in failing)


def test_ipe_gracefully_handles_no_declared_numbers(tmp_path):
    """When the Cover sheet doesn't declare row counts, IPE checks should
    return status `not_declared`, not fail hard."""
    uar_path = tmp_path / "uar.xlsx"
    _write(uar_path, {
        "Cover": [["User Access Review"], [], ["System", "NetSuite"]],
        "System Access Export": [
            ["Username", "Full Name", "Email", "Role", "Account Status"],
            [],
            ["alice.smith", "Alice", "alice@corp.com", "Analyst", "Active"],
        ],
        "Access Review": [
            ["Email", "Name", "Role", "Account Status", "Reviewer Decision", "Reviewed By", "Review Date"],
            [],
            ["alice@corp.com", "Alice", "Analyst", "Active", "Retain", "Priya", datetime(2026, 6, 30)],
        ],
    })
    hris_path = tmp_path / "hris.xlsx"
    _write(hris_path, {
        "Employees": [
            ["Employee ID", "Work Email", "Employment Status", "Job Title"],
            [],
            ["EMP-1", "alice@corp.com", "Active", "Analyst"],
        ],
    })
    d = reconcile_user_access_review(load_xlsx(uar_path), load_xlsx(hris_path)).to_summary_dict()
    total_check = next(
        c for c in d["ipe_checks"]
        if c["check"] == "Total export row count matches Cover sheet declaration"
    )
    assert total_check["status"] == "not_declared"
