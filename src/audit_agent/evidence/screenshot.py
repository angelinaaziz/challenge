"""Vision-based fact extraction from screenshots."""

from __future__ import annotations

from pathlib import Path

from audit_agent.llm import ImagePart, LLMProvider, Message, TextPart
from audit_agent.schemas import ScreenshotFacts


PROMPT_FILE = Path(__file__).parent.parent / "prompts" / "screenshot_extraction.md"


def _read_prompt() -> str:
    return PROMPT_FILE.read_text()


def extract_screenshot_facts(
    image_path: Path,
    control_name: str,
    control_description: str,
    provider: LLMProvider,
) -> tuple[ScreenshotFacts, dict]:
    system = _read_prompt()
    context = (
        f"# Control context (for orientation only — do not judge the control here)\n\n"
        f"Control: {control_name}\n\n"
        f"{control_description}\n"
    )
    user = Message(
        role="user",
        parts=[
            TextPart(text=context),
            ImagePart.from_path(str(image_path)),
        ],
    )
    facts, meta = provider.complete_structured(
        system=system,
        messages=[user],
        schema=ScreenshotFacts,
        purpose=f"Extract facts from {image_path.name}",
        max_tokens=6144,
    )
    facts.file = image_path.name
    return facts, meta
