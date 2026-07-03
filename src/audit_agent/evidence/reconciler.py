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
from typing import Any, Literal, Optional

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
class IPECheck:
    """Information Produced by the Entity — did the source data reconcile
    against its own declared numbers?

    An auditor doesn't trust reviewer decisions on top of source data whose
    integrity hasn't been verified. IPE checks are the deterministic first
    line of defence: if the Cover sheet says "332 accounts in scope" and
    the System Access Export has 334 rows total with 2 service accounts,
    do those numbers agree? If not, either the reviewer worked from a
    different export or the workpaper is stale.

    Bead literally markets "IPE completeness testing" as a product feature.
    """
    check: str
    status: Literal["pass", "fail", "not_declared"]
    detail: str


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
    ipe_checks: list[IPECheck] = field(default_factory=list)

    def to_summary_dict(self) -> dict[str, Any]:
        def ipe_list() -> list[dict[str, str]]:
            return [
                {"check": c.check, "status": c.status, "detail": c.detail}
                for c in self.ipe_checks
            ]

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
            "ipe_checks": ipe_list(),
            "ipe_failures_count": sum(1 for c in self.ipe_checks if c.status == "fail"),
        }


def _lower(x: Any) -> str:
    return str(x).strip().lower() if x is not None else ""


# Small controlled vocab for employment-status normalisation. Real-world HRIS
# systems vary on how they spell "terminated" (Workday says "Terminated",
# NetSuite HR says "Ended", some SAP setups say "Separated" or "Retired").
# Rather than exact-matching "terminated" we tokenise the status value and
# check for any of these signals — much more robust to unseen data.
_TERMINATED_TOKENS = {
    "terminated", "termed", "terminate",
    "separated", "separation", "ended",
    "retired", "resigned", "left",
    "inactive-terminated",
    "involuntary", "voluntary",  # standalone in some HRIS
}
_ON_LEAVE_TOKENS = {
    "on leave", "leave", "loa",
    "sabbatical", "furlough", "furloughed",
    "medical leave", "parental leave", "maternity", "paternity",
}


def _status_matches(status: str, tokens: set[str]) -> bool:
    """Return True if the normalised status contains any of the vocab tokens.

    Splits on whitespace, hyphens, slashes and en-dashes so `Terminated - Retired`,
    `Terminated/Involuntary`, and `on-leave` all match. Also checks the full
    normalised string for multi-word tokens like "on leave".
    """
    if not status:
        return False
    s = status.strip().lower()
    if s in tokens:
        return True
    # Multi-word token check (e.g. "on leave").
    for t in tokens:
        if " " in t and t in s:
            return True
    # Single-word token check via delimited split.
    parts = set()
    current = ""
    for ch in s:
        if ch.isalpha():
            current += ch
        else:
            if current:
                parts.add(current)
                current = ""
    if current:
        parts.add(current)
    return bool(parts & tokens)


def _int(x: Any) -> Optional[int]:
    """Best-effort int coerce for Cover-sheet declared counts."""
    if isinstance(x, int):
        return x
    if isinstance(x, str) and x.strip().isdigit():
        return int(x.strip())
    return None


def _run_ipe_checks(
    access_book: XlsxWorkbook,
    export_sheet: XlsxSheet,
    review_sheet: XlsxSheet,
    orphan_count: int,
    system_export_rows: int,
) -> list[IPECheck]:
    """Deterministic IPE (Information Produced by the Entity) checks.

    The auditor trusts reviewer decisions only if the underlying source data
    reconciles against its own declared numbers. If the Cover sheet says X
    accounts and the export has Y, that's an IPE integrity finding — and it
    doesn't require an LLM to notice.
    """
    checks: list[IPECheck] = []
    # Cover-sheet KV pairs are keyed by declared label (case-preserved).
    cover: dict[str, Any] = {}
    for sh in access_book.sheets.values():
        for label, (value, _coord) in sh.kv.items():
            cover[label] = value

    # -- Total accounts in export vs actual system export rows -------------
    declared_total = _int(cover.get("Accounts In Scope")) or _int(
        cover.get("Total accounts in export")
    )
    declared_service = _int(cover.get("Service accounts (out of scope)")) or 0
    if declared_total is not None:
        expected = declared_total + declared_service
        if expected == system_export_rows:
            checks.append(
                IPECheck(
                    check="Total export row count matches Cover sheet declaration",
                    status="pass",
                    detail=(
                        f"Cover declares {declared_total} in-scope + {declared_service} "
                        f"service accounts = {expected}. Actual system access export "
                        f"has {system_export_rows} rows."
                    ),
                )
            )
        else:
            checks.append(
                IPECheck(
                    check="Total export row count matches Cover sheet declaration",
                    status="fail",
                    detail=(
                        f"Cover declares {declared_total} in-scope + {declared_service} "
                        f"service accounts = {expected} expected, but actual export has "
                        f"{system_export_rows} rows. Reviewer may have worked from a "
                        f"different snapshot — IPE integrity finding."
                    ),
                )
            )
    else:
        checks.append(
            IPECheck(
                check="Total export row count matches Cover sheet declaration",
                status="not_declared",
                detail="Cover sheet does not declare an in-scope row count to reconcile against.",
            )
        )

    # -- Service-account carve-out reconciles to orphans (no HRIS record) ---
    if declared_service:
        if declared_service == orphan_count:
            checks.append(
                IPECheck(
                    check="Service-account carve-out matches reperformance orphans",
                    status="pass",
                    detail=(
                        f"Cover declares {declared_service} service accounts out of "
                        f"scope; reperformance found exactly {orphan_count} orphan(s) "
                        f"(users in access export with no HRIS record)."
                    ),
                )
            )
        else:
            checks.append(
                IPECheck(
                    check="Service-account carve-out matches reperformance orphans",
                    status="fail",
                    detail=(
                        f"Cover declares {declared_service} service accounts, "
                        f"but reperformance found {orphan_count} orphan(s). "
                        f"Either a service account is missing from the carve-out, "
                        f"or a human employee is missing from HRIS."
                    ),
                )
            )

    # -- Reviewer decision counts vs Cover declared retained/revoked --------
    declared_retained = _int(cover.get("Accounts Retained"))
    declared_revoked = _int(cover.get("Accounts Flagged for Revocation"))
    if declared_retained is not None or declared_revoked is not None:
        # Count from actual reviewer sheet decisions.
        rev_col = _find_col(review_sheet.headers, ["reviewer decision", "decision"])
        actual_retained = actual_revoked = 0
        for row in review_sheet.rows:
            dec = _lower(row.values.get(rev_col)) if rev_col else ""
            if "retain" in dec:
                actual_retained += 1
            elif "revoke" in dec or "remove" in dec:
                actual_revoked += 1
        ok = True
        mismatches = []
        if declared_retained is not None and declared_retained != actual_retained:
            ok = False
            mismatches.append(
                f"Cover Retained={declared_retained} vs actual {actual_retained}"
            )
        if declared_revoked is not None and declared_revoked != actual_revoked:
            ok = False
            mismatches.append(
                f"Cover Revoked={declared_revoked} vs actual {actual_revoked}"
            )
        if ok:
            checks.append(
                IPECheck(
                    check="Reviewer decision counts match Cover sheet totals",
                    status="pass",
                    detail=(
                        f"Actual counts on Access Review sheet ({actual_retained} retain / "
                        f"{actual_revoked} revoke) reconcile to Cover totals."
                    ),
                )
            )
        else:
            checks.append(
                IPECheck(
                    check="Reviewer decision counts match Cover sheet totals",
                    status="fail",
                    detail=" · ".join(mismatches)
                    + ". Suggests the reviewer sheet was edited after the Cover was written.",
                )
            )

    return checks


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
        _ = row.coords.get(exp_cols.status, "?") if exp_cols.status else "?"
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

        # Tokenised match so alt vocab (Terminated - Retired, Separated,
        # Ended, etc.) is still surfaced. Same for on-leave.
        if _status_matches(hris_status, _TERMINATED_TOKENS) and sys_status == "active":
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
        elif _status_matches(hris_status, _ON_LEAVE_TOKENS) and sys_status == "active":
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

    ipe_checks = _run_ipe_checks(
        access_book=access_book,
        export_sheet=export_sheet,
        review_sheet=review_sheet,
        orphan_count=len(orphans),
        system_export_rows=len(export_sheet.rows),
    )

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
        ipe_checks=ipe_checks,
    )
