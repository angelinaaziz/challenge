"""Gemini 3 Pro provider — via google-genai SDK with response schema."""

from __future__ import annotations

import json
import os
import time
from typing import Any, TypeVar

from google import genai
from google.genai import types
from pydantic import BaseModel

from audit_agent.llm.base import ImagePart, Message, TextPart

TModel = TypeVar("TModel", bound=BaseModel)


class GeminiProvider:
    name = "gemini"

    def __init__(self, model: str | None = None):
        self.model = model or os.environ.get("GEMINI_MODEL", "gemini-3-pro")
        api_key = os.environ.get("GOOGLE_API_KEY") or os.environ.get("GEMINI_API_KEY")
        self.client = genai.Client(api_key=api_key)

    def complete_structured(
        self,
        system: str,
        messages: list[Message],
        schema: type[TModel],
        purpose: str,
        max_tokens: int = 4096,
    ) -> tuple[TModel, dict[str, Any]]:
        contents = [_to_gemini_content(m) for m in messages]
        # Gemini Developer API rejects `additionalProperties`; strip it from the schema.
        gemini_schema = _strip_gemini_incompatible(schema.model_json_schema())
        # Gemini 3.x preview models often need generous headroom for structured output.
        budget = max(max_tokens * 2, 16384)

        t0 = time.monotonic()
        resp = self.client.models.generate_content(
            model=self.model,
            contents=contents,
            config=types.GenerateContentConfig(
                system_instruction=system,
                response_mime_type="application/json",
                response_json_schema=gemini_schema,
                max_output_tokens=budget,
            ),
        )
        latency_ms = int((time.monotonic() - t0) * 1000)
        text = resp.text or "{}"
        finish = None
        try:
            finish = resp.candidates[0].finish_reason
        except Exception:
            pass
        payload = _parse_json_lenient(text, finish)
        parsed = schema.model_validate(payload)
        usage = getattr(resp, "usage_metadata", None)
        meta = {
            "provider": self.name,
            "model": self.model,
            "input_tokens": getattr(usage, "prompt_token_count", None) if usage else None,
            "output_tokens": getattr(usage, "candidates_token_count", None) if usage else None,
            "latency_ms": latency_ms,
        }
        return parsed, meta


def _parse_json_lenient(text: str, finish_reason: Any) -> dict:
    """Try strict json.loads; on failure, attempt lightweight repair.

    Handles common Gemini truncation modes:
      - hit MAX_TOKENS → JSON cut off mid-string → close open structures.
      - stray trailing commas / missing quotes on the tail → strip trailing garbage.
    """
    text = text.strip()
    # Strip ```json ... ``` fences if present.
    if text.startswith("```"):
        text = text.strip("`")
        text = text.split("\n", 1)[-1] if text.startswith("json") else text
        if text.rstrip().endswith("```"):
            text = text.rstrip().rstrip("`").rstrip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    # Try progressive right-truncation until we hit a valid prefix, then close brackets.
    for cut in range(len(text), max(0, len(text) - 4000), -1):
        candidate = text[:cut]
        # Balance braces / brackets
        opens_c = candidate.count("{") - candidate.count("}")
        opens_b = candidate.count("[") - candidate.count("]")
        if opens_c < 0 or opens_b < 0:
            continue
        patched = candidate.rstrip().rstrip(",") + ("]" * opens_b) + ("}" * opens_c)
        try:
            return json.loads(patched)
        except json.JSONDecodeError:
            continue
    raise ValueError(
        f"Gemini returned unparseable JSON (finish_reason={finish_reason}). "
        f"First 300 chars: {text[:300]!r}"
    )


def _strip_gemini_incompatible(schema: dict) -> dict:
    """Gemini Developer API rejects `additionalProperties`, `title`, and `default`.
    Also drops `$defs` in favor of inlined refs (google-genai handles refs)."""
    BAD_KEYS = {"additionalProperties", "title", "default"}

    def clean(node):
        if isinstance(node, dict):
            return {k: clean(v) for k, v in node.items() if k not in BAD_KEYS}
        if isinstance(node, list):
            return [clean(x) for x in node]
        return node

    return clean(schema)


def _to_gemini_content(m: Message) -> types.Content:
    parts: list[types.Part] = []
    for p in m.parts:
        if isinstance(p, TextPart):
            parts.append(types.Part.from_text(text=p.text))
        elif isinstance(p, ImagePart):
            if p.label:
                parts.append(types.Part.from_text(text=f"[image: {p.label}]"))
            parts.append(types.Part.from_bytes(data=p.data, mime_type=p.media_type))
    role = "user" if m.role == "user" else "model"
    return types.Content(role=role, parts=parts)
