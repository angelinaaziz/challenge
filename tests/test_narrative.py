"""Tests for the deterministic audit narrative builder.

`_build_audit_narrative` turns raw AttributeAssessment lists into the
executive_summary / key_findings / recommended_actions that appear at the top
of every workpaper. It's pure Python and pure derivation — no LLM. That means
we can and should test it: the story the reviewer reads is provably consistent
with the verdicts every time.
"""

from __future__ import annotations

from audit_agent.pipeline import _build_audit_narrative
from audit_agent.schemas import (
    AttributeAssessment,
    ControlConclusion,
    EvidenceCoverage,
    EvidenceRef,
    Verdict,
)


def _attr(text: str, verdict: Verdict, rationale: str = "Because of x.") -> AttributeAssessment:
    return AttributeAssessment(
        control="Test",
        sample_id="s1",
        attribute_id=text.lower().replace(" ", "-"),
        attribute_text=text,
        verdict=verdict,
        confidence=0.9,
        rationale=rationale,
        evidence_refs=[
            EvidenceRef(file="f.xlsx", locator="A1", observation="Seen"),
        ],
    )


def _cov(all_files=None, cited=None, uncited=None) -> EvidenceCoverage:
    return EvidenceCoverage(
        all_files=all_files or ["a.xlsx"],
        cited_files=cited or ["a.xlsx"],
        uncited_files=uncited or [],
    )


def test_pass_narrative_no_open_actions():
    """When every attribute succeeds, actions should be 'nothing to do'."""
    attrs = [_attr("Attr A", Verdict.SUCCESS), _attr("Attr B", Verdict.SUCCESS)]
    summary, findings, actions = _build_audit_narrative(
        ControlConclusion.CONTROL_PASS, attrs, _cov(), None
    )
    assert "passed" in summary.lower()
    assert all(f.severity == "pass" for f in findings if f.severity != "warn")
    assert len(actions) == 1
    assert "no open actions" in actions[0].lower()


def test_fail_narrative_surfaces_failed_attribute_first():
    fail_attr = _attr("Attr A", Verdict.FAIL, rationale="Reviewer missed X.")
    attrs = [fail_attr, _attr("Attr B", Verdict.SUCCESS)]
    summary, findings, actions = _build_audit_narrative(
        ControlConclusion.CONTROL_FAIL, attrs, _cov(), None
    )
    assert "failed" in summary.lower()
    assert "1 of 2" in summary
    # First finding is the fail attribute
    assert findings[0].severity == "fail"
    assert findings[0].text == "Attr A"
    # Action lists remediation for the failed attribute
    assert any("Attr A" in a for a in actions)


def test_inconclusive_narrative_reads_as_needs_more_evidence():
    attrs = [
        _attr("Attr A", Verdict.FURTHER_EVIDENCE_REQUIRED),
        _attr("Attr B", Verdict.SUCCESS),
    ]
    summary, findings, actions = _build_audit_narrative(
        ControlConclusion.CONTROL_INCONCLUSIVE, attrs, _cov(), None
    )
    assert "cannot be signed off" in summary.lower()
    assert any(f.severity == "warn" and "insufficient evidence" in f.text.lower() for f in findings)
    assert any("Attr A" in a for a in actions)


def test_reconciliation_findings_are_surfaced_in_narrative():
    """When the reperformance module handed us a `reviewer_missed` finding,
    the narrative should surface it as a fail and add a remediation action."""
    attrs = [_attr("Remediation", Verdict.FAIL)]
    recon = {
        "reviewer_missed_findings_count": 1,
        "reviewer_missed_findings": [
            {
                "name": "Kevin Lewis",
                "email": "kevin.lewis@corp.com",
                "detail": "HRIS terminated, system Active",
                "role_or_title": "Analyst",
                "system_status": "active",
                "hris_status": "terminated",
                "reviewer_decision": "retain",
                "locators": "Access Review!E187",
            }
        ],
        "orphans_no_hris_record": [],
        "terminated_but_active_in_system_count": 1,
    }
    summary, findings, actions = _build_audit_narrative(
        ControlConclusion.CONTROL_FAIL, attrs, _cov(), recon
    )
    assert "reviewer missed" in summary.lower()
    assert any("Kevin Lewis" in f.text for f in findings)
    assert any("Kevin Lewis" in a and "revoke" in a.lower() for a in actions)


def test_uncited_evidence_becomes_a_warn_finding():
    attrs = [_attr("Attr A", Verdict.SUCCESS)]
    cov = _cov(
        all_files=["a.xlsx", "b.xlsx"],
        cited=["a.xlsx"],
        uncited=["b.xlsx"],
    )
    _, findings, _ = _build_audit_narrative(
        ControlConclusion.CONTROL_PASS, attrs, cov, None
    )
    assert any(
        f.severity == "warn" and "b.xlsx" in f.text
        for f in findings
    )
