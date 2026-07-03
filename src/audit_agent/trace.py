"""Trace logging. Every LLM call is written to a JSONL file so an auditor can reproduce
the reasoning path deterministically (given the same evidence + prompts)."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from audit_agent.schemas import LLMCall


class Tracer:
    def __init__(self, path: Path):
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        # Truncate at construction so each run gets a clean trace.
        self.path.write_text("")

    def log(
        self,
        *,
        provider: str,
        model: str,
        purpose: str,
        system: str,
        user_text: str,
        meta: dict[str, Any],
        output_summary: str,
    ) -> None:
        rec = LLMCall(
            ts=datetime.now(timezone.utc),
            provider=provider,
            model=model,
            purpose=purpose,
            input_tokens=meta.get("input_tokens"),
            output_tokens=meta.get("output_tokens"),
            latency_ms=meta.get("latency_ms"),
            system_hash=_h(system),
            user_hash=_h(user_text),
            output_summary=output_summary[:400],
        )
        with self.path.open("a") as f:
            f.write(rec.model_dump_json() + "\n")


def _h(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()[:16]
