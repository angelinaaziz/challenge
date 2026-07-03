"""Typer CLI.

Commands:
    bead-agent audit <control-dir>     Run the pipeline, produce assessments
    bead-agent eval  <control-dir>     Multi-model scoreboard vs golden
    bead-agent info  <control-dir>     Parse the control + list samples (no LLM audit)
    bead-agent show  <assessment.json> Pretty-print a past assessment file
    bead-agent trace <run-dir>         Show the trace log for a past run
    bead-agent report <run-dir>        Generate a self-contained HTML report
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

import typer
from dotenv import load_dotenv
from rich.console import Console
from rich.padding import Padding
from rich.panel import Panel
from rich.rule import Rule
from rich.table import Table
from rich.text import Text

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

# Bead palette (from usebead.ai): mint accents, warm cream neutrals, warm coral for FAIL.
_VERDICT_STYLE = {
    "SUCCESS": "bold #88d98d",
    "FAIL": "bold #f6b0aa",
    "FURTHER_EVIDENCE_REQUIRED": "bold #e8c07a",
}
_VERDICT_EMOJI = {
    "SUCCESS": "●",
    "FAIL": "●",
    "FURTHER_EVIDENCE_REQUIRED": "●",
    "CONTROL_PASS": "●",
    "CONTROL_FAIL": "●",
    "CONTROL_INCONCLUSIVE": "●",
}
_CONCLUSION_STYLE = {
    "CONTROL_PASS": "bold #88d98d",
    "CONTROL_FAIL": "bold #f6b0aa",
    "CONTROL_INCONCLUSIVE": "bold #e8c07a",
}
_ACCENT = "#88d98d"          # Bead mint
_PAPER = "#dbdad4"           # Bead cream
_MUTED = "#bab8b0"


def _short_rationale(text: str, max_chars: int = 220) -> str:
    """Return the first sentence-ish, capped at max_chars — full text via `show`."""
    text = text.replace("\n", " ").strip()
    if len(text) <= max_chars:
        return text
    cut = text[:max_chars]
    # Prefer to cut at the last sentence boundary if there is one.
    for terminator in ". ! ?".split():
        idx = cut.rfind(terminator)
        if idx >= max_chars * 0.6:
            return cut[: idx + 1] + " …"
    return cut + " …"


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

    _render_audit_summary(assessments, provider, out)


# --- audit rendering --------------------------------------------------------

def _render_audit_summary(assessments, provider, out: Path) -> None:
    """The scannable per-sample layout users see when a run finishes.

    Design: one panel per sample. Big control-conclusion badge. Per-attribute
    row with verdict icon, confidence bar, rationale preview. No truncated
    column headers. Details available via `bead-agent show`.
    """
    CONSOLE.print()
    header = Text.assemble(
        ("BEAD AUDIT ", f"{_ACCENT} bold"),
        ("· ", "dim"),
        ("run complete", _PAPER),
        ("  ", ""),
        (f"[{provider.name}:{provider.model}]", "dim"),
    )
    CONSOLE.print(Padding(header, (0, 2)))
    CONSOLE.print()

    for sa in assessments:
        _render_sample_summary(sa)

    _render_cost_footer(out)

    CONSOLE.print()
    CONSOLE.print(Padding(f"Results: [bold]{out}[/]", (0, 2)))
    CONSOLE.print(
        Padding(
            f"[dim]Inspect a sample: [cyan]bead-agent show {out}/<sample>/assessment.json[/]\n"
            f"See LLM call cost breakdown: [cyan]bead-agent trace {out}[/]\n"
            f"Generate HTML report: [cyan]bead-agent report {out}[/][/dim]",
            (0, 2),
        )
    )


def _render_sample_summary(sa) -> None:
    conclusion_style = _CONCLUSION_STYLE[sa.control_conclusion.value]
    conclusion_emoji = _VERDICT_EMOJI[sa.control_conclusion.value]

    # Headline card — big verdict + coverage
    heading = Text.assemble(
        (f"{conclusion_emoji}  ", ""),
        (sa.sample_id, "bold cyan"),
        ("   ", ""),
        (sa.control_conclusion.value, conclusion_style),
    )
    heading_lines = [heading]
    if sa.evidence_coverage:
        cov = sa.evidence_coverage
        heading_lines.append(
            Text.assemble(
                ("evidence coverage: ", "dim"),
                (f"{int(cov.coverage_rate * 100)}%", "bold"),
                ("   ", ""),
                (f"({len(cov.cited_files)}/{len(cov.all_files)} files cited)", "dim"),
            )
        )
        if cov.uncited_files:
            heading_lines.append(
                Text.assemble(
                    ("uncited: ", "dim yellow"),
                    (", ".join(cov.uncited_files), "yellow"),
                )
            )
    if sa.consistency_disagreement_rate is not None:
        heading_lines.append(
            Text.assemble(
                ("model disagreement: ", "dim"),
                (f"{sa.consistency_disagreement_rate:.0%}", "bold"),
            )
        )

    heading_text = Text("\n").join(heading_lines)
    CONSOLE.print(
        Panel(
            heading_text,
            border_style=conclusion_style.split()[-1],  # 'red'|'green'|'yellow'
            padding=(1, 2),
        )
    )

    # Reperformance summary (UAR only)
    if sa.reperformance_notes:
        CONSOLE.print(
            Padding(
                Panel(
                    Text(sa.reperformance_notes, style=""),
                    title=Text("Reperformance", style="bold"),
                    title_align="left",
                    border_style="blue",
                    padding=(0, 2),
                ),
                (0, 2),
            )
        )

    # Attributes — one clean block per attribute
    CONSOLE.print(Padding(Text("Attribute verdicts", style="dim underline"), (1, 2)))
    for a in sa.attributes:
        style = _VERDICT_STYLE[a.verdict.value]
        base = style.split()[-1]
        emoji = _VERDICT_EMOJI[a.verdict.value]

        title_line = Text.assemble(
            (f"{emoji}  ", ""),
            (a.attribute_text, "bold"),
        )
        meta_line = Text.assemble(
            (a.verdict.value, style),
            ("   confidence ", "dim"),
            (f"{a.confidence:.2f}", "bold"),
            ("   citations ", "dim"),
            (f"{len(a.evidence_refs)}", "bold"),
        )
        body = Text(_short_rationale(a.rationale), style="")

        block = Text("\n").join([title_line, meta_line, Text(""), body])
        CONSOLE.print(
            Padding(
                Panel(block, border_style=base, padding=(0, 2)),
                (0, 4),
            )
        )
    CONSOLE.print()


def _render_cost_footer(out: Path) -> None:
    summary = _read_trace_summary(out / "trace.jsonl")
    if not summary:
        return
    text = Text.assemble(
        ("Cost ", "dim"),
        (f"${summary['cost']:.4f}", f"bold {_PAPER}"),
        ("   ", ""),
        ("Calls ", "dim"),
        (f"{summary['calls']}", f"bold {_PAPER}"),
        ("   ", ""),
        ("Tokens ", "dim"),
        (f"{summary['input_tokens']:,} in / {summary['output_tokens']:,} out", f"bold {_PAPER}"),
        ("   ", ""),
        ("Cache-hit ", "dim"),
        (f"{summary['cache_hit_pct']:.0f}%", f"bold {_ACCENT}"),
        (f" ({summary['cache_read_tokens']:,} tok)", "dim"),
    )
    CONSOLE.print(Rule(style=f"{_ACCENT} dim"))
    CONSOLE.print(Padding(text, (0, 2)))
    CONSOLE.print(Rule(style=f"{_ACCENT} dim"))


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
    style = _CONCLUSION_STYLE[sa.control_conclusion.value]
    base = style.split()[-1]
    emoji = _VERDICT_EMOJI[sa.control_conclusion.value]

    # --- Header card
    header_lines = [
        Text.assemble((sa.control, "bold cyan")),
        Text.assemble(
            ("sample ", "dim"),
            (sa.sample_id, "bold"),
            ("  ·  ", "dim"),
            (sa.model, "dim"),
        ),
    ]
    header_lines.append(Text(""))
    header_lines.append(
        Text.assemble(
            (f"{emoji}  ", ""),
            (sa.control_conclusion.value, style),
        )
    )
    if sa.evidence_coverage:
        cov = sa.evidence_coverage
        header_lines.append(
            Text.assemble(
                ("evidence coverage: ", "dim"),
                (f"{int(cov.coverage_rate * 100)}%", "bold"),
                (" · ", "dim"),
                (f"{len(cov.cited_files)}/{len(cov.all_files)} files cited", "dim"),
            )
        )
        if cov.uncited_files:
            header_lines.append(
                Text.assemble(
                    ("uncited: ", "dim yellow"),
                    (", ".join(cov.uncited_files), "yellow"),
                )
            )
    if sa.consistency_disagreement_rate is not None:
        header_lines.append(
            Text.assemble(
                ("model disagreement: ", "dim"),
                (f"{sa.consistency_disagreement_rate:.0%}", "bold"),
            )
        )

    CONSOLE.print()
    CONSOLE.print(
        Panel(Text("\n").join(header_lines), border_style=base, padding=(1, 2))
    )

    # --- Reperformance summary
    if sa.reperformance_notes:
        CONSOLE.print(
            Padding(
                Panel(
                    Text(sa.reperformance_notes),
                    title=Text("Reperformance summary", style="bold"),
                    title_align="left",
                    border_style="blue",
                    padding=(0, 2),
                ),
                (0, 0),
            )
        )

    # --- Attribute cards
    for a in sa.attributes:
        vstyle = _VERDICT_STYLE[a.verdict.value]
        vbase = vstyle.split()[-1]
        vemoji = _VERDICT_EMOJI[a.verdict.value]

        lines: list[Text] = []
        lines.append(
            Text.assemble(
                (a.verdict.value, vstyle),
                ("   confidence ", "dim"),
                (f"{a.confidence:.2f}", "bold"),
                ("   citations ", "dim"),
                (f"{len(a.evidence_refs)}", "bold"),
            )
        )
        lines.append(Text(""))
        lines.append(Text(a.rationale))

        if a.policy_references:
            lines.append(Text(""))
            lines.append(Text("Policy references", style="bold underline"))
            for p in a.policy_references:
                lines.append(
                    Text.assemble(
                        ("  • ", "dim"),
                        (p.source, "cyan"),
                        (" § ", "dim"),
                        (p.section, ""),
                    )
                )
                lines.append(Text(f'    "{p.quote}"', style="italic dim"))

        if a.evidence_refs:
            lines.append(Text(""))
            lines.append(Text("Evidence", style="bold underline"))
            for e in a.evidence_refs:
                lines.append(
                    Text.assemble(
                        ("  • ", "dim"),
                        (e.file, "cyan"),
                        ("  @  ", "dim"),
                        (e.locator, "magenta"),
                    )
                )
                lines.append(Text(f"    {e.observation}", style="dim"))

        if a.exceptions_considered:
            lines.append(Text(""))
            lines.append(Text("Exceptions considered", style="bold underline"))
            for x in a.exceptions_considered:
                lines.append(Text(f"  • {x}"))

        block = Text("\n").join(lines)
        CONSOLE.print()
        CONSOLE.print(
            Panel(
                block,
                title=Text.assemble((f"{vemoji}  ", ""), (a.attribute_text, "bold")),
                title_align="left",
                border_style=vbase,
                padding=(1, 2),
            )
        )


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


# --- report -----------------------------------------------------------------

@app.command()
def report(
    run_dir: Path = typer.Argument(
        ...,
        exists=True,
        file_okay=False,
        dir_okay=True,
        help="Output directory containing sample assessment.json files and trace.jsonl.",
    ),
    open_browser: bool = typer.Option(
        False, "--open", help="Open the report in the default browser after generating."
    ),
):
    """Generate a self-contained HTML report of a past run.

    Writes report.html into the same directory. No external dependencies —
    styles are inlined so the file works offline and can be emailed as a
    single attachment.
    """
    from audit_agent.html_report import build_report

    out_path = build_report(run_dir)
    CONSOLE.print(f"[green]Wrote[/] [bold]{out_path}[/]")
    if open_browser:
        import webbrowser

        webbrowser.open(out_path.as_uri())


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
