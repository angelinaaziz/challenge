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
):
    """Audit a control folder and emit per-sample assessments."""
    provider = make_provider(model)
    if out is None:
        out = Path("output") / control_dir.name / provider.name
    out.mkdir(parents=True, exist_ok=True)

    cfg = RunConfig(control_dir=control_dir, out_dir=out, provider=provider, verify=not no_verify)
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
