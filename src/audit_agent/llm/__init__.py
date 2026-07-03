"""LLM provider abstraction. All prompts route through a single Protocol so the pipeline
can swap Claude Opus 4.7, GPT-5.4 and Gemini 3 Pro without touching the audit logic."""

from audit_agent.llm.base import (
    ImagePart,
    LLMProvider,
    Message,
    TextPart,
    make_provider,
)

__all__ = ["LLMProvider", "Message", "TextPart", "ImagePart", "make_provider"]
