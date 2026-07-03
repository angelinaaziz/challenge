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
/* Bead-themed audit report — light mode. Warm paper background, deep forest ink,
   restrained mint accent. Palette pulled from usebead.ai. No external assets. */
:root {
  --paper: #faf8f3;          /* warm cream page background */
  --paper-soft: #f2efe6;
  --card: #ffffff;
  --border: #e5e0d2;         /* soft warm border */
  --border-strong: #d1cbba;
  --ink: #0b362c;            /* deep forest — headings + primary text */
  --ink-2: #1c6151;          /* softer forest for body */
  --muted: #6f6a5f;
  --muted-2: #928c7c;
  --accent: #148f72;         /* Bead deep mint — high contrast on paper */
  --accent-2: #88d98d;       /* Bead bright mint — badges and highlights */
  --accent-soft: rgba(20, 143, 114, 0.08);

  --pass: #148f72;
  --pass-soft: rgba(20, 143, 114, 0.10);
  --pass-border: rgba(20, 143, 114, 0.28);

  --fail: #b83a2e;
  --fail-soft: rgba(184, 58, 46, 0.06);
  --fail-border: rgba(184, 58, 46, 0.24);

  --warn: #a17321;
  --warn-soft: rgba(161, 115, 33, 0.06);
  --warn-border: rgba(161, 115, 33, 0.24);
}
* { box-sizing: border-box; }
html, body { background: var(--paper); }
body {
  margin: 0;
  font-family: -apple-system, BlinkMacSystemFont, "SF Pro Text", Inter,
    "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
  color: var(--ink-2);
  line-height: 1.6;
  font-size: 14px;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}
.mono {
  font-family: ui-monospace, "SF Mono", "JetBrains Mono", Menlo, Consolas, monospace;
}
.container {
  max-width: 880px;
  margin: 0 auto;
  padding: 72px 40px 96px;
}

/* --- Header --- */
header.hero {
  padding-bottom: 32px;
  margin-bottom: 40px;
  border-bottom: 1px solid var(--border);
}
header.hero .eyebrow {
  color: var(--accent);
  font-size: 11px;
  letter-spacing: 0.20em;
  text-transform: uppercase;
  font-weight: 600;
  margin-bottom: 16px;
  display: flex;
  align-items: center;
  gap: 10px;
}
header.hero .eyebrow::before {
  content: "";
  width: 6px; height: 6px;
  border-radius: 50%;
  background: var(--accent-2);
  box-shadow: 0 0 0 4px var(--accent-soft);
}
header.hero h1 {
  margin: 0;
  font-size: 32px;
  font-weight: 500;
  letter-spacing: -0.02em;
  color: var(--ink);
  line-height: 1.2;
}
header.hero .meta {
  color: var(--muted);
  font-size: 13px;
  margin-top: 8px;
}
header.hero .meta strong { color: var(--ink); font-weight: 500; }

/* --- BLUF (bottom-line-up-front) verdict banner --- */
.bluf {
  display: grid;
  grid-template-columns: auto 1fr;
  gap: 32px;
  align-items: center;
  padding: 40px;
  border-radius: 12px;
  margin-bottom: 48px;
  border: 1px solid;
}
.bluf.pass { background: var(--pass-soft); border-color: var(--pass-border); }
.bluf.fail { background: var(--fail-soft); border-color: var(--fail-border); }
.bluf.warn { background: var(--warn-soft); border-color: var(--warn-border); }
.bluf .verdict-icon-lg {
  width: 84px; height: 84px;
  border-radius: 50%;
  display: flex; align-items: center; justify-content: center;
  font-size: 40px; font-weight: 700;
  border: 3px solid;
}
.bluf.pass .verdict-icon-lg { color: var(--pass); border-color: var(--pass); background: white; }
.bluf.fail .verdict-icon-lg { color: var(--fail); border-color: var(--fail); background: white; }
.bluf.warn .verdict-icon-lg { color: var(--warn); border-color: var(--warn); background: white; }
.bluf .verdict-body {}
.bluf .verdict-label {
  font-size: 12px; letter-spacing: 0.20em;
  text-transform: uppercase; font-weight: 700;
  margin-bottom: 8px;
}
.bluf.pass .verdict-label { color: var(--pass); }
.bluf.fail .verdict-label { color: var(--fail); }
.bluf.warn .verdict-label { color: var(--warn); }
.bluf .verdict-headline {
  font-size: 28px; font-weight: 500;
  color: var(--ink); letter-spacing: -0.02em;
  line-height: 1.25; margin: 0;
}
.bluf .verdict-context {
  color: var(--muted); font-size: 13px; margin-top: 12px;
}

/* --- Badges --- */
.badge {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 6px 12px 6px 10px;
  border-radius: 4px;
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  border: 1px solid;
  margin-top: 24px;
}
.badge.pass { color: var(--pass); background: var(--pass-soft); border-color: var(--pass-border); }
.badge.fail { color: var(--fail); background: var(--fail-soft); border-color: var(--fail-border); }
.badge.warn { color: var(--warn); background: var(--warn-soft); border-color: var(--warn-border); }
.badge .dot { width: 6px; height: 6px; border-radius: 50%; background: currentColor; }

/* --- Sample sections --- */
.sample-card {
  padding: 40px 0 8px;
  border-bottom: 1px solid var(--border);
  margin-bottom: 40px;
}
.sample-card:last-of-type { border-bottom: none; margin-bottom: 24px; }
.sample-card .sample-header {
  display: flex;
  align-items: baseline;
  gap: 20px;
  margin-bottom: 8px;
}
.sample-card .sample-label {
  color: var(--muted);
  font-size: 11px;
  letter-spacing: 0.20em;
  text-transform: uppercase;
  font-weight: 600;
}
.sample-card h2 {
  margin: 8px 0 0 0;
  font-size: 24px;
  font-weight: 500;
  letter-spacing: -0.015em;
  color: var(--ink);
}
.sample-card .sample-meta {
  display: flex;
  gap: 32px;
  flex-wrap: wrap;
  color: var(--muted);
  font-size: 12px;
  margin-top: 12px;
}
.sample-card .sample-meta strong { color: var(--ink); font-weight: 500; }

/* --- Section titles --- */
.section-title {
  color: var(--muted);
  font-size: 10px;
  letter-spacing: 0.20em;
  text-transform: uppercase;
  font-weight: 600;
  margin: 40px 0 16px;
}

/* --- Executive summary --- */
.exec-summary {
  font-size: 16px;
  line-height: 1.65;
  color: var(--ink);
  padding: 20px 0 4px;
  border-left: 3px solid var(--accent);
  padding-left: 20px;
  margin-bottom: 4px;
}

/* --- Findings --- */
ul.findings { list-style: none; padding: 0; margin: 0 0 8px; }
ul.findings li.finding {
  display: grid;
  grid-template-columns: 24px 1fr;
  gap: 12px;
  padding: 12px 0;
  border-bottom: 1px solid var(--border);
  align-items: start;
}
ul.findings li.finding:last-child { border-bottom: none; }
ul.findings .finding-icon {
  font-size: 13px;
  line-height: 1.4;
  text-align: center;
}
ul.findings li.pass .finding-icon { color: var(--pass); }
ul.findings li.warn .finding-icon { color: var(--warn); }
ul.findings li.fail .finding-icon { color: var(--fail); }
ul.findings .finding-text {
  font-size: 14px;
  color: var(--ink-2);
  line-height: 1.5;
}
ul.findings li.fail .finding-text { color: var(--ink); font-weight: 500; }

/* --- Recommended actions --- */
ol.actions {
  padding-left: 20px;
  margin: 0 0 24px;
  color: var(--ink-2);
}
ol.actions li {
  padding: 8px 0;
  font-size: 14px;
  line-height: 1.55;
}
ol.actions li::marker { color: var(--accent); font-weight: 600; }

/* --- Reperformance callout --- */
.reperformance {
  background: var(--accent-soft);
  border: 1px solid rgba(20, 143, 114, 0.16);
  border-left: 3px solid var(--accent);
  border-radius: 6px;
  padding: 20px 24px;
  color: var(--ink);
  font-size: 13px;
  line-height: 1.75;
  overflow-x: auto;
  font-family: ui-monospace, "SF Mono", Menlo, monospace;
}
.reperformance-label {
  color: var(--accent);
  font-size: 10px;
  letter-spacing: 0.20em;
  text-transform: uppercase;
  margin-bottom: 12px;
  font-weight: 600;
  font-family: -apple-system, BlinkMacSystemFont, Inter, sans-serif;
}

/* --- Coverage strip --- */
.coverage {
  display: flex;
  gap: 40px;
  padding: 16px 0;
  color: var(--muted);
  font-size: 13px;
  border-top: 1px solid var(--border);
  border-bottom: 1px solid var(--border);
  margin-bottom: 32px;
}
.coverage .label { color: var(--muted); font-size: 11px; letter-spacing: 0.14em; text-transform: uppercase; font-weight: 600; }
.coverage .value { color: var(--ink); font-size: 15px; font-weight: 500; margin-top: 2px; }
.coverage .uncited .value { color: var(--warn); }

/* --- Attribute cards --- */
details.attribute {
  background: var(--card);
  border: 1px solid var(--border);
  border-radius: 8px;
  margin-bottom: 12px;
  overflow: hidden;
  transition: border-color 0.15s ease, box-shadow 0.15s ease;
}
details.attribute:hover { border-color: var(--border-strong); }
details.attribute[open] { box-shadow: 0 1px 2px rgba(11, 54, 44, 0.04); }
details.attribute > summary {
  list-style: none;
  cursor: pointer;
  padding: 20px 24px;
  display: grid;
  grid-template-columns: auto 1fr auto;
  gap: 20px;
  align-items: center;
}
details.attribute > summary::-webkit-details-marker { display: none; }
details.attribute > summary:hover { background: var(--paper-soft); }
details.attribute[open] > summary { background: var(--paper-soft); }
details.attribute .verdict-icon {
  font-size: 12px;
  font-weight: 700;
  width: 22px; height: 22px;
  border-radius: 50%;
  display: inline-flex; align-items: center; justify-content: center;
  border: 1.5px solid;
  line-height: 1;
}
details.attribute[data-verdict="SUCCESS"] .verdict-icon { color: var(--pass); border-color: var(--pass); background: var(--pass-soft); }
details.attribute[data-verdict="FAIL"] .verdict-icon    { color: var(--fail); border-color: var(--fail); background: var(--fail-soft); }
details.attribute[data-verdict="FURTHER_EVIDENCE_REQUIRED"] .verdict-icon { color: var(--warn); border-color: var(--warn); background: var(--warn-soft); }
details.attribute .attr-title {
  font-weight: 500;
  font-size: 15px;
  color: var(--ink);
  letter-spacing: -0.005em;
  line-height: 1.45;
}
details.attribute .verdict-text {
  font-size: 10px;
  letter-spacing: 0.18em;
  text-transform: uppercase;
  font-weight: 700;
  margin-top: 4px;
}
details.attribute[data-verdict="SUCCESS"] .verdict-text { color: var(--pass); }
details.attribute[data-verdict="FAIL"] .verdict-text    { color: var(--fail); }
details.attribute[data-verdict="FURTHER_EVIDENCE_REQUIRED"] .verdict-text { color: var(--warn); }
details.attribute .attr-meta {
  color: var(--muted);
  font-size: 11px;
  white-space: nowrap;
  text-align: right;
  line-height: 1.4;
  font-family: ui-monospace, Menlo, monospace;
}
details.attribute .attr-meta strong { color: var(--ink); font-weight: 600; }
details.attribute .body {
  padding: 4px 28px 28px;
  border-top: 1px solid var(--border);
  background: var(--card);
}
details.attribute .body h4 {
  color: var(--muted);
  font-size: 10px;
  letter-spacing: 0.20em;
  text-transform: uppercase;
  font-weight: 600;
  margin: 24px 0 10px;
}
details.attribute .body p {
  margin: 0;
  color: var(--ink-2);
  font-size: 14px;
  line-height: 1.65;
}
details.attribute .body ul { list-style: none; padding: 0; margin: 0; }
details.attribute .body ul li {
  padding: 14px 0;
  border-bottom: 1px solid var(--border);
  font-size: 13px;
}
details.attribute .body ul li:last-child { border-bottom: none; padding-bottom: 4px; }
details.attribute .body .file  { color: var(--accent); font-size: 13px; font-family: ui-monospace, Menlo, monospace; font-weight: 500; }
details.attribute .body .loc   { color: var(--ink); background: var(--accent-soft); padding: 1px 6px; border-radius: 3px; font-size: 12px; font-family: ui-monospace, Menlo, monospace; }
details.attribute .body .obs   { color: var(--muted); font-size: 13px; margin-top: 6px; line-height: 1.55; }
details.attribute .body .quote {
  color: var(--ink-2); padding: 10px 14px;
  border-left: 2px solid var(--accent);
  background: var(--accent-soft);
  margin-top: 8px;
  font-size: 13px;
  font-style: italic;
  border-radius: 0 4px 4px 0;
}

/* --- Trace table --- */
.trace-section h2 {
  font-size: 20px;
  font-weight: 500;
  color: var(--ink);
  margin: 56px 0 6px;
  letter-spacing: -0.015em;
}
.trace-section .trace-meta {
  color: var(--muted); font-size: 12px; margin-bottom: 20px;
}
.trace-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 12px;
  font-family: ui-monospace, "SF Mono", Menlo, monospace;
  background: var(--card);
  border: 1px solid var(--border);
  border-radius: 6px;
  overflow: hidden;
}
.trace-table th, .trace-table td {
  padding: 11px 14px;
  border-bottom: 1px solid var(--border);
  text-align: left;
  color: var(--ink);
}
.trace-table tbody tr:last-child td { border-bottom: none; }
.trace-table tbody tr:hover { background: var(--paper-soft); }
.trace-table th {
  color: var(--muted); font-weight: 600;
  text-transform: uppercase; font-size: 10px;
  letter-spacing: 0.16em;
  background: var(--paper-soft);
  font-family: -apple-system, Inter, sans-serif;
}
.trace-table td.num  { text-align: right; color: var(--ink-2); }
.trace-table td.cost { color: var(--accent); text-align: right; font-weight: 500; }

/* --- Evidence inventory --- */
.inventory {
  border: 1px solid var(--border);
  border-radius: 8px;
  overflow: hidden;
  background: var(--card);
  margin-bottom: 20px;
}
.inventory-row {
  display: grid;
  grid-template-columns: auto 1fr auto;
  gap: 20px;
  padding: 16px 20px;
  border-bottom: 1px solid var(--border);
  align-items: center;
}
.inventory-row:last-child { border-bottom: none; }
.inventory-row .kind-pill {
  font-size: 10px;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: var(--accent);
  background: var(--accent-soft);
  padding: 4px 10px;
  border-radius: 4px;
  font-weight: 600;
  font-family: ui-monospace, Menlo, monospace;
}
.inventory-row .file-body { min-width: 0; }
.inventory-row .file-name {
  color: var(--ink); font-weight: 500; font-size: 14px;
  font-family: ui-monospace, Menlo, monospace;
  margin-bottom: 4px;
  word-break: break-all;
}
.inventory-row .file-summary { color: var(--muted); font-size: 12px; line-height: 1.5; }
.inventory-row .cited-pill {
  font-size: 11px;
  padding: 4px 10px;
  border-radius: 4px;
  white-space: nowrap;
  font-weight: 500;
}
.inventory-row .cited-pill.cited {
  color: var(--pass); background: var(--pass-soft); border: 1px solid var(--pass-border);
}
.inventory-row .cited-pill.uncited {
  color: var(--warn); background: var(--warn-soft); border: 1px solid var(--warn-border);
}

/* --- Sign-off --- */
.signoff {
  background: var(--card);
  border: 1px solid var(--border);
  border-radius: 10px;
  padding: 32px;
  margin-top: 48px;
}
.signoff h3 {
  margin: 0 0 8px 0;
  font-size: 20px; font-weight: 500;
  letter-spacing: -0.015em;
  color: var(--ink);
}
.signoff .signoff-note {
  color: var(--muted); font-size: 13px; margin-bottom: 24px;
  line-height: 1.55;
}
.signoff .decision-row {
  display: flex; gap: 12px; flex-wrap: wrap;
  margin-bottom: 24px;
}
.signoff .decision-btn {
  padding: 12px 20px;
  border-radius: 6px;
  border: 1px solid var(--border);
  font-size: 13px; font-weight: 500;
  color: var(--muted); background: var(--paper);
  cursor: pointer;
  transition: all 0.15s ease;
  font-family: inherit;
  display: flex; align-items: center; gap: 8px;
}
.signoff .decision-btn:hover { border-color: var(--border-strong); color: var(--ink); }
.signoff .decision-btn.accept:hover { border-color: var(--pass); color: var(--pass); background: var(--pass-soft); }
.signoff .decision-btn.reject:hover { border-color: var(--fail); color: var(--fail); background: var(--fail-soft); }
.signoff .decision-btn.rework:hover { border-color: var(--warn); color: var(--warn); background: var(--warn-soft); }
.signoff .fields {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
  margin-top: 24px;
}
.signoff .field label {
  display: block;
  font-size: 11px; letter-spacing: 0.12em;
  text-transform: uppercase; font-weight: 600;
  color: var(--muted); margin-bottom: 8px;
}
.signoff .field input,
.signoff .field textarea {
  width: 100%;
  padding: 10px 14px;
  font-size: 14px;
  border: 1px solid var(--border);
  border-radius: 6px;
  background: var(--paper);
  color: var(--ink);
  font-family: inherit;
}
.signoff .field input:focus,
.signoff .field textarea:focus {
  outline: none; border-color: var(--accent);
  box-shadow: 0 0 0 3px var(--accent-soft);
}
.signoff .field.wide { grid-column: 1 / -1; }
.signoff .field textarea { min-height: 80px; resize: vertical; }

/* --- Footer --- */
.footer {
  margin-top: 60px;
  padding-top: 28px;
  border-top: 1px solid var(--border);
  color: var(--muted-2);
  font-size: 11px;
  text-align: center;
  letter-spacing: 0.05em;
}
.footer code {
  color: var(--ink); background: var(--paper-soft);
  padding: 3px 8px; border-radius: 3px; font-size: 11px;
  font-family: ui-monospace, Menlo, monospace;
}
.footer a { color: var(--accent); text-decoration: none; }

@media print {
  body { background: white; color: black; }
  details.attribute { break-inside: avoid; }
  details.attribute[open] > summary { background: none; }
  details.attribute .body { display: block !important; }
}
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
    parts.append(f'<div class="verdict-text">{verdict.replace("_", " ")}</div>')
    parts.append("</div>")
    parts.append(
        f'<div class="attr-meta">Confidence <strong>{a.confidence:.2f}</strong><br>'
        f"{len(a.evidence_refs)} citation{'s' if len(a.evidence_refs) != 1 else ''}</div>"
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
    parts.append('<div class="sample-header">')
    parts.append('<div>')
    parts.append('<div class="sample-label">Sample</div>')
    parts.append(f"<h2>{_esc(sa.sample_id)}</h2>")
    parts.append('</div>')
    parts.append(
        f'<div class="badge {_BADGE_CLASS[conclusion]}" style="margin-top:0;"><span class="dot"></span>'
        f"{conclusion.replace('_', ' ')}</div>"
    )
    parts.append('</div>')

    parts.append('<div class="sample-meta">')
    parts.append(f"<span><strong>{sa.model}</strong></span>")
    parts.append(f'<span>generated {_esc(sa.generated_at.strftime("%d %b %Y, %H:%M UTC"))}</span>')
    if sa.consistency_disagreement_rate is not None:
        parts.append(
            f"<span>disagreement <strong>{sa.consistency_disagreement_rate:.0%}</strong></span>"
        )
    parts.append("</div>")

    # --- Executive summary (what happened + why) --------------------------
    if sa.executive_summary:
        parts.append('<div class="section-title">Executive summary</div>')
        parts.append(f'<div class="exec-summary">{_esc(sa.executive_summary)}</div>')

    # --- Key findings ------------------------------------------------------
    if sa.key_findings:
        parts.append('<div class="section-title">Key findings</div>')
        parts.append('<ul class="findings">')
        sev_class = {"pass": "pass", "warn": "warn", "fail": "fail"}
        sev_icon = {"pass": "●", "warn": "▲", "fail": "■"}
        for f in sa.key_findings:
            parts.append(
                f'<li class="finding {sev_class[f.severity]}">'
                f'<span class="finding-icon">{sev_icon[f.severity]}</span>'
                f'<span class="finding-text">{_esc(f.text)}</span>'
                f"</li>"
            )
        parts.append('</ul>')

    # --- Recommended actions ----------------------------------------------
    if sa.recommended_actions:
        parts.append('<div class="section-title">What to do next</div>')
        parts.append('<ol class="actions">')
        for act in sa.recommended_actions:
            parts.append(f"<li>{_esc(act)}</li>")
        parts.append('</ol>')

    if sa.reperformance_notes:
        parts.append('<div class="section-title">Reperformance</div>')
        parts.append('<div class="reperformance">')
        parts.append('<div class="reperformance-label">Deterministic re-check · ground truth</div>')
        parts.append(_esc(sa.reperformance_notes))
        parts.append('</div>')
    # IPE checks — surface even if there's no LLM-produced narrative.
    # We store IPE in the same trace JSONL / assessment JSON.
    ipe_html = _render_ipe_checks(sa)
    if ipe_html:
        parts.append(ipe_html)

    if sa.evidence_coverage:
        cov = sa.evidence_coverage
        parts.append('<div class="coverage">')
        parts.append('<div>')
        parts.append('<div class="label">Evidence coverage</div>')
        parts.append(f'<div class="value">{int(cov.coverage_rate * 100)}%</div>')
        parts.append('</div>')
        parts.append('<div>')
        parts.append('<div class="label">Files cited</div>')
        parts.append(f'<div class="value">{len(cov.cited_files)} of {len(cov.all_files)}</div>')
        parts.append('</div>')
        if cov.uncited_files:
            parts.append('<div class="uncited">')
            parts.append('<div class="label">Uncited</div>')
            parts.append(f'<div class="value">{_esc(", ".join(cov.uncited_files))}</div>')
            parts.append('</div>')
        parts.append("</div>")

    parts.append('<div class="section-title">Attribute verdicts</div>')
    for a in sa.attributes:
        parts.append(_render_attribute(a))

    # Evidence inventory — what was tested, in what file.
    parts.append(_render_evidence_inventory(sa))

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
        f"<h2>Decision log <span style='color:var(--muted); font-size: 13px; font-weight: 400;'>· {len(rows)} LLM calls · ${total:.4f}</span></h2>"
    )
    parts.append(
        '<div class="trace-meta">Every judgment the agent made. '
        "Each row is one LLM call &mdash; the audit-trail record of how the verdict was reached.</div>"
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


def _render_ipe_checks(sa: SampleAssessment) -> str:
    """IPE (Information Produced by the Entity) check results — deterministic
    reconciliation of the source data against its own declared numbers.

    Rendered as a callout so an auditor sees IPE integrity findings before
    they read reviewer decisions on top of the source data."""
    if not sa.ipe_checks:
        return ""
    fail_count = sum(1 for c in sa.ipe_checks if c.status == "fail")
    label = (
        "IPE integrity checks · all passed"
        if fail_count == 0
        else f"IPE integrity checks · {fail_count} finding(s)"
    )
    parts = ['<div class="section-title">IPE (Information Produced by the Entity)</div>']
    parts.append('<div class="reperformance">')
    parts.append(f'<div class="reperformance-label">{label}</div>')
    for c in sa.ipe_checks:
        badge = {"pass": "✓", "fail": "✕", "not_declared": "—"}[c.status]
        colour = {"pass": "var(--pass)", "fail": "var(--fail)", "not_declared": "var(--muted)"}[c.status]
        parts.append(
            f'<div style="margin: 8px 0; display: flex; gap: 12px;">'
            f'<span style="color: {colour}; font-weight: 600; width: 16px;">{badge}</span>'
            f'<span><strong style="color: var(--ink);">{_esc(c.check)}</strong><br>'
            f'<span style="color: var(--muted); font-size: 12px;">{_esc(c.detail)}</span></span>'
            f"</div>"
        )
    parts.append("</div>")
    return "".join(parts)


def _render_evidence_inventory(sa: SampleAssessment) -> str:
    if not sa.evidence_inventory:
        return ""
    parts = ['<div class="section-title">Evidence inventory · what was tested</div>']
    parts.append('<div class="inventory">')
    for ei in sa.evidence_inventory:
        cited_class = "cited" if ei.cited_by_attributes else "uncited"
        cited_label = (
            f"Cited by {len(ei.cited_by_attributes)} verdict"
            f"{'s' if len(ei.cited_by_attributes) != 1 else ''}"
            if ei.cited_by_attributes
            else "Uncited"
        )
        kb = ei.bytes_size / 1024
        size_str = f"{kb:.1f} KB" if kb < 1024 else f"{kb/1024:.1f} MB"
        parts.append('<div class="inventory-row">')
        parts.append(f'<div class="kind-pill">{_esc(ei.kind)}</div>')
        parts.append('<div class="file-body">')
        parts.append(f'<div class="file-name">{_esc(ei.file)} <span style="color:var(--muted-2); font-weight:400;">· {size_str}</span></div>')
        parts.append(f'<div class="file-summary">{_esc(ei.extraction_summary)}</div>')
        parts.append("</div>")
        parts.append(f'<div class="cited-pill {cited_class}">{_esc(cited_label)}</div>')
        parts.append("</div>")
    parts.append("</div>")
    return "".join(parts)


def _render_signoff(control: str, model: str, run_verdict: str) -> str:
    """Human sign-off area — auditor accept/reject/rework + name + date + notes.

    On submit, the browser downloads a JSON manifest of the decision — the
    audit-file convention. No backend required: everything is client-side,
    the manifest is deterministic-format so a human can attach it to the
    workpaper file. In a production Bead deployment this would POST to the
    audit-log service; for the take-home the JSON download is proof-of-shape.
    """
    manifest_js = (
        "function signoffManifest(decision){"
        "const now = new Date().toISOString();"
        f"const manifest = {{"
        f"  workpaper: {json.dumps(control)},"
        f"  model: {json.dumps(model)},"
        f"  ai_conclusion: {json.dumps(run_verdict)},"
        "  reviewer_decision: decision,"
        "  reviewer_name: document.getElementById('rev-name').value || null,"
        "  reviewer_date: document.getElementById('rev-date').value || null,"
        "  reviewer_notes: document.getElementById('rev-notes').value || null,"
        "  signed_at: now,"
        "  report_url: window.location.href,"
        "};"
        "if (!manifest.reviewer_name) {"
        "  alert('Please enter your name before signing off.');"
        "  document.getElementById('rev-name').focus();"
        "  return;"
        "}"
        "if (!manifest.reviewer_date) {"
        "  manifest.reviewer_date = now.slice(0,10);"
        "}"
        "const blob = new Blob([JSON.stringify(manifest, null, 2)], "
        "  {type:'application/json'});"
        "const a = document.createElement('a');"
        "a.href = URL.createObjectURL(blob);"
        "a.download = 'signoff-' + decision.toLowerCase() + '-' + now.slice(0,10) + '.json';"
        "a.click();"
        "URL.revokeObjectURL(a.href);"
        "document.getElementById('signoff-status').innerHTML = "
        "  '<strong>' + decision + '</strong> recorded &middot; ' + "
        "  'manifest downloaded &middot; attach to workpaper file.';"
        "document.getElementById('signoff-status').style.color = "
        "  decision === 'ACCEPT' ? 'var(--pass)' : "
        "  decision === 'REJECT' ? 'var(--fail)' : 'var(--warn)';"
        "}"
    )
    return (
        f"<script>{manifest_js}</script>"
        '<div class="signoff">'
        '<h3>Reviewer sign-off</h3>'
        '<div class="signoff-note">'
        "The AI agent proposed the verdicts above. As the responsible auditor, "
        "accept, reject, or send back for rework. Your decision downloads a signed "
        "JSON manifest — attach that to your workpaper file as the human-in-the-loop record."
        "</div>"
        '<div class="fields" style="margin-bottom: 24px;">'
        '<div class="field"><label for="rev-name">Reviewer name (required)</label>'
        '<input id="rev-name" type="text" placeholder="e.g. Priya Nadkarni, Director of Finance Systems"></div>'
        '<div class="field"><label for="rev-date">Sign-off date</label>'
        '<input id="rev-date" type="date"></div>'
        '<div class="field wide"><label for="rev-notes">Rationale / conditions / follow-up</label>'
        '<textarea id="rev-notes" placeholder="Optional: reasons for the decision, any conditions on acceptance, follow-up required..."></textarea></div>'
        "</div>"
        '<div class="decision-row">'
        '<button type="button" class="decision-btn accept" onclick="signoffManifest(\'ACCEPT\')">'
        "&check; Accept AI conclusion</button>"
        '<button type="button" class="decision-btn rework" onclick="signoffManifest(\'REWORK\')">'
        "&#9998; Send back for rework</button>"
        '<button type="button" class="decision-btn reject" onclick="signoffManifest(\'REJECT\')">'
        "&times; Reject conclusion</button>"
        "</div>"
        '<div id="signoff-status" style="margin-top: 16px; font-size: 13px; color: var(--muted);"></div>'
        "</div>"
    )


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

    # Build the BLUF headline sentence.
    fails_total = 0
    hedged_total = 0
    for sa in assessments:
        for a in sa.attributes:
            if a.verdict.value == "FAIL":
                fails_total += 1
            elif a.verdict.value == "FURTHER_EVIDENCE_REQUIRED":
                hedged_total += 1

    if run_verdict == "CONTROL_PASS":
        bluf_label = "Control passed"
        bluf_headline = "All tested attributes met their criteria."
        bluf_context = "No remediation actions raised. Retain the workpaper for the audit file."
    elif run_verdict == "CONTROL_FAIL":
        bluf_label = "Control failed"
        bluf_headline = (
            f"{fails_total} attribute{'s' if fails_total != 1 else ''} "
            f"positively contradicted by the evidence."
        )
        bluf_context = (
            f"{hedged_total} additional attribute{'s' if hedged_total != 1 else ''} "
            "need supplementary evidence to close. Action list below."
            if hedged_total else
            "See recommended actions per sample below."
        )
    else:  # INCONCLUSIVE
        bluf_label = "Cannot sign off yet"
        bluf_headline = (
            f"{hedged_total} attribute{'s' if hedged_total != 1 else ''} "
            "need supplementary evidence before this control can be concluded."
        )
        bluf_context = "See action list per sample below."
    bluf_class = _BADGE_CLASS[run_verdict]

    parts = [
        "<!doctype html><html lang=\"en\"><head><meta charset=\"utf-8\">",
        f"<title>Bead · {_esc(control)}</title>",
        '<meta name="viewport" content="width=device-width, initial-scale=1">',
        f"<style>{_CSS}</style></head><body>",
        '<div class="container">',
        '<header class="hero">',
        '<div class="eyebrow">Bead audit workpaper</div>',
        f'<h1 class="display">{_esc(control)}</h1>',
        '<div class="meta">',
        f"Tested by <strong>{_esc(model)}</strong> across "
        f"<strong>{len(assessments)}</strong> sample{'s' if len(assessments) != 1 else ''}",
        "</div>",
        "</header>",
        # BLUF banner
        f'<div class="bluf {bluf_class}">',
        f'<div class="verdict-icon-lg">{_VERDICT_ICON[run_verdict]}</div>',
        '<div class="verdict-body">',
        f'<div class="verdict-label">{_esc(bluf_label)}</div>',
        f'<h2 class="verdict-headline">{_esc(bluf_headline)}</h2>',
        f'<div class="verdict-context">{_esc(bluf_context)}</div>',
        "</div>",
        "</div>",
    ]

    for sa in assessments:
        parts.append(_render_sample(sa))

    parts.append(_render_trace(run_dir / "trace.jsonl"))

    # Sign-off area — SOX / internal audit persona needs an explicit accept/reject.
    parts.append(_render_signoff(control, model, run_verdict))

    parts.append(
        '<div class="footer">'
        "Generated by <code>bead-agent report</code> &middot; "
        "self-contained, no external assets &middot; "
        'themed after <a href="https://usebead.ai">usebead.ai</a>'
        "</div>"
    )
    parts.append("</div></body></html>")

    out_path = run_dir / "report.html"
    out_path.write_text("".join(parts))
    return out_path
