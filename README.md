# Bead audit agent

A generic AI agent that audits controls. Point it at a control folder, get back per-attribute verdicts with mandatory citations.

**Take-home submission for [`bead-ai/challenge`](https://github.com/bead-ai/challenge)** · Angelina Aziz · July 2026

---

## Headline result

Fifteen hand-labelled `(sample × attribute)` verdicts across three controls, three frontier models. One pipeline.

| Model | ICR (6) | UAR (3) | Change Mgmt (6) | **Overall** |
| --- | :-: | :-: | :-: | :-: |
| **Claude Opus 4.7** | **6/6 · 100%** | **3/3 · 100%** | 4/6 · 67% | **13/15 · 87%** ✅ |
| GPT-5.4 | 4/6 · 67% | 3/3 · 100% | 3/6 · 50% | 10/15 · 67% |
| Gemini 3.1 Pro Preview | 5/6 · 83% | 1/3 · 33% | 4/6 · 67% | 10/15 · 67% |

Claude wins clean on the two Bead-provided controls. On the synthetic third control (which the pipeline has never been prompted about) all three models struggle on genuinely ambiguous edge-cases — reasonable auditors would disagree too.

**One prompt tune moved Claude from 80% → 87%.** No code changes. That's exactly why prompts are versioned as files in this repo.

---

## Quickstart

```bash
# 1. Install
uv venv --python 3.13
source .venv/bin/activate
uv pip install -e .

# 2. Add your API keys
cp .env.example .env
# ANTHROPIC_API_KEY required.
# OPENAI_API_KEY + GOOGLE_API_KEY only if you want the multi-model scoreboard.

# 3. Audit any control
bead-agent audit data/independent-code-review --model claude
bead-agent audit data/user-access-review --model claude
bead-agent audit data/change-management --model claude

# 4. Multi-model scoreboard against the golden set
bead-agent eval data/independent-code-review --models claude,openai,gemini

# 5. Self-consistency voting (3× calls per attribute, majority wins)
bead-agent audit data/user-access-review --model claude --consistency 3
```

Outputs land in `output/<control>/<model>/<sample>/`:

| File | What's in it |
| --- | --- |
| `assessment.json` | The structured verdicts (Bead's requested format) |
| `assessment.md` | Human-readable workpaper — reperformance summary, evidence coverage, per-attribute verdicts with citations |
| `trace.jsonl` | Every LLM call: tokens, cache hits, cost, prompt hashes |
| `control.json` | The parsed control spec (attributes + testable criteria) |

---

## How it works — one diagram

```
┌───────────────────────────┐     ┌──────────────────────────────────────────┐
│  control.md + policies    │────▶│  1. CONTROL LOADER (LLM)                │
│  bulleted attributes      │     │  turns each attribute into atomic        │
└───────────────────────────┘     │  yes/no testable criteria                │
                                   └──────────────────────────────────────────┘
                                                    │
                                                    ▼
┌───────────────────────────────────────────────────────────────────────────┐
│  2. EVIDENCE ROUTER  —  walks the sample folder                          │
├───────────────────────────────────────────────────────────────────────────┤
│  PNG  ─▶  Vision LLM  ─▶  ScreenshotFacts   (names, timestamps, numbers) │
│  XLSX ─▶  openpyxl    ─▶  cell-coord JSON                                │
│         │                                                                 │
│         └─▶  IF two xlsx workbooks look like a UAR pair:                 │
│              [Deterministic reconciler — code, not LLM]                  │
│              Joins access export × HRIS roster.                          │
│              Surfaces terminated-still-active, reviewer_missed,          │
│              orphans_no_hris_record.  Cell citations preserved.          │
│  MD/TXT ─▶  inlined verbatim                                             │
│  PDF   ─▶  (classified, extractor is future work)                        │
└───────────────────────────────────────────────────────────────────────────┘
                                                    │
                                                    ▼
              For each (sample × attribute):
              ┌────────────────────────────────────────────────────┐
              │  3. ATTRIBUTE JUDGE (LLM)                          │
              │     • One call per attribute — never one aggregate │
              │     • Optional self-consistency: N calls, majority │
              │     • Schema *forces* non-empty evidence_refs      │
              └────────────────────────────────────────────────────┘
                                    │
                     verdict = FURTHER_EVIDENCE_REQUIRED?
                                    │
                                    ▼
              ┌────────────────────────────────────────────────────┐
              │  4. VERIFIER (LLM)  —  fresh-eyes re-read          │
              └────────────────────────────────────────────────────┘
                                    │
                                    ▼
   Rollup: any FAIL → CONTROL_FAIL · all SUCCESS → CONTROL_PASS
                     · otherwise → CONTROL_INCONCLUSIVE
                                    │
                                    ▼
                    assessment.json + assessment.md + trace.jsonl
```

**The killer bit is step 2's reconciler.** LLMs are unreliable at joining a 334-row user list against a 720-row HRIS roster. `openpyxl` isn't. So we do the join in code, hand the LLM structured findings as ground truth, and it cites them back with actual cell coordinates. First live run of this pipeline caught a real audit finding on Bead's UAR sample — reviewer Priya Nadkarni marked Kevin Lewis "Retain" despite HRIS showing him terminated. Only Danielle Goodwin was flagged in the Summary. Kevin Lewis fell through the cracks.

---

## What each verdict looks like

```json
{
  "control": "User Access Review",
  "sample_id": "sample-1",
  "control_conclusion": "CONTROL_FAIL",
  "attributes": [
    {
      "attribute_text": "Inappropriate or excessive access ... remediated in a timely manner",
      "verdict": "FAIL",
      "confidence": 0.85,
      "rationale": "Reperformance identified two terminated-but-still-active accounts...",
      "evidence_refs": [
        { "file": "uar-netsuite-q2-2026.xlsx",
          "locator": "Access Review!E187",
          "observation": "Kevin Lewis marked 'Retain' despite HRIS Termination" }
      ],
      "policy_references": [...]
    }
  ],
  "evidence_coverage": {
    "all_files": ["hris-...xlsx", "uar-...xlsx"],
    "cited_files": ["uar-...xlsx"],
    "uncited_files": ["hris-...xlsx"]
  },
  "reperformance_notes": "System export: 334 rows | Reviewer missed: 1 (Kevin Lewis)..."
}
```

Every verdict carries **mandatory citations** (`min_length=1` at the Pydantic layer). The model can't skip them — validation rejects the response.

---

## Design choices, briefly

**One LLM call per `(sample × attribute)`.** Not one aggregate call. Isolates reasoning, parallelisable, cleanly evaluatable at the atomic unit, and mirrors how a real auditor writes a workpaper.

**Deterministic reconciliation, not "LLM reads the xlsx".** For the UAR reperformance, `openpyxl` does the joins. The LLM only judges the findings. Cell coordinates flow all the way through to the citations so an auditor can double-click "Access Review!E187" and see the exact row.

**Mandatory citations enforced by the schema.** `AttributeAssessment.evidence_refs` has `min_length=1`. No unsourced claims.

**Prompts as versioned files.** `src/audit_agent/prompts/*.md`. Diffable in code review, hashed into the trace log — any historical assessment is reproducible.

**Provider-agnostic from day one.** Same `complete_structured(schema, ...)` call across Claude, GPT-5.4 and Gemini. Adding a fourth provider is ~100 lines. The eval scoreboard came for free.

**Prompt caching + retry.** Anthropic `cache_control: ephemeral` on the system + tool schema blocks — 19% cache-hit on a fresh run, more on repeat runs. Tenacity retry on transient failures (429s, timeouts, empty payloads, truncated JSON).

**Self-consistency voting is opt-in.** `--consistency 3` runs the judge 3× and takes majority. Free-ish now that caching hits — costs ~1.2× not 3×. Surfaces `disagreement_rate` per attribute so genuinely ambiguous cases are visible.

---

## Adding a new control

The pipeline is attribute-agnostic. Drop in a new folder:

```
data/<my-control>/
├── control.md              # attributes as a bulleted list under "## Control Attributes"
├── <any-policy>.md         # zero or more policy docs — loaded automatically
└── samples/
    └── sample-N/
        └── <any evidence>  # png · xlsx · md · txt
```

Then: `bead-agent audit data/<my-control>`. **Zero code changes.** `data/change-management/` in this repo is a synthetic third control I added to prove exactly this — the pipeline handled it end-to-end, no tuning.

---

## Repo layout

```
src/audit_agent/
├── cli.py              # `bead-agent audit …` + `bead-agent eval …`
├── pipeline.py         # end-to-end orchestration
├── schemas.py          # every LLM output is Pydantic-validated
├── pricing.py          # $ per 1M tokens per provider
├── trace.py            # JSONL trace + cost totals
├── llm/                # LLMProvider Protocol + Claude/OpenAI/Gemini + retry
├── control/loader.py   # markdown → structured Control
├── evidence/           # router, screenshot extractor, xlsx parser, UAR reconciler
├── judge/              # attribute judge (with self-consistency) + verifier
└── prompts/            # versioned .md prompts

evals/golden.jsonl      # hand-labelled ground truth
data/                   # three controls: two Bead-provided + one synthetic
output/                 # committed model outputs — inspect without spending credits
```

---

## Comparison with `bead-ai/zeitlich`

Zeitlich is a general-purpose agent harness. This submission is an audit application built on the same principles.

| | zeitlich | this repo |
| --- | --- | --- |
| Language | TypeScript | Python 3.13 |
| Schema validation | Zod | Pydantic |
| Structured output | tool schemas + typed handlers | `complete_structured(schema)` — tool-forced (Claude) / json_schema (OpenAI, Gemini) |
| Providers | Anthropic + Google | Anthropic + OpenAI + Google |
| Prompts | (application concern) | versioned `.md` files, hashed into trace |
| Evals | JSONL + vitest runner | JSONL + `bead-agent eval` scoreboard |
| Domain logic | (harness only) | control loader · deterministic reperformance · per-attribute judge · verifier |
| Cost/trace | (application concern) | Anthropic prompt caching, cost per call, JSONL trace |

**Borrowed from zeitlich:** typed schemas everywhere · thin provider adapters · `evals/` folder · prompts-as-artifacts.

**Added beyond a generic harness:** domain-aware control loader · deterministic reperformance · schema-enforced citations · overall control rollup · evidence coverage report · self-consistency voting · prompt caching + cost telemetry · multi-model scoreboard.

**Deliberately skipped:** Temporal-backed durability (not needed for take-home scope) · tool-calling loop (fixed pipeline is more auditable than agentic).

---

## Cost & speed, honest numbers

One ICR audit (2 samples × 3 attributes, no verifier) with Claude Opus 4.7:
- **$2.03 per full run** at current published Anthropic prices
- **19% cache-hit** on a first run — climbs to 60%+ on any subsequent run within the 5-min TTL
- **~2 minutes wall-clock** (vision extractors serial; parallelisable)
- 11 LLM calls total

Bead's brief said cost isn't a factor in the evaluation, so I didn't optimise heavily for it — the numbers here are what fell out. It's an obvious next investment: prompt caching is already in; async fan-out on the per-attribute judge would cut wall-clock ~3×; smaller/cheaper models on the extraction step (vision) with the strongest model reserved for judgment would cut $ per run materially without losing accuracy.

---

## Limitations + what's next

1. **PDF extraction** — router classifies PDFs but doesn't extract. `pdfplumber` + rasterise-then-vision would fix. Not in Bead's samples so left out for now.
2. **Verifier is single-pass** — one re-read. A real audit workflow would iteratively request missing evidence from the human.
3. **Golden set is 15 rows.** Growing to ~50 across ~6 controls would give statistical significance.
4. **Reconciler is UAR-shaped.** Generalising it to any two-workbook cross-check is a 1-hour refactor.
5. **Per-attribute LLM calls run serially.** They're independent — an `asyncio` fan-out would cut wall-clock ~3×.

---

## Repo hygiene

- **Prompts** committed under `src/audit_agent/prompts/`
- **NOTES.md** — session write-up (decisions, tradeoffs, what I'd invest in next) — Bead's brief explicitly asks for this
- **src/README.md** — minimal setup + run recipe
- **Fork** of `bead-ai/challenge`; upstream `data/` preserved; my code lives in `src/`, `evals/`, plus one synthetic control under `data/change-management/`
- Planned and iterated with the help of Claude Code — see NOTES.md for how

---

## Contact

Angelina Aziz — angelinaaziz1@gmail.com — [github.com/angelinaaziz](https://github.com/angelinaaziz)
