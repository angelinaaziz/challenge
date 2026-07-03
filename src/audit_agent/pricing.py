"""Model pricing as of mid-2026. USD per 1M tokens.

Numbers here are order-of-magnitude — the point isn't to be a billing service,
it's to make the caching win visible in the CLI summary. Update from the
vendors' pricing pages when they change.
"""

from __future__ import annotations

# provider:model → {input, cache_read, cache_write, output} USD per 1M tokens
_PRICES: dict[str, dict[str, float]] = {
    "claude:claude-opus-4-7": {
        "input": 15.00,
        "cache_read": 1.50,          # 10% of input, standard Anthropic ratio
        "cache_write": 18.75,        # 1.25x input, standard 5-min ephemeral rate
        "output": 75.00,
    },
    "openai:gpt-5.4": {
        "input": 10.00,
        "cache_read": 5.00,
        "cache_write": 10.00,
        "output": 30.00,
    },
    "gemini:gemini-3.1-pro-preview": {
        "input": 1.25,
        "cache_read": 0.31,
        "cache_write": 1.25,
        "output": 5.00,
    },
}


def price_per_million(provider: str, model: str) -> dict[str, float]:
    key = f"{provider}:{model}"
    return _PRICES.get(key, {"input": 0.0, "cache_read": 0.0, "cache_write": 0.0, "output": 0.0})


def call_cost_usd(
    provider: str,
    model: str,
    input_tokens: int = 0,
    output_tokens: int = 0,
    cache_read_tokens: int = 0,
    cache_write_tokens: int = 0,
) -> float:
    """Approximate cost of a single call in USD.

    input_tokens is the *non-cached* input token count (Anthropic reports this
    as-is; cache_read + cache_write are separate line items).
    """
    p = price_per_million(provider, model)
    return (
        (input_tokens - cache_read_tokens - cache_write_tokens) * p["input"]
        + cache_read_tokens * p["cache_read"]
        + cache_write_tokens * p["cache_write"]
        + output_tokens * p["output"]
    ) / 1_000_000
