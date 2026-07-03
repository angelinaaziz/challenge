"""Deterministic reperformance of a User Access Review.

The auditor's job is not to trust the reviewer's conclusion — it's to reperform
the reconciliation. This module does the join between the system access export
and the HRIS source-of-truth deterministically, then flags exceptions the reviewer
should have caught. The output is fed to the LLM judge as ground-truth evidence.

We deliberately do NOT hardcode column names for NetSuite / Workday. Instead we
detect columns by heuristic (fuzzy match on header text) so this same code can
run against SAP, Salesforce, Snowflake, etc. exports.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any, Optional

from audit_agent.evidence.xlsx_parser import XlsxSheet, XlsxWorkbook


# --- Column detection --------------------------------------------------------

def _find_col(headers: list[str], candidates: list[str]) -> Optional[str]:
    lowered = {h.lower(): h for h in headers}
    for cand in candidates:
        for lh, h in lowered.items():
            if cand in lh:
                return h
    return None


@dataclass
class ColumnMap:
    email: Optional[str] = None
    username: Optional[str] = None
    name: Optional[str] = None
    role: Optional[str] = None
    status: Optional[str] = None
    department: Optional[str] = None
    job_title: Optional[str] = None
    termination_date: Optional[str] = None
    hire_date: Optional[str] = None
    reviewer_decision: Optional[str] = None
    reviewer: Optional[str] = None
    review_date: Optional[str] = None


def map_system_export(headers: list[str]) -> ColumnMap:
    """Best-effort mapping for a system access export (e.g. NetSuite)."""
    return ColumnMap(
        email=_find_col(headers, ["email"]),
        username=_find_col(headers, ["username", "user id", "login"]),
        name=_find_col(headers, ["full name", "name"]),
        role=_find_col(headers, ["role", "group", "permission"]),
        status=_find_col(headers, ["account status", "status"]),
    )


def map_hris(headers: list[str]) -> ColumnMap:
    return ColumnMap(
        email=_find_col(headers, ["work email", "email"]),
        name=_find_col(headers, ["full name"]) or None,
        department=_find_col(headers, ["department"]),
        job_title=_find_col(headers, ["job title", "title"]),
        status=_find_col(headers, ["employment status", "status"]),
        termination_date=_find_col(headers, ["termination date", "term date"]),
        hire_date=_find_col(headers, ["hire date", "start date"]),
    )


def map_reviewer_sheet(headers: list[str]) -> ColumnMap:
    return ColumnMap(
        email=_find_col(headers, ["email"]),
        name=_find_col(headers, ["name"]),
        role=_find_col(headers, ["role"]),
        status=_find_col(headers, ["account status", "status"]),
        reviewer_decision=_find_col(headers, ["reviewer decision", "decision"]),
        reviewer=_find_col(headers, ["reviewed by", "reviewer"]),
        review_date=_find_col(headers, ["review date", "date"]),
    )


# --- Sheet role detection ----------------------------------------------------

def _sheet_role(sheet: XlsxSheet) -> str:
    """Return one of: 'cover', 'access_export', 'access_review', 'summary', 'unknown'."""
    name = sheet.name.lower()
    if not sheet.is_tabular:
        if "cover" in name or "summary" in name or "note" in name:
            return "summary_or_cover"
        return "unknown"
    hset = {h.lower() for h in sheet.headers}
    if any("reviewer decision" in h for h in hset) or any("decision" == h for h in hset):
        return "access_review"
    if "account status" in hset and ("username" in hset or "email" in hset):
        return "access_export"
    if any("employment status" in h for h in hset):
        return "hris_roster"
    return "unknown"


def find_hris_sheet(book: XlsxWorkbook) -> XlsxSheet | None:
    for sh in book.sheets.values():
        if _sheet_role(sh) == "hris_roster":
            return sh
    return None


def find_access_export_sheet(book: XlsxWorkbook) -> XlsxSheet | None:
    for sh in book.sheets.values():
        if _sheet_role(sh) == "access_export":
            return sh
    return None


def find_access_review_sheet(book: XlsxWorkbook) -> XlsxSheet | None:
    for sh in book.sheets.values():
        if _sheet_role(sh) == "access_review":
            return sh
    return None


# --- The reconciliation ------------------------------------------------------

@dataclass
class UserFinding:
    email: str
    name: str
    role_or_title: str
    system_status: str
    hris_status: str
    reviewer_decision: str
    finding_type: str
    detail: str
    source_locators: list[str] = field(default_factory=list)


@dataclass
class UARReconciliation:
    system_export_rows: int
    hris_rows: int
    reviewer_sheet_rows: int
    matched_users: int
    orphans_no_hris_record: list[UserFinding]
    terminated_but_active_in_system: list[UserFinding]
    on_leave_but_active_in_system: list[UserFinding]
    reviewer_missed_findings: list[UserFinding]
    inactive_but_retained: list[UserFinding]
    reviewer_names: set[str]
    unique_review_dates: list[str]
    cover_sheet: dict[str, str]

    def to_summary_dict(self) -> dict[str, Any]:
        def uf_list(items: list[UserFinding]) -> list[dict[str, str]]:
            return [
                {
                    "email": f.email,
                    "name": f.name,
                    "role_or_title": f.role_or_title,
                    "system_status": f.system_status,
                    "hris_status": f.hris_status,
                    "reviewer_decision": f.reviewer_decision,
                    "detail": f.detail,
                    "locators": ", ".join(f.source_locators),
                }
                for f in items
            ]

        return {
            "system_export_rows": self.system_export_rows,
            "hris_rows": self.hris_rows,
            "reviewer_sheet_rows": self.reviewer_sheet_rows,
            "matched_users": self.matched_users,
            "orphans_no_hris_record_count": len(self.orphans_no_hris_record),
            "orphans_no_hris_record": uf_list(self.orphans_no_hris_record),
            "terminated_but_active_in_system_count": len(self.terminated_but_active_in_system),
            "terminated_but_active_in_system": uf_list(self.terminated_but_active_in_system),
            "on_leave_but_active_in_system_count": len(self.on_leave_but_active_in_system),
            "on_leave_but_active_in_system": uf_list(self.on_leave_but_active_in_system),
            "reviewer_missed_findings_count": len(self.reviewer_missed_findings),
            "reviewer_missed_findings": uf_list(self.reviewer_missed_findings),
            "inactive_but_retained_count": len(self.inactive_but_retained),
            "inactive_but_retained": uf_list(self.inactive_but_retained)[:20],
            "reviewer_names": sorted(self.reviewer_names),
            "unique_review_dates": self.unique_review_dates,
            "cover_sheet": self.cover_sheet,
        }


def _lower(x: Any) -> str:
    return str(x).strip().lower() if x is not None else ""


def reconcile_user_access_review(
    access_book: XlsxWorkbook,
    hris_book: XlsxWorkbook,
) -> UARReconciliation:
    """Perform the reperformance.

    - access_book: the UAR workbook (has Cover, Access Export, Access Review, Summary sheets)
    - hris_book: the HRIS export (independent source of truth)
    """
    export_sheet = find_access_export_sheet(access_book)
    review_sheet = find_access_review_sheet(access_book)
    hris_sheet = find_hris_sheet(hris_book)
    if not export_sheet or not review_sheet or not hris_sheet:
        raise ValueError(
            "Could not identify required sheets. "
            f"export={bool(export_sheet)}, review={bool(review_sheet)}, hris={bool(hris_sheet)}"
        )

    exp_cols = map_system_export(export_sheet.headers)
    rev_cols = map_reviewer_sheet(review_sheet.headers)
    hris_cols = map_hris(hris_sheet.headers)

    # Build HRIS by email.
    hris_by_email: dict[str, dict[str, Any]] = {}
    for row in hris_sheet.rows:
        email = _lower(row.values.get(hris_cols.email)) if hris_cols.email else ""
        if not email:
            continue
        hris_by_email[email] = {
            "row": row,
            "name": row.values.get(hris_cols.name) if hris_cols.name else "",
            "job_title": row.values.get(hris_cols.job_title) if hris_cols.job_title else "",
            "department": row.values.get(hris_cols.department) if hris_cols.department else "",
            "status": _lower(row.values.get(hris_cols.status)) if hris_cols.status else "",
            "termination_date": row.values.get(hris_cols.termination_date)
            if hris_cols.termination_date
            else None,
            "email_coord": row.coords.get(hris_cols.email, "?"),
            "status_coord": row.coords.get(hris_cols.status, "?"),
        }

    # Build reviewer decisions by email.
    review_by_email: dict[str, dict[str, Any]] = {}
    reviewer_names: set[str] = set()
    review_dates: set[str] = set()
    for row in review_sheet.rows:
        email = _lower(row.values.get(rev_cols.email)) if rev_cols.email else ""
        if not email:
            continue
        rev_dec = row.values.get(rev_cols.reviewer_decision) if rev_cols.reviewer_decision else ""
        rev_by = row.values.get(rev_cols.reviewer) if rev_cols.reviewer else ""
        rev_date = row.values.get(rev_cols.review_date) if rev_cols.review_date else ""
        if rev_by:
            reviewer_names.add(str(rev_by).strip())
        if isinstance(rev_date, (datetime, date)):
            review_dates.add(rev_date.isoformat())
        elif rev_date:
            review_dates.add(str(rev_date))
        review_by_email[email] = {
            "row": row,
            "decision": _lower(rev_dec),
            "reviewer": rev_by,
            "date": rev_date,
            "coord_decision": row.coords.get(rev_cols.reviewer_decision, "?")
            if rev_cols.reviewer_decision
            else "?",
        }

    # Iterate system access export.
    orphans: list[UserFinding] = []
    terminated_active: list[UserFinding] = []
    on_leave_active: list[UserFinding] = []
    reviewer_missed: list[UserFinding] = []
    inactive_retained: list[UserFinding] = []
    matched = 0

    for row in export_sheet.rows:
        email = _lower(row.values.get(exp_cols.email)) if exp_cols.email else ""
        name = row.values.get(exp_cols.name) if exp_cols.name else ""
        role = row.values.get(exp_cols.role) if exp_cols.role else ""
        sys_status = _lower(row.values.get(exp_cols.status)) if exp_cols.status else ""
        if not email:
            continue

        rev_entry = review_by_email.get(email)
        rev_decision = rev_entry["decision"] if rev_entry else "no_reviewer_entry"
        exp_email_coord = row.coords.get(exp_cols.email, "?") if exp_cols.email else "?"
        exp_status_coord = row.coords.get(exp_cols.status, "?") if exp_cols.status else "?"
        rev_coord = rev_entry["coord_decision"] if rev_entry else "?"

        hris = hris_by_email.get(email)
        if not hris:
            orphans.append(
                UserFinding(
                    email=email,
                    name=str(name),
                    role_or_title=str(role),
                    system_status=str(sys_status),
                    hris_status="NOT_IN_HRIS",
                    reviewer_decision=str(rev_decision),
                    finding_type="no_hris_record",
                    detail=(
                        "User exists in system access export but has no matching record in "
                        "the HRIS roster — service account or leaver missed by HR export."
                    ),
                    source_locators=[
                        f"{export_sheet.name}!{exp_email_coord}",
                        f"{review_sheet.name}!{rev_coord}" if rev_entry else "",
                    ],
                )
            )
            continue

        matched += 1
        hris_status = hris["status"]

        if hris_status == "terminated" and sys_status == "active":
            f = UserFinding(
                email=email,
                name=str(name),
                role_or_title=str(role),
                system_status=str(sys_status),
                hris_status=str(hris_status),
                reviewer_decision=str(rev_decision),
                finding_type="terminated_still_active",
                detail=(
                    "HRIS shows this employee is terminated, but their system account is still "
                    "Active. Access should have been revoked."
                ),
                source_locators=[
                    f"{export_sheet.name}!{exp_email_coord}",
                    f"HRIS Employees!{hris['email_coord']}",
                    f"{review_sheet.name}!{rev_coord}" if rev_entry else "",
                ],
            )
            terminated_active.append(f)
            if rev_decision == "retain":
                reviewer_missed.append(f)
        elif hris_status == "on leave" and sys_status == "active":
            on_leave_active.append(
                UserFinding(
                    email=email,
                    name=str(name),
                    role_or_title=str(role),
                    system_status=str(sys_status),
                    hris_status=str(hris_status),
                    reviewer_decision=str(rev_decision),
                    finding_type="on_leave_still_active",
                    detail=(
                        "HRIS shows employee on leave; access remains active. Not necessarily "
                        "a finding (policy-dependent) but should be reviewer-considered."
                    ),
                    source_locators=[
                        f"{export_sheet.name}!{exp_email_coord}",
                        f"HRIS Employees!{hris['email_coord']}",
                    ],
                )
            )
        if sys_status == "inactive" and rev_decision == "retain":
            inactive_retained.append(
                UserFinding(
                    email=email,
                    name=str(name),
                    role_or_title=str(role),
                    system_status=str(sys_status),
                    hris_status=str(hris_status),
                    reviewer_decision=str(rev_decision),
                    finding_type="inactive_retained_ok",
                    detail=(
                        "Account already inactive in system; reviewer retained decision "
                        "(no further action needed)."
                    ),
                    source_locators=[
                        f"{export_sheet.name}!{exp_email_coord}",
                        f"{review_sheet.name}!{rev_coord}",
                    ],
                )
            )

    # Cover sheet extraction (for reviewer + period metadata)
    cover_sheet: dict[str, str] = {}
    for sh in access_book.sheets.values():
        for label, (value, _coord) in sh.kv.items():
            cover_sheet[label] = str(value)

    return UARReconciliation(
        system_export_rows=len(export_sheet.rows),
        hris_rows=len(hris_sheet.rows),
        reviewer_sheet_rows=len(review_sheet.rows),
        matched_users=matched,
        orphans_no_hris_record=orphans,
        terminated_but_active_in_system=terminated_active,
        on_leave_but_active_in_system=on_leave_active,
        reviewer_missed_findings=reviewer_missed,
        inactive_but_retained=inactive_retained,
        reviewer_names=reviewer_names,
        unique_review_dates=sorted(review_dates),
        cover_sheet=cover_sheet,
    )
