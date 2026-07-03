# Setup

## Prerequisites
- Python 3.11 or later (tested on 3.13)
- [`uv`](https://docs.astral.sh/uv/) via `curl -LsSf https://astral.sh/uv/install.sh | sh`
- An Anthropic API key (required). OpenAI and Google API keys are optional, only needed for multi-model eval.

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
# OPENAI_API_KEY + GOOGLE_API_KEY are optional (needed for multi-model eval)
```

## Run

```bash
# Audit a single control. Auto-opens the HTML report when done.
bead-agent audit ../data/independent-code-review
bead-agent audit ../data/user-access-review
bead-agent audit ../data/change-management

# Swap models
bead-agent audit ../data/independent-code-review --model openai
bead-agent audit ../data/independent-code-review --model gemini

# Peek at a control without spending API credit
bead-agent info ../data/user-access-review

# Score all three models against the hand-labelled golden set
bead-agent eval ../data/independent-code-review --models claude,openai,gemini

# Skip the FURTHER_EVIDENCE_REQUIRED verifier pass (useful for eval sweeps)
bead-agent audit ../data/independent-code-review --no-verify

# Regenerate the HTML report + Excel workpaper for a past run
bead-agent report output/user-access-review/claude

# Pretty-print a past assessment.json in the terminal
bead-agent show output/user-access-review/claude/sample-1/assessment.json
```

Outputs land in `output/<control>/<model>/`:
- `report.html` is the Bead-themed HTML report (auto-opens on `audit`)
- `<sample>/assessment.json` holds the structured verdicts (Bead's requested format)
- `<sample>/assessment.md` is the readable workpaper
- `<sample>/workpaper.xlsx` is the native Excel workpaper
- `control.json` has the parsed control spec, and `trace.jsonl` logs every LLM call, hashed

Run the tests and linter:

```bash
uv pip install pytest ruff
pytest tests/ -v
ruff check src/ tests/
```

See the top-level [README](../README.md) for the architecture, model scoreboard, and design write-up.
