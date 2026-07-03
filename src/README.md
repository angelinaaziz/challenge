# Setup

## Prerequisites
- Python ≥ 3.11 (tested on 3.13)
- [`uv`](https://docs.astral.sh/uv/) — `curl -LsSf https://astral.sh/uv/install.sh | sh`
- An Anthropic API key (required). OpenAI + Google API keys (optional, only for multi-model eval).

## Install

```bash
uv venv --python 3.13
source .venv/bin/activate
uv pip install -e .
```

## Configure

```bash
cp ../.env.example ../.env    # from repo root
# Fill in ANTHROPIC_API_KEY (required)
# OPENAI_API_KEY + GOOGLE_API_KEY (optional — only needed for multi-model eval)
```

## Run

```bash
# Audit a single control with Claude Opus 4.7
bead-agent audit ../data/independent-code-review --model claude
bead-agent audit ../data/user-access-review --model claude
bead-agent audit ../data/change-management --model claude

# Swap models
bead-agent audit ../data/independent-code-review --model openai
bead-agent audit ../data/independent-code-review --model gemini

# Score all three models against the hand-labeled golden set
bead-agent eval ../data/independent-code-review --models claude,openai,gemini

# Skip the FURTHER_EVIDENCE_REQUIRED verifier pass (faster; useful for eval sweeps)
bead-agent audit ../data/independent-code-review --model claude --no-verify
```

Outputs land in `output/<control>/<model>/<sample>/`:
- `assessment.json` — structured verdicts (Bead's requested format)
- `assessment.md` — human-readable workpaper
- Plus `control.json` (parsed control spec) and `trace.jsonl` (every LLM call, hashed)

See the top-level [README](../README.md) for the full architecture, model scoreboard, and design write-up.
