"""OpenAI provider — via the Responses API with strict JSON schema."""

from __future__ import annotations

import json
import os
import time
from typing import Any, TypeVar

from openai import OpenAI
from pydantic import BaseModel

from audit_agent.llm.base import ImagePart, Message, TextPart
from audit_agent.llm.retry import with_retry

TModel = TypeVar("TModel", bound=BaseModel)


class OpenAIProvider:
    name = "openai"

    def __init__(self, model: str | None = None):
        self.model = model or os.environ.get("OPENAI_MODEL", "gpt-5.4")
        self.client = OpenAI()

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
        oai_messages = [{"role": "system", "content": system}]
        for m in messages:
            oai_messages.append(_to_openai_msg(m))

        t0 = time.monotonic()
        # Use chat.completions with json_schema response_format — works cross-model reliably.
        json_schema = schema.model_json_schema()
        resp = self.client.chat.completions.create(
            model=self.model,
            max_completion_tokens=max_tokens,
            messages=oai_messages,
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "name": schema.__name__,
                    "schema": _sanitize_json_schema(json_schema),
                    "strict": False,
                },
            },
        )
        latency_ms = int((time.monotonic() - t0) * 1000)
        text = resp.choices[0].message.content or "{}"
        payload = json.loads(text)
        parsed = schema.model_validate(payload)
        meta = {
            "provider": self.name,
            "model": self.model,
            "input_tokens": getattr(resp.usage, "prompt_tokens", None),
            "output_tokens": getattr(resp.usage, "completion_tokens", None),
            "latency_ms": latency_ms,
        }
        return parsed, meta


def _to_openai_msg(m: Message) -> dict:
    content: list[dict] = []
    for part in m.parts:
        if isinstance(part, TextPart):
            content.append({"type": "text", "text": part.text})
        elif isinstance(part, ImagePart):
            if part.label:
                content.append({"type": "text", "text": f"[image: {part.label}]"})
            content.append(
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:{part.media_type};base64,{part.as_base64()}",
                    },
                }
            )
    return {"role": m.role, "content": content}


def _sanitize_json_schema(s: dict) -> dict:
    """OpenAI's json_schema mode dislikes some pydantic-generated constructs.
    We shallow-clean: drop 'default', drop 'title', ensure objects have additionalProperties=False."""
    def clean(node):
        if isinstance(node, dict):
            node = {k: v for k, v in node.items() if k not in ("title", "default")}
            if node.get("type") == "object" and "additionalProperties" not in node:
                node["additionalProperties"] = False
            return {k: clean(v) for k, v in node.items()}
        if isinstance(node, list):
            return [clean(x) for x in node]
        return node
    return clean(s)
