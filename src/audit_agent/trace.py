"""Trace logging. Every LLM call is written to a JSONL file so an auditor can reproduce
the reasoning path deterministically (given the same evidence + prompts)."""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from audit_agent.pricing import call_cost_usd
from audit_agent.schemas import LLMCall


class Tracer:
    def __init__(self, path: Path):
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        # Truncate at construction so each run gets a clean trace.
        self.path.write_text("")
        # Running totals so the CLI summary can print a headline cost + cache-hit rate.
        self.total_cost_usd = 0.0
        self.total_input = 0
        self.total_output = 0
        self.total_cache_read = 0
        self.total_cache_write = 0
        self.call_count = 0

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
        input_t = meta.get("input_tokens") or 0
        output_t = meta.get("output_tokens") or 0
        cache_r = meta.get("cache_read_tokens") or 0
        cache_w = meta.get("cache_write_tokens") or 0
        cost = call_cost_usd(
            provider=provider,
            model=model,
            input_tokens=input_t,
            output_tokens=output_t,
            cache_read_tokens=cache_r,
            cache_write_tokens=cache_w,
        )
        self.total_cost_usd += cost
        self.total_input += input_t
        self.total_output += output_t
        self.total_cache_read += cache_r
        self.total_cache_write += cache_w
        self.call_count += 1

        rec = LLMCall(
            ts=datetime.now(timezone.utc),
            provider=provider,
            model=model,
            purpose=purpose,
            input_tokens=input_t,
            output_tokens=output_t,
            cache_read_tokens=cache_r,
            cache_write_tokens=cache_w,
            cost_usd=cost,
            latency_ms=meta.get("latency_ms"),
            system_hash=_h(system),
            user_hash=_h(user_text),
            output_summary=output_summary[:400],
        )
        with self.path.open("a") as f:
            f.write(rec.model_dump_json() + "\n")

    def summary_line(self) -> str:
        """Compact cost + cache-hit summary for the CLI."""
        cached_input = self.total_cache_read
        billed_input = self.total_input
        cache_hit_rate = (cached_input / billed_input * 100) if billed_input else 0.0
        return (
            f"${self.total_cost_usd:.4f} · {self.call_count} calls · "
            f"{self.total_input:,} input / {self.total_output:,} output tokens · "
            f"cache-read {self.total_cache_read:,} tokens ({cache_hit_rate:.0f}% of input)"
        )


def _h(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()[:16]
