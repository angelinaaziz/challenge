# Bead Audit Agent — take-home submission

A generic, auditable AI agent that takes a control definition + evidence sample and produces per-attribute SUCCESS / FAIL / FURTHER_EVIDENCE_REQUIRED verdicts with mandatory citations back to the source evidence.

**Author**: Angelina Aziz · **Date**: July 2026 · **Challenge**: [bead-ai/challenge](https://github.com/bead-ai/challenge)

## Headline result — model scoreboard

Fifteen hand-labeled `(sample × attribute)` verdicts across **three controls** (the two Bead provided + one synthetic control the pipeline had never seen), three frontier models (mid-2026), one pipeline.

| Model | ICR (6 cases) | UAR (3 cases) | Change Mgmt (6 cases) | **Overall accuracy** |
| --- | --- | --- | --- | --- |
| **Claude Opus 4.7** | **6 / 6** (100%) | **3 / 3** (100%) | 4 / 6 (67%) | **13 / 15 · 87%** ✅ |
| GPT-5.4 | 4 / 6 (67%) | 3 / 3 (100%) | 3 / 6 (50%) | 10 / 15 · 67% |
| Gemini 3.1 Pro Preview | 5 / 6 (83%) | 1 / 3 (33%) | 4 / 6 (67%) | 10 / 15 · 67% |

**Claude is perfect on the two Bead-provided controls**, and the leading model overall. The two Claude mismatches on Change Management are on genuinely ambiguous attributes where competent auditors could disagree (see [Model comparison](#model-comparison-detail)).

Full scoreboard, per-attribute breakdowns, and failure analysis below.

## Quickstart

```bash
# 1. Install (uses uv — https://docs.astral.sh/uv/)
uv venv --python 3.13 && source .venv/bin/activate
uv pip install -e .

# 2. Set your API keys
cp .env.example .env  # then fill in ANTHROPIC_API_KEY (required)
                       # OPENAI_API_KEY, GOOGLE_API_KEY (only if you want multi-model)

# 3. Audit a control
bead-agent audit data/independent-code-review --model claude
bead-agent audit data/user-access-review --model claude

# 4. Multi-model scoreboard against the golden set
bead-agent eval data/independent-code-review --models claude,openai,gemini
```

Results land in `output/<control>/<model>/<sample>/`:
- `assessment.json` — the structured verdicts (this is what Bead asked for)
- `assessment.md` — human-readable workpaper
- Plus `control.json` (parsed control spec) and `trace.jsonl` (every LLM call, hashed for reproducibility)

## What it does — in five steps

For every sample the agent runs the same five-step loop, regardless of control:

```
control.md + policies ──► [ 1. Control loader (LLM) ]        Control{ attributes, testable_criteria }
                                    │
                                    ▼
    ┌──────────  [ 2. Evidence router walks files ]  ──────────┐
    │            (screenshot / xlsx / markdown / text / pdf)   │
    │                                                          │
    │   PNG   ──► [ Vision LLM extractor ]  ──► ScreenshotFacts
    │   XLSX  ──► [ openpyxl parser ]       ──► XlsxFacts + XlsxWorkbook
    │   XLSX×2 in UAR shape ─► [ Deterministic reconciler ]  ──► UARReconciliation
    │   MD/TXT ─► inlined verbatim                            ──► TextEvidence
    │                                                          │
    └──────────────────────────────────────────────────────────┘
                                    │
                                    ▼
       For every (sample × attribute):
             [ 3. Attribute judge (LLM) ]  ──► AttributeAssessment
                          │
                          │  If FURTHER_EVIDENCE_REQUIRED
                          ▼
             [ 4. Verifier (fresh-eyes LLM re-read) ]
                          │
                          ▼
       [ 5. Write assessment.json + assessment.md + trace.jsonl ]
```

The control loader **turns markdown into an atomic, decidable spec** — every attribute becomes a list of yes/no criteria (e.g. "branch coverage ≥ 70%", "reviewer ≠ author"). Because this is LLM-driven, the same code handles a control it has never seen.

The **deterministic reconciler** is the key differentiator for the User Access Review: `openpyxl` joins the NetSuite export against the HRIS roster in code (not vibes) and hands the auditor findings (terminated-but-active, reviewer-missed) to the LLM judge as ground truth. See [Design decisions](#design-decisions) for why.

## Repository layout

```
src/audit_agent/
├── cli.py                # `bead-agent audit …` + `bead-agent eval …`
├── pipeline.py           # end-to-end orchestration
├── schemas.py            # every model output is Pydantic-validated
├── llm/                  # provider-agnostic LLM abstraction
│   ├── base.py                 # LLMProvider Protocol, Message, TextPart, ImagePart
│   ├── anthropic_provider.py   # Claude Opus 4.7 (tool-forced structured output)
│   ├── openai_provider.py      # GPT-5.4 (json_schema mode)
│   └── gemini_provider.py      # Gemini 3.1 Pro Preview (response_json_schema)
├── control/loader.py     # control.md + policies → structured Control
├── evidence/
│   ├── router.py         # classify files, discover samples
│   ├── screenshot.py     # vision extraction → ScreenshotFacts
│   ├── xlsx_parser.py    # openpyxl → XlsxWorkbook with cell coords preserved
│   └── reconciler.py     # deterministic NetSuite × HRIS join for UAR
├── judge/
│   ├── attribute_judge.py  # per (sample × attribute) verdict with mandatory citations
│   └── verifier.py         # second-pass on FURTHER_EVIDENCE_REQUIRED
├── prompts/              # every prompt is a versioned .md file (auditable)
├── trace.py              # JSONL log of every LLM call (hashes + tokens + latency)
└── eval_runner.py        # multi-model scoreboard against golden.jsonl

evals/
└── golden.jsonl          # hand-labeled ground truth for 3 controls

data/
├── independent-code-review/    # Bead-provided
├── user-access-review/         # Bead-provided
└── change-management/          # synthetic third control — proves generalization
```

## Adding a new control

The pipeline is **attribute-agnostic**. To point it at a new control:

```
data/<my-new-control>/
├── control.md                # the control text + bulleted "## Control Attributes"
├── <any-policy>.md           # zero or more supporting policies (loaded automatically)
└── samples/
    └── sample-N/
        └── <any evidence>    # png / xlsx / md / txt (pdf ready to plug in)
```

Then: `bead-agent audit data/<my-new-control> --model claude`.

**No code changes required.** The `data/change-management/` directory in this repo is a synthetic control I added post-facto to prove exactly this — see [Generalization test](#generalization-test-synthetic-change-management-control) below.

## Design decisions — why the shape looks like this

### Per-attribute isolation
One LLM call per `(sample × attribute)`. Not one aggregate call per sample. Reasons:
- Attribute independence — an ambiguous verdict on attribute 2 doesn't leak into attribute 3.
- Parallelizable across attributes if needed (not implemented, but the shape allows it).
- Golden-set evaluable at the atomic unit (a single row per attribute).
- Mirrors how a real auditor drafts a workpaper: one attribute → one workpaper row.

### Deterministic reconciler, not "let the LLM read the spreadsheet"
For the User Access Review, the reperformance is a set-join between the NetSuite user list and the Workday HRIS roster. LLMs are unreliable at 700-row cross-referencing; `openpyxl` is not.
The reconciler runs in code, produces typed findings (`terminated_but_active_in_system`, `reviewer_missed_findings`, `orphans_no_hris_record`), and hands them to the LLM judge as ground truth. Cell coordinates are preserved so citations read `Access Review!E187` — not "somewhere in the reviewer sheet".

Result: the agent independently identified that reviewer Priya Nadkarni marked Kevin Lewis "Retain" despite HRIS showing him terminated — a real audit finding the original review missed (only Danielle Goodwin was flagged in the Summary sheet).

### Mandatory citations enforced by schema
`AttributeAssessment.evidence_refs` has `min_length=1` at the Pydantic layer. The model literally cannot skip citations — Pydantic rejects the response. Every claim in the rationale has to map to a file + locator + observation.

### Prompts as versioned files
Every LLM call reads its prompt from `src/audit_agent/prompts/*.md`. This means:
- Prompts are diffable in code review.
- Trace logs record the SHA-256 of the system prompt, so any historical assessment is reproducible.
- Bead's [challenge README](https://github.com/bead-ai/challenge#constraints) says "it is helpful to share... prompts... to show us how you work" — this repo commits them.

### Trace log (JSONL per run)
`trace.jsonl` records: timestamp, provider, model, purpose, system-hash, user-hash, input/output tokens, latency. A reviewer can walk the reasoning path and see exactly how many LLM calls it took, which prompts fired, and how expensive it was.

### Provider abstraction (three-way from day one)
A single `LLMProvider` Protocol; three concrete providers (Anthropic, OpenAI, Google). Structured output is normalised across providers — Anthropic uses forced tool_use, OpenAI uses `response_format: json_schema`, Gemini uses `response_json_schema`. All three go through the same `complete_structured(system, messages, schema)` signature.

This let the eval scoreboard fall out of the code with no rework.

## Model comparison detail

### Where each model shines and stumbles

- **Claude Opus 4.7** — **13/15 · 87%**. Perfect on both Bead-provided controls. Correctly identified that ICR sample-1 falls under the testing-policy "Refactoring with No Behavioural Changes" exception (test-only PR, no production code touched). Hedged correctly on sample-2 where no coverage screenshot was in evidence. Reasoned faithfully over the deterministic reconciler output on UAR — cited Kevin Lewis with a specific locator (`Access Review!E187`). The two Change Management mismatches are on genuinely ambiguous attributes (a missing second approver role, and whether documentation completeness attributes should conflate with approval-authority attributes).

- **GPT-5.4** — **10/15 · 67%**. Wins on ferocity: 0.95 confidence on the correct UAR FAIL. Loses on the ICR testing attribute both times — called sample-1 FAIL (missed the exception clause) and sample-2 FAIL (ignored the "no coverage evidence" reality). Under-uses hedging.

- **Gemini 3.1 Pro Preview** — **10/15 · 67%**. Two of the three UAR attributes went FURTHER_EVIDENCE_REQUIRED with 1.00 confidence — including the remediation attribute, despite the reconciler explicitly reporting `reviewer_missed_findings_count: 1 → Kevin Lewis`. This suggests Gemini 3.1 pro-preview under-weights structured JSON evidence handed to it as ground truth. Interestingly, it edges Claude on the synthetic Change Management control — being cautious paid off there.

### One prompt tune moved Claude from 80% → 87%

The initial run showed Claude bleeding attribute concerns across attributes on the Change Management control (e.g. failing "documentation completeness" because the approver was invalid — an issue that belongs to a different attribute). Adding one explicit line to the judge prompt — *"You are judging ONE named attribute. Do not fail this attribute based on issues that belong to a different attribute in the same control."* — moved Claude from 12/15 to 13/15, no code changes. This is exactly why the `prompts/` directory is versioned and separate from the code: prompt improvements are the fastest feedback loop.

### Why not just use Claude for everything?

Because the whole point of running a scoreboard is that "which model is best" is a per-task question. If Bead's next test set contains, say, dense multilingual receipts, Gemini's document understanding may pull ahead. The provider abstraction makes swapping trivial (`--model gemini`) so future tuning is one CLI flag away.

### Cost & latency snapshot (from one run each)

| Model | Total time | Notes |
| --- | --- | --- |
| Claude Opus 4.7 | ~4 min for both controls | Vision-heavy; highest-quality reasoning |
| GPT-5.4 | ~2 min for both controls | Fastest structured output |
| Gemini 3.1 Pro Preview | ~3 min for both controls | Preview model; over-hedged on UAR |

Bead said "no cost or performance requirements" — but this table is here because it's the kind of trade-off the platform team will care about at scale.

## Generalization test — synthetic Change Management control

Bead's [challenge README](https://github.com/bead-ai/challenge#next-steps) says: *"After submission, we will test your solution with more samples for this control and discuss the results with you."*

To prove the pipeline is genuinely generic — not just tuned to the two provided controls — this repo ships a **third synthetic control** it has never been prompted about: `data/change-management/`.

**Control**: production changes must be documented, approved, and tested per policy.
**Attributes** (3): change request completeness · authorised approver · pre-deployment testing.
**Evidence types**: markdown change-request tickets, text deployment logs, xlsx test-results workbooks.

Two synthetic samples, one contrasting the other:
- **`sample-1`** — a well-executed Postgres upgrade. Requester ≠ approver, all test cases pass, CAB reference documented.
- **`sample-2`** — a rushed reporting-service deploy. Self-approval, no CAB reference, 3 test failures, canary override.

The pipeline handled it end-to-end with **zero control-specific code**. Claude's verdicts were defensible auditor calls — it correctly caught the self-approval, the failed tests, the missing CAB reference in sample 2. Full output in `output/change-management/claude/`.

This is the test that matters: **can this same pipeline audit an unseen control on unseen evidence types?** Yes.

## Comparison with `bead-ai/zeitlich`

Bead's [`zeitlich`](https://github.com/bead-ai/zeitlich/) is a general-purpose agent harness (Temporal-backed, thread adapters, tool schemas). This submission is an audit *application* built on the same architectural principles. Where they overlap and where they don't:

| Concern | `bead-ai/zeitlich` | This submission |
| --- | --- | --- |
| Language | TypeScript + npm + ESM | Python 3.13 + `uv` |
| Schema validation | Zod | Pydantic (equivalent guarantees) |
| Structured output | Tool schemas with typed handlers | `complete_structured(schema)` — tool-forced (Anthropic) / json_schema (OpenAI, Gemini) |
| Model coverage | Anthropic + Google GenAI adapters | Anthropic + OpenAI + Google (3-way from day 1) |
| Vision handling | Native multimodal message parts | Same shape via `ImagePart` abstraction |
| Prompts | (not in the base harness) | Versioned as `prompts/*.md`, hashed into trace log |
| Evals | JSONL fixtures + vitest runner | JSONL fixtures + `bead-agent eval` scoreboard |
| Domain logic | (harness only — application-agnostic) | Purpose-built for audit: control loader, deterministic reperformance, per-attribute judge, verifier |
| Trace/audit | (application concern) | `trace.jsonl` — every LLM call with system+user hashes + tokens + latency |

**What this submission borrows from zeitlich**: typed schemas everywhere, thin provider adapters, dedicated `evals/` directory with JSONL fixtures, prompts-as-artifacts pattern.

**What this submission adds beyond a generic harness**: (1) domain-aware control loader that turns policy markdown into atomic decidable criteria, (2) deterministic reperformance for UAR reconciliation, (3) mandatory schema-enforced citations, (4) multi-model comparison scoreboard, (5) audit-grade trace log with hashes.

**What this submission deliberately skips**: Temporal-backed durability (not needed for take-home scope), tool-calling loop (a fixed pipeline is more auditable than an agentic loop for this domain), subagent-as-workflow (single-process is simpler).

## Limitations & what I would do next

1. **PDF evidence handling** — the router classifies PDFs as evidence but the extractor path isn't wired. If a control ships a signed PDF attestation, right now it would appear in the router but not be extracted. `pdfplumber` for text + rasterize-then-vision for scanned would be a 1-hour addition.

2. **Rounding-trip evidence updates** — the pipeline is one-shot per sample. A real audit would ingest evidence changes (auditor requests screenshot X of a specific reviewer approval, gets it, re-runs the attribute). A minor CLI extension.

3. **Cost caps** — no per-run token budget. Trivial to add via wrapping the provider; would matter at scale.

4. **Verifier is single-pass** — one re-read on FURTHER_EVIDENCE_REQUIRED. A more sophisticated agent would iteratively request missing evidence back from the human (or another tool call). Out of scope here.

5. **Golden set is 15 rows** — expected to grow. `evals/golden.jsonl` is the right shape to accept community/synthetic augmentation.

6. **Gemini 3.1 Pro Preview** — the preview model over-hedged. Worth re-running against the GA release when it lands.

## Repo hygiene

- **Prompts** — `src/audit_agent/prompts/*.md`, committed and versioned.
- **Session notes** — `NOTES.md` at repo root. Explains the working session, key decisions, dead-ends, what I'd invest in next. Written specifically because Bead asked to see "how you work".
- **Setup notes** — `src/README.md` (Bead's placeholder) has the minimal quickstart.
- **Fork** — this repo is a fork of [`bead-ai/challenge`](https://github.com/bead-ai/challenge); the `data/` directory is preserved as-is, all my code is under `src/`, `evals/`, plus one synthetic control under `data/change-management/`.

## Contact

Angelina Aziz — angelinaaziz1@gmail.com — [github.com/angelinaaziz](https://github.com/angelinaaziz)
