"""End-to-end audit pipeline: control_dir + provider → per-sample assessments."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from rich.console import Console
from rich.progress import track

from audit_agent.control import load_control
from audit_agent.evidence import (
    EvidenceBundle,
    classify_sample,
    extract_screenshot_facts,
    extract_xlsx_facts,
    reconcile_user_access_review,
)
from audit_agent.evidence.router import discover_samples
from audit_agent.judge import judge_attribute, verify_attribute
from audit_agent.llm import LLMProvider
from audit_agent.schemas import (
    AttributeAssessment,
    AuditFinding,
    Control,
    ControlConclusion,
    EvidenceCoverage,
    EvidenceItem,
    SampleAssessment,
    ScreenshotFacts,
    TextEvidence,
    Verdict,
    XlsxFacts,
    rollup_verdicts,
)
from audit_agent.trace import Tracer


CONSOLE = Console()


@dataclass
class RunConfig:
    control_dir: Path
    out_dir: Path
    provider: LLMProvider
    verify: bool = True
    consistency: int = 1  # >1 = self-consistency voting on the judge


def _load_evidence(
    bundle: EvidenceBundle,
    control: Control,
    provider: LLMProvider,
    tracer: Tracer,
) -> tuple[list[ScreenshotFacts], list[XlsxFacts], list[TextEvidence], Optional[dict]]:
    screenshots: list[ScreenshotFacts] = []
    xlsx_facts: list[XlsxFacts] = []
    text_evidence: list[TextEvidence] = []
    reconciliation: Optional[dict] = None

    for ef in bundle.screenshots:
        CONSOLE.log(f"  • extracting {Path(ef.path).name}")
        facts, meta = extract_screenshot_facts(
            Path(ef.path), control.name, control.description, provider
        )
        screenshots.append(facts)
        tracer.log(
            provider=provider.name,
            model=provider.model,
            purpose=f"screenshot:{Path(ef.path).name}",
            system="prompts/screenshot_extraction.md",
            user_text=str(control.name),
            meta=meta,
            output_summary=f"{facts.inferred_type} — {len(facts.key_facts)} facts",
        )

    # Markdown / text evidence — small files just get inlined for the judge.
    for ef in bundle.files:
        if ef.kind in ("markdown", "text"):
            p = Path(ef.path)
            content = p.read_text()
            # Cap huge files defensively.
            if len(content) > 40_000:
                content = content[:40_000] + f"\n\n[truncated {len(content)-40_000} more chars]"
            text_evidence.append(TextEvidence(file=p.name, content=content))
            CONSOLE.log(f"  • loaded text evidence {p.name}")

    if bundle.workbooks:
        # UAR-shape: attempt reconciliation between the two workbooks.
        loaded = [(ef, extract_xlsx_facts(Path(ef.path))) for ef in bundle.workbooks]
        for _ef, (_book, facts) in loaded:
            xlsx_facts.append(facts)

        # If we have two workbooks, try to identify which is the access review (UAR)
        # and which is the HRIS by looking for a "reviewer decision" sheet.
        access_book = None
        hris_book = None
        for _ef, (book, _facts) in loaded:
            from audit_agent.evidence.reconciler import (
                find_access_review_sheet,
                find_hris_sheet,
            )
            if find_access_review_sheet(book):
                access_book = book
            if find_hris_sheet(book):
                hris_book = book
        if access_book and hris_book:
            CONSOLE.log("  • running deterministic UAR reconciliation")
            recon = reconcile_user_access_review(access_book, hris_book)
            reconciliation = recon.to_summary_dict()

    return screenshots, xlsx_facts, text_evidence, reconciliation


def _process_sample(
    bundle: EvidenceBundle,
    control: Control,
    cfg: RunConfig,
    tracer: Tracer,
) -> SampleAssessment:
    CONSOLE.rule(f"[bold cyan]sample: {bundle.sample_id}")
    screenshots, xlsx_facts, text_evidence, reconciliation = _load_evidence(
        bundle, control, cfg.provider, tracer
    )

    attributes: list[AttributeAssessment] = []
    disagreements: list[float] = []
    for attr in track(control.attributes, description=f"  judging {bundle.sample_id}"):
        assessment, meta = judge_attribute(
            control=control,
            attribute=attr,
            sample_id=bundle.sample_id,
            screenshots=screenshots,
            xlsx=xlsx_facts,
            text_evidence=text_evidence,
            reconciliation=reconciliation,
            provider=cfg.provider,
            consistency=cfg.consistency,
        )
        if "disagreement_rate" in meta:
            disagreements.append(meta["disagreement_rate"])
        tracer.log(
            provider=cfg.provider.name,
            model=cfg.provider.model,
            purpose=f"judge:{attr.id}:{bundle.sample_id}",
            system="prompts/attribute_judge.md",
            user_text=attr.text,
            meta=meta,
            output_summary=f"{assessment.verdict.value} ({assessment.confidence:.2f})",
        )

        if cfg.verify and assessment.verdict == Verdict.FURTHER_EVIDENCE_REQUIRED:
            CONSOLE.log(f"  • verifying {attr.id} (was FURTHER_EVIDENCE_REQUIRED)")
            assessment, vmeta = verify_attribute(
                first_pass=assessment,
                control=control,
                attribute=attr,
                sample_id=bundle.sample_id,
                screenshots=screenshots,
                xlsx=xlsx_facts,
                text_evidence=text_evidence,
                reconciliation=reconciliation,
                provider=cfg.provider,
            )
            tracer.log(
                provider=cfg.provider.name,
                model=cfg.provider.model,
                purpose=f"verify:{attr.id}:{bundle.sample_id}",
                system="prompts/verifier.md",
                user_text=attr.text,
                meta=vmeta,
                output_summary=f"{assessment.verdict.value} ({assessment.confidence:.2f})",
            )
        attributes.append(assessment)

    conclusion = rollup_verdicts([a.verdict for a in attributes])
    coverage = _compute_evidence_coverage(bundle, attributes)
    inventory = _build_evidence_inventory(
        bundle, attributes, screenshots, xlsx_facts, text_evidence
    )
    disagreement = (sum(disagreements) / len(disagreements)) if disagreements else None
    execsum, findings, actions = _build_audit_narrative(
        conclusion, attributes, coverage, reconciliation
    )

    return SampleAssessment(
        control=control.name,
        sample_id=bundle.sample_id,
        generated_at=datetime.now(timezone.utc),
        model=f"{cfg.provider.name}:{cfg.provider.model}",
        attributes=attributes,
        control_conclusion=conclusion,
        executive_summary=execsum,
        key_findings=findings,
        recommended_actions=actions,
        evidence_coverage=coverage,
        evidence_inventory=inventory,
        consistency_disagreement_rate=disagreement,
        reperformance_notes=(
            None
            if reconciliation is None
            else _summary_from_reconciliation(reconciliation)
        ),
    )


def _build_audit_narrative(
    conclusion: ControlConclusion,
    attributes: list[AttributeAssessment],
    coverage: EvidenceCoverage,
    reconciliation: Optional[dict],
) -> tuple[str, list[AuditFinding], list[str]]:
    """Turn structured verdicts into an auditor-friendly narrative.

    Answers the four questions Angelina flagged as must-haves:
    - Why did it succeed or fail? → executive_summary
    - What did we find? → key_findings
    - What can I do now? → recommended_actions
    - What was actually tested? → coverage (elsewhere) + inventory (elsewhere)

    Everything here is DETERMINISTIC — derived from the schema, not another LLM
    call. That means it's cheap, reproducible, and the auditor can trust the
    story matches the verdicts exactly.
    """
    fails = [a for a in attributes if a.verdict == Verdict.FAIL]
    hedged = [a for a in attributes if a.verdict == Verdict.FURTHER_EVIDENCE_REQUIRED]
    passes = [a for a in attributes if a.verdict == Verdict.SUCCESS]

    # -- Executive summary --------------------------------------------------
    if conclusion == ControlConclusion.CONTROL_PASS:
        summary = (
            f"The control passed. All {len(passes)} attribute(s) tested cleanly with "
            f"citation-backed evidence. No follow-up findings raised."
        )
    elif conclusion == ControlConclusion.CONTROL_FAIL:
        summary = (
            f"The control failed. {len(fails)} of {len(attributes)} attribute(s) were "
            f"positively contradicted by the evidence. "
            f"{f'{len(hedged)} attribute(s) also require additional evidence to close. ' if hedged else ''}"
            f"The auditee has open remediation to complete before this control can be signed off."
        )
    else:  # INCONCLUSIVE
        summary = (
            f"The control cannot be signed off from this evidence bundle. "
            f"{len(hedged)} attribute(s) need further evidence, "
            f"{len(passes)} passed, and none positively failed. "
            f"Request the missing evidence and re-audit."
        )

    if reconciliation:
        missed = reconciliation.get("reviewer_missed_findings_count", 0) or 0
        terminated = reconciliation.get("terminated_but_active_in_system_count", 0) or 0
        if missed:
            summary += (
                f" Deterministic reperformance surfaced {missed} finding(s) the reviewer "
                f"missed — see the reperformance summary."
            )
        elif terminated:
            summary += (
                f" Deterministic reperformance flagged {terminated} account(s) requiring "
                f"consideration — reviewer decisions checked."
            )

    # -- Key findings --------------------------------------------------------
    findings: list[AuditFinding] = []
    for a in fails:
        findings.append(AuditFinding(severity="fail", text=f"{a.attribute_text}"))
    for a in hedged:
        findings.append(
            AuditFinding(severity="warn", text=f"Insufficient evidence: {a.attribute_text}")
        )
    for a in passes:
        findings.append(AuditFinding(severity="pass", text=a.attribute_text))

    if reconciliation:
        missed = reconciliation.get("reviewer_missed_findings", [])
        for m in missed[:3]:  # cap for signal density
            findings.append(
                AuditFinding(
                    severity="fail",
                    text=f"Reviewer missed: {m['name']} ({m['email']}) — {m['detail']}",
                )
            )
        orphans = reconciliation.get("orphans_no_hris_record", [])
        for o in orphans[:3]:
            findings.append(
                AuditFinding(
                    severity="warn",
                    text=f"No HRIS record: {o['name']} ({o['email']}) — {o['detail']}",
                )
            )

    # -- Uncited-evidence signal ---------------------------------------------
    if coverage and coverage.uncited_files:
        findings.append(
            AuditFinding(
                severity="warn",
                text=(
                    f"Evidence file(s) were provided but not cited by any verdict: "
                    f"{', '.join(coverage.uncited_files)}. Confirm relevance or extraction gap."
                ),
            )
        )

    # -- Recommended actions -------------------------------------------------
    actions: list[str] = []
    for a in fails:
        actions.append(
            f"Remediate the root cause of the FAIL on “{a.attribute_text}”, "
            f"then re-submit for testing. Rationale: {a.rationale.split('.')[0]}."
        )
    for a in hedged:
        actions.append(
            f"Provide additional evidence to close “{a.attribute_text}”. "
            f"Specifically: {a.rationale.split('.')[0]}."
        )
    if reconciliation:
        missed = reconciliation.get("reviewer_missed_findings", [])
        for m in missed[:3]:
            actions.append(
                f"Revoke {m['name']}'s access ({m['email']}) and update the review "
                f"process to catch terminated employees still marked Retain."
            )
    if not actions:
        actions.append(
            "No open actions from this run — retain evidence + workpaper for the audit file."
        )

    return summary, findings, actions


def _build_evidence_inventory(
    bundle: EvidenceBundle,
    attributes: list[AttributeAssessment],
    screenshots: list[ScreenshotFacts],
    xlsx_facts: list[XlsxFacts],
    text_evidence: list[TextEvidence],
) -> list[EvidenceItem]:
    """One entry per file the pipeline ingested — with what got extracted
    and which attribute verdicts cite it."""
    ss_by_name = {s.file: s for s in screenshots}
    xl_by_name = {x.file: x for x in xlsx_facts}
    tx_by_name = {t.file: t for t in text_evidence}
    # Map filename → list of attribute IDs that cite it (tolerant match).
    citation_map: dict[str, list[str]] = {}
    for a in attributes:
        for ref in a.evidence_refs:
            citation_map.setdefault(ref.file.strip(), []).append(a.attribute_id)

    def _cited_by(name: str) -> list[str]:
        # Case-insensitive/whitespace-tolerant lookup.
        for k, v in citation_map.items():
            if k.strip().lower() == name.strip().lower():
                return v
        return []

    items: list[EvidenceItem] = []
    for ef in bundle.files:
        name = Path(ef.path).name
        summary: str
        if ef.kind == "screenshot":
            sf = ss_by_name.get(name)
            if sf is not None:
                summary = f"{sf.inferred_type} · {len(sf.key_facts)} facts extracted"
                if sf.people_mentioned:
                    summary += f" · {len(sf.people_mentioned)} people"
                if sf.ambiguities:
                    summary += f" · {len(sf.ambiguities)} ambiguity flag(s)"
            else:
                summary = "Screenshot detected but extraction did not produce facts."
        elif ef.kind == "xlsx":
            xf = xl_by_name.get(name)
            if xf is not None:
                total_rows = sum(s.row_count for s in xf.sheets)
                summary = (
                    f"Workbook · {len(xf.sheets)} sheet(s), {total_rows} rows total. "
                    f"Sheets: {', '.join(s.name for s in xf.sheets[:5])}"
                    + ("…" if len(xf.sheets) > 5 else "")
                )
            else:
                summary = "Workbook detected but no sheet summaries produced."
        elif ef.kind in ("markdown", "text"):
            tx = tx_by_name.get(name)
            if tx is not None:
                word_count = len(tx.content.split())
                summary = f"Text · {word_count:,} words, inlined verbatim into the judge prompt"
            else:
                summary = "Text detected but was not inlined (empty file?)"
        elif ef.kind == "pdf":
            summary = "PDF detected · extractor not yet wired (see limitations)"
        else:
            summary = f"File type `{ef.kind}` — not a supported extraction path"

        items.append(
            EvidenceItem(
                file=name,
                kind=ef.kind,
                bytes_size=ef.bytes_size,
                extraction_summary=summary,
                cited_by_attributes=_cited_by(name),
            )
        )
    return items


def _compute_evidence_coverage(
    bundle: EvidenceBundle, attributes: list[AttributeAssessment]
) -> EvidenceCoverage:
    """Files given to the pipeline vs files cited by at least one verdict."""
    all_files = sorted({Path(f.path).name for f in bundle.files})
    cited: set[str] = set()
    for a in attributes:
        for ref in a.evidence_refs:
            cited.add(ref.file)
    # A judge sometimes cites a file with a slightly different name (e.g. omits
    # trailing spaces). Best-effort tolerant match: case-insensitive, trimmed.
    all_norm = {f.strip().lower(): f for f in all_files}
    cited_normalized: set[str] = set()
    for c in cited:
        key = c.strip().lower()
        if key in all_norm:
            cited_normalized.add(all_norm[key])
        else:
            # Cited file we can't map to a provided file — worth flagging in future.
            pass
    uncited = [f for f in all_files if f not in cited_normalized]
    return EvidenceCoverage(
        all_files=all_files,
        cited_files=sorted(cited_normalized),
        uncited_files=uncited,
    )


def _summary_from_reconciliation(recon: dict) -> str:
    lines = [
        f"System export: {recon['system_export_rows']} rows",
        f"HRIS roster: {recon['hris_rows']} rows",
        f"Reviewer sheet: {recon['reviewer_sheet_rows']} rows",
        f"Matched to HRIS: {recon['matched_users']}",
        f"Orphans (no HRIS record): {recon['orphans_no_hris_record_count']}",
        f"Terminated but active in system: {recon['terminated_but_active_in_system_count']}",
        f"On leave but active in system: {recon['on_leave_but_active_in_system_count']}",
        f"Reviewer missed (terminated + retained): {recon['reviewer_missed_findings_count']}",
    ]
    return " | ".join(lines)


def run_audit(cfg: RunConfig) -> list[SampleAssessment]:
    tracer = Tracer(cfg.out_dir / "trace.jsonl")

    CONSOLE.rule(f"[bold]Loading control from {cfg.control_dir}")
    control = load_control(cfg.control_dir, cfg.provider)
    (cfg.out_dir / "control.json").write_text(control.model_dump_json(indent=2, exclude={"policies"}))
    CONSOLE.log(
        f"Parsed control [bold]{control.name}[/] with {len(control.attributes)} attributes."
    )

    bundles = discover_samples(cfg.control_dir)
    CONSOLE.log(f"Found {len(bundles)} sample(s): {[b.sample_id for b in bundles]}")

    assessments: list[SampleAssessment] = []
    for bundle in bundles:
        sa = _process_sample(bundle, control, cfg, tracer)
        _write_sample_output(sa, cfg.out_dir)
        assessments.append(sa)

    return assessments


def _write_sample_output(sa: SampleAssessment, out_dir: Path) -> None:
    d = out_dir / sa.sample_id
    d.mkdir(parents=True, exist_ok=True)
    (d / "assessment.json").write_text(sa.model_dump_json(indent=2))
    (d / "assessment.md").write_text(_render_markdown(sa))


def _render_markdown(sa: SampleAssessment) -> str:
    emoji = {
        "CONTROL_PASS": "✅",
        "CONTROL_FAIL": "❌",
        "CONTROL_INCONCLUSIVE": "⚠️",
    }[sa.control_conclusion.value]
    lines = [
        f"# {sa.control} — {sa.sample_id}",
        f"_generated: {sa.generated_at.isoformat()} · model: {sa.model}_",
        "",
        f"## {emoji} Control conclusion: `{sa.control_conclusion.value}`",
    ]
    if sa.reperformance_notes:
        lines += ["", "### Reperformance summary", sa.reperformance_notes]
    if sa.evidence_coverage:
        cov = sa.evidence_coverage
        lines += [
            "",
            f"### Evidence coverage — {int(cov.coverage_rate * 100)}%",
            f"- All files provided: {len(cov.all_files)}",
            f"- Cited in at least one verdict: {len(cov.cited_files)}",
        ]
        if cov.uncited_files:
            lines.append(f"- **Uncited:** {', '.join(f'`{f}`' for f in cov.uncited_files)}")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## Attribute-level verdicts")
    lines.append("")
    for a in sa.attributes:
        emoji = {"SUCCESS": "✅", "FAIL": "❌", "FURTHER_EVIDENCE_REQUIRED": "⚠️"}[
            a.verdict.value
        ]
        lines += [
            f"## {emoji} {a.attribute_text}",
            f"**Verdict**: `{a.verdict.value}`  · confidence `{a.confidence:.2f}`",
            "",
            a.rationale,
            "",
        ]
        if a.policy_references:
            lines.append("**Policy references:**")
            for p in a.policy_references:
                lines.append(f"- `{p.source}` § {p.section}: “{p.quote}”")
            lines.append("")
        if a.evidence_refs:
            lines.append("**Evidence:**")
            for e in a.evidence_refs:
                lines.append(f"- `{e.file}` @ `{e.locator}` — {e.observation}")
            lines.append("")
        if a.exceptions_considered:
            lines.append("**Exceptions considered:**")
            for x in a.exceptions_considered:
                lines.append(f"- {x}")
            lines.append("")
    return "\n".join(lines)
