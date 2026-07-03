"""Test fixtures — build synthetic UAR + HRIS workbooks in memory.

Kept intentionally minimal (~5-10 rows per fixture) so the tests read like a
control test setup, not a data dump. Each fixture stresses a different real-
world variation we might see when Bead throws unseen data at the pipeline.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Sequence

import pytest
from openpyxl import Workbook

from audit_agent.evidence.xlsx_parser import load_xlsx


def _write_wb(path: Path, sheets: dict[str, list[list]]) -> Path:
    """Write a workbook with the given {sheet_name: [rows]} structure."""
    wb = Workbook()
    default = wb.active
    wb.remove(default)
    for name, rows in sheets.items():
        ws = wb.create_sheet(title=name)
        for row in rows:
            ws.append(row)
    wb.save(path)
    return path


# --- Baseline fixture (matches Bead's provided UAR shape) --------------------

@pytest.fixture
def uar_baseline(tmp_path):
    """A minimal UAR workbook that mirrors the shape of Bead's provided sample.

    Two employees, one terminated, one on-leave, plus one service account.
    """
    uar = tmp_path / "uar.xlsx"
    _write_wb(uar, {
        "Cover": [
            ["User Access Review"],
            [],
            ["System", "NetSuite (Production)"],
            ["Review Period", "Q2 2026"],
            ["Reviewer", "Priya Nadkarni, Director, Finance Systems"],
        ],
        "System Access Export": [
            ["Username", "Full Name", "Email", "Role", "Account Status"],
            [],
            ["alice.smith", "Alice Smith", "alice@corp.com", "Analyst", "Active"],
            ["bob.jones",   "Bob Jones",   "bob@corp.com",   "Manager", "Active"],
            ["svc-integration", "Service Account", "svc-integration@corp.com", "Integration", "Active"],
        ],
        "Access Review": [
            ["Email", "Name", "Role", "Account Status", "Reviewer Decision", "Reviewed By", "Review Date"],
            [],
            ["alice@corp.com", "Alice Smith", "Analyst", "Active", "Retain", "Priya Nadkarni", datetime(2026, 6, 30)],
            ["bob@corp.com",   "Bob Jones",   "Manager", "Active", "Retain", "Priya Nadkarni", datetime(2026, 6, 30)],
            ["svc-integration@corp.com", "Service Account", "Integration", "Active", "Retain", "Priya Nadkarni", datetime(2026, 6, 30)],
        ],
    })
    hris = tmp_path / "hris.xlsx"
    _write_wb(hris, {
        "Employees": [
            ["Employee ID", "First Name", "Last Name", "Work Email", "Employment Status"],
            [],
            ["EMP-001", "Alice", "Smith", "alice@corp.com", "Active"],
            ["EMP-002", "Bob",   "Jones", "bob@corp.com",   "Terminated"],
        ],
    })
    return load_xlsx(uar), load_xlsx(hris)


# --- Perturbation: alternate status vocabulary ------------------------------

@pytest.fixture
def uar_alt_status_vocab(tmp_path):
    """HRIS uses 'Terminated - Retired' instead of the canonical 'Terminated'.

    This is the exact stress case the staff review flagged: strict `== "terminated"`
    matches would miss it, tokenised matches should catch it.
    """
    uar = tmp_path / "uar.xlsx"
    _write_wb(uar, {
        "System Access Export": [
            ["Username", "Full Name", "Email", "Role", "Account Status"],
            [],
            ["ravi.kumar", "Ravi Kumar", "ravi@corp.com", "Warehouse", "Active"],
        ],
        "Access Review": [
            ["Email", "Name", "Role", "Account Status", "Reviewer Decision", "Reviewed By", "Review Date"],
            [],
            ["ravi@corp.com", "Ravi Kumar", "Warehouse", "Active", "Retain", "Priya", datetime(2026, 6, 30)],
        ],
    })
    hris = tmp_path / "hris.xlsx"
    _write_wb(hris, {
        "Employees": [
            ["Employee ID", "Work Email", "Employment Status", "Termination Date"],
            [],
            ["EMP-333", "ravi@corp.com", "Terminated - Retired", datetime(2026, 4, 12)],
        ],
    })
    return load_xlsx(uar), load_xlsx(hris)


def _hris_rows(rows: Sequence[Sequence]) -> list[list]:
    """Standard HRIS sheet header used across fixtures — 3+ columns to satisfy
    the reconciler's header-row heuristic."""
    return [
        ["Employee ID", "Work Email", "Employment Status", "Job Title"],
        [],
        *rows,
    ]


# --- Perturbation: renamed reviewer sheet ------------------------------------

@pytest.fixture
def uar_renamed_reviewer_sheet(tmp_path):
    """Reviewer sheet is called 'Q3 Reviewer Decisions' not 'Access Review'.

    The reconciler detects sheet role from headers, not name — so it should still find it.
    """
    uar = tmp_path / "uar.xlsx"
    _write_wb(uar, {
        "System Access Export": [
            ["Username", "Full Name", "Email", "Role", "Account Status"],
            [],
            ["cara.lee", "Cara Lee", "cara@corp.com", "Analyst", "Active"],
        ],
        "Q3 Reviewer Decisions": [
            ["Email", "Name", "Role", "Account Status", "Reviewer Decision", "Reviewed By", "Review Date"],
            [],
            ["cara@corp.com", "Cara Lee", "Analyst", "Active", "Revoke", "Priya", datetime(2026, 9, 30)],
        ],
    })
    hris = tmp_path / "hris.xlsx"
    _write_wb(hris, {
        "Employees": _hris_rows([
            ["EMP-101", "cara@corp.com", "Terminated", "Analyst"],
        ]),
    })
    return load_xlsx(uar), load_xlsx(hris)


# --- Perturbation: orphan-only export (all users lack HRIS records) ----------

@pytest.fixture
def uar_all_orphans(tmp_path):
    """Every user is missing from HRIS — should surface as `orphans_no_hris_record`."""
    uar = tmp_path / "uar.xlsx"
    _write_wb(uar, {
        "System Access Export": [
            ["Username", "Full Name", "Email", "Role", "Account Status"],
            [],
            ["svc-1", "Service 1", "svc1@corp.com", "Integration", "Active"],
            ["svc-2", "Service 2", "svc2@corp.com", "Integration", "Active"],
        ],
        "Access Review": [
            ["Email", "Name", "Role", "Account Status", "Reviewer Decision", "Reviewed By", "Review Date"],
            [],
            ["svc1@corp.com", "Service 1", "Integration", "Active", "Retain", "Priya", datetime(2026, 6, 30)],
            ["svc2@corp.com", "Service 2", "Integration", "Active", "Retain", "Priya", datetime(2026, 6, 30)],
        ],
    })
    hris = tmp_path / "hris.xlsx"
    _write_wb(hris, {
        "Employees": _hris_rows([
            ["EMP-999", "someone.else@corp.com", "Active", "Analyst"],
        ]),
    })
    return load_xlsx(uar), load_xlsx(hris)


# --- Perturbation: on-leave still active (policy-dependent, not a hard fail) --

@pytest.fixture
def uar_on_leave(tmp_path):
    uar = tmp_path / "uar.xlsx"
    _write_wb(uar, {
        "System Access Export": [
            ["Username", "Full Name", "Email", "Role", "Account Status"],
            [],
            ["fatima.p", "Fatima P", "fatima@corp.com", "Analyst", "Active"],
        ],
        "Access Review": [
            ["Email", "Name", "Role", "Account Status", "Reviewer Decision", "Reviewed By", "Review Date"],
            [],
            ["fatima@corp.com", "Fatima P", "Analyst", "Active", "Retain", "Priya", datetime(2026, 6, 30)],
        ],
    })
    hris = tmp_path / "hris.xlsx"
    _write_wb(hris, {
        "Employees": _hris_rows([
            ["EMP-207", "fatima@corp.com", "On Leave", "Analyst"],
        ]),
    })
    return load_xlsx(uar), load_xlsx(hris)
