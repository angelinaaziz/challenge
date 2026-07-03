"""Provider-agnostic LLM interface.

Design goals:
- One call shape: complete_structured(system, messages, schema) -> BaseModel.
- Content parts are provider-agnostic (text or image bytes); each provider translates.
- No streaming — audit output is deterministic-final, not chat.
- Errors surface as exceptions; the caller decides retry policy.
"""

from __future__ import annotations

import base64
from dataclasses import dataclass, field
from typing import Any, Protocol, TypeVar

from pydantic import BaseModel

TModel = TypeVar("TModel", bound=BaseModel)


@dataclass
class TextPart:
    text: str


@dataclass
class ImagePart:
    """PNG/JPEG bytes; the provider encodes to whatever format its SDK wants."""
    data: bytes
    media_type: str = "image/png"
    label: str | None = None  # optional caption prepended in text for context

    @classmethod
    def from_path(cls, path: str) -> "ImagePart":
        with open(path, "rb") as f:
            return cls(data=f.read(), media_type=_guess_media(path), label=path.split("/")[-1])

    def as_base64(self) -> str:
        return base64.b64encode(self.data).decode("ascii")


def _guess_media(path: str) -> str:
    lower = path.lower()
    if lower.endswith(".jpg") or lower.endswith(".jpeg"):
        return "image/jpeg"
    if lower.endswith(".webp"):
        return "image/webp"
    if lower.endswith(".gif"):
        return "image/gif"
    return "image/png"


@dataclass
class Message:
    role: str  # "user" | "assistant"
    parts: list[TextPart | ImagePart] = field(default_factory=list)


class LLMProvider(Protocol):
    """A provider knows how to run a structured completion."""

    name: str  # short identifier: "claude" | "openai" | "gemini"
    model: str  # concrete model id

    def complete_structured(
        self,
        system: str,
        messages: list[Message],
        schema: type[TModel],
        purpose: str,
        max_tokens: int = 4096,
    ) -> tuple[TModel, dict[str, Any]]:
        """Return (parsed_output, metadata). metadata has token counts + latency_ms."""
        ...


def make_provider(name: str) -> LLMProvider:
    """Factory. `name` in {"claude", "openai", "gemini"}."""
    # Auto-load .env so ad-hoc scripts + notebooks work without extra setup.
    from dotenv import load_dotenv
    load_dotenv()
    if name == "claude":
        from audit_agent.llm.anthropic_provider import AnthropicProvider
        return AnthropicProvider()
    if name == "openai":
        from audit_agent.llm.openai_provider import OpenAIProvider
        return OpenAIProvider()
    if name == "gemini":
        from audit_agent.llm.gemini_provider import GeminiProvider
        return GeminiProvider()
    raise ValueError(f"Unknown provider: {name!r}. Use one of: claude, openai, gemini.")
