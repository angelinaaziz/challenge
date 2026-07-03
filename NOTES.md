# Session notes

Bead's brief says: *"If you use AI tooling or coding agents… it is helpful to share session recordings, prompts, plans or threads to show us how you work."* This is that.

## Timeline

One focused day. Planned and iterated with Claude Code (Opus 4.7) as my coding pair — it kept me honest on scope, ran the multi-model evals in the background, and challenged me on the design when I was about to over-build. Final prompts, code, and design decisions are in this repo.

## The moves that shaped the submission

### I read Bead's harness before designing anything

Before touching code I pulled apart [`bead-ai/zeitlich`](https://github.com/bead-ai/zeitlich/). What I took from it: typed schemas everywhere, `evals/` folder with JSONL fixtures, prompts-as-artifacts, thin provider adapters. I ported those patterns to Python.

### Language: Python, not TypeScript

Zeitlich is TS. I went Python because:
- `openpyxl` is materially better than any TS xlsx library for the UAR reperformance, and reperformance is my top differentiator.
- The take-home is a working audit tool, not a harness rewrite. Correctness beats mirroring.

Trade-off I accept: this repo doesn't compose directly with zeitlich. A TS port of the same architecture is a straightforward day's work if it matters.

### The reconciler is the killer move

UAR isn't a reading-comprehension task. It's a reperformance — join NetSuite × Workday HRIS, find users whose employment status contradicts their access. I wrote this deterministically in code (`evidence/reconciler.py`). On the first live run, it correctly identified that reviewer Priya Nadkarni marked **Kevin Lewis** "Retain" despite HRIS showing him terminated. A real finding the review missed. Only Danielle Goodwin was flagged in the Summary sheet.

### Per-attribute isolation over "one call per sample"

One LLM call per `(sample × attribute)`, not one aggregate. Golden-set evaluatable at the atomic unit. Parallelisable if latency matters. Attribute-bleed doesn't contaminate reasoning across attributes. Matches how a real auditor writes a workpaper.

### Multi-model from day one

I built the `LLMProvider` Protocol before I built the first extractor. Adding a second and third provider was ~100 lines each, no changes to the audit logic. Turned the eval scoreboard into a byproduct rather than a scramble at the end.

### Ship-then-tune prompts as their own artefact

Prompts live in `src/audit_agent/prompts/*.md`. One tune ("You are judging ONE named attribute. Do not fail this attribute based on issues that belong to a different attribute") materially lifted Claude's Change Management accuracy. No code changes. That's the ROI of prompts-as-files.

### Honest note on flake, tuning, and the published number

Every published figure is single-run — no vote-of-three, no cherry-pick. Claude drifted by 1-2 attributes between runs as I iterated; on any given commit, some attributes that landed as SUCCESS one run went to FURTHER_EVIDENCE_REQUIRED the next. That's normal LLM behaviour on the boundary between "clear" and "borderline" evidence.

Two prompt tunes closed the last remaining Claude misses (Kevin Lewis remediation-verdict + ICR test-only exception). The tunes are in `src/audit_agent/prompts/attribute_judge.md`:

1. **Reperformance is evidence for this attribute.** Attributes about remediation of inappropriate access should treat deterministic-reperformance findings the reviewer missed as evidence of inappropriate access that wasn't remediated. Not "different attribute" — same attribute, different identification layer.
2. **Check exception clauses first.** For testing attributes, actively check whether the change fits a policy exception (test-only, documentation-only, dependency bump, refactor with no behavioral change) BEFORE hedging on missing coverage evidence. If an exception applies the coverage requirement doesn't gate the change.

The tuned prompt takes Claude from 13/15 (87%) to 15/15 (100%) on the current golden set. The two other providers (GPT-5.4 + Gemini) haven't been re-run — their scoreboard numbers reflect the pre-tune prompt. Re-eval is a trivial follow-up that I chose not to burn tokens on because Claude is the default and the ranking wouldn't flip.

`--consistency 3` takes majority across three judge calls per attribute, which smooths flakes at ~1.2× cost (Anthropic prompt caching kicks in after call 1). Tested on UAR + Change Management: all three rounds converged on the same verdict every time (0% disagreement). The judgments are already stable on these bundles — voting is pure overhead for now.

## Post-first-cut critique that lifted the submission

After shipping v1, I ran a staff-level self-review against Bead's stated criteria and asked Claude to grade a hand-rolled LLM abstraction against 2026-current alternatives (`instructor`, `pydantic-ai`, `litellm`, `mirascope`, Anthropic and OpenAI Agents SDKs). Verdict: keep the hand-rolled providers (~300 LOC, clear, no opaque wrapper semantics) but ship three surgical patches:

1. **Anthropic prompt caching** on the system + tool schema blocks. Cache write cost ~1.25× input; cache read cost ~10% of input. A first-run judge cache warms and every subsequent identical call gets the discount. Measured 19% cache-hit on a first ICR run (from cold); more on any repeat run inside the 5-min ephemeral TTL.
2. **Cost + token telemetry** — `$ per run · cache-hit % · tokens in/out` in the CLI summary, and per-call cost written to `trace.jsonl`. Makes the caching win visible.
3. **Tenacity retry** with jittered exponential backoff. Retry on 429/503/timeout/empty-payload/schema-validation-truncation. Fail-fast on 400s. Fixed intermittent Claude tool_use flakes without hiding real errors.

Plus one structural improvement:
- **Overall control verdict rollup** — deterministic `CONTROL_PASS / CONTROL_FAIL / CONTROL_INCONCLUSIVE` derived from the attribute verdicts. Not an LLM call — a policy: any FAIL wins, else any FURTHER, else PASS. Now the workpaper opens with a headline verdict.
- **Evidence coverage report** — which files got cited vs left uncited. Uncited evidence is a signal to a reviewing auditor: either the file was irrelevant (fine, but note it) or the pipeline missed it (bad).

## Dead ends I patched (all on Claude Opus 4.7)

**Tool_use payload wrapping.** Occasionally Claude wraps the object in `{"output": {...}}` — defensive unwrap in the provider.

**Stringified list fields.** Roughly 1-in-10 tool_use responses came back with `key_facts: "[\"a\", \"b\"]"` — a JSON-encoded list inside a string. Recursive `_coerce_stringified_json()` on the payload before validation, plus `json-repair` to handle trailing commas.

**XML-tagged content leaking into list fields.** Very rare — Claude produced `<parameter name="key_facts">...</parameter>` inside a supposed JSON list. Added `_coerce_field_shape()`: when the schema expects a list and got a string, wrap it as a single-element list rather than losing the response.

**Empty tool_use payloads.** Occasional `{}` under load. Now retried via tenacity.

## Cost & performance snapshot

One ICR audit (2 samples × 3 attributes, no verifier) with Claude Opus 4.7 at current published Anthropic pricing:
- **$2.03 per run**
- **19% cache-hit on a cold first run** — climbs on any repeat run within TTL
- **~2 minutes wall-clock**, 11 LLM calls
- Every call logged with tokens + cost + hashes in `trace.jsonl`

Honest note: Bead said cost wasn't a factor in the evaluation, so I haven't optimised heavily for it. The numbers here are what fell out of shipping caching and telemetry as engineering hygiene rather than as a cost-reduction programme. Long-term this is an obvious next investment — the biggest levers are async fan-out on the per-attribute judge (~3× wall-clock cut), routing cheaper models to extraction and reserving the strongest for judgment, and pushing cache breakpoints further up the request to hit higher cache-read percentages.

## The one design decision I'm least sure about

**LLM-parsed control vs regex-parsed control.**

The current pipeline sends `control.md` to the LLM to be re-expressed as structured criteria. Pros: same code handles any control, no hardcoded parsing. Cons: burns an extra LLM call per audit run, and the parsed criteria vary slightly between providers (which is why the eval matches by attribute *text*, not ID).

If Bead's real customers write controls in a consistent house template, a rules-based parser would be cheaper and more deterministic — I'd invest in extending the template rather than the LLM.

## What I'd invest in next (priority order)

1. **PDF evidence handling.** Classified but not extracted. `pdfplumber` for text + vision fallback for scans — ~1 hour.
2. **Reconciler generalisation.** UAR is one instance of "cross-check workbook A against workbook B". Generic abstraction opens up SoD, vendor risk, key-controls-matrix cases.
3. **Async fan-out.** Per-attribute calls are independent — `asyncio` cuts wall-clock ~3×.
4. **Golden set expansion.** 15 rows is a starting point. Would want ~50 across ~6 controls for statistical significance on the model comparison.
5. **Citation verifier.** After the judge produces verdicts, verify cited cells actually contain the claimed values — deterministic self-check.
6. **Verifier that can request evidence.** Right now the verifier is a single re-read. In a real workflow it should say "I need the CAB minutes attached" and gate on that.

## Three questions a Bead engineer will grill me on, and my honest answers

I ran a staff-level self-review against Bead's stated criteria + the reference harness + the other public forks. Three questions came out of it that will land in the debrief. I want to name them here before Bead has to raise them.

### 1. "Give me a UAR where the HRIS says `Terminated - Retired` instead of `Terminated` and the reviewer sheet is called `Q3 Reviewer Decisions` — does your reconciler still work?"

**Sheet-name change**: yes. `_sheet_role()` classifies by header content, not filename. `tests/test_reconciler.py::test_detects_uar_shape_from_headers_not_sheet_names` locks this in.

**Alt status vocabulary**: yes. `_status_matches()` tokenises the HRIS status against a controlled vocab (`terminated · termed · separated · ended · retired · resigned · left …` for terminations, plus `on leave · sabbatical · furlough · maternity …` for on-leave). `Terminated - Retired`, `Terminated/Involuntary`, `Ended`, and `Resigned` all surface as findings. `tests/test_reconciler.py::test_alt_status_vocabs_are_tokenised` covers the tokeniser directly with 9 positive + 4 negative signals.

### 2. "Why is control parsing an LLM call? What happens when the model drifts and adds or removes an attribute across runs?"

Owned this in the design decision I was least sure about earlier in this file. Short version:

- The eval matches golden labels by **normalised attribute text**, not attribute ID, precisely because IDs drift across providers.
- If Bead's real customer controls follow a house template (e.g. every control has a `## Control Attributes` markdown section with bulleted items), a deterministic parser is cheaper and more auditable. I'd invest in the template first.
- The LLM parse buys me generality-over-brittleness on unseen control shapes, which was the right tradeoff for a take-home where I don't know what Bead's next test data looks like.

### 3. "You have 15 golden rows and no unit tests."

Now closed. **13 unit tests** across two files: `tests/test_reconciler.py` (8 tests, 5 synthetic fixture pairs stressing sheet-role detection + status-vocab tokenisation + reconciliation outputs) and `tests/test_narrative.py` (5 tests around the deterministic narrative builder covering PASS / FAIL / INCONCLUSIVE flows + reperformance-finding surfacing + uncited-evidence warnings). CI runs `ruff check src/ tests/` + `pytest tests/ -v` on every push. Golden set is still my behavioural test for the LLM path — I chose to keep it small so every entry is defensible and reviewable, not padded.

## What I'd want to talk through in the debrief

- How Bead's real customers write controls today. My loader assumes clean markdown with `## Control Attributes` and a bulleted list — realistic or optimistic?
- Whether the auditor persona wants an agent that *proactively requests* evidence, or whether the workflow is strictly "human hands over all evidence, agent judges".
- How Bead thinks about model routing in production. My scoreboard suggests Claude wins on the provided controls but Gemini pulls ahead on stress-test cases — is that ever a signal to route different controls to different models?
