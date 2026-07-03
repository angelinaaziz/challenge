# Bead audit agent

Give it a control folder. It reads the rules, looks at the evidence, and tells you which parts pass, which fail, and where the evidence lives.

**Take-home for [`bead-ai/challenge`](https://github.com/bead-ai/challenge)** · Angelina Aziz · July 2026

---

## The result

I hand-labelled 15 correct answers across three controls (Bead's two + one I invented to stress-test the pipeline), ran three frontier models against them, and scored the output.

| Model | Independent Code Review | User Access Review | Change Management | **Overall** |
| --- | :-: | :-: | :-: | :-: |
| **Claude Opus 4.7** | **6/6 (100%)** | **3/3 (100%)** | 4/6 (67%) | **13/15 · 87%** ✅ |
| GPT-5.4 | 4/6 (67%) | 3/3 (100%) | 3/6 (50%) | 10/15 · 67% |
| Gemini 3.1 Pro Preview | 5/6 (83%) | 1/3 (33%) | 4/6 (67%) | 10/15 · 67% |

Claude gets Bead's two controls perfectly. All three models tie or struggle on my synthetic third control — those attributes are genuinely ambiguous, and reasonable auditors would disagree too.

**One tweak to the prompt lifted Claude from 80% → 87%.** No code change. That's why the prompts live as files you can diff in review.

---

## What you get out

Three outputs per run — from raw JSON for machines to a Bead-themed HTML workpaper you can send to a reviewer.

| Format | Best for |
| --- | --- |
| `assessment.json` | Machines. Structured verdicts with citations — Bead's requested output. |
| `assessment.md` | Reading in the terminal or the repo — headline verdict, reperformance summary, evidence coverage, per-attribute detail with citations. |
| **`report.html`** | **Sharing.** Self-contained single-file HTML report, Bead-themed light mode, opens offline, emailable. Generate with `bead-agent report <run-dir>`. |

Committed sample outputs live under `output/<control>/<model>/report.html` — open any of them in a browser to see what the pipeline produces.

## Try it

```bash
# 1. install
uv venv --python 3.13 && source .venv/bin/activate
uv pip install -e .

# 2. add your API key
cp .env.example .env       # then fill in ANTHROPIC_API_KEY

# 3. audit
bead-agent audit data/independent-code-review

# 4. get the workpaper
bead-agent report output/independent-code-review/claude --open
```

That's it. Everything else is optional flags.

---

## Six commands

Every command has `--help`.

| Command | What it does |
| --- | --- |
| `bead-agent audit <control-dir>` | Run the full pipeline. Get JSON + markdown verdicts. |
| `bead-agent info <control-dir>` | Peek at a control without spending API credit — shows parsed attributes, discovered samples, estimated call count. |
| `bead-agent show <assessment.json>` | Pretty-print a past verdict in the terminal. |
| `bead-agent trace <run-dir>` | Table of every LLM call: tokens, cost, latency. |
| `bead-agent report <run-dir>` | **Self-contained HTML report** — Bead-themed, one file, opens offline. |
| `bead-agent eval <control-dir>` | Multi-model scoreboard against the hand-labelled golden set. |

### `audit` flags

| Flag | Default | What it does |
| --- | --- | --- |
| `--model, -m` | `claude` | `claude` \| `openai` \| `gemini` |
| `--out, -o` | `output/<control>/<model>/` | Where to write results |
| `--no-verify` | off | Skip the second-pass re-read on hedged verdicts |
| `--consistency, -k` | `1` | Run the judge N times per attribute, majority wins |

### `eval` flags

| Flag | Default | What it does |
| --- | --- | --- |
| `--models` | `claude,openai,gemini` | Which providers to score |
| `--golden` | `evals/golden.jsonl` | Path to ground truth |

### Environment variables

| Var | Required for | Default model ID |
| --- | --- | --- |
| `ANTHROPIC_API_KEY` | `--model claude` | `claude-opus-4-7` |
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
   assessment.json (structured) + assessment.md (readable) + trace.jsonl (audit trail)
   Optional: report.html — the shareable Bead-themed workpaper.
```

**The bit that matters most is step 2 for User Access Review.** LLMs are unreliable at cross-referencing 334 users against 720 HR records. `openpyxl` isn't. So the code does the join, finds terminated staff whose access wasn't revoked, and hands the findings to the LLM as ground truth. On Bead's UAR sample this caught **Kevin Lewis** — flagged as terminated in HRIS, but the reviewer left his access active. The original review missed it.

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

The schema enforces `evidence_refs` non-empty. The model literally can't skip citations — Pydantic rejects the response.

---

## Why the design is the way it is

**One LLM call per attribute, not per sample.** Isolates reasoning. Parallelisable. Cleanly evaluatable at the atomic unit. Matches how a real auditor writes a workpaper (one attribute → one row).

**Code does the reconciliation, not the LLM.** For UAR, `openpyxl` joins the workbooks and passes the LLM structured findings. Cell coordinates flow through so the citation reads `Access Review!E187`, not "somewhere in the reviewer sheet".

**Schemas enforce citations.** `evidence_refs` has `min_length=1`. No unsourced claims possible.

**Prompts are versioned files.** In `src/audit_agent/prompts/*.md`. Diffable, reviewable, hashed into the trace log for reproducibility.

**Three LLM providers from day one.** Same `complete_structured(schema, ...)` call across Claude, GPT and Gemini. Adding another provider is ~100 lines. The multi-model scoreboard was a byproduct.

**Prompt caching + retry.** Anthropic `cache_control: ephemeral` on the system + tool schema — 19% cache-hit on a cold run, more on repeats. Tenacity retry on transient failures.

**Self-consistency voting is optional.** `--consistency 3` runs the judge 3× and takes majority. Cheap now that caching is in.

---

## Adding a new control

Drop in a folder. No code changes.

```
data/<my-control>/
├── control.md          # bulleted list of attributes under "## Control Attributes"
├── <any-policy>.md     # policies (loaded automatically)
└── samples/
    └── sample-N/       # any mix of png · xlsx · md · txt
```

```bash
bead-agent audit data/<my-control>
```

`data/change-management/` in this repo is a synthetic third control I added to prove exactly this — the pipeline handled it end-to-end with no tuning.

---

## Where things live

```
src/audit_agent/
├── cli.py           # bead-agent audit / info / show / trace / report / eval
├── pipeline.py      # ties everything together
├── schemas.py       # every LLM output is Pydantic-validated
├── pricing.py       # $/1M tokens per provider
├── trace.py         # JSONL trace + cost totals
├── html_report.py   # self-contained HTML report generator (Bead-themed)
├── llm/             # provider Protocol + Claude/OpenAI/Gemini + retry
├── control/loader.py       # markdown → structured Control
├── evidence/               # router, screenshot extractor, xlsx parser, UAR reconciler
├── judge/                  # attribute judge (with self-consistency) + verifier
└── prompts/                # versioned .md prompts

evals/golden.jsonl   # hand-labelled ground truth
data/                # three controls (two Bead-provided, one synthetic)
output/              # committed model outputs — inspect without spending credits
```

### Output layout

Everything runs write to `output/<control>/<model>/`:

| File | What's in it |
| --- | --- |
| `control.json` | Parsed control (attributes + testable criteria) |
| `trace.jsonl` | Every LLM call: tokens, cache hits, cost, latency, hashes |
| `<sample>/assessment.json` | Structured verdicts (Bead's requested format) |
| `<sample>/assessment.md` | Readable workpaper |
| `report.html` | Bead-themed HTML report (`bead-agent report`) |

---

## Comparison with `bead-ai/zeitlich`

Zeitlich is a general-purpose agent harness. This repo is an audit application built on the same principles.

| | zeitlich | this repo |
| --- | --- | --- |
| Language | TypeScript | Python 3.13 |
| Schemas | Zod | Pydantic |
| Structured output | Tool schemas + typed handlers | `complete_structured(schema)` |
| Providers | Anthropic + Google | Anthropic + OpenAI + Google |
| Prompts | (application concern) | Versioned `.md` files, hashed into trace |
| Evals | JSONL + vitest | JSONL + `bead-agent eval` scoreboard |
| Domain logic | (harness only) | control loader · reperformance · per-attribute judge · verifier |
| Cost + telemetry | (application concern) | Anthropic prompt caching, per-call cost, JSONL trace |

**Borrowed from zeitlich:** typed schemas everywhere, thin provider adapters, `evals/` dir, prompts-as-artifacts.

**Added on top:** LLM-parsed control · deterministic reperformance · schema-enforced citations · control-level rollup · evidence coverage · self-consistency · prompt caching + cost telemetry · multi-model scoreboard.

---

## Cost & speed

One ICR audit (2 samples × 3 attributes, no verifier) with Claude Opus 4.7:

- **$2.03 per run** at current Anthropic prices
- **19% cache-hit** cold. Climbs to 60%+ on repeat runs inside the 5-min TTL.
- **~2 minutes wall-clock**, 11 LLM calls

Bead said cost isn't a factor in the evaluation so I haven't optimised heavily for it. Long-term the obvious levers are: async fan-out on per-attribute judges (~3× wall-clock cut), routing cheaper models to extraction while keeping Claude for judgment, and pushing cache breakpoints further up the request.

---

## Limitations & what's next

1. **PDF evidence.** Classified but not extracted. `pdfplumber` + vision fallback for scans is ~1 hour.
2. **Verifier is single-pass.** In a real workflow it should be able to ask for missing evidence.
3. **Golden set is 15 rows.** Would want ~50 across ~6 controls for real statistical weight.
4. **Reconciler is UAR-shaped.** Generalising to any two-workbook cross-check is ~1 hour.
5. **Per-attribute judges run serially.** They're independent — `asyncio` cuts wall-clock ~3×.

---

## Repo hygiene

- **Prompts** live in `src/audit_agent/prompts/`
- **Session notes** in `NOTES.md` — decisions, tradeoffs, what I'd invest in next. Bead explicitly asks for this.
- **Setup** in `src/README.md`
- **Fork** of `bead-ai/challenge`; upstream `data/` preserved; my code in `src/`, `evals/`, plus one synthetic control at `data/change-management/`
- Planned and iterated with Claude Code — kept scope honest, ran multi-model evals in the background, challenged the design when I was about to over-build

---

Angelina Aziz · angelinaaziz1@gmail.com · [github.com/angelinaaziz](https://github.com/angelinaaziz)
