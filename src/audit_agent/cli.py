"""Typer CLI. `bead-agent audit <control-dir>` runs the full pipeline."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer
from dotenv import load_dotenv
from rich.console import Console
from rich.table import Table

from audit_agent.llm import make_provider
from audit_agent.pipeline import RunConfig, run_audit

load_dotenv()

app = typer.Typer(add_completion=False, no_args_is_help=True)
CONSOLE = Console()


@app.command()
def audit(
    control_dir: Path = typer.Argument(
        ..., exists=True, file_okay=False, dir_okay=True, help="Directory containing control.md"
    ),
    model: str = typer.Option("claude", "--model", "-m", help="claude | openai | gemini"),
    out: Optional[Path] = typer.Option(
        None,
        "--out",
        "-o",
        help="Output directory (default: output/<control>/<model>/)",
    ),
    no_verify: bool = typer.Option(
        False, "--no-verify", help="Skip the FURTHER_EVIDENCE_REQUIRED verifier pass."
    ),
    consistency: int = typer.Option(
        1,
        "--consistency",
        "-k",
        help="Self-consistency voting: run the judge N times and take majority. "
        "N=3 costs 3x tokens but materially lifts accuracy on ambiguous cases.",
    ),
):
    """Audit a control folder and emit per-sample assessments."""
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

    # Print a compact summary table.
    table = Table(title=f"Audit summary — {provider.name}:{provider.model}")
    table.add_column("Sample")
    table.add_column("Attribute")
    table.add_column("Verdict")
    table.add_column("Conf")
    for sa in assessments:
        for a in sa.attributes:
            style = {"SUCCESS": "green", "FAIL": "red", "FURTHER_EVIDENCE_REQUIRED": "yellow"}[
                a.verdict.value
            ]
            table.add_row(
                sa.sample_id,
                a.attribute_text[:60] + ("…" if len(a.attribute_text) > 60 else ""),
                f"[{style}]{a.verdict.value}[/{style}]",
                f"{a.confidence:.2f}",
            )
    CONSOLE.print(table)
    # Read cost totals from the trace file just written.
    from audit_agent.trace import Tracer  # noqa: F401 (kept for symmetry)
    trace_path = out / "trace.jsonl"
    if trace_path.exists():
        total_cost = 0.0
        input_t = output_t = cache_r = calls = 0
        import json as _json
        for line in trace_path.read_text().splitlines():
            if not line.strip():
                continue
            d = _json.loads(line)
            total_cost += d.get("cost_usd") or 0
            input_t += d.get("input_tokens") or 0
            output_t += d.get("output_tokens") or 0
            cache_r += d.get("cache_read_tokens") or 0
            calls += 1
        cache_hit_pct = (cache_r / input_t * 100) if input_t else 0.0
        CONSOLE.print(
            f"\n[dim]Cost: [bold]${total_cost:.4f}[/bold] · {calls} calls · "
            f"{input_t:,} in / {output_t:,} out tokens · "
            f"cache-hit {cache_hit_pct:.0f}% ({cache_r:,} tokens)[/dim]"
        )
    CONSOLE.print(f"\nResults written to [bold]{out}[/]")


@app.command()
def eval(
    control_dir: Path = typer.Argument(..., exists=True, file_okay=False),
    golden: Path = typer.Option(
        Path("evals/golden.jsonl"), "--golden", help="Path to hand-labeled golden set."
    ),
    models: str = typer.Option(
        "claude,openai,gemini",
        "--models",
        help="Comma-separated list of providers to test.",
    ),
):
    """Run the audit against multiple models, compare to golden, print a scoreboard."""
    from audit_agent.eval_runner import run_eval

    run_eval(control_dir=control_dir, golden_path=golden, model_names=models.split(","))
