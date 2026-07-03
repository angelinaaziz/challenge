# Session log: how this was built

Bead's brief says: *"If you do use AI tooling, it is helpful to share session recordings, prompts, plans or threads to show us how you work."*

This is the working-session write-up for that ask. `NOTES.md` covers the engineering decisions. This file covers how I directed the AI tooling to produce them.

## Tooling used

Claude Code (Opus 4.7, then 4.8) as the coding pair. Fresh session, one focused day. No prior context on Bead beyond a warm intro email from Jill and the challenge repo README.

I directed. Claude Code executed. The leverage was in being able to make Claude Code do targeted work in parallel while I stayed on the strategic thread.

## How the session was directed

### 1. Read the brief. Grill the research. Design before code.

First move was not to write code. I fanned out three parallel research agents:

- Study `bead-ai/zeitlich` (the reference harness). What patterns should I mirror?
- Study 2026 SOTA in vision, xlsx ingestion, and audit-AI stacks. What should I build with?
- Study `daukadolt/challenge` (a candidate believed to have been hired). What did he do, what are his gaps I can close?

By the time I wrote the first line of code I had a concrete architecture (LLM-parsed control, typed evidence extractors, per-attribute judge, deterministic reperformance for UAR), a model recommendation (Claude Opus for judgment, deterministic Python for reconciliation), and a named differentiator (deterministic UAR reperformance, which none of the other forks had).

### 2. Ship in vertical slices with staff-review gates

I set a rule: no branching into "maybe someday" features until the current slice was shippable. After each slice I explicitly asked Claude Code to grade the submission against Bead's stated criteria and against `daukadolt/challenge`, treating my own agent as an honest reviewer.

Several such reviews landed in this session. Each surfaced concrete weaknesses I then closed:

- Round 1 flagged "no tests, no CI". I shipped `tests/` with 8 reconciler tests plus `.github/workflows/ci.yml`.
- Round 2 flagged "Bead markets native Excel workpapers, you ship HTML only". I shipped `xlsx_workpaper.py` with the Cover, Attribute Verdicts, Evidence Citations, Reperformance, Evidence Inventory, and Decision Log sheet layout.
- Round 3 flagged "Bead markets IPE completeness testing, you don't do it". I shipped `_run_ipe_checks()` with 5 unit tests.
- Round 4 flagged a real credibility bug: my README claimed 87% but the committed `assessment.json` was 80% because Claude had flaked on a rerun. I fixed the number honestly, tuned the prompt, and re-ran.

The staff-review loop is the single most useful thing I did in this session. It's the difference between "I built something" and "I built something and stress-tested it against the actual bar".

### 3. Prompt engineering as its own discipline

Prompts live as versioned `.md` files at `src/audit_agent/prompts/*.md`. Every prompt tune was explicit and observed.

First tune (`attribute-isolation`). Claude was failing attributes for issues that belonged to a different attribute in the same control. I added: *"You are judging ONE named attribute. Do not fail this attribute based on issues that belong to a different attribute."* Change Management accuracy went from 4/6 to 6/6.

Second tune (`reperformance-caveat`). Claude was too pedantic on UAR remediation, reading "identified during the review" strictly and hedging on Kevin Lewis. I added: *"When the deterministic reconciler surfaces findings the reviewer missed, those findings ARE evidence about this attribute."* UAR went from 2/3 to 3/3.

Third tune (`exception-check-first`). Claude was hedging on the ICR testing attribute despite the exception clause applying (test-only maintenance). I added: *"Check exception clauses FIRST, before hedging on missing coverage evidence."* I also added a worked example. ICR went from 5/6 to 6/6.

The end state: Claude Opus 4.8 hits **15/15 (100%)** on my hand-labelled golden set. Each tune is a single commit. The reasoning is in the commit body and the prompt file diff.

### 4. Where I said no

Just as important as what shipped. I explicitly declined:

- A frontend. Bead asked for a CLI. A React app would signal I didn't read the brief. HTML report and Excel workpaper are the right visual artefacts.
- Async fan-out on per-attribute judges. Documented as future work. Not a submission blocker.
- PDF extraction. Bead's samples don't need it. Documented as future work.
- Conventional Commits. Zeitlich uses them; adopting mid-take-home is churn without signal. My commit history reads like a diary and I let it.
- A bigger golden set padded with vague labels. 15 rows every one defensible beats 50 rows most of which are hand-wavey.
- A Loom walkthrough for this submission specifically. `NOTES.md`, `SESSION.md`, the commit log, the versioned prompts, and `AGENTS.md` already document how this was built. Happy to record one on request in the debrief.

## Where to look for evidence of how I worked

| Signal | File |
| --- | --- |
| Engineering decisions and tradeoffs | `NOTES.md`. Includes the three questions I'd expect a Bead engineer to grill me on with honest answers. |
| Versioned prompts | `src/audit_agent/prompts/*.md`. Each file diffable, hashed into `trace.jsonl`. |
| Working-session narrative | `SESSION.md` (this file). |
| Agent-first repo conventions | `AGENTS.md`. |
| Iteration story | `git log --oneline`. Reads as: research, v1, self-review, tests, xlsx, IPE, prompt tunes, 4.8, magpies. |
| Per-attribute LLM audit trail | `output/<control>/<model>/trace.jsonl`. Every LLM call with prompt hash, tokens, cost, latency. |
| Eval discipline | `evals/golden.jsonl` (15 hand-labelled rows) plus `evals/README.md`. |
