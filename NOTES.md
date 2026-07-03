# Session notes — how I built this

Bead's [challenge README](https://github.com/bead-ai/challenge#constraints) says: *"If you use AI tooling or coding agents… it is helpful to share session recordings, prompts, plans or threads to show us how you work."*

This is that file. Honest, unpolished, in-session decisions.

## Timeline

- **Session length**: One focused day (~7 hours).
- **Tooling**: Claude Code (Opus 4.7) as coding agent for the build. All final prompts, code, and design decisions are in this repo.
- **Approach**: Plan-first — I refused to write code until the plan was defensible.

## The moves that shaped the submission

### 1. I read Bead's harness before designing anything

Before touching code I pulled apart [`bead-ai/zeitlich`](https://github.com/bead-ai/zeitlich/) and studied a hired predecessor's [take-home solution](https://github.com/daukadolt/challenge) at a strategic level (not the code). Findings that shaped my design:

- Zeitlich: TypeScript, Zod, Anthropic-first, thin thread adapters, `evals/` directory with JSONL fixtures. Signals: typed schemas everywhere, prompts-as-artifacts, eval loops matter.
- The predecessor's solution (from ~7 months earlier) was Python + BAML, `gpt-4o` vision, no xlsx support, no citations, no eval harness, markdown output only. Two-phase extract-then-evaluate was the right shape — I kept that pattern. The gaps (xlsx, citations, evals, modern models) became my differentiators.

### 2. Language decision: Python, not TypeScript

Zeitlich is TS, so a TS solution would signal "I read your harness." I went Python anyway because:
- `openpyxl` is materially better than any TS xlsx library for the UAR reperformance work, and reperformance is my top differentiator.
- The take-home is a working audit tool, not a harness rewrite. Correctness beats mirroring.
- The predecessor shipped Python and got hired — language isn't the deciding factor.

The trade-off I explicitly accept: this repo doesn't compose with zeitlich itself. If Bead wants it to plug in, a TS port of the same architecture is straightforward.

### 3. The reconciler is the killer move

The User Access Review isn't a reading-comprehension task — it's a **reperformance**: join NetSuite × Workday HRIS, find users whose employment status contradicts their access. I wrote this deterministically in code (`evidence/reconciler.py`) and hand the auditor findings to the LLM judge as ground truth. On the very first run, it correctly identified that reviewer Priya Nadkarni marked **Kevin Lewis** "Retain" despite HRIS showing him terminated — a real finding the original review missed (only Danielle Goodwin was flagged in the Summary sheet). No LLM would have caught this reading 700 rows.

### 4. Per-attribute isolation over "one call per sample"

The predecessor's solution used one aggregate LLM call per sample. I went the other way: one LLM call per `(sample × attribute)`. Reasons:
- Golden-set evaluable at the atomic unit.
- Parallelizable if latency matters.
- Failure of one attribute doesn't contaminate reasoning on another.
- Matches how a real auditor drafts a workpaper.

This decision paid off during prompt tuning — I could see exactly which attribute Claude was getting wrong and fix it in isolation.

### 5. Multi-model from day one — no rework needed to add providers

I built the `LLMProvider` Protocol before I built the first extractor. Adding a second and third provider was 100 lines each, no changes to the audit logic. This turned the eval scoreboard into a byproduct rather than a scramble at the end.

Trade-off: three providers means three subtle SDK quirks to normalize (Anthropic tool_use payloads occasionally stringify list fields; Gemini rejects `additionalProperties` in schemas and needs JSON-repair on truncation; OpenAI needs sanitized json_schema). Each got patched in the provider file, not leaked into the pipeline.

### 6. I hand-labeled the golden set myself

Nine `(sample × attribute)` rows for the two Bead controls, then six more for a synthetic third control. Each row has a `notes` field explaining the reasoning. Two rows are genuinely ambiguous verdicts where I picked the strictest defensible reading (see `evals/golden.jsonl`) — not because I wanted to look right, but because that's how real audit workpapers are reviewed.

### 7. Synthetic third control to prove generalization

Bead's README explicitly says they'll test with more samples. To prove the pipeline is genuinely generic — not tuned to the two provided controls — I added `data/change-management/` with a synthetic policy, two contrasting samples, and markdown/text/xlsx evidence types. The pipeline handled it end-to-end with **zero control-specific code**. Verdicts were defensible auditor calls (correctly caught self-approval, failed tests, missing CAB reference in sample 2).

## Dead ends I hit

### Claude Opus 4.7 stringifying list fields in tool_use

Roughly one in ten Claude tool_use responses came back with `key_facts: "[\"a\", \"b\"]"` — a JSON-encoded list inside a string — instead of an actual list. Pydantic rejected it. My fix: a recursive `_coerce_stringified_json()` on the payload before validation, using the `json-repair` library to handle trailing commas / leaked whitespace. This is a defensive patch; the underlying tool_use invariant should hold, but it doesn't 100% of the time.

### Gemini truncation + missing `additionalProperties` support

Gemini 3.1 Pro Preview:
- Rejects `additionalProperties` in schemas → I strip it before send.
- Occasionally hits `MAX_TOKENS` mid-JSON on complex schemas → doubled the token budget and added a lenient right-truncation JSON repair fallback.

### OpenAI needing schema sanitization

The `response_format: json_schema` strict mode rejects Pydantic-generated schemas that have `default`/`title` fields and expects `additionalProperties: false` explicitly. Small `_sanitize_json_schema()` walker in the provider.

### `gemini-3-pro` isn't a real model ID (yet)

I guessed the default model IDs upfront, hit a 404 on Gemini, listed the available models, and swapped to `gemini-3.1-pro-preview`. Documented as env-configurable — easy to swap once GA lands.

## What I'd invest in next (in priority order)

1. **PDF evidence handling.** Router classifies but doesn't extract. `pdfplumber` for text + vision fallback for scans — ~1 hour.
2. **Evidence request loop.** On `FURTHER_EVIDENCE_REQUIRED`, generate a specific human-readable "please supply X" note back to the auditor. Right now it's implicit in the rationale.
3. **Parallel per-attribute execution.** All attribute calls are independent — could run concurrently with an `asyncio` pool. Would cut wall-clock ~3×.
4. **Cost cap + retry policy.** Wrap providers in a budget-aware layer for real deployment.
5. **Larger golden set.** 15 rows is a starting point. Would want ~50 rows across ~6 controls to trust the model-comparison numbers at production scale.
6. **Verifier that can request evidence.** Right now the verifier is a single re-read. In a real audit workflow it should be allowed to say "I need the CAB minutes attached" and gate on that.

## The one design decision I'm least sure about

**LLM-parsed control vs regex-parsed control.**

The current pipeline sends `control.md` to the LLM to be re-expressed as structured criteria. Pros: same code handles any control, no hardcoded parsing. Cons: burns an extra LLM call per audit run, and the parsed criteria vary slightly between providers (which is why the eval matches by attribute *text*, not ID).

If Bead's controls follow a strict template, a rules-based parser would be cheaper and more deterministic — and I'd invest in extending the template rather than the LLM.

## What I'd want to talk about in the debrief

- How Bead's real customers write controls today. My control loader assumes a clean markdown structure with `## Control Attributes` and a bulleted list; is that realistic or optimistic?
- Whether the auditor persona ever wants an agent that *proactively requests* evidence, or whether the workflow is strictly "human gives all evidence, agent judges".
- How Bead thinks about model swapping in production. My scoreboard suggests Claude wins today but Gemini pulls ahead on stress-test cases — is that ever a signal to route different controls to different models?
