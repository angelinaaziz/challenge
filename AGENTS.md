# AGENTS.md

Notes for coding agents (Claude Code, Cursor, Codex) working in this repo.

## Repo shape

- `src/audit_agent/` is the pipeline. Python 3.13, Pydantic schemas, one `LLMProvider` Protocol with three concrete providers (Claude, OpenAI, Gemini).
- `src/audit_agent/prompts/*.md` is where every prompt lives. Versioned. If you touch one, note it in the commit body.
- `tests/` has 18 pytest tests around the reconciler, narrative builder, and IPE validator. None of them hit an API.
- `evals/golden.jsonl` is the hand-labelled ground truth for the LLM-path behavioural tests. Run via `bead-agent eval`, which does call APIs.
- `data/` holds the three controls. Two are Bead-provided, one is synthetic. Upstream files are preserved from the fork parent.
- `output/` has committed model outputs. Regenerate with `bead-agent report <run-dir>`.

## Before running anything

Copy `.env.example` to `.env` and fill in `ANTHROPIC_API_KEY` (required, the default model is Claude).

`OPENAI_API_KEY` and `GOOGLE_API_KEY` are only needed when you run `bead-agent eval` with multiple providers.

Every LLM call costs money. `pytest tests/` gives you feedback that doesn't hit the API. Only run `bead-agent audit` when you need fresh model output.

## Golden set and tests contract

`pytest tests/` must stay green. It's zero-cost because every fixture is an in-memory openpyxl workbook.

`bead-agent eval data/<control>` runs the LLM pipeline against `evals/golden.jsonl`. This does cost money (roughly $1 to $3 per full run with prompt caching).

If you tune a prompt, note the expected verdict shift in the commit body, then re-run the affected control to verify.

## Prompt-editing conventions

Every prompt file starts with a `# Role` block, then `# Task`, then `# Guidance`.

Worked examples live in a `# Worked examples` section at the bottom.

Keep bullets terse. The model is reading these too.

If you change a prompt, run at least one control end-to-end to confirm no regression in verdict quality.

## Provider swap

Model IDs are env-configurable (`CLAUDE_MODEL`, `OPENAI_MODEL`, `GEMINI_MODEL`). Change `.env`, no code touched.

Adding a new provider: copy `llm/anthropic_provider.py` shape into `llm/<name>_provider.py`, wire in `llm/base.py::make_provider`, match the `LLMProvider` Protocol. The rest of the pipeline is provider-agnostic.

## Local runs: cost and safety

Auto-open of the HTML report is on by default. Pass `--no-open` in CI or headless environments.

Prompt caching is on for Anthropic. Subsequent runs of the same control burn about 20% of the input tokens they otherwise would.

Control cache lives at `data/<control>/.control-cache-<hash>.json`. Gitignored. Keyed by (control_md + system_prompt + provider + model). Delete it to force a re-parse.

## Do not

Commit anything under `.env` (secrets) or `output/**/trace.jsonl` (both gitignored).

Break the `assessment.json` schema without also updating the HTML report and Excel workpaper writers that read from it.

Skip `evidence_refs` in a verdict. The Pydantic schema enforces `min_length=1` for a reason.
