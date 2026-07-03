"""Load a control from a directory: control.md + any *policy*.md siblings.

The control is passed to the LLM once to be re-expressed as structured criteria — this
means the same code handles any new control the challenge hands us, without prompting
Bead's specific controls into the extraction step."""

from __future__ import annotations

from pathlib import Path

from audit_agent.llm import LLMProvider, Message, TextPart
from audit_agent.schemas import Control


PROMPT_FILE = Path(__file__).parent.parent / "prompts" / "control_extraction.md"


def _read_prompt() -> str:
    return PROMPT_FILE.read_text()


def load_control(control_dir: Path, provider: LLMProvider) -> Control:
    """Read control.md + adjacent *.md policy files, and return a structured Control.

    Any markdown file that isn't `control.md` is treated as a policy document.
    """
    control_md_path = control_dir / "control.md"
    if not control_md_path.exists():
        raise FileNotFoundError(f"Missing control.md in {control_dir}")

    control_md = control_md_path.read_text()

    policies: dict[str, str] = {}
    for md in control_dir.glob("*.md"):
        if md.name == "control.md":
            continue
        policies[md.name] = md.read_text()

    system = _read_prompt()
    body = ["# control.md\n\n", control_md]
    if policies:
        body.append("\n\n# Policy documents\n")
        for name, text in policies.items():
            body.append(f"\n## {name}\n\n{text}\n")
    user_text = "".join(body)

    parsed, _meta = provider.complete_structured(
        system=system,
        messages=[Message(role="user", parts=[TextPart(text=user_text)])],
        schema=Control,
        purpose="Extract structured Control from control.md + policy docs",
        max_tokens=8192,
    )
    # Ensure we keep the raw policy text on the Control for downstream citations.
    parsed.policies = policies
    return parsed
