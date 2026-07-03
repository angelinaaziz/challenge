# AGENTS.md

Notes for coding agents (Claude Code, Cursor, Codex, etc.) working in this repo.

## Repo shape

- `src/audit_agent/` — the pipeline. Pure Python 3.13, Pydantic schemas, one `LLMProvider` Protocol with three concrete providers (Claude, OpenAI, Gemini).
- `src/audit_agent/prompts/*.md` — every prompt lives as a versioned file. If you touch one, note it in the commit body.
- `tests/` — 18 pytest tests around the reconciler + narrative builder + IPE validator. Zero of them hit an API.
- `evals/golden.jsonl` — hand-labelled ground truth for the LLM-path behavioural tests. Run via `bead-agent eval`, which does call APIs.
- `data/` — three controls (two Bead-provided + one synthetic). Upstream files preserved from the fork parent.
- `output/` — committed model outputs; regenerate with `bead-agent report <run-dir>`.

## Before running anything

- Copy `.env.example` → `.env` and fill in `ANTHROPIC_API_KEY` (required for `--model claude`, the default).
- `OPENAI_API_KEY` + `GOOGLE_API_KEY` are only needed for `bead-agent eval` with multiple providers.
- Every LLM call costs money. **Run `pytest tests/`** for feedback that doesn't hit the API. Only run `bead-agent audit` when you actually need fresh model output.

## Golden-set + tests contract

- `pytest tests/` must stay green. It's zero-cost — every fixture is an in-memory openpyxl workbook.
- `bead-agent eval data/<control>` runs the LLM pipeline against `evals/golden.jsonl`. This DOES cost money (roughly $1–3 per full run with prompt caching).
- If you tune a prompt, note the expected verdict shift in the commit body and re-run the affected control to verify.

## Prompt-editing conventions

- Every prompt file starts with a `# Role` block, followed by `# Task` and `# Guidance`.
- Worked examples live in a `# Worked examples — the reasoning shape I expect` section at the bottom.
- Keep bullets terse; the model is reading these too.
- If you change a prompt, run at least one control end-to-end to confirm no regression in verdict quality.

## Provider swap

- Model IDs are env-configurable (`CLAUDE_MODEL`, `OPENAI_MODEL`, `GEMINI_MODEL`). Change `.env`, no code touched.
- New provider? Copy `llm/anthropic_provider.py` shape into `llm/<name>_provider.py`, wire in `llm/base.py::make_provider`. Match the `LLMProvider` Protocol; the rest of the pipeline is provider-agnostic.

## Local runs — cost + safety

- Auto-open the HTML report is on by default. Pass `--no-open` in CI / headless environments.
- Prompt caching is on for Anthropic — subsequent runs of the same control burn ~20% of the input tokens they otherwise would.
- Control cache lives at `data/<control>/.control-cache-<hash>.json` — gitignored, keyed by (control_md + system_prompt + provider + model). Delete it if you want to force a re-parse.

## Do NOT

- Commit anything under `.env` (secrets) or `output/**/trace.jsonl` (both gitignored).
- Break the `assessment.json` schema without also updating the HTML report + Excel workpaper writers that read from it.
- Skip `evidence_refs` in a verdict — the Pydantic schema enforces `min_length=1` for a reason.
