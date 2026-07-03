# Evals

Hand-labelled behavioural test set for the LLM path of the pipeline. Zero-cost tests around the deterministic reconciler live under `tests/`; this directory covers the parts of the pipeline that involve model calls.

## `golden.jsonl`

One JSON object per line. Each row is one `(control × sample × attribute)` triple with the expected verdict and a human-readable note explaining the reasoning.

**Row shape:**

| Field | Type | Purpose |
| --- | --- | --- |
| `id` | string | Stable identifier — `<control>-<sample>-<slug>`. Category-aware slugs (e.g. `-testing`, `-remediation`, `-approval`, `-independence`, `-cadence`, `-ownership`) let the scoreboard slice by category. |
| `category` | string | Short tag: `review · independence · testing · cadence · ownership · remediation · documentation · approval · testing-evidence`. Enables per-category accuracy breakdowns. |
| `control_dir` | string | Path to the control (relative to repo root). Matches by directory name so cwd doesn't matter. |
| `sample_id` | string | Sample folder id under `samples/` (or "sample-1" if the control has no sub-samples). |
| `attribute_text` | string | Verbatim attribute text as written in `control.md`. Match is normalised so provider-specific attribute IDs don't matter. |
| `verdict` | enum | `SUCCESS` \| `FAIL` \| `FURTHER_EVIDENCE_REQUIRED`. |
| `notes` | string | Free-text rationale. Not scored — but if a reviewer wants to argue with a label, this is where the reasoning lives. |

## Category breakdown

Current golden set is **15 labelled rows** across the three controls:

| Control | Category | Row count |
| --- | --- | --- |
| independent-code-review | review | 2 |
| independent-code-review | independence | 2 |
| independent-code-review | testing | 2 |
| user-access-review | cadence | 1 |
| user-access-review | ownership | 1 |
| user-access-review | remediation | 1 |
| change-management | documentation | 2 |
| change-management | approval | 2 |
| change-management | testing-evidence | 2 |

Small on purpose. Every row is a defensible auditor call I can walk through in a debrief; padding the set with vague labels would make the scoreboard less honest, not more.

## Running the scoreboard

```bash
bead-agent eval data/independent-code-review --models claude,openai,gemini
```

Reads `golden.jsonl`, runs the pipeline under each model against the specified control, scores by normalised `attribute_text`, prints matches / mismatches with the golden verdict and the model's actual verdict side-by-side.

**Cost note:** each full multi-model eval run is ~$3-6 depending on cache warmth. Use `--models claude` for cheaper single-model iteration.

## Environment

Needs `ANTHROPIC_API_KEY` at minimum (default model is Claude). Add `OPENAI_API_KEY` / `GOOGLE_API_KEY` only for the multi-model scoreboard.

## Adding new golden entries

1. Hand-label with a defensible one-sentence reason.
2. Slug the `id` field to include the category (`<control>-<sample>-<category>`).
3. Set the `category` field for scoreboard slicing.
4. Match `attribute_text` verbatim to `control.md`.

Then re-run `bead-agent eval` to confirm the new rows behave.
