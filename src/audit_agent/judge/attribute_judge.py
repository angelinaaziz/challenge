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
) -> tuple[AttributeAssessment, dict[str, Any]]:
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

    assessment, meta = provider.complete_structured(
        system=system,
        messages=[Message(role="user", parts=[TextPart(text=user_text)])],
        schema=AttributeAssessment,
        purpose=f"Judge {attribute.id} on {sample_id}",
        max_tokens=2048,
    )
    # Force identifying fields — the model doesn't need to remember them.
    assessment.control = control.name
    assessment.sample_id = sample_id
    assessment.attribute_id = attribute.id
    assessment.attribute_text = attribute.text
    return assessment, meta
