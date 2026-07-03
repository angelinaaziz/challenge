"""Schemas for the whole pipeline. Everything the model produces is Pydantic-validated
so the audit trail is machine-checkable, not a vibes summary."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Literal, Optional

from pydantic import BaseModel, Field


class Verdict(str, Enum):
    SUCCESS = "SUCCESS"
    FAIL = "FAIL"
    FURTHER_EVIDENCE_REQUIRED = "FURTHER_EVIDENCE_REQUIRED"


# --- Control definition (parsed from control.md + policy files) --------------

class ControlAttribute(BaseModel):
    id: str = Field(description="Short slug, kebab-case.")
    text: str = Field(description="Verbatim attribute text from control.md.")
    testable_criteria: list[str] = Field(
        description=(
            "Concrete, decidable sub-criteria a reperformer must check to judge this attribute. "
            "Derived from the attribute plus any policy documents in scope."
        )
    )
    relevant_policies: list[str] = Field(
        default_factory=list,
        description="Names of policy documents that inform this attribute (e.g. testing-policy.md).",
    )


class Control(BaseModel):
    name: str
    description: str
    attributes: list[ControlAttribute]
    policies: dict[str, str] = Field(
        default_factory=dict,
        description="filename → full text of any policy documents shipped with the control.",
    )


# --- Evidence + extraction ---------------------------------------------------

class EvidenceFile(BaseModel):
    path: str
    kind: Literal["screenshot", "xlsx", "pdf", "markdown", "text", "other"]
    bytes_size: int


class EvidenceRef(BaseModel):
    """A citation back to a specific place in a specific evidence file. Non-empty in all verdicts."""
    file: str
    locator: str = Field(
        description=(
            "Where in the file. For screenshots: describe the region (e.g. 'Merge status bar', "
            "'Reviewers panel'). For xlsx: sheet + cell range (e.g. 'Access Review!E13'). "
            "For markdown: heading or line hint."
        )
    )
    observation: str = Field(
        description="What was observed at that locator, in the auditor's own words."
    )


class PolicyReference(BaseModel):
    """A citation into a policy document."""
    source: str = Field(description="Policy filename.")
    section: str
    quote: str


# --- Extracted facts per evidence type ---------------------------------------

class ScreenshotFacts(BaseModel):
    """Structured facts extracted from a single screenshot by a vision model."""
    file: str
    inferred_type: str = Field(
        description=(
            "e.g. 'GitHub PR page', 'GitHub commit page', 'CI workflow run', "
            "'Coverage report dashboard', 'Sign-off ticket', 'Unknown'."
        )
    )
    key_facts: list[str] = Field(
        description=(
            "Verbatim, quotable facts a reperformer would want. "
            "Prefer facts with numbers, dates, usernames, statuses."
        )
    )
    people_mentioned: list[dict[str, str]] = Field(
        default_factory=list,
        description="[{name, role: 'author'|'reviewer'|'committer'|'commenter'|'other'}]",
    )
    timestamps_visible: list[str] = Field(default_factory=list)
    numeric_metrics: dict[str, str] = Field(
        default_factory=dict,
        description="Key metric name → value string (e.g. 'branch_coverage_pct': '44.62%').",
    )
    ambiguities: list[str] = Field(
        default_factory=list,
        description="Anything the model couldn't clearly read or which is ambiguous.",
    )


class XlsxSheetSummary(BaseModel):
    name: str
    row_count: int
    col_count: int
    headers: list[str]
    sample_rows: list[dict[str, str]] = Field(
        default_factory=list, description="Up to 5 example rows as {col_header: value_str}."
    )


class XlsxFacts(BaseModel):
    file: str
    sheets: list[XlsxSheetSummary]


class TextEvidence(BaseModel):
    """A plain text or markdown evidence file. Small enough to include verbatim."""
    file: str
    content: str


# --- The judgment output — the thing Bead actually asked for -----------------

class AttributeAssessment(BaseModel):
    control: str
    sample_id: str
    attribute_id: str
    attribute_text: str
    verdict: Verdict
    confidence: float = Field(ge=0.0, le=1.0)
    rationale: str = Field(
        description=(
            "Short, plain-English explanation. Reference specific facts. "
            "If FURTHER_EVIDENCE_REQUIRED, explicitly state what evidence would resolve it."
        )
    )
    policy_references: list[PolicyReference] = Field(
        default_factory=list,
        description="Policy citations if any policy document constrains this attribute.",
    )
    evidence_refs: list[EvidenceRef] = Field(
        min_length=1,
        description="Non-empty. Citations back to specific evidence files/regions supporting the verdict.",
    )
    exceptions_considered: list[str] = Field(
        default_factory=list,
        description="Any policy exceptions or edge cases the judge explicitly considered.",
    )


class SampleAssessment(BaseModel):
    control: str
    sample_id: str
    generated_at: datetime
    model: str
    attributes: list[AttributeAssessment]
    reperformance_notes: Optional[str] = Field(
        default=None,
        description=(
            "For controls that require reperformance (e.g. UAR), a short summary of what "
            "the deterministic re-check found — separate from the LLM's per-attribute reasoning."
        ),
    )


# --- Trace records for reproducibility ---------------------------------------

class LLMCall(BaseModel):
    ts: datetime
    provider: str
    model: str
    purpose: str
    input_tokens: Optional[int] = None
    output_tokens: Optional[int] = None
    latency_ms: Optional[int] = None
    system_hash: str = Field(description="sha256 of the system prompt.")
    user_hash: str = Field(description="sha256 of the user prompt (excluding images).")
    output_summary: str = Field(description="Compact summary of what came back.")
