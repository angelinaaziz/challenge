"""Second-pass verification for FURTHER_EVIDENCE_REQUIRED verdicts.

A first-pass hedged verdict often means either (a) genuine ambiguity or (b)
first-pass timidity. We re-ask with a fresh prompt to distinguish the two.
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
    Verdict,
    XlsxFacts,
)


PROMPT_FILE = Path(__file__).parent.parent / "prompts" / "verifier.md"


def _read_prompt() -> str:
    return PROMPT_FILE.read_text()


def verify_attribute(
    first_pass: AttributeAssessment,
    control: Control,
    attribute: ControlAttribute,
    sample_id: str,
    screenshots: list[ScreenshotFacts],
    xlsx: list[XlsxFacts],
    text_evidence: list[TextEvidence],
    reconciliation: Optional[dict[str, Any]],
    provider: LLMProvider,
) -> tuple[AttributeAssessment, dict[str, Any]]:
    if first_pass.verdict != Verdict.FURTHER_EVIDENCE_REQUIRED:
        return first_pass, {"skipped": True}

    system = _read_prompt()
    user_text = (
        f"# Attribute under review\n\n**{attribute.text}**\n\n"
        f"Testable criteria:\n" + "\n".join(f"- {c}" for c in attribute.testable_criteria) + "\n\n"
        f"# First-pass verdict (which was FURTHER_EVIDENCE_REQUIRED)\n\n"
        + json.dumps(first_pass.model_dump(), indent=2, default=str)
        + "\n\n"
        f"# Evidence (same as before — re-read carefully)\n\n"
        + _facts_block(screenshots, xlsx, text_evidence, reconciliation)
    )
    assessment, meta = provider.complete_structured(
        system=system,
        messages=[Message(role="user", parts=[TextPart(text=user_text)])],
        schema=AttributeAssessment,
        purpose=f"Verify {attribute.id} on {sample_id}",
        max_tokens=2048,
    )
    assessment.control = control.name
    assessment.sample_id = sample_id
    assessment.attribute_id = attribute.id
    assessment.attribute_text = attribute.text
    return assessment, meta


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
        parts.append("## Deterministic reperformance")
        parts.append(json.dumps(reconciliation, indent=2, default=str))
    return "\n\n".join(parts)
