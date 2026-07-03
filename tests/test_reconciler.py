"""Unit tests for the deterministic UAR reconciler.

These are the tests the reconciler needs — not a golden-set behavioural check.
They stress the header/status detection heuristics with synthetic fixtures so
we can regression-test against unseen sample variations without spending an
API call.
"""

from __future__ import annotations

from audit_agent.evidence.reconciler import (
    find_access_export_sheet,
    find_access_review_sheet,
    find_hris_sheet,
    reconcile_user_access_review,
)


# --- Shape detection --------------------------------------------------------

def test_detects_uar_shape_from_headers_not_sheet_names(uar_renamed_reviewer_sheet):
    """Reviewer sheet named 'Q3 Reviewer Decisions' should still be detected.

    The reconciler classifies sheets by header content, not filename or sheet
    title. If Bead's next test data renames the reviewer sheet, the pipeline
    should still recognise it.
    """
    uar, hris = uar_renamed_reviewer_sheet
    assert find_access_review_sheet(uar) is not None
    assert find_access_review_sheet(uar).name == "Q3 Reviewer Decisions"
    assert find_access_export_sheet(uar) is not None
    assert find_hris_sheet(hris) is not None


def test_baseline_uar_produces_expected_shape(uar_baseline):
    uar, hris = uar_baseline
    recon = reconcile_user_access_review(uar, hris).to_summary_dict()
    assert recon["system_export_rows"] == 3
    assert recon["hris_rows"] == 2
    assert recon["reviewer_sheet_rows"] == 3


# --- The Kevin Lewis scenario -----------------------------------------------

def test_reconciler_flags_terminated_but_active_when_reviewer_retained(uar_baseline):
    """The headline finding: someone terminated in HRIS marked Retain on the review.

    Bob is terminated in HRIS, but the reviewer marked him Retain. That's
    exactly the Kevin Lewis pattern the deterministic reconciler exists to catch.
    """
    uar, hris = uar_baseline
    recon = reconcile_user_access_review(uar, hris).to_summary_dict()
    assert recon["reviewer_missed_findings_count"] == 1
    missed = recon["reviewer_missed_findings"]
    assert len(missed) == 1
    assert missed[0]["email"] == "bob@corp.com"
    assert missed[0]["reviewer_decision"] == "retain"


def test_reconciler_surfaces_orphans_as_findings(uar_baseline):
    """Users in the system export without an HRIS record (e.g. service accounts)."""
    uar, hris = uar_baseline
    recon = reconcile_user_access_review(uar, hris).to_summary_dict()
    assert recon["orphans_no_hris_record_count"] == 1
    assert recon["orphans_no_hris_record"][0]["email"] == "svc-integration@corp.com"


def test_reconciler_treats_on_leave_as_soft_finding_not_hard_fail(uar_on_leave):
    """On-leave employees with active access are policy-dependent, not a hard finding.

    The reconciler surfaces them separately so a reviewer can judge — some orgs
    keep on-leave access, some suspend it. We shouldn't turn it into a fail without
    a policy signal.
    """
    uar, hris = uar_on_leave
    recon = reconcile_user_access_review(uar, hris).to_summary_dict()
    assert recon["on_leave_but_active_in_system_count"] == 1
    assert recon["terminated_but_active_in_system_count"] == 0
    assert recon["reviewer_missed_findings_count"] == 0


# --- Robustness to unseen data ----------------------------------------------

def test_all_orphans_case_no_matches(uar_all_orphans):
    """When zero users match HRIS, we should surface every one as an orphan."""
    uar, hris = uar_all_orphans
    recon = reconcile_user_access_review(uar, hris).to_summary_dict()
    assert recon["matched_users"] == 0
    assert recon["orphans_no_hris_record_count"] == 2
    assert recon["terminated_but_active_in_system_count"] == 0


def test_alt_status_vocabs_are_tokenised():
    """Direct-level test of the vocab tokeniser on the value strings we've
    seen in real HRIS exports."""
    from audit_agent.evidence.reconciler import (
        _ON_LEAVE_TOKENS,
        _TERMINATED_TOKENS,
        _status_matches,
    )
    # Positive termination signals
    for s in [
        "Terminated",
        "TERMINATED",
        "terminated",
        "Terminated - Retired",
        "Terminated/Involuntary",
        "Separated",
        "Ended",
        "Retired",
        "Resigned",
    ]:
        assert _status_matches(s, _TERMINATED_TOKENS), s
    # Negative — real "Active" and "On Leave" should NOT be termed.
    for s in ["Active", "on leave", "On Leave", "Sabbatical"]:
        assert not _status_matches(s, _TERMINATED_TOKENS), s

    # Positive on-leave signals
    for s in ["On Leave", "Leave", "Sabbatical", "Furloughed", "Maternity Leave"]:
        assert _status_matches(s, _ON_LEAVE_TOKENS), s


def test_alt_status_vocab_still_detected(uar_alt_status_vocab):
    """HRIS says 'Terminated - Retired' not 'Terminated'.

    Robustness against unseen status vocab: the reconciler tokenises the
    normalised HRIS status against a controlled vocabulary of termination
    signals, so multi-word variants ("Terminated - Retired", "Separated",
    "Ended") still surface as findings.
    """
    uar, hris = uar_alt_status_vocab
    recon = reconcile_user_access_review(uar, hris).to_summary_dict()
    assert recon["terminated_but_active_in_system_count"] == 1
    assert recon["terminated_but_active_in_system"][0]["email"] == "ravi@corp.com"
