"""Typer CLI.

Commands:
    bead-agent audit <control-dir>     Run the pipeline, produce assessments
    bead-agent eval  <control-dir>     Multi-model scoreboard vs golden
    bead-agent info  <control-dir>     Parse the control + list samples (no LLM audit)
    bead-agent show  <assessment.json> Pretty-print a past assessment file
    bead-agent trace <run-dir>         Show the trace log for a past run
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

import typer
from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from audit_agent.llm import make_provider
from audit_agent.pipeline import RunConfig, run_audit

load_dotenv()

HELP_EPILOG = """
Examples:
    bead-agent audit data/independent-code-review
    bead-agent audit data/user-access-review --model gemini --consistency 3
    bead-agent eval  data/independent-code-review --models claude,openai,gemini
    bead-agent info  data/change-management
    bead-agent show  output/user-access-review/claude/sample-1/assessment.json
"""

app = typer.Typer(
    add_completion=False,
    no_args_is_help=True,
    help="Bead audit agent — turn a control folder into per-attribute verdicts.",
    epilog=HELP_EPILOG,
)
CONSOLE = Console()


# --- Shared helpers ---------------------------------------------------------

_VERDICT_STYLE = {
    "SUCCESS": "green",
    "FAIL": "red",
    "FURTHER_EVIDENCE_REQUIRED": "yellow",
}
_VERDICT_EMOJI = {
    "SUCCESS": "✅",
    "FAIL": "❌",
    "FURTHER_EVIDENCE_REQUIRED": "⚠️",
    "CONTROL_PASS": "✅",
    "CONTROL_FAIL": "❌",
    "CONTROL_INCONCLUSIVE": "⚠️",
}


def _read_trace_summary(trace_path: Path) -> dict:
    if not trace_path.exists():
        return {}
    total_cost = 0.0
    input_t = output_t = cache_r = calls = 0
    for line in trace_path.read_text().splitlines():
        if not line.strip():
            continue
        d = json.loads(line)
        total_cost += d.get("cost_usd") or 0
        input_t += d.get("input_tokens") or 0
        output_t += d.get("output_tokens") or 0
        cache_r += d.get("cache_read_tokens") or 0
        calls += 1
    return {
        "cost": total_cost,
        "input_tokens": input_t,
        "output_tokens": output_t,
        "cache_read_tokens": cache_r,
        "calls": calls,
        "cache_hit_pct": (cache_r / input_t * 100) if input_t else 0.0,
    }


# --- audit ------------------------------------------------------------------

@app.command()
def audit(
    control_dir: Path = typer.Argument(
        ...,
        exists=True,
        file_okay=False,
        dir_okay=True,
        help="Directory containing control.md and evidence samples.",
    ),
    model: str = typer.Option(
        "claude",
        "--model",
        "-m",
        help="LLM provider: claude | openai | gemini.",
    ),
    out: Optional[Path] = typer.Option(
        None,
        "--out",
        "-o",
        help="Output directory (default: output/<control>/<model>/).",
    ),
    no_verify: bool = typer.Option(
        False,
        "--no-verify",
        help="Skip the FURTHER_EVIDENCE_REQUIRED verifier pass (faster; useful for evals).",
    ),
    consistency: int = typer.Option(
        1,
        "--consistency",
        "-k",
        help="Self-consistency voting: run the judge N times per attribute and take majority. "
        "N=3 costs ~3x tokens on the judge step (cheaper with cache warm) but lifts accuracy.",
    ),
):
    """Audit a control folder and emit per-sample assessments.

    Reads control.md + any policy files, discovers samples, extracts facts
    from evidence (screenshots/xlsx/markdown), and produces a verdict per
    (sample × control attribute) with mandatory citations.

    Outputs land in <out>/:
      - control.json                 the parsed control spec
      - trace.jsonl                  every LLM call (tokens, cost, hashes)
      - <sample>/assessment.json     structured verdicts (Bead's format)
      - <sample>/assessment.md       human-readable workpaper
    """
    provider = make_provider(model)
    if out is None:
        out = Path("output") / control_dir.name / provider.name
    out.mkdir(parents=True, exist_ok=True)

    cfg = RunConfig(
        control_dir=control_dir,
        out_dir=out,
        provider=provider,
        verify=not no_verify,
        consistency=consistency,
    )
    assessments = run_audit(cfg)

    # Attribute-level summary table
    table = Table(title=f"Audit summary — {provider.name}:{provider.model}", show_lines=True)
    table.add_column("Sample", style="cyan")
    table.add_column("Attribute")
    table.add_column("Verdict")
    table.add_column("Conf", justify="right")
    for sa in assessments:
        for a in sa.attributes:
            style = _VERDICT_STYLE[a.verdict.value]
            table.add_row(
                sa.sample_id,
                a.attribute_text[:60] + ("…" if len(a.attribute_text) > 60 else ""),
                f"[{style}]{a.verdict.value}[/{style}]",
                f"{a.confidence:.2f}",
            )
    CONSOLE.print(table)

    # Sample-level rollup panel
    rollup_lines = []
    for sa in assessments:
        e = _VERDICT_EMOJI[sa.control_conclusion.value]
        rollup_lines.append(f"  {e} {sa.sample_id}: [bold]{sa.control_conclusion.value}[/]")
        if sa.evidence_coverage:
            cov = sa.evidence_coverage
            rollup_lines.append(
                f"     coverage: {int(cov.coverage_rate * 100)}% "
                f"({len(cov.cited_files)}/{len(cov.all_files)} evidence files cited)"
            )
    CONSOLE.print(Panel("\n".join(rollup_lines), title="Control conclusion", border_style="dim"))

    # Cost + cache stats
    summary = _read_trace_summary(out / "trace.jsonl")
    if summary:
        CONSOLE.print(
            f"[dim]Cost: [bold]${summary['cost']:.4f}[/bold] · "
            f"{summary['calls']} calls · "
            f"{summary['input_tokens']:,} in / {summary['output_tokens']:,} out tokens · "
            f"cache-hit {summary['cache_hit_pct']:.0f}% ({summary['cache_read_tokens']:,} tokens)[/dim]"
        )

    CONSOLE.print(f"\nResults written to [bold]{out}[/]")
    CONSOLE.print(
        f"Inspect: [cyan]bead-agent show {out}/<sample>/assessment.json[/cyan]"
    )


# --- info -------------------------------------------------------------------

@app.command()
def info(
    control_dir: Path = typer.Argument(
        ...,
        exists=True,
        file_okay=False,
        dir_okay=True,
        help="Control directory to inspect.",
    ),
    model: str = typer.Option(
        "claude",
        "--model",
        "-m",
        help="LLM used to parse the control (small cost per invocation).",
    ),
):
    """Parse the control + list discovered samples — no audit, no verdicts.

    Useful for:
      - Verifying the pipeline discovers your samples correctly.
      - Seeing the atomic testable_criteria the LLM extracts from the control.
      - Estimating cost before running a full audit.
    """
    from audit_agent.control import load_control
    from audit_agent.evidence.router import discover_samples

    provider = make_provider(model)
    CONSOLE.print(f"[dim]Parsing control with {provider.name}:{provider.model}...[/]")
    control = load_control(control_dir, provider)

    CONSOLE.print()
    CONSOLE.print(Panel(f"[bold]{control.name}[/bold]\n\n{control.description}", border_style="cyan"))

    # Attributes table
    attr_table = Table(title="Attributes", show_lines=True)
    attr_table.add_column("#", style="dim", width=3)
    attr_table.add_column("Text")
    attr_table.add_column("Testable criteria", overflow="fold")
    attr_table.add_column("Policies", style="dim")
    for i, a in enumerate(control.attributes, 1):
        attr_table.add_row(
            str(i),
            a.text,
            "\n".join(f"• {c}" for c in a.testable_criteria),
            ", ".join(a.relevant_policies) or "—",
        )
    CONSOLE.print(attr_table)

    # Samples table
    bundles = discover_samples(control_dir)
    sample_table = Table(title="Discovered samples", show_lines=True)
    sample_table.add_column("Sample id", style="cyan")
    sample_table.add_column("Evidence files", overflow="fold")
    for b in bundles:
        files = [f"{f.kind}: {Path(f.path).name}" for f in b.files]
        sample_table.add_row(b.sample_id, "\n".join(files) or "—")
    CONSOLE.print(sample_table)

    # Total LLM-call estimate
    n_attrs = len(control.attributes)
    n_samples = len(bundles)
    total_screenshots = sum(len(b.screenshots) for b in bundles)
    est_calls = 1 + total_screenshots + (n_attrs * n_samples)  # control-parse + extract + judge
    CONSOLE.print(
        f"\n[dim]Estimated LLM calls per run (no verifier, --consistency 1): "
        f"[bold]{est_calls}[/bold] "
        f"(1 control-parse + {total_screenshots} screenshot extraction + "
        f"{n_attrs} attributes × {n_samples} samples = {n_attrs * n_samples} judgments)[/dim]"
    )


# --- show -------------------------------------------------------------------

@app.command()
def show(
    assessment_path: Path = typer.Argument(
        ...,
        exists=True,
        file_okay=True,
        dir_okay=False,
        help="Path to an assessment.json file.",
    ),
):
    """Pretty-print a past assessment.json in the terminal.

    Use this to inspect audit output without opening the JSON file directly.
    """
    from audit_agent.schemas import SampleAssessment

    sa = SampleAssessment(**json.loads(assessment_path.read_text()))
    emoji = _VERDICT_EMOJI[sa.control_conclusion.value]

    header = (
        f"[bold]{sa.control}[/bold]  ·  sample: {sa.sample_id}\n"
        f"model: {sa.model}\n"
        f"generated: {sa.generated_at.isoformat()}\n"
        f"\n{emoji}  [bold]{sa.control_conclusion.value}[/bold]"
    )
    if sa.consistency_disagreement_rate is not None:
        header += f"\nconsistency disagreement: {sa.consistency_disagreement_rate:.0%}"
    if sa.evidence_coverage:
        cov = sa.evidence_coverage
        header += (
            f"\nevidence coverage: {int(cov.coverage_rate * 100)}% — "
            f"{len(cov.cited_files)}/{len(cov.all_files)} files cited"
        )
        if cov.uncited_files:
            header += f"\nuncited: {', '.join(cov.uncited_files)}"
    CONSOLE.print(Panel(header, border_style="cyan"))

    if sa.reperformance_notes:
        CONSOLE.print(Panel(sa.reperformance_notes, title="Reperformance", border_style="dim"))

    for a in sa.attributes:
        style = _VERDICT_STYLE[a.verdict.value]
        emoji_a = _VERDICT_EMOJI[a.verdict.value]
        body_lines = [
            f"[{style}]{emoji_a}  {a.verdict.value}[/{style}]  ·  confidence {a.confidence:.2f}",
            "",
            a.rationale,
        ]
        if a.policy_references:
            body_lines.append("")
            body_lines.append("[bold]Policy references:[/bold]")
            for p in a.policy_references:
                body_lines.append(f"  • {p.source} § {p.section}: “{p.quote}”")
        if a.evidence_refs:
            body_lines.append("")
            body_lines.append("[bold]Evidence:[/bold]")
            for e in a.evidence_refs:
                body_lines.append(f"  • {e.file} @ {e.locator}")
                body_lines.append(f"    [dim]{e.observation}[/dim]")
        if a.exceptions_considered:
            body_lines.append("")
            body_lines.append("[bold]Exceptions considered:[/bold]")
            for x in a.exceptions_considered:
                body_lines.append(f"  • {x}")
        CONSOLE.print(Panel("\n".join(body_lines), title=a.attribute_text))


# --- trace ------------------------------------------------------------------

@app.command()
def trace(
    run_dir: Path = typer.Argument(
        ...,
        exists=True,
        file_okay=False,
        dir_okay=True,
        help="Output directory containing trace.jsonl.",
    ),
):
    """Show the trace log for a past run — every LLM call with tokens + cost."""
    trace_path = run_dir / "trace.jsonl"
    if not trace_path.exists():
        CONSOLE.print(f"[red]No trace.jsonl at {trace_path}[/]")
        raise typer.Exit(1)

    table = Table(title=f"LLM call trace — {run_dir}", show_lines=False)
    table.add_column("#", style="dim", width=3)
    table.add_column("Purpose", overflow="fold")
    table.add_column("In", justify="right")
    table.add_column("Cache", justify="right", style="green")
    table.add_column("Out", justify="right")
    table.add_column("$", justify="right")
    table.add_column("Latency", justify="right", style="dim")

    total_cost = 0.0
    for i, line in enumerate(trace_path.read_text().splitlines(), 1):
        if not line.strip():
            continue
        d = json.loads(line)
        total_cost += d.get("cost_usd") or 0
        table.add_row(
            str(i),
            d.get("purpose", "?")[:70],
            f"{d.get('input_tokens') or 0:,}",
            f"{d.get('cache_read_tokens') or 0:,}",
            f"{d.get('output_tokens') or 0:,}",
            f"${d.get('cost_usd') or 0:.4f}",
            f"{d.get('latency_ms') or 0}ms",
        )
    CONSOLE.print(table)
    CONSOLE.print(f"\n[bold]Total: ${total_cost:.4f}[/bold]")


# --- eval -------------------------------------------------------------------

@app.command()
def eval(
    control_dir: Path = typer.Argument(..., exists=True, file_okay=False, dir_okay=True),
    golden: Path = typer.Option(
        Path("evals/golden.jsonl"),
        "--golden",
        help="Path to hand-labelled golden set.",
    ),
    models: str = typer.Option(
        "claude,openai,gemini",
        "--models",
        help="Comma-separated list of providers to score.",
    ),
):
    """Run the audit against multiple models, compare to the golden set, print a scoreboard."""
    from audit_agent.eval_runner import run_eval
    run_eval(control_dir=control_dir, golden_path=golden, model_names=models.split(","))
