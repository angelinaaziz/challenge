"""Multi-model eval. Runs the audit under each provider, compares to a hand-labeled
golden set, prints a scoreboard.

golden.jsonl format (one JSON object per line):
    {"control_dir": "data/independent-code-review",
     "sample_id": "sample-1",
     "attribute_id": "code-reviews-performed-prior-to-merge",
     "verdict": "SUCCESS",
     "notes": "..."}
"""

from __future__ import annotations

import json
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

from rich.console import Console
from rich.table import Table

from audit_agent.llm import make_provider
from audit_agent.pipeline import RunConfig, run_audit
from audit_agent.schemas import SampleAssessment, Verdict


CONSOLE = Console()


@dataclass
class GoldenLabel:
    control_dir: str
    sample_id: str
    attribute_text: str  # verbatim from control.md — stable across providers
    verdict: Verdict
    notes: str = ""


def load_golden(path: Path) -> list[GoldenLabel]:
    labels: list[GoldenLabel] = []
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        d = json.loads(line)
        labels.append(
            GoldenLabel(
                control_dir=d["control_dir"],
                sample_id=d["sample_id"],
                attribute_text=d["attribute_text"],
                verdict=Verdict(d["verdict"]),
                notes=d.get("notes", ""),
            )
        )
    return labels


def _labels_by_control(labels: list[GoldenLabel]) -> dict[str, list[GoldenLabel]]:
    out: dict[str, list[GoldenLabel]] = defaultdict(list)
    for lab in labels:
        out[lab.control_dir].append(lab)
    return out


def _norm(s: str) -> str:
    return "".join(c.lower() for c in s if c.isalnum())


def _score_run(
    assessments: list[SampleAssessment], relevant_labels: list[GoldenLabel]
) -> tuple[int, int, list[tuple[GoldenLabel, str]]]:
    # Match by normalized attribute_text (case-insensitive, punctuation-stripped)
    # so LLM-parsed attribute IDs don't need to align across providers.
    by_key = {
        (sa.sample_id, _norm(a.attribute_text)): a
        for sa in assessments
        for a in sa.attributes
    }
    matches = 0
    total = 0
    mismatches: list[tuple[GoldenLabel, str]] = []
    for lab in relevant_labels:
        got = by_key.get((lab.sample_id, _norm(lab.attribute_text)))
        if got is None:
            mismatches.append((lab, "MISSING"))
            total += 1
            continue
        total += 1
        if got.verdict == lab.verdict:
            matches += 1
        else:
            mismatches.append((lab, got.verdict.value))
    return matches, total, mismatches


def run_eval(control_dir: Path, golden_path: Path, model_names: list[str]) -> None:
    if not golden_path.exists():
        raise FileNotFoundError(
            f"No golden set at {golden_path}. Hand-label first (see README)."
        )
    labels = load_golden(golden_path)
    per_control = _labels_by_control(labels)
    relevant_labels = per_control.get(str(control_dir), [])
    if not relevant_labels:
        # Fallback: try filename tail match (so 'data/user-access-review' matches
        # regardless of the caller's cwd).
        for k, v in per_control.items():
            if Path(k).name == control_dir.name:
                relevant_labels = v
                break
    if not relevant_labels:
        raise ValueError(f"No golden labels for control_dir={control_dir}")

    scores: dict[str, dict] = {}
    for name in model_names:
        provider = make_provider(name.strip())
        out_dir = Path("output") / control_dir.name / provider.name
        out_dir.mkdir(parents=True, exist_ok=True)
        CONSOLE.rule(f"[bold]Running {provider.name}:{provider.model}")
        assessments = run_audit(
            RunConfig(control_dir=control_dir, out_dir=out_dir, provider=provider, verify=True)
        )
        matches, total, mismatches = _score_run(assessments, relevant_labels)
        scores[f"{provider.name}:{provider.model}"] = {
            "matches": matches,
            "total": total,
            "accuracy": matches / total if total else 0.0,
            "mismatches": mismatches,
        }

    _print_scoreboard(scores, control_dir)


def _print_scoreboard(scores: dict[str, dict], control_dir: Path) -> None:
    table = Table(title=f"Model scoreboard — {control_dir.name}")
    table.add_column("Model")
    table.add_column("Correct")
    table.add_column("Total")
    table.add_column("Accuracy")
    for k, v in scores.items():
        acc = v["accuracy"]
        style = "green" if acc >= 0.8 else "yellow" if acc >= 0.5 else "red"
        table.add_row(k, str(v["matches"]), str(v["total"]), f"[{style}]{acc:.1%}[/{style}]")
    CONSOLE.print(table)

    for k, v in scores.items():
        if v["mismatches"]:
            CONSOLE.print(f"\n[bold]{k} mismatches:[/]")
            for lab, got in v["mismatches"]:
                CONSOLE.print(
                    f"  • {lab.sample_id} / {lab.attribute_text[:60]}: "
                    f"expected [green]{lab.verdict.value}[/], got [red]{got}[/]"
                )
