"""Per-attribute LLM judgment.

One (sample × attribute) → one AttributeAssessment. Isolating the judgment per
attribute lets us reason more precisely, parallelize, and evaluate each verdict
against a hand-labeled golden set. It also mirrors how a real auditor drafts a
workpaper — one row per attribute, not one blob per control.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Optional

from audit_agent.llm import LLMProvider, Message, TextPart
from audit_agent.schemas import (
    AttributeAssessment,
    Control,
    ControlAttribute,
    ScreenshotFacts,
    TextEvidence,
    XlsxFacts,
)


PROMPT_FILE = Path(__file__).parent.parent / "prompts" / "attribute_judge.md"


def _read_prompt() -> str:
    return PROMPT_FILE.read_text()


def _facts_block(
    screenshots: list[ScreenshotFacts],
    xlsx: list[XlsxFacts],
    text_evidence: list[TextEvidence],
    reconciliation: Optional[dict[str, Any]],
) -> str:
    parts: list[str] = []
    if screenshots:
        parts.append("## Screenshot facts")
        for f in screenshots:
            parts.append(json.dumps(f.model_dump(), indent=2, default=str))
    if xlsx:
        parts.append("## Workbook summaries")
        for x in xlsx:
            parts.append(json.dumps(x.model_dump(), indent=2, default=str))
    if text_evidence:
        parts.append("## Text / markdown evidence (verbatim)")
        for t in text_evidence:
            parts.append(f"### file: {t.file}\n\n```\n{t.content}\n```")
    if reconciliation is not None:
        parts.append("## Deterministic reperformance (ground truth — trust this)")
        parts.append(json.dumps(reconciliation, indent=2, default=str))
    return "\n\n".join(parts)


def _policy_block(control: Control, attribute: ControlAttribute) -> str:
    """Give the judge verbatim policy text for policies that constrain this attribute."""
    if not attribute.relevant_policies:
        return ""
    blocks: list[str] = ["## Relevant policies (verbatim)"]
    for pname in attribute.relevant_policies:
        text = control.policies.get(pname)
        if text:
            blocks.append(f"### {pname}\n\n{text}")
    return "\n\n".join(blocks) if len(blocks) > 1 else ""


def judge_attribute(
    control: Control,
    attribute: ControlAttribute,
    sample_id: str,
    screenshots: list[ScreenshotFacts],
    xlsx: list[XlsxFacts],
    text_evidence: list[TextEvidence],
    reconciliation: Optional[dict[str, Any]],
    provider: LLMProvider,
    consistency: int = 1,
) -> tuple[AttributeAssessment, dict[str, Any]]:
    """One or more judgment rounds; on `consistency > 1` we take majority verdict.

    Self-consistency: on tricky judgments a single LLM call can flake. Running
    N judgments and taking majority is a well-known reliability lift for the
    cost of N× tokens. We surface the disagreement rate in metadata so the
    reviewing auditor sees where the model was unsure.
    """
    system = _read_prompt()

    user_sections = [
        f"# Control\n\n**{control.name}**\n\n{control.description}",
        f"# Attribute under test\n\n**{attribute.text}**\n\n"
        f"Testable criteria:\n" + "\n".join(f"- {c}" for c in attribute.testable_criteria),
        f"# Sample\n\nsample_id = `{sample_id}`",
    ]
    policy_block = _policy_block(control, attribute)
    if policy_block:
        user_sections.append(policy_block)
    user_sections.append(
        "# Evidence\n\n" + _facts_block(screenshots, xlsx, text_evidence, reconciliation)
    )

    user_text = "\n\n---\n\n".join(user_sections)

    def _one_round() -> tuple["AttributeAssessment", dict[str, Any]]:
        a, m = provider.complete_structured(
            system=system,
            messages=[Message(role="user", parts=[TextPart(text=user_text)])],
            schema=AttributeAssessment,
            purpose=f"Judge {attribute.id} on {sample_id}",
            max_tokens=2048,
        )
        # Force identifying fields — the model doesn't need to remember them.
        a.control = control.name
        a.sample_id = sample_id
        a.attribute_id = attribute.id
        a.attribute_text = attribute.text
        return a, m

    if consistency <= 1:
        return _one_round()

    rounds: list["AttributeAssessment"] = []
    metas: list[dict[str, Any]] = []
    for _ in range(consistency):
        a, m = _one_round()
        rounds.append(a)
        metas.append(m)

    # Majority verdict; tie-break: pick the verdict with the highest mean confidence.
    from collections import Counter

    counter = Counter(a.verdict for a in rounds)
    top_count = counter.most_common(1)[0][1]
    winners = [v for v, c in counter.items() if c == top_count]
    if len(winners) == 1:
        winning_verdict = winners[0]
    else:
        confs = {
            v: sum(a.confidence for a in rounds if a.verdict == v)
            / max(1, sum(1 for a in rounds if a.verdict == v))
            for v in winners
        }
        winning_verdict = max(confs, key=confs.get)

    winning_rounds = [a for a in rounds if a.verdict == winning_verdict]
    # Pick the winning round with the highest confidence as our canonical response.
    canonical = max(winning_rounds, key=lambda a: a.confidence)
    disagreement = 1.0 - (top_count / consistency)

    # Fold aggregate metadata: sum tokens and take max latency (worst-case wall-clock).
    agg_meta = {
        "provider": metas[0].get("provider"),
        "model": metas[0].get("model"),
        "input_tokens": sum(m.get("input_tokens") or 0 for m in metas),
        "output_tokens": sum(m.get("output_tokens") or 0 for m in metas),
        "latency_ms": max(m.get("latency_ms") or 0 for m in metas),
        "consistency_rounds": consistency,
        "disagreement_rate": disagreement,
    }
    return canonical, agg_meta
