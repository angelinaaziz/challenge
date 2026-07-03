"""Shared retry policy for LLM calls.

Retries transient failures (429, 503, timeout, empty payload, JSON validation
that indicates a truncated response). Does NOT retry client errors (400s,
authentication, unrecoverable schema mismatches) — that would waste time and
tokens on something a retry can't fix.
"""

from __future__ import annotations

import logging
from typing import Any, Callable, TypeVar

from pydantic import ValidationError
from tenacity import (
    RetryCallState,
    Retrying,
    retry_if_exception,
    stop_after_attempt,
    wait_exponential_jitter,
)

T = TypeVar("T")

_LOG = logging.getLogger("audit_agent.retry")


def _is_transient(exc: BaseException) -> bool:
    """Classify errors as transient (retry) vs fatal (fail-fast)."""
    name = type(exc).__name__
    # Common transient markers across SDKs.
    if name in {
        "APITimeoutError",
        "APIConnectionError",
        "InternalServerError",
        "ServiceUnavailableError",
        "RateLimitError",
    }:
        return True
    if isinstance(exc, ValidationError):
        # Validation errors caused by truncated/empty structured output are
        # often flakes — one more attempt often clears them.
        return True
    # Some SDKs raise a generic APIError with a status_code attribute.
    code = getattr(exc, "status_code", None)
    if code in (429, 500, 502, 503, 504):
        return True
    # Empty-payload sentinel from providers (raised as ValueError with our msg).
    if isinstance(exc, ValueError) and "empty" in str(exc).lower():
        return True
    return False


def _log_attempt(state: RetryCallState) -> None:
    if state.attempt_number > 1 and state.outcome and state.outcome.failed:
        exc = state.outcome.exception()
        _LOG.warning(
            "retry attempt %s: %s: %s",
            state.attempt_number,
            type(exc).__name__ if exc else "?",
            str(exc)[:120] if exc else "",
        )


def with_retry(fn: Callable[..., T], *args: Any, max_attempts: int = 3, **kwargs: Any) -> T:
    """Call fn(*args, **kwargs) with retry on transient failures."""
    for attempt in Retrying(
        stop=stop_after_attempt(max_attempts),
        wait=wait_exponential_jitter(initial=1, max=8),
        retry=retry_if_exception(_is_transient),
        reraise=True,
        after=_log_attempt,
    ):
        with attempt:
            return fn(*args, **kwargs)
    # Unreachable — Retrying will either return or reraise.
    raise RuntimeError("with_retry exited without a result")
