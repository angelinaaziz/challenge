"""Load a control from a directory: control.md + any *policy*.md siblings.

The control is passed to the LLM once to be re-expressed as structured criteria — this
means the same code handles any new control the challenge hands us, without prompting
Bead's specific controls into the extraction step."""

from __future__ import annotations

import hashlib
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

    # Cache the parsed control on disk keyed by content hash. Rerunning the
    # same audit shouldn't burn an LLM call to re-parse an unchanged control,
    # and it makes the pipeline resilient to the ~1/20 Claude tool_use flake
    # where the initial extraction returns an empty payload.
    system = _read_prompt()
    body = ["# control.md\n\n", control_md]
    if policies:
        body.append("\n\n# Policy documents\n")
        for name, text in policies.items():
            body.append(f"\n## {name}\n\n{text}\n")
    user_text = "".join(body)

    cache_key = hashlib.sha256(
        (system + user_text + provider.name + provider.model).encode()
    ).hexdigest()[:16]
    cache_path = control_dir / f".control-cache-{cache_key}.json"
    if cache_path.exists():
        parsed = Control.model_validate_json(cache_path.read_text())
        parsed.policies = policies
        return parsed

    parsed, _meta = provider.complete_structured(
        system=system,
        messages=[Message(role="user", parts=[TextPart(text=user_text)])],
        schema=Control,
        purpose="Extract structured Control from control.md + policy docs",
        max_tokens=8192,
    )
    parsed.policies = policies
    # Write cache without the raw policy text (kept in-memory) — smaller file,
    # cache invalidates naturally if the control.md or prompt changes.
    to_cache = parsed.model_copy(update={"policies": {}})
    cache_path.write_text(to_cache.model_dump_json(indent=2))
    return parsed
