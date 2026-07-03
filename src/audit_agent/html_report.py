"""Self-contained HTML report generator.

Design goals:
    - Single file, no external CSS/JS/CDN. Works offline, emailable.
    - Workpaper aesthetic: audit reviewers should be able to skim in <30 seconds.
    - Every attribute expandable to full rationale + citations.
    - Trace log tabbed at the bottom (cost + latency per LLM call).
"""

from __future__ import annotations

import html
import json
from pathlib import Path
from typing import Any

from audit_agent.schemas import SampleAssessment, rollup_verdicts


_CSS = """
:root {
  --bg: #0e1116;
  --card: #161a22;
  --card-hover: #1c2130;
  --border: #232936;
  --text: #d5dae4;
  --muted: #7a8598;
  --accent: #6c8fff;
  --success: #4bcf87;
  --success-bg: rgba(75, 207, 135, 0.10);
  --fail: #ff6b6b;
  --fail-bg: rgba(255, 107, 107, 0.10);
  --warn: #f5c265;
  --warn-bg: rgba(245, 194, 101, 0.10);
  --code-bg: #0a0c11;
}
* { box-sizing: border-box; }
body {
  margin: 0;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Inter, Roboto,
    "Helvetica Neue", Arial, sans-serif;
  background: var(--bg);
  color: var(--text);
  line-height: 1.55;
  font-size: 15px;
}
.container {
  max-width: 960px;
  margin: 0 auto;
  padding: 48px 32px 96px;
}
header.hero {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding-bottom: 32px;
  border-bottom: 1px solid var(--border);
  margin-bottom: 32px;
}
header.hero .eyebrow {
  color: var(--muted);
  font-size: 13px;
  letter-spacing: 0.06em;
  text-transform: uppercase;
}
header.hero h1 { margin: 0; font-size: 32px; font-weight: 600; letter-spacing: -0.01em; }
header.hero .meta {
  color: var(--muted);
  font-size: 13px;
  font-family: ui-monospace, SFMono-Regular, "SF Mono", Menlo, monospace;
}
.badge {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 4px 12px;
  border-radius: 999px;
  font-size: 13px;
  font-weight: 600;
  letter-spacing: 0.02em;
}
.badge.pass    { color: var(--success); background: var(--success-bg); }
.badge.fail    { color: var(--fail);    background: var(--fail-bg); }
.badge.warn    { color: var(--warn);    background: var(--warn-bg); }
.badge .dot { width: 8px; height: 8px; border-radius: 50%; background: currentColor; }
.sample-card {
  background: var(--card);
  border: 1px solid var(--border);
  border-radius: 14px;
  padding: 28px;
  margin-bottom: 24px;
}
.sample-card h2 { margin: 0 0 16px 0; font-size: 20px; font-weight: 600; }
.sample-card .sample-meta {
  display: flex;
  gap: 24px;
  flex-wrap: wrap;
  color: var(--muted);
  font-size: 13px;
  margin-top: 8px;
}
.sample-card .sample-meta strong { color: var(--text); }
.section-title {
  color: var(--muted);
  font-size: 11px;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  margin: 24px 0 12px;
}
.reperformance {
  background: rgba(108, 143, 255, 0.06);
  border: 1px solid rgba(108, 143, 255, 0.25);
  border-radius: 10px;
  padding: 16px 20px;
  color: var(--text);
  font-family: ui-monospace, SFMono-Regular, "SF Mono", Menlo, monospace;
  font-size: 13px;
  line-height: 1.7;
  overflow-x: auto;
}
details.attribute {
  background: var(--card);
  border: 1px solid var(--border);
  border-left: 3px solid transparent;
  border-radius: 10px;
  margin-bottom: 12px;
  overflow: hidden;
  transition: border-color 0.15s ease;
}
details.attribute[data-verdict="SUCCESS"] { border-left-color: var(--success); }
details.attribute[data-verdict="FAIL"]    { border-left-color: var(--fail); }
details.attribute[data-verdict="FURTHER_EVIDENCE_REQUIRED"] { border-left-color: var(--warn); }
details.attribute > summary {
  list-style: none;
  cursor: pointer;
  padding: 18px 22px;
  display: grid;
  grid-template-columns: auto 1fr auto;
  gap: 16px;
  align-items: center;
}
details.attribute > summary::-webkit-details-marker { display: none; }
details.attribute > summary:hover { background: var(--card-hover); }
details.attribute .verdict-icon { font-size: 20px; line-height: 1; }
details.attribute .verdict-text {
  font-size: 11px;
  letter-spacing: 0.10em;
  text-transform: uppercase;
  font-weight: 600;
}
details.attribute[data-verdict="SUCCESS"] .verdict-text { color: var(--success); }
details.attribute[data-verdict="FAIL"] .verdict-text { color: var(--fail); }
details.attribute[data-verdict="FURTHER_EVIDENCE_REQUIRED"] .verdict-text { color: var(--warn); }
details.attribute .attr-title { font-weight: 500; font-size: 15px; color: var(--text); }
details.attribute .attr-meta {
  color: var(--muted);
  font-size: 12px;
  font-family: ui-monospace, SFMono-Regular, monospace;
  white-space: nowrap;
}
details.attribute .body {
  padding: 4px 22px 24px;
  border-top: 1px solid var(--border);
}
details.attribute[open] > summary { border-bottom: 1px solid var(--border); }
details.attribute .body h4 {
  color: var(--muted);
  font-size: 11px;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  font-weight: 600;
  margin: 20px 0 8px;
}
details.attribute .body p { margin: 12px 0 0; }
details.attribute .body ul { list-style: none; padding: 0; margin: 8px 0 0; }
details.attribute .body ul li {
  padding: 10px 0 10px 0;
  border-bottom: 1px solid var(--border);
  color: var(--text);
  font-size: 14px;
}
details.attribute .body ul li:last-child { border-bottom: none; }
details.attribute .body .file  { color: var(--accent); font-family: ui-monospace, monospace; font-size: 13px; }
details.attribute .body .loc   { color: #d38dff; font-family: ui-monospace, monospace; font-size: 13px; }
details.attribute .body .obs   { color: var(--muted); font-size: 13px; margin-top: 4px; }
details.attribute .body .quote { color: var(--text); font-style: italic; padding-left: 12px; border-left: 2px solid var(--border); margin-top: 6px; font-size: 13px; }
.coverage {
  display: flex;
  gap: 24px;
  padding: 12px 20px;
  background: var(--card);
  border: 1px solid var(--border);
  border-radius: 10px;
  margin-bottom: 24px;
  font-size: 13px;
  color: var(--muted);
}
.coverage strong { color: var(--text); }
.coverage .uncited { color: var(--warn); }
.trace-section h2 {
  font-size: 16px;
  color: var(--text);
  margin: 40px 0 12px;
}
.trace-table {
  width: 100%;
  border-collapse: collapse;
  font-family: ui-monospace, monospace;
  font-size: 12px;
}
.trace-table th, .trace-table td {
  padding: 8px 12px;
  border-bottom: 1px solid var(--border);
  text-align: left;
}
.trace-table th { color: var(--muted); font-weight: 500; text-transform: uppercase; font-size: 10px; letter-spacing: 0.10em; }
.trace-table td.num  { text-align: right; }
.trace-table td.cost { color: var(--success); text-align: right; }
.footer {
  margin-top: 60px;
  padding-top: 24px;
  border-top: 1px solid var(--border);
  color: var(--muted);
  font-size: 12px;
  text-align: center;
}
.footer code { color: var(--text); background: var(--code-bg); padding: 2px 6px; border-radius: 4px; }
"""


_VERDICT_ICON = {
    "SUCCESS": "✓",
    "FAIL": "✕",
    "FURTHER_EVIDENCE_REQUIRED": "?",
    "CONTROL_PASS": "✓",
    "CONTROL_FAIL": "✕",
    "CONTROL_INCONCLUSIVE": "?",
}
_BADGE_CLASS = {
    "SUCCESS": "pass",
    "FAIL": "fail",
    "FURTHER_EVIDENCE_REQUIRED": "warn",
    "CONTROL_PASS": "pass",
    "CONTROL_FAIL": "fail",
    "CONTROL_INCONCLUSIVE": "warn",
}


def _esc(x: Any) -> str:
    return html.escape(str(x)) if x is not None else ""


def _render_attribute(a: Any) -> str:
    verdict = a.verdict.value
    parts: list[str] = []
    parts.append(f'<details class="attribute" data-verdict="{verdict}">')
    parts.append("<summary>")
    parts.append(f'<div class="verdict-icon">{_VERDICT_ICON[verdict]}</div>')
    parts.append('<div class="attr-title">')
    parts.append(f"<div>{_esc(a.attribute_text)}</div>")
    parts.append(f'<div class="verdict-text">{verdict}</div>')
    parts.append("</div>")
    parts.append(
        f'<div class="attr-meta">conf {a.confidence:.2f} · {len(a.evidence_refs)} citations</div>'
    )
    parts.append("</summary>")
    parts.append('<div class="body">')

    parts.append("<h4>Rationale</h4>")
    parts.append(f"<p>{_esc(a.rationale)}</p>")

    if a.policy_references:
        parts.append("<h4>Policy references</h4>")
        parts.append("<ul>")
        for p in a.policy_references:
            parts.append("<li>")
            parts.append(f'<div><span class="file">{_esc(p.source)}</span>')
            parts.append(f" § {_esc(p.section)}</div>")
            parts.append(f'<div class="quote">{_esc(p.quote)}</div>')
            parts.append("</li>")
        parts.append("</ul>")

    if a.evidence_refs:
        parts.append("<h4>Evidence</h4>")
        parts.append("<ul>")
        for e in a.evidence_refs:
            parts.append("<li>")
            parts.append(
                f'<div><span class="file">{_esc(e.file)}</span> '
                f'@ <span class="loc">{_esc(e.locator)}</span></div>'
            )
            parts.append(f'<div class="obs">{_esc(e.observation)}</div>')
            parts.append("</li>")
        parts.append("</ul>")

    if a.exceptions_considered:
        parts.append("<h4>Exceptions considered</h4>")
        parts.append("<ul>")
        for x in a.exceptions_considered:
            parts.append(f"<li>{_esc(x)}</li>")
        parts.append("</ul>")

    parts.append("</div></details>")
    return "".join(parts)


def _render_sample(sa: SampleAssessment) -> str:
    parts: list[str] = []
    parts.append('<section class="sample-card">')
    conclusion = sa.control_conclusion.value
    parts.append(
        f'<div class="badge {_BADGE_CLASS[conclusion]}"><span class="dot"></span>'
        f"{conclusion}</div>"
    )
    parts.append(f"<h2>Sample: {_esc(sa.sample_id)}</h2>")
    parts.append('<div class="sample-meta">')
    parts.append(f"<span><strong>{sa.model}</strong></span>")
    parts.append(f"<span>generated: {_esc(sa.generated_at.isoformat())}</span>")
    if sa.consistency_disagreement_rate is not None:
        parts.append(
            f"<span>disagreement <strong>{sa.consistency_disagreement_rate:.0%}</strong></span>"
        )
    parts.append("</div>")

    if sa.reperformance_notes:
        parts.append('<div class="section-title">Reperformance summary</div>')
        parts.append(f'<div class="reperformance">{_esc(sa.reperformance_notes)}</div>')

    if sa.evidence_coverage:
        cov = sa.evidence_coverage
        parts.append('<div class="section-title">Evidence coverage</div>')
        parts.append('<div class="coverage">')
        parts.append(
            f"<div><strong>{int(cov.coverage_rate * 100)}%</strong> "
            f"({len(cov.cited_files)}/{len(cov.all_files)} files cited)</div>"
        )
        if cov.uncited_files:
            parts.append(
                f'<div class="uncited">Uncited: {_esc(", ".join(cov.uncited_files))}</div>'
            )
        parts.append("</div>")

    parts.append('<div class="section-title">Attribute verdicts</div>')
    for a in sa.attributes:
        parts.append(_render_attribute(a))
    parts.append("</section>")
    return "".join(parts)


def _render_trace(trace_path: Path) -> str:
    if not trace_path.exists():
        return ""
    rows: list[dict] = []
    for line in trace_path.read_text().splitlines():
        if not line.strip():
            continue
        rows.append(json.loads(line))
    if not rows:
        return ""

    total = sum(r.get("cost_usd") or 0 for r in rows)
    parts: list[str] = []
    parts.append('<section class="trace-section">')
    parts.append(
        f"<h2>LLM call trace <span style='color:var(--muted); font-size: 13px; font-weight: 400;'>· {len(rows)} calls · ${total:.4f}</span></h2>"
    )
    parts.append('<table class="trace-table">')
    parts.append(
        "<thead><tr>"
        "<th>#</th><th>Purpose</th><th>In</th><th>Cache</th><th>Out</th><th>$</th><th>Latency</th>"
        "</tr></thead>"
    )
    parts.append("<tbody>")
    for i, r in enumerate(rows, 1):
        parts.append("<tr>")
        parts.append(f"<td>{i}</td>")
        parts.append(f'<td>{_esc(r.get("purpose", "?"))}</td>')
        parts.append(f'<td class="num">{r.get("input_tokens") or 0:,}</td>')
        parts.append(f'<td class="num">{r.get("cache_read_tokens") or 0:,}</td>')
        parts.append(f'<td class="num">{r.get("output_tokens") or 0:,}</td>')
        parts.append(f'<td class="cost">${r.get("cost_usd") or 0:.4f}</td>')
        parts.append(f'<td class="num">{r.get("latency_ms") or 0}ms</td>')
        parts.append("</tr>")
    parts.append("</tbody></table>")
    parts.append("</section>")
    return "".join(parts)


def build_report(run_dir: Path) -> Path:
    """Scan run_dir for assessment.json files and write report.html alongside them."""
    assessments: list[SampleAssessment] = []
    for sub in sorted(run_dir.iterdir()):
        if sub.is_dir():
            ap = sub / "assessment.json"
            if ap.exists():
                raw = json.loads(ap.read_text())
                # Back-compat for pre-rollup outputs: derive control_conclusion
                # from the attribute verdicts if the file doesn't have it yet.
                if "control_conclusion" not in raw:
                    from audit_agent.schemas import Verdict
                    raw["control_conclusion"] = rollup_verdicts(
                        [Verdict(a["verdict"]) for a in raw.get("attributes", [])]
                    ).value
                assessments.append(SampleAssessment(**raw))
    if not assessments:
        raise FileNotFoundError(f"No sample assessments found under {run_dir}")

    control = assessments[0].control
    model = assessments[0].model

    conclusions = {sa.control_conclusion.value for sa in assessments}
    if "CONTROL_FAIL" in conclusions:
        run_verdict = "CONTROL_FAIL"
    elif "CONTROL_INCONCLUSIVE" in conclusions:
        run_verdict = "CONTROL_INCONCLUSIVE"
    else:
        run_verdict = "CONTROL_PASS"

    parts = [
        "<!doctype html><html lang=\"en\"><head><meta charset=\"utf-8\">",
        f"<title>Audit report — {_esc(control)}</title>",
        '<meta name="viewport" content="width=device-width, initial-scale=1">',
        f"<style>{_CSS}</style></head><body>",
        '<div class="container">',
        '<header class="hero">',
        '<div class="eyebrow">Bead audit report</div>',
        f"<h1>{_esc(control)}</h1>",
        '<div class="meta">',
        f"model {_esc(model)} · {len(assessments)} sample(s)",
        "</div>",
        '<div style="margin-top:12px;">',
        f'<span class="badge {_BADGE_CLASS[run_verdict]}"><span class="dot"></span>'
        f"{run_verdict}</span>",
        "</div>",
        "</header>",
    ]

    for sa in assessments:
        parts.append(_render_sample(sa))

    parts.append(_render_trace(run_dir / "trace.jsonl"))

    parts.append(
        '<div class="footer">'
        "Generated by <code>bead-agent report</code> · "
        "self-contained, no external assets."
        "</div>"
    )
    parts.append("</div></body></html>")

    out_path = run_dir / "report.html"
    out_path.write_text("".join(parts))
    return out_path
