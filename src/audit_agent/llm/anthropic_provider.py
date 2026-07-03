"""Claude Opus 4.7 provider — via the Anthropic SDK's tool-forced structured output pattern."""

from __future__ import annotations

import json
import os
import time
from typing import Any, TypeVar

from anthropic import Anthropic
from pydantic import BaseModel

from audit_agent.llm.base import ImagePart, Message, TextPart
from audit_agent.llm.retry import with_retry

TModel = TypeVar("TModel", bound=BaseModel)


class AnthropicProvider:
    name = "claude"

    def __init__(self, model: str | None = None):
        self.model = model or os.environ.get("CLAUDE_MODEL", "claude-opus-4-7")
        self.client = Anthropic()  # picks up ANTHROPIC_API_KEY

    def complete_structured(
        self,
        system: str,
        messages: list[Message],
        schema: type[TModel],
        purpose: str,
        max_tokens: int = 4096,
    ) -> tuple[TModel, dict[str, Any]]:
        return with_retry(
            self._complete_once, system, messages, schema, purpose, max_tokens
        )

    def _complete_once(
        self,
        system: str,
        messages: list[Message],
        schema: type[TModel],
        purpose: str,
        max_tokens: int,
    ) -> tuple[TModel, dict[str, Any]]:
        # Force JSON output via a synthetic tool. Cross-provider abstraction here.
        tool_name = "record_output"
        json_schema = schema.model_json_schema()
        anthropic_messages = [_to_anthropic_msg(m) for m in messages]

        # Prompt caching: the system prompt + tool schema are identical across
        # every per-attribute call, so caching them cuts input token cost ~85%.
        # `cache_control: ephemeral` on the last block of a section marks the
        # cache breakpoint — everything from the start of that section up to
        # (and including) the breakpoint is cached for ~5 minutes.
        system_blocks = [
            {
                "type": "text",
                "text": system,
                "cache_control": {"type": "ephemeral"},
            }
        ]
        t0 = time.monotonic()
        resp = self.client.messages.create(
            model=self.model,
            system=system_blocks,
            max_tokens=max_tokens,
            # Tool description is deliberately purpose-free so identical judge
            # calls hit the cache. The per-call purpose ends up in the user
            # message, not baked into the cacheable tool schema.
            tools=[
                {
                    "name": tool_name,
                    "description": (
                        "Record the final structured output. "
                        "You MUST call this tool exactly once."
                    ),
                    "input_schema": json_schema,
                    "cache_control": {"type": "ephemeral"},
                }
            ],
            tool_choice={"type": "tool", "name": tool_name},
            messages=anthropic_messages,
        )
        latency_ms = int((time.monotonic() - t0) * 1000)

        payload = _extract_tool_input(resp, tool_name)
        # Some responses wrap the object in a single-key envelope like {"output": {...}}
        # when the model runs out of budget mid-structure. Unwrap defensively.
        if (
            isinstance(payload, dict)
            and len(payload) == 1
            and next(iter(payload.keys())) in {"output", "result", "value"}
        ):
            payload = next(iter(payload.values()))
        # Claude Opus 4.7 tool_use sometimes stringifies list/dict field values.
        # Recursively coerce any string that looks like JSON back into a real object.
        payload = _coerce_stringified_json(payload)
        # Fall back: if a top-level field is expected to be a list but came
        # back as a stray string (Claude sometimes returns XML-tagged content),
        # wrap it as a single-element list so validation passes rather than
        # losing the data entirely.
        payload = _coerce_field_shape(payload, schema)
        parsed = schema.model_validate(payload)

        usage = resp.usage
        meta = {
            "provider": self.name,
            "model": self.model,
            "input_tokens": getattr(usage, "input_tokens", None),
            "output_tokens": getattr(usage, "output_tokens", None),
            "cache_read_tokens": getattr(usage, "cache_read_input_tokens", 0) or 0,
            "cache_write_tokens": getattr(usage, "cache_creation_input_tokens", 0) or 0,
            "latency_ms": latency_ms,
        }
        return parsed, meta


def _coerce_field_shape(payload: dict, schema: type[BaseModel]) -> dict:
    """When a top-level field is expected as list/dict but arrived as a stray
    string (Claude Opus 4.7 sometimes leaks XML-tag-formatted content), coerce
    to a shape validation accepts, rather than losing the entire response.

    Preserves the model's content — better a raw-string list entry with a
    slightly-garbled first element than a hard failure.
    """
    import typing

    if not isinstance(payload, dict):
        return payload
    # Use pydantic's own model_fields which resolves `from __future__ import
    # annotations` string types back to the real generic.
    for field_name, field_info in schema.model_fields.items():
        if field_name not in payload:
            continue
        value = payload[field_name]
        ann = field_info.annotation
        origin = typing.get_origin(ann)
        if origin is list and not isinstance(value, list):
            payload[field_name] = [value] if value is not None else []
        elif origin is dict and isinstance(value, str):
            try:
                payload[field_name] = json.loads(value)
            except json.JSONDecodeError:
                payload[field_name] = {}
    return payload


def _coerce_stringified_json(node):
    """Walk a nested dict/list; parse any string that looks like a JSON list/object.
    Uses json-repair to handle Claude's occasional trailing commas / whitespace quirks."""
    from json_repair import repair_json

    if isinstance(node, str):
        s = node.strip().rstrip(",").strip()
        looks_json = (s.startswith("[") and "]" in s) or (s.startswith("{") and "}" in s)
        if looks_json:
            try:
                repaired = repair_json(s)
                parsed = json.loads(repaired)
                return _coerce_stringified_json(parsed)
            except Exception:
                return node
        return node
    if isinstance(node, list):
        return [_coerce_stringified_json(x) for x in node]
    if isinstance(node, dict):
        return {k: _coerce_stringified_json(v) for k, v in node.items()}
    return node


def _to_anthropic_msg(m: Message) -> dict:
    content: list[dict] = []
    for part in m.parts:
        if isinstance(part, TextPart):
            content.append({"type": "text", "text": part.text})
        elif isinstance(part, ImagePart):
            if part.label:
                content.append({"type": "text", "text": f"[image: {part.label}]"})
            content.append(
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": part.media_type,
                        "data": part.as_base64(),
                    },
                }
            )
    return {"role": m.role, "content": content}


def _extract_tool_input(resp, tool_name: str) -> dict:
    for block in resp.content:
        if getattr(block, "type", None) == "tool_use" and block.name == tool_name:
            return block.input  # already a dict
    # Some SDK responses may still stream text — fall back
    text_bits = [b.text for b in resp.content if getattr(b, "type", None) == "text"]
    if text_bits:
        return json.loads("\n".join(text_bits))
    raise RuntimeError(f"Anthropic response missing tool_use for {tool_name!r}")
