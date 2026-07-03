"""Walk a sample directory, classify every file, group into an EvidenceBundle."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from audit_agent.schemas import EvidenceFile

SCREENSHOT_EXTS = {".png", ".jpg", ".jpeg", ".webp"}
XLSX_EXTS = {".xlsx"}
PDF_EXTS = {".pdf"}
MARKDOWN_EXTS = {".md"}
TEXT_EXTS = {".txt", ".log"}


def _kind(path: Path) -> str:
    ext = path.suffix.lower()
    if ext in SCREENSHOT_EXTS:
        return "screenshot"
    if ext in XLSX_EXTS:
        return "xlsx"
    if ext in PDF_EXTS:
        return "pdf"
    if ext in MARKDOWN_EXTS:
        return "markdown"
    if ext in TEXT_EXTS:
        return "text"
    return "other"


@dataclass
class EvidenceBundle:
    sample_id: str
    sample_dir: Path
    files: list[EvidenceFile]

    @property
    def screenshots(self) -> list[EvidenceFile]:
        return [f for f in self.files if f.kind == "screenshot"]

    @property
    def workbooks(self) -> list[EvidenceFile]:
        return [f for f in self.files if f.kind == "xlsx"]


def classify_sample(sample_dir: Path, sample_id: str | None = None) -> EvidenceBundle:
    """Return an EvidenceBundle for a single sample.

    A "sample" is either a folder under samples/ (Independent Code Review shape) or the
    top-level control directory itself when the evidence is the two xlsx workbooks
    sitting next to control.md (User Access Review shape).
    """
    sid = sample_id or sample_dir.name
    files: list[EvidenceFile] = []
    for p in sorted(sample_dir.iterdir()):
        if p.is_file() and not p.name.startswith("."):
            # Skip the control/policy markdowns themselves — they're not evidence.
            if p.name in {"control.md", "testing-policy.md"} or p.name.startswith("policy"):
                continue
            files.append(
                EvidenceFile(path=str(p), kind=_kind(p), bytes_size=p.stat().st_size)
            )
    return EvidenceBundle(sample_id=sid, sample_dir=sample_dir, files=files)


def discover_samples(control_dir: Path) -> list[EvidenceBundle]:
    """Find all samples in a control directory, supporting both shapes:

    Shape A (Independent Code Review):
        control_dir/
            control.md
            testing-policy.md
            samples/
                sample-1/  *.png
                sample-2/  *.png

    Shape B (User Access Review):
        control_dir/
            control.md
            uar-*.xlsx
            hris-*.xlsx
    """
    samples_dir = control_dir / "samples"
    if samples_dir.is_dir():
        bundles = []
        for sub in sorted(samples_dir.iterdir()):
            if sub.is_dir():
                bundles.append(classify_sample(sub))
        return bundles
    # No samples/ subdir → the control dir itself is the single sample.
    return [classify_sample(control_dir, sample_id="sample-1")]
