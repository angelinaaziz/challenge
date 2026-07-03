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
    Control,
    SampleAssessment,
    ScreenshotFacts,
    TextEvidence,
    Verdict,
    XlsxFacts,
)
from audit_agent.trace import Tracer


CONSOLE = Console()


@dataclass
class RunConfig:
    control_dir: Path
    out_dir: Path
    provider: LLMProvider
    verify: bool = True


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
        )
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

    return SampleAssessment(
        control=control.name,
        sample_id=bundle.sample_id,
        generated_at=datetime.now(timezone.utc),
        model=f"{cfg.provider.name}:{cfg.provider.model}",
        attributes=attributes,
        reperformance_notes=(
            None
            if reconciliation is None
            else _summary_from_reconciliation(reconciliation)
        ),
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
    lines = [
        f"# {sa.control} — {sa.sample_id}",
        f"_generated: {sa.generated_at.isoformat()} · model: {sa.model}_",
    ]
    if sa.reperformance_notes:
        lines += ["", "## Reperformance", sa.reperformance_notes]
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
