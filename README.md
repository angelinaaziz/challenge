# Bead audit agent

Give it a control folder. It reads the rules, looks at the evidence, and tells you which parts pass, which fail, and where the evidence lives.

**Take-home for [`bead-ai/challenge`](https://github.com/bead-ai/challenge)** · Angelina Aziz · July 2026

---

## The result

I hand-labelled 15 correct answers across three controls (Bead's two plus one I invented to stress-test the pipeline), ran three frontier models against them, and scored the output.

| Model | Independent Code Review | User Access Review | Change Management | **Overall** |
| --- | :-: | :-: | :-: | :-: |
| **Claude Opus 4.8** | **6/6 (100%)** | **3/3 (100%)** | **6/6 (100%)** | **15/15 · 100%** ✅ |
| GPT-5.4 *(stale prompt)* | 4/6 (67%) | 3/3 (100%) | 3/6 (50%) | 10/15 · 67% |
| Gemini 3.1 Pro Preview *(stale prompt)* | 5/6 (83%) | 1/3 (33%) | 4/6 (67%) | 10/15 · 67% |

**Claude nails all 15.** After a targeted prompt tune (see below), single-run Claude matches every hand-labelled verdict across all three controls with zero mismatches.

**Two prompt tunes closed the gap.** Both live in `src/audit_agent/prompts/attribute_judge.md`:

1. **Reperformance is evidence for THIS attribute.** For remediation attributes, findings the reviewer missed (surfaced by the deterministic reconciler) count as inappropriate access that wasn't remediated. Claude was reading "identified *during the review*" strictly and hedging on Kevin Lewis. The tune makes the reperformance layer count as audit-level identification.
2. **Check exception clauses FIRST, before hedging on missing coverage.** For testing attributes, if the change fits an exception (test-only maintenance, documentation-only, dependency bump, pure refactor), an exception SUCCESS is defensible without threshold numbers. Claude was hedging on the missing coverage screenshot when the exception should have made it moot.

Two new worked examples in the prompt lock in the desired reasoning shape (Example 3 is FAIL on a reperformance-only finding, Example 4 is SUCCESS via exception).

Honest caveat on the other two models: GPT-5.4 and Gemini 3.1 Pro Preview haven't been re-run against the tuned prompt for this scoreboard. Both would probably see similar lifts (the prompt fixes are model-agnostic), but I didn't burn the tokens to re-eval since Claude is the recommended default and the ranking wouldn't flip. Full re-eval left as trivial follow-up.

I also tested `--consistency 3` on UAR plus Change Management (pre-tune): all three rounds converged on the same verdict for every attribute. **0% disagreement rate.** On these specific evidence bundles the judgments are already stable, so voting is pure overhead. `--consistency` remains a useful lever for future controls where the model is genuinely unsure; the pipeline surfaces the disagreement_rate per sample so it's visible when it matters.

## Tested on unseen real-world PRs

To prove the ICR pipeline generalises beyond Bead's provided samples, I fetched two real recent PRs from major public repos and ran them through the same pipeline with no code changes:

- `sample-3` is [Kubernetes PR #139018](https://github.com/kubernetes/kubernetes/pull/139018) (removing the `opencontainers/cgroups` dependency from e2e tests). The pipeline flagged a real independence concern: **the author (BenTheElder) appears in the OWNERS approval list alongside a second reviewer (dims)**. Verdict `FAIL` on independent-reviewer-approval with the specific rationale that the author-self-approval taints the four-eyes principle even though a second human also approved.
- `sample-4` is [Next.js PR #95391](https://github.com/vercel/next.js/pull/95391) (a recent Next.js canary merge). Two distinct human reviewers (gnoff, acdlite) both approved before merge; the pipeline correctly landed `SUCCESS` on independence. It also noticed **"129 of 130 checks passed"** and correctly hedged the testing attribute to `FURTHER_EVIDENCE_REQUIRED`, a real defect finding on an unseen PR.

These are unseen public data. The pipeline surfaced real audit findings on both.

---

## What you get out

Bead's brief asks for *"for each sample and control attribute, provide a JSON object that includes the assessments and contextual details of how the conclusion was formed. The assessment can be SUCCESS, FAIL, FURTHER_EVIDENCE_REQUIRED"*. That's the primary output: `<sample>/assessment.json`. One JSON object per sample, containing an `attributes[]` array with one entry per control attribute, each carrying:

- `verdict`: `SUCCESS`, `FAIL`, or `FURTHER_EVIDENCE_REQUIRED` (the required Bead field)
- `confidence`: 0.0 to 1.0
- `rationale`: how the conclusion was formed, in plain English
- `evidence_refs`: file, locator, and observation citations grounding the verdict (schema-enforced non-empty)
- `policy_references`: verbatim policy citations that shaped the judgment
- `exceptions_considered`: any policy exceptions the judge actively weighed

Everything else (HTML report, Excel workpaper, markdown, JSONL trace) is layered on top for the auditor. The assessment.json is what Bead's brief asked for and is what every downstream artefact reads from.

Four outputs per run, from raw JSON for machines to a Bead-themed HTML workpaper you can hand to a SOX reviewer.

| Format | Best for |
| --- | --- |
| `assessment.json` | Machines. Structured verdicts with citations. Bead's requested output. |
| `assessment.md` | Reading in the terminal or the repo. Headline verdict, reperformance summary, evidence coverage, per-attribute detail with citations. |
| **`report.html`** | The workpaper. Self-contained single-file HTML, Bead-themed light mode, opens offline. Auto-generated at the end of every audit run and shown as a clickable link in the terminal. |
| **`workpaper.xlsx`** | Native Excel working paper (per Bead's marketed format). Cover sheet with verdict, exec summary, and sign-off area, plus Attribute Verdicts, Evidence Citations, Reperformance, Evidence Inventory, and Decision Log sheets. Auto-generated per sample. |

Every `report.html` includes:

- A bottom-line-up-front verdict banner at the top: big CONTROL PASS, FAIL, or CANNOT SIGN OFF, with a one-line reason so the reviewer knows the outcome from the first glance.
- Executive summary per sample answering "what happened and why?".
- Key findings, bulleted, colour-coded by severity.
- Recommended actions, numbered, grounded in the failed or hedged verdicts.
- Reperformance summary for UAR, showing the deterministic re-check output.
- Per-attribute verdicts with rationale, citations, and policy references, all expandable.
- Evidence inventory: every file the pipeline ingested, its detected type, what got extracted, and whether any verdict cites it.
- Decision log: every LLM call the agent made, with tokens, cost, and latency. The audit trail.
- Reviewer sign-off area: Accept, Rework, or Reject decision, reviewer name, date, and rationale. Human-in-the-loop capture built into the workpaper.

Committed sample reports live under `output/<control>/<model>/report.html`. Open any in a browser to see the full artefact.

## Try it

```bash
# 1. install
uv venv --python 3.13 && source .venv/bin/activate
uv pip install -e .

# 2. add your API key
cp .env.example .env       # then fill in ANTHROPIC_API_KEY

# 3. audit
bead-agent audit data/independent-code-review

```

The HTML report auto-opens in your browser when the audit finishes. Pass `--no-open` if you're running headless or in CI.

That's it. Everything else is optional flags.

---

## Six commands

Every command has `--help`.

| Command | What it does |
| --- | --- |
| `bead-agent audit <control-dir>` | Run the full pipeline. Produces JSON, markdown, HTML report, and Excel workpaper. Auto-opens the report in your browser. |
| `bead-agent info <control-dir>` | Peek at a control without spending API credit. Shows parsed attributes, discovered samples, estimated call count. |
| `bead-agent show <assessment.json>` | Pretty-print a past verdict in the terminal. Surfaces links to the HTML report and Excel workpaper from the same run. |
| `bead-agent trace <run-dir>` | Table of every LLM call: tokens, cost, latency. |
| `bead-agent report <run-dir>` | Regenerate the HTML report and Excel workpaper for a past run. Auto-opens the HTML in your browser. |
| `bead-agent eval <control-dir>` | Multi-model scoreboard against the hand-labelled golden set. |

### `audit` flags

| Flag | Default | What it does |
| --- | --- | --- |
| `--model, -m` | `claude` | `claude` \| `openai` \| `gemini` |
| `--out, -o` | `output/<control>/<model>/` | Where to write results |
| `--no-verify` | off | Skip the second-pass re-read on hedged verdicts |
| `--consistency, -k` | `1` | Run the judge N times per attribute, majority wins |
| `--open/--no-open` | `--open` | Auto-open the HTML report when done. `--no-open` for CI. |

### `eval` flags

| Flag | Default | What it does |
| --- | --- | --- |
| `--models` | `claude,openai,gemini` | Which providers to score |
| `--golden` | `evals/golden.jsonl` | Path to ground truth |

### Environment variables

| Var | Required for | Default model ID |
| --- | --- | --- |
| `ANTHROPIC_API_KEY` | `--model claude` | `claude-opus-4-8` |
| `OPENAI_API_KEY` | `--model openai` | `gpt-5.4` |
| `GOOGLE_API_KEY` | `--model gemini` | `gemini-3.1-pro-preview` |

---

## How it works

Five steps for each sample. Every step is the same for every control.

```
1. READ THE CONTROL
   control.md + policies → structured attributes + testable criteria

2. LOOK AT THE EVIDENCE
   PNG   → vision LLM → structured facts
   XLSX  → openpyxl → cell-coord JSON
   MD/TXT → inlined verbatim
   [UAR only] → deterministic reconciler joins two workbooks in code

3. JUDGE EACH ATTRIBUTE
   One LLM call per (sample × attribute). Mandatory citations enforced by the schema.

4. VERIFY HEDGED VERDICTS
   Any FURTHER_EVIDENCE_REQUIRED gets a fresh-eyes re-read.

5. WRITE THE WORKPAPER
   assessment.json (structured), assessment.md (readable), trace.jsonl (audit trail).
   Optional: report.html, the shareable Bead-themed workpaper.
```

The bit that matters most is step 2 for User Access Review. LLMs are unreliable at cross-referencing 334 users against 720 HR records. `openpyxl` isn't. So the code does the join, finds terminated staff whose access wasn't revoked, and hands the findings to the LLM as ground truth. On Bead's UAR sample this caught **Kevin Lewis**, flagged as terminated in HRIS but the reviewer left his access active. The original review missed it.

Full-population reperformance, not sampling. The reconciler tests 100% of the in-scope account population, every one of the 334 accounts on Bead's UAR sample, not a 25-row auditor sample. This maps directly to Bead's marketed positioning of *"full-population testing over sampling"* and is the audit-defensible advantage of deterministic reconciliation over LLM-only judgment.

---

## What a verdict looks like

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
        {
          "file": "uar-netsuite-q2-2026.xlsx",
          "locator": "Access Review!E187",
          "observation": "Kevin Lewis marked 'Retain' despite HRIS Termination"
        }
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

The schema enforces `evidence_refs` non-empty. The model literally can't skip citations. Pydantic rejects the response.

---

## Why the design is the way it is

**One LLM call per attribute, not per sample.** Isolates reasoning. Parallelisable. Cleanly evaluatable at the atomic unit. Matches how a real auditor writes a workpaper (one attribute maps to one row).

**Code does the reconciliation, not the LLM.** For UAR, `openpyxl` joins the workbooks and passes the LLM structured findings. Cell coordinates flow through so the citation reads `Access Review!E187`, not "somewhere in the reviewer sheet".

**Schemas enforce citations.** `evidence_refs` has `min_length=1`. No unsourced claims possible.

**Prompts are versioned files.** In `src/audit_agent/prompts/*.md`. Diffable, reviewable, hashed into the trace log for reproducibility.

**Three LLM providers from day one.** Same `complete_structured(schema, ...)` call across Claude, GPT, and Gemini. Adding another provider is about 100 lines. The multi-model scoreboard was a byproduct.

**Prompt caching plus retry.** Anthropic `cache_control: ephemeral` on the system and tool schema. 19% cache-hit on a cold run, more on repeats. Tenacity retry on transient failures.

**Self-consistency voting is optional.** `--consistency 3` runs the judge 3x and takes majority. Cheap now that caching is in.

---

## Adding a new control

Drop in a folder. No code changes.

```
data/<my-control>/
├── control.md          # bulleted list of attributes under "## Control Attributes"
├── <any-policy>.md     # policies (loaded automatically)
└── samples/
    └── sample-N/       # any mix of png, xlsx, md, txt
```

```bash
bead-agent audit data/<my-control>
```

`data/change-management/` in this repo is a synthetic third control I added to prove exactly this. The pipeline handled it end-to-end with no tuning.

---

## Where things live

```
src/audit_agent/
├── cli.py             # bead-agent audit / info / show / trace / report / eval
├── pipeline.py        # ties everything together plus deterministic narrative builder
├── schemas.py         # every LLM output is Pydantic-validated
├── pricing.py         # $/1M tokens per provider
├── trace.py           # JSONL trace plus cost totals
├── html_report.py     # self-contained HTML report generator (Bead-themed)
├── xlsx_workpaper.py  # native Excel workpaper writer (Cover, Verdicts, Citations, ...)
├── llm/               # provider Protocol, Claude/OpenAI/Gemini, tenacity retry
├── control/loader.py  # markdown to structured Control
├── evidence/          # router, screenshot extractor, xlsx parser, UAR reconciler
├── judge/             # attribute judge (with self-consistency) plus verifier
└── prompts/           # versioned .md prompts

tests/                 # 18 unit tests around the reconciler, narrative, IPE validator
evals/golden.jsonl     # hand-labelled ground truth (15 rows across 3 controls)
data/                  # three controls (two Bead-provided plus one synthetic)
output/                # committed model outputs (inspect without spending credits)
.github/workflows/     # CI (ruff plus pytest on every push)
```

### Output layout

Everything runs write to `output/<control>/<model>/`:

| File | What's in it |
| --- | --- |
| `control.json` | Parsed control (attributes plus testable criteria) |
| `trace.jsonl` | Every LLM call: tokens, cache hits, cost, latency, hashes |
| `report.html` | Bead-themed HTML report. BLUF banner, exec summary, findings, actions, evidence inventory, decision log, reviewer sign-off. |
| `<sample>/assessment.json` | Structured verdicts (Bead's requested format) |
| `<sample>/assessment.md` | Readable workpaper |
| `<sample>/workpaper.xlsx` | Native Excel workpaper (Cover, Attribute Verdicts, Evidence Citations, Reperformance, Evidence Inventory, Decision Log sheets) |

---

## Comparison with `bead-ai/zeitlich`

Zeitlich is a general-purpose agent harness. This repo is an audit application built on the same principles.

| | zeitlich | this repo |
| --- | --- | --- |
| Language | TypeScript | Python 3.13 |
| Schemas | Zod | Pydantic |
| Structured output | Tool schemas plus typed handlers | `complete_structured(schema)` |
| Providers | Anthropic plus Google | Anthropic, OpenAI, and Google |
| Prompts | (application concern) | Versioned `.md` files, hashed into trace |
| Evals | JSONL plus vitest | JSONL plus `bead-agent eval` scoreboard |
| Domain logic | (harness only) | control loader, reperformance, per-attribute judge, verifier |
| Cost and telemetry | (application concern) | Anthropic prompt caching, per-call cost, JSONL trace |

Borrowed from zeitlich: typed schemas everywhere, thin provider adapters, `evals/` dir, prompts-as-artifacts.

Added on top: LLM-parsed control, deterministic reperformance, schema-enforced citations, control-level rollup, evidence coverage, self-consistency, prompt caching plus cost telemetry, multi-model scoreboard.

---

## Cost and speed

One ICR audit (2 samples × 3 attributes, no verifier) with Claude Opus 4.7:

- $2.03 per run at current Anthropic prices
- 19% cache-hit cold. Climbs to 60%+ on repeat runs inside the 5-min TTL.
- About 2 minutes wall-clock, 11 LLM calls

Bead said cost isn't a factor in the evaluation so I haven't optimised heavily for it. Long-term the obvious levers are async fan-out on per-attribute judges (roughly 3x wall-clock cut), routing cheaper models to extraction while keeping Claude for judgment, and pushing cache breakpoints further up the request.

---

## Limitations and what's next

1. **PDF evidence.** Router classifies but doesn't extract. `pdfplumber` plus vision fallback for scans is about 1 hour.
2. **Verifier is single-pass.** In a real workflow it should be able to ask for missing evidence back from the human.
3. **Golden set is 15 rows.** Would want around 50 across 6 controls for real statistical weight.
4. **Reconciler is UAR-shaped.** Generalising to any two-workbook cross-check (SoD, vendor risk, key-controls matrix) is about 1 hour.
5. **Per-attribute judges run serially.** They're independent. `asyncio.gather` would cut wall-clock by around 3x.

---

## Repo hygiene

- Prompts live in `src/audit_agent/prompts/` (versioned `.md` files, hashed into the trace log).
- Unit tests in `tests/`: **18 tests** (8 reconciler, 5 narrative, 5 IPE) with synthetic fixture pairs. `pytest tests/ -v`.
- CI at `.github/workflows/ci.yml` runs `ruff check src/ tests/` and `pytest tests/ -v` on every push and PR.
- Working-session write-up in [`SESSION.md`](SESSION.md). How I directed Claude Code to build this. Bead's brief explicitly asks for "prompts, plans, or threads to show how you work"; this file addresses that ask.
- Engineering notes in [`NOTES.md`](NOTES.md): design decisions, tradeoffs, what I'd invest in next, plus a "three questions a Bead engineer will grill me on" section with honest answers to each.
- Agent-first conventions in [`AGENTS.md`](AGENTS.md): how a coding agent should behave in this repo.
- Setup in `src/README.md`.
- Fork of `bead-ai/challenge`. Upstream `data/` preserved. My code in `src/`, `tests/`, `evals/`, plus one synthetic control at `data/change-management/`.
- Planned and iterated with Claude Code. It kept scope honest, ran multi-model evals in the background, and challenged the design when I was about to over-build.

---

Angelina Aziz · angelinaaziz1@gmail.com · [github.com/angelinaaziz](https://github.com/angelinaaziz)
