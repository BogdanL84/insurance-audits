"""
html_report.py — Render an audit-state.json + per-policy analyses into a
single self-contained dark-mode HTML file (inline CSS, no JS, no external
assets) for distribution.

Public entry: render_audit_report(state, policy_analyses, slug)
              → str (full HTML document)

Output structure:
  - Document header   : client name, audit date, severity pill totals
  - Program-Level     : findings with policy_file ∈ {"", "PROGRAM", "N/A"}
  - One per policy    : policy header card + Ugly / Bad / Review / Good cards
  - Multi-policy refs : rendered under every listed policy with a
                        "Shared with X" annotation in the meta line
"""

from __future__ import annotations

import html
import re
from collections import Counter
from datetime import datetime
from pathlib import Path


# Order policies appear in the report. Anything not listed here renders
# alphabetically at the end.
DEFAULT_POLICY_ORDER = [
    "AUTO.pdf",
    "BOP.pdf",
    "UMBRELLA.pdf",
    "USLI EPLI.pdf",
    "WC PEKIN 24.pdf",
]

CAT_TO_CLASS = {
    "Ugly":         "ugly",
    "Bad":          "bad",
    "Review":       "review",
    "Needs Review": "review",
    "Good":         "good",
}

CAT_ORDER = ["Ugly", "Bad", "Review", "Good"]


# ── Helpers ────────────────────────────────────────────────────────
def _split_policy_file(pf: str) -> list[str]:
    """Multi-policy heuristic — accept ',' and ';'. Filter to .pdf endings."""
    if not pf:
        return []
    normalized = pf.replace(";", ",")
    raw_pieces = [p.strip() for p in normalized.split(",") if p.strip()]
    pieces = [Path(p).name for p in raw_pieces if p.lower().endswith(".pdf")]
    return pieces or [Path(pf).name]


def _escape_paragraphs(text: str) -> str:
    """Escape HTML and split on blank lines into <p> blocks."""
    if not text:
        return ""
    # Normalize CRLF; collapse 3+ blank lines to 2
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    parts = re.split(r"\n\s*\n", text.strip())
    return "\n".join(
        f"<p>{html.escape(p.strip()).replace(chr(10), '<br>')}</p>"
        for p in parts if p.strip()
    )


def _category_of(f: dict) -> str:
    """Normalize 'Needs Review' → 'Review' for ordering, but keep display label."""
    raw = (f.get("category") or "").strip()
    if raw == "Needs Review":
        return "Review"
    return raw


def _category_class(f: dict) -> str:
    return CAT_TO_CLASS.get((f.get("category") or "").strip(), "")


def _risk_badge_html(f: dict) -> str:
    L = f.get("likelihood")
    S = f.get("severity")
    R = f.get("risk_score")
    if not (L and S):
        return ""
    cls = _category_class(f)
    if R is None:
        try:
            R = int(L) * int(S)
        except (TypeError, ValueError):
            return ""
    return (
        f'<span class="risk {cls}">'
        f"Risk {html.escape(str(R))}/25 · Likelihood {html.escape(str(L))} "
        f"× Severity {html.escape(str(S))}"
        f"</span>"
    )


def _finding_html(f: dict, current_policy: str | None = None) -> str:
    cat_class = _category_class(f)
    title     = html.escape((f.get("requirement_type") or "(untitled finding)").strip())
    page      = html.escape((f.get("policy_page") or "").strip())
    gd        = (f.get("gap_description") or f.get("description") or "").strip()
    rec       = (f.get("recommendation") or "").strip()
    pf        = (f.get("policy_file") or "").strip()

    multi_note = ""
    if current_policy:
        pieces = _split_policy_file(pf)
        others = [p for p in pieces if p != current_policy]
        if others:
            multi_note = (
                f'<span class="shared-note">Shared with '
                f'{html.escape(", ".join(others))}</span>'
            )

    risk_badge = _risk_badge_html(f)

    # Always render the meta line for visual consistency. When no page
    # reference was captured, surface that explicitly rather than omitting
    # the line — every finding card should have the same vertical structure.
    page_html = (
        page if page
        else '<span class="page-missing">Page reference not captured</span>'
    )
    meta_pieces = [page_html]
    if multi_note:
        meta_pieces.append(multi_note)
    if risk_badge:
        meta_pieces.append(risk_badge)
    meta_html = f'<div class="finding-meta">{" · ".join(meta_pieces)}</div>'

    body_html = _escape_paragraphs(gd) if gd else (
        '<p class="finding-empty">No detail provided in source data.</p>'
    )

    rec_html = ""
    if rec:
        rec_html = (
            '<div class="finding-recommendation">'
            '<strong>Recommendation:</strong> '
            f'{_escape_paragraphs(rec)}'
            "</div>"
        )

    return f"""\
      <article class="finding {cat_class}">
        <div class="finding-title">{title}</div>
        {meta_html}
        <div class="finding-body">
{body_html}
        </div>
        {rec_html}
      </article>
"""


def _severity_block(label: str, label_class: str, findings: list,
                    current_policy: str | None) -> str:
    """One Ugly/Bad/Review/Good subsection. Skipped if empty."""
    if not findings:
        return ""
    # Sort high risk-score first within block
    def _key(f):
        rs = f.get("risk_score")
        return (-rs if isinstance(rs, (int, float)) else 0,
                (f.get("requirement_type") or "").lower())
    findings = sorted(findings, key=_key)
    body = "\n".join(_finding_html(f, current_policy) for f in findings)
    return f"""\
    <div class="severity-block {label_class}">
      <h3>{label} <span class="count">({len(findings)})</span></h3>
{body}
    </div>
"""


def _grouped_by_category(findings: list) -> dict:
    """Return {'Ugly': [...], 'Bad': [...], 'Review': [...], 'Good': [...]}."""
    grp = {c: [] for c in CAT_ORDER}
    for f in findings:
        cat = _category_of(f)
        if cat in grp:
            grp[cat].append(f)
    return grp


def _policy_meta_dl(pa: dict) -> str:
    """Build the <dl> meta block for a policy header card."""
    rows = []
    def _row(label, value):
        if not value:
            return
        if isinstance(value, list):
            value = " · ".join(str(v) for v in value if v)
        rows.append(
            f"<dt>{html.escape(label)}</dt>"
            f"<dd>{html.escape(str(value))}</dd>"
        )
    _row("Carrier",         pa.get("carrier"))
    _row("Policy Number",   pa.get("policy_number"))
    eff = pa.get("effective_date")
    exp = pa.get("expiry_date") or pa.get("expiration_date")
    if eff or exp:
        _row("Effective", f"{eff or '—'} → {exp or '—'}")
    _row("Named Insured",   pa.get("named_insured"))
    _row("Policy Type",     pa.get("policy_type"))
    _row("Coverage Parts",  pa.get("coverage_parts"))
    if not rows:
        return ""
    return f'<dl class="policy-meta">{"".join(rows)}</dl>'


def _section_header_html(section_num: str, title: str, subtitle: str = "") -> str:
    """Reference-style header: mono uppercase 'Section 0N' + DM Serif title +
    2px ink underline. Optional subtitle paragraph beneath."""
    sub = (
        f'<p class="section-subtitle">{html.escape(subtitle)}</p>'
        if subtitle else ""
    )
    return (
        '<header class="section-header">'
        f'<div class="section-num">Section {html.escape(section_num)}</div>'
        f'<h2 class="section-title">{title}</h2>'
        f'{sub}'
        '</header>'
    )


def _policy_section(pdf_name: str, findings: list, pa: dict,
                    section_num: str, section_id: str) -> str:
    grouped = _grouped_by_category(findings)
    blocks_html = "".join(
        _severity_block(
            label=("Ugly — critical exposures" if cat == "Ugly" else
                   "Bad — gaps needing attention" if cat == "Bad" else
                   "Needs Review" if cat == "Review" else
                   "Good — confirmed coverage"),
            label_class=cat.lower(),
            findings=grouped[cat],
            current_policy=pdf_name,
        )
        for cat in CAT_ORDER
    )

    if not blocks_html.strip():
        return ""

    # Section title combines pdf filename + carrier + policy_type when available.
    carrier      = pa.get("carrier") or ""
    title_suffix = pa.get("policy_type") or ""
    if carrier and title_suffix:
        title = f"{html.escape(pdf_name)} <span class='section-title-suffix'>· {html.escape(carrier)} {html.escape(title_suffix)}</span>"
    elif carrier:
        title = f"{html.escape(pdf_name)} <span class='section-title-suffix'>· {html.escape(carrier)}</span>"
    else:
        title = html.escape(pdf_name)

    meta_dl = _policy_meta_dl(pa)

    return f"""\
  <section class="section policy" id="{section_id}">
    {_section_header_html(section_num, title)}
    <div class="policy-header">
      {meta_dl}
    </div>
{blocks_html}
  </section>
"""


def _program_section(findings: list, section_num: str = "02") -> str:
    grouped = _grouped_by_category(findings)
    blocks_html = "".join(
        _severity_block(
            label=("Ugly — critical exposures" if cat == "Ugly" else
                   "Bad — gaps needing attention" if cat == "Bad" else
                   "Needs Review" if cat == "Review" else
                   "Good — confirmed coverage"),
            label_class=cat.lower(),
            findings=grouped[cat],
            current_policy=None,
        )
        for cat in CAT_ORDER
    )
    if not blocks_html.strip():
        return ""
    subtitle = (
        "Issues that span the program — missing coverage types, cross-policy "
        "entity gaps, named-insured inconsistencies — and items not anchored "
        "to a specific policy."
    )
    return f"""\
  <section class="section policy program-level" id="program">
    {_section_header_html(section_num, "Program-Level Findings", subtitle)}
{blocks_html}
  </section>
"""


# ── CSS (inline, single source of truth) ──────────────────────────
# Stages 1+2 of redesign port (2026-05-08): design tokens + sidebar +
# cover hero + section structure lifted from Risk_Treasury_Blueprint_v5.html.
# Light theme on warm off-white (paper-warm body, white cards), dark sidebar
# + dark cover hero providing architectural contrast. DM Sans / DM Serif
# Display / JetBrains Mono typography. Severity stoplight colors retained
# for severity tagging only — they don't drive the document palette.
# Stage 3 (finding-card re-skin + prominent page citation) is the next
# checkpoint.
_CSS = """
:root {
  /* Sidebar + cover — unchanged from light/dark transition */
  --ink:           #0a0f1a;
  --ink-soft:      #1f2937;
  /* Main canvas (now dark, slightly warmer than ink so sidebar reads as a separate plane) */
  --paper:         #14191f;
  --paper-warm:    #1a1f26;
  --card:          #1c222b;
  --card-soft:     #232a35;
  /* Text */
  --text:          #e8e4d8;
  --text-strong:   #f4f0e6;
  --muted:         #8a9099;
  --muted-dark:    #6b7280;
  /* Borders — subtle dark-on-dark */
  --border:        #2a323d;
  --border-strong: #3a4451;
  /* Accents */
  --accent:        #5fbb91;
  --accent-dark:   #3d9970;
  --warm:          #e8a06b;
  --teal:          #5eead4;          /* sidebar only — do not bleed into main */
  --conf-red:      #ff7370;
  /* Severity — financial-dashboard stoplight, no bg washes */
  --sev-ugly:      #f25c5c;
  --sev-bad:       #f5a368;
  --sev-review:    #ecc94b;
  --sev-good:      #5fbb91;
}
* { margin: 0; padding: 0; box-sizing: border-box; }
html { scroll-behavior: smooth; }
body {
  font-family: 'DM Sans', sans-serif;
  background: var(--paper);
  color: var(--text);
  line-height: 1.6;
  font-size: 16px;
  -webkit-font-smoothing: antialiased;
}

/* ── Sidebar TOC (fixed left, dark) ─────────────────────────────── */
.toc {
  position: fixed;
  top: 0; left: 0;
  width: 280px;
  height: 100vh;
  background: var(--ink);
  color: var(--text);
  padding: 2.5rem 1.5rem 2rem;
  overflow-y: auto;
  z-index: 100;
  border-right: 1px solid var(--ink-soft);
}
.toc-brand {
  font-family: 'DM Serif Display', serif;
  font-size: 1.7rem;
  color: var(--text-strong);
  line-height: 1.05;
  margin-bottom: 0.3rem;
  letter-spacing: -0.01em;
}
.toc-version {
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.65rem;
  letter-spacing: 0.18em;
  text-transform: uppercase;
  color: var(--teal);
  margin-bottom: 2.2rem;
}
.toc-label {
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.62rem;
  letter-spacing: 0.18em;
  text-transform: uppercase;
  color: #6b7280;
  margin-bottom: 0.8rem;
  padding-bottom: 0.6rem;
  border-bottom: 1px solid var(--ink-soft);
}
.toc-list { list-style: none; padding: 0; margin-bottom: 1.5rem; }
.toc-list li { margin: 0; padding: 0; }
.toc-list a {
  display: block;
  padding: 0.55rem 0.7rem;
  color: #94a3b8;
  text-decoration: none;
  font-size: 0.88rem;
  border-radius: 4px;
  transition: all 0.15s;
}
.toc-list a:hover {
  background: var(--ink-soft);
  color: var(--teal);
  padding-left: 1rem;
}
.toc-list a.active {
  background: var(--ink-soft);
  color: var(--teal);
}
.toc-list .num {
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.7rem;
  color: var(--teal);
  margin-right: 0.6rem;
  font-weight: 500;
}
.toc-list .toc-counts {
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.65rem;
  color: #6b7280;
  margin-left: 0.5rem;
}
.toc-foot {
  margin-top: 2rem;
  padding-top: 1rem;
  border-top: 1px solid var(--ink-soft);
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.62rem;
  color: #6b7280;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  line-height: 1.7;
}
.confidential-on-dark {
  color: #ff6b67;
  font-weight: 700;
  letter-spacing: 0.12em;
  text-transform: uppercase;
}

.main { margin-left: 280px; }

/* ── Cover hero (full 100vh, dark, teal accent) ─────────────────── */
.cover {
  min-height: 100vh;
  background: var(--ink);
  color: var(--text);
  padding: 6rem 5rem 4rem;
  display: flex;
  flex-direction: column;
  justify-content: center;
  position: relative;
  overflow: hidden;
}
.cover::before {
  content: '';
  position: absolute;
  top: -10%; right: -10%;
  width: 700px; height: 700px;
  background: radial-gradient(circle, rgba(94,234,210,0.08) 0%, transparent 60%);
  pointer-events: none;
}
.cover::after {
  content: '';
  position: absolute;
  bottom: 0; left: 0; right: 0;
  height: 1px;
  background: linear-gradient(90deg, transparent, var(--teal), transparent);
  opacity: 0.3;
}
.cover-confidential-banner {
  position: relative;
  display: inline-block;
  border: 1.5px solid #ff6b67;
  padding: 0.65rem 1.1rem;
  margin-bottom: 2rem;
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.78rem;
  letter-spacing: 0.1em;
  background: rgba(200, 48, 44, 0.08);
  border-radius: 4px;
  align-self: flex-start;
  width: max-content;
}
.cover-tag {
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.75rem;
  letter-spacing: 0.2em;
  text-transform: uppercase;
  color: var(--teal);
  margin-bottom: 2.2rem;
  position: relative;
}
.cover h1 {
  font-family: 'DM Serif Display', serif;
  font-size: clamp(3rem, 6.5vw, 5.5rem);
  line-height: 1.02;
  color: var(--text-strong);
  margin-bottom: 1.5rem;
  letter-spacing: -0.02em;
  position: relative;
}
.cover .subtitle {
  font-family: 'DM Sans', sans-serif;
  font-size: 1.25rem;
  color: #94a3b8;
  max-width: 56ch;
  line-height: 1.55;
  margin-bottom: 3.5rem;
  position: relative;
  letter-spacing: 0;
  text-transform: none;
}
.cover-meta {
  display: grid;
  grid-template-columns: repeat(3, max-content);
  gap: 3rem;
  position: relative;
}
.cover-meta-item .meta-label {
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.65rem;
  letter-spacing: 0.18em;
  text-transform: uppercase;
  color: #6b7280;
  margin-bottom: 0.5rem;
}
.cover-meta-item .meta-value {
  font-family: 'DM Serif Display', serif;
  font-size: 1.5rem;
  color: var(--text-strong);
  line-height: 1.1;
}

/* ── Section (numbered, with header) ──────────────────────────── */
.section {
  padding: 5rem 5rem 5rem;
  max-width: 1200px;
  border-bottom: 1px solid var(--border);
}
.section:last-of-type { border-bottom: none; }
.section-header {
  margin-bottom: 2.5rem;
  padding-bottom: 1.5rem;
  border-bottom: 2px solid var(--text-strong);
}
.section-num {
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.75rem;
  letter-spacing: 0.2em;
  text-transform: uppercase;
  color: var(--accent);
  margin-bottom: 0.8rem;
  font-weight: 600;
}
.section-title {
  font-family: 'DM Serif Display', serif;
  font-size: clamp(2.2rem, 4vw, 3.2rem);
  line-height: 1.08;
  color: var(--text-strong);
  letter-spacing: -0.02em;
  margin: 0;
}
.section-title-suffix {
  font-family: 'DM Sans', sans-serif;
  font-weight: 400;
  font-size: 0.55em;
  color: var(--muted);
  letter-spacing: 0;
  margin-left: 0.4em;
  vertical-align: middle;
}
.section-subtitle {
  font-family: 'DM Sans', sans-serif;
  font-size: 1.05rem;
  color: var(--text);
  line-height: 1.55;
  margin-top: 0.85rem;
  max-width: 75ch;
}

/* ── Bignum cards (executive summary 4-up row) ──────────────────── */
.bignum {
  font-family: 'DM Serif Display', serif;
  font-size: 3.4rem;
  color: var(--accent);
  line-height: 1;
  margin-bottom: 0.35rem;
}
.bignum.warm   { color: var(--warm); }
.bignum.ugly   { color: var(--sev-ugly); }
.bignum.muted  { color: var(--text-strong); }
.bignum-card {
  text-align: left;
  padding: 1.4rem 1.5rem;
  border: 1px solid var(--border);
  border-radius: 8px;
  background: var(--card);
}
.bignum-card .label {
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.62rem;
  letter-spacing: 0.18em;
  text-transform: uppercase;
  color: var(--muted);
}

/* ── Grids ──────────────────────────────────────────────────────── */
.grid-2 { display: grid; grid-template-columns: 1fr 1fr; gap: 1.5rem; margin: 1.5rem 0; }
.grid-3 { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 1.5rem; margin: 1.5rem 0; }
.grid-4 { display: grid; grid-template-columns: repeat(4, 1fr); gap: 1.5rem; margin: 1.5rem 0; }

/* ── Callouts ───────────────────────────────────────────────────── */
.callout {
  background: var(--card);
  border: 1px solid var(--border);
  border-left: 3px solid var(--accent);
  padding: 1.25rem 1.5rem;
  margin: 1rem 0;
  border-radius: 0 6px 6px 0;
}
.callout.warm { border-left-color: var(--warm); }
.callout.ugly { border-left-color: var(--sev-ugly); }
.callout p { color: var(--text); margin: 0 0 0.6rem; max-width: none; font-size: 1rem; line-height: 1.55; }
.callout p:last-child { margin-bottom: 0; }
.callout strong { color: var(--text-strong); font-weight: 700; }
.callout .tag {
  display: inline-block;
  padding: 0.2em 0.65em;
  border-radius: 100px;
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.7rem;
  font-weight: 600;
  letter-spacing: 0.05em;
  text-transform: uppercase;
  margin-right: 0.5rem;
  background: transparent;
  border: 1px solid currentColor;
}
.callout .tag.ugly { color: var(--sev-ugly); }
.callout .tag.warm { color: var(--warm); }
.callout .tag.bad  { color: var(--sev-bad); }
.callout .tag.good { color: var(--sev-good); }
.callout .tag.review { color: var(--sev-review); }

/* ── Tables (severity-by-policy + others) ───────────────────────── */
table {
  width: 100%;
  border-collapse: collapse;
  margin: 1.5rem 0;
  font-size: 0.95rem;
  background: var(--card);
  border-radius: 6px;
  overflow: hidden;
  border: 1px solid var(--border);
}
thead { background: var(--ink); }
th {
  text-align: left;
  padding: 0.85rem 1rem;
  font-size: 0.72rem;
  text-transform: uppercase;
  letter-spacing: 0.1em;
  color: var(--text-strong);
  font-weight: 600;
  font-family: 'JetBrains Mono', monospace;
}
th.right, td.right   { text-align: right; }
th.center, td.center { text-align: center; }
td {
  padding: 0.7rem 1rem;
  border-bottom: 1px solid var(--border);
  color: var(--text);
  font-size: 0.95rem;
}
tr:last-child td { border-bottom: none; }
tr.highlight td { background: var(--card-soft); font-weight: 600; color: var(--accent); }
td.sev-ugly   { color: var(--sev-ugly);   font-weight: 700; }
td.sev-bad    { color: var(--sev-bad);    font-weight: 700; }
td.sev-review { color: var(--sev-review); font-weight: 700; }
td.sev-good   { color: var(--sev-good);   font-weight: 700; }

/* ── Policy header card (sits inside each policy section) ───────── */
.policy-header {
  background: var(--card);
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 1.5rem 1.75rem;
  margin-bottom: 1.5rem;
}
.policy-header h2 {
  margin: 0 0 0.6rem;
  font-family: 'DM Serif Display', serif;
  font-size: 1.7rem;
  line-height: 1.15;
  color: var(--text-strong);
  letter-spacing: -0.01em;
}
.policy-header .program-subtitle {
  color: var(--text);
  font-size: 0.95rem;
  line-height: 1.55;
  max-width: 72ch;
}
.policy-meta {
  display: grid;
  grid-template-columns: max-content 1fr;
  gap: 0.45rem 1.5rem;
  font-size: 0.95rem;
  margin: 0.85rem 0 0;
}
.policy-meta dt {
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.7rem;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: var(--muted);
  padding-top: 0.15rem;
}
.policy-meta dd { color: var(--text); margin: 0; }

/* Severity subsection */
.severity-block { margin-top: 1.75rem; }
.severity-block h3 {
  margin: 0 0 0.85rem;
  font-family: 'DM Sans', sans-serif;
  font-size: 1rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.1em;
}
.severity-block.ugly h3   { color: var(--sev-ugly); }
.severity-block.bad h3    { color: var(--sev-bad); }
.severity-block.review h3 { color: var(--sev-review); }
.severity-block.good h3   { color: var(--sev-good); }
.severity-block h3 .count {
  font-family: 'JetBrains Mono', monospace;
  font-weight: 500;
  font-size: 0.78rem;
  letter-spacing: 0.05em;
  margin-left: 0.5rem;
  color: var(--muted);
}

/* Finding card — base shell from reference .card pattern, severity left border */
.finding {
  background: var(--card);
  border: 1px solid var(--border);
  border-left-width: 3px;
  border-radius: 6px;
  padding: 1.1rem 1.4rem;
  margin-bottom: 0.85rem;
}
.finding.ugly   { border-left-color: var(--sev-ugly); }
.finding.bad    { border-left-color: var(--sev-bad); }
.finding.review { border-left-color: var(--sev-review); }
.finding.good   { border-left-color: var(--sev-good); }
.finding-title {
  font-family: 'DM Serif Display', serif;
  font-size: 1.2rem;
  line-height: 1.3;
  margin: 0 0 0.4rem;
  color: var(--text-strong);
  letter-spacing: -0.005em;
}
.finding-meta {
  color: var(--muted);
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.7rem;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  margin-bottom: 0.7rem;
}
.finding-meta .risk {
  display: inline-block;
  margin-left: 0.5rem;
  padding: 1px 8px;
  border-radius: 4px;
  background: transparent;
  border: 1px solid var(--border-strong);
  color: var(--text);
  font-weight: 600;
}
.finding-meta .risk.ugly   { color: var(--sev-ugly);   border-color: var(--sev-ugly); }
.finding-meta .risk.bad    { color: var(--sev-bad);    border-color: var(--sev-bad); }
.finding-meta .risk.review { color: var(--sev-review); border-color: var(--sev-review); }
.finding-meta .shared-note {
  color: var(--accent);
  text-transform: none;
  letter-spacing: 0;
}
.finding-meta .page-missing {
  color: var(--muted);
  font-style: italic;
  text-transform: none;
  letter-spacing: 0;
}
.finding-body {
  color: var(--text);
  font-size: 1rem;
  line-height: 1.65;
}
.finding-body p { margin: 0 0 0.6rem; max-width: 75ch; }
.finding-body p:last-child { margin-bottom: 0; }
.finding-body strong { color: var(--text-strong); font-weight: 600; }
.finding-body .finding-empty { color: var(--muted); font-style: italic; }
.finding-recommendation {
  margin-top: 0.95rem;
  padding-top: 0.85rem;
  border-top: 1px dashed var(--border);
  font-size: 0.92rem;
  color: var(--text);
}
.finding-recommendation strong {
  color: var(--accent);
  font-weight: 700;
}
.finding-recommendation p {
  margin: 0 0 0.4rem;
  color: var(--text);
  max-width: 75ch;
}
.finding-recommendation p:first-of-type { display: inline; }

/* ── Responsive (mobile/narrow) ──────────────────────────────── */
@media (max-width: 900px) {
  .toc { display: none; }
  .main { margin-left: 0; }
  .section { padding: 3rem 1.5rem; }
  .cover { padding: 4rem 1.5rem 3rem; }
  .grid-2, .grid-3, .grid-4 { grid-template-columns: 1fr; }
  .cover-meta { grid-template-columns: 1fr; gap: 1.5rem; }
  table { font-size: 0.85rem; }
  th, td { padding: 0.55rem 0.7rem; }
  .cover h1 { font-size: clamp(2.2rem, 8vw, 3.2rem); }
  .section-title { font-size: clamp(1.8rem, 5vw, 2.4rem); }
}

/* ── Print stylesheet — drop sidebar, white bg, page-break aware ─ */
@media print {
  .toc { display: none; }
  .main { margin-left: 0; }
  html, body { background: white; color: black; }
  .cover {
    background: white; color: black;
    min-height: auto; padding: 3rem 2rem;
    page-break-after: always;
  }
  .cover h1, .cover .cover-meta-item .meta-value, .cover .subtitle { color: black; }
  .cover-tag, .cover-meta-item .meta-label { color: #555; }
  .cover::before, .cover::after { display: none; }
  .cover-confidential-banner { color: #c8302c; border-color: #c8302c; }
  .section { padding: 2rem; page-break-inside: avoid; }
  .section-header { page-break-after: avoid; border-bottom-color: #000; }
  .section-title, .policy-header h2, .finding-title { color: #000; }
  .finding, .policy-header, .callout, .bignum-card, table { page-break-inside: avoid; }
  .finding, .policy-header, .bignum-card, table { background: white; border-color: #ccc; }
  .finding-body, .finding-meta, .policy-meta dt, .finding-recommendation,
  .finding-recommendation strong, .finding-body strong, .policy-meta dd,
  td, .section-subtitle, .toc, .toc * { color: #222; }
  thead { background: #000; }
  th { color: white; }
  tr.highlight td { background: #f1ede4; color: #000; }
  .severity-block h3, .policy-header h2, .finding-title { page-break-after: avoid; }
  .severity-block.ugly h3, td.sev-ugly, .finding-meta .risk.ugly,
  .callout.ugly, .callout .tag.ugly, .bignum.ugly        { color: #b00020; }
  .severity-block.bad h3, td.sev-bad, .finding-meta .risk.bad,
  .callout .tag.bad, .bignum.warm                        { color: #c75300; }
  .severity-block.review h3, td.sev-review, .finding-meta .risk.review,
  .callout .tag.review                                   { color: #8a6a00; }
  .severity-block.good h3, td.sev-good,
  .callout .tag.good, .bignum                            { color: #1f7a3d; }
  .finding.ugly  { border-left-color: #b00020; }
  .finding.bad   { border-left-color: #c75300; }
  .finding.review{ border-left-color: #8a6a00; }
  .finding.good  { border-left-color: #1f7a3d; }
  .finding-meta .risk { border-color: currentColor; background: white; }
}
"""


def _anchor_slug(pdf_name: str) -> str:
    s = pdf_name.lower()
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    return s or "policy"


def _toc_sidebar_html(
    display_name: str,
    audit_date: str,
    toc_entries: list,  # list of (section_num, anchor_id, label, count)
) -> str:
    """Fixed-left dark sidebar. toc_entries are tuples of
    (section_num, anchor_id, label, finding_count_or_None)."""
    items = []
    for num, anchor, label, n in toc_entries:
        cnt_html = (
            f'<span class="toc-counts">({n})</span>'
            if isinstance(n, int) and n > 0 else ""
        )
        items.append(
            f'<li><a href="#{anchor}">'
            f'<span class="num">{html.escape(num)}</span>'
            f'{html.escape(label)}{cnt_html}'
            f'</a></li>'
        )
    return f"""\
<nav class="toc">
  <div class="toc-brand">Insurance Audit</div>
  <div class="toc-version">
    {html.escape(display_name).upper()} ·
    <span class="confidential-on-dark">Confidential</span>
  </div>
  <div class="toc-label">Contents</div>
  <ul class="toc-list">
{''.join(items)}
  </ul>
  <div class="toc-foot">
    Property of Bogdan Laza, CLCS<br>
    For discussion only<br>
    Not for distribution
  </div>
</nav>
"""


def _carrier_brand(carrier: str) -> str:
    """Extract a brand token from a long carrier string. Mirrors
    findings_filter._carrier_brand_token but kept local to avoid the
    cross-module import from a renderer."""
    if not carrier:
        return ""
    s = re.sub(
        r"\b(Insurance|Ins\.?|Company|Co\.?|Group|Mutual|Corp(?:oration)?|"
        r"Limited|Ltd\.?)\b",
        "", carrier, flags=re.I,
    )
    tokens = [t for t in re.split(r"[\s,/()]+", s) if t and len(t) > 1]
    return tokens[0] if tokens else carrier.split()[0]


def _count_unique_carriers(policy_analyses: list) -> int:
    seen = set()
    for pa in policy_analyses or []:
        b = _carrier_brand(pa.get("carrier") or "")
        if b:
            seen.add(b.lower())
    return len(seen)


def _cover_hero_html(
    display_name: str,
    audit_date: str,
    n_findings: int,
    n_critical: int,
    n_policies: int,
    n_carriers: int,
) -> str:
    """Full-screen dark hero with confidential banner, mono tag, big
    serif title, narrative subtitle, and 3-up meta grid."""
    audit_date_pretty = _format_audit_date(audit_date)
    subtitle = (
        f"An audit of the firm's commercial insurance program — "
        f"{n_policies} {'policy' if n_policies == 1 else 'policies'} across "
        f"{n_carriers} {'carrier' if n_carriers == 1 else 'carriers'}, "
        f"identifying {n_findings} findings and {n_critical} critical "
        f"{'exposure' if n_critical == 1 else 'exposures'}."
    )
    return f"""
<section id="cover" class="cover">
  <div class="cover-confidential-banner">
    <span class="confidential-on-dark">Confidential</span> ·
    For {html.escape(display_name)} leadership only
  </div>
  <div class="cover-tag">Insurance Program Audit · {html.escape(audit_date_pretty.upper())}</div>
  <h1>{html.escape(display_name)}</h1>
  <p class="subtitle">{html.escape(subtitle)}</p>
  <div class="cover-meta">
    <div class="cover-meta-item">
      <div class="meta-label">Client</div>
      <div class="meta-value">{html.escape(display_name)}</div>
    </div>
    <div class="cover-meta-item">
      <div class="meta-label">Audit Date</div>
      <div class="meta-value">{html.escape(audit_date_pretty)}</div>
    </div>
    <div class="cover-meta-item">
      <div class="meta-label">Prepared By</div>
      <div class="meta-value">Bogdan Laza, CLCS</div>
    </div>
  </div>
</section>
"""


def _format_audit_date(iso_or_str: str) -> str:
    """ISO date → 'May 8, 2026'. Returns input unchanged on parse failure."""
    if not iso_or_str:
        return ""
    try:
        dt = datetime.strptime(iso_or_str[:10], "%Y-%m-%d")
        return dt.strftime("%b %-d, %Y") if hasattr(dt, "strftime") else iso_or_str
    except (ValueError, TypeError):
        return iso_or_str
    except Exception:
        return iso_or_str


def _severity_by_policy_table_html(
    policy_rows: list,  # list of (pdf_name, carrier_short, U, B, R, G, total)
    program_row: tuple | None,
    grand_totals: tuple,
) -> str:
    """Dark-thead severity-by-policy table for the executive summary.
    program_row optional. grand_totals = (U, B, R, G, total)."""
    rows = []
    for pdf_name, carrier, U, B, R, G, total in policy_rows:
        rows.append(
            f"<tr>"
            f"<td><strong>{html.escape(pdf_name)}</strong></td>"
            f"<td>{html.escape(carrier)}</td>"
            f"<td class='center sev-ugly'>{U}</td>"
            f"<td class='center sev-bad'>{B}</td>"
            f"<td class='center sev-review'>{R}</td>"
            f"<td class='center sev-good'>{G}</td>"
            f"<td class='right'><strong>{total}</strong></td>"
            f"</tr>"
        )
    if program_row:
        _, _, U, B, R, G, total = program_row
        rows.append(
            f"<tr>"
            f"<td><strong>Program-level</strong></td>"
            f"<td>—</td>"
            f"<td class='center sev-ugly'>{U}</td>"
            f"<td class='center sev-bad'>{B}</td>"
            f"<td class='center sev-review'>{R}</td>"
            f"<td class='center sev-good'>{G}</td>"
            f"<td class='right'><strong>{total}</strong></td>"
            f"</tr>"
        )
    gU, gB, gR, gG, gT = grand_totals
    rows.append(
        f"<tr class='highlight'>"
        f"<td colspan='2'><strong>Total</strong></td>"
        f"<td class='center'><strong>{gU}</strong></td>"
        f"<td class='center'><strong>{gB}</strong></td>"
        f"<td class='center'><strong>{gR}</strong></td>"
        f"<td class='center'><strong>{gG}</strong></td>"
        f"<td class='right'><strong>{gT}</strong></td>"
        f"</tr>"
    )
    return f"""
<table>
  <thead>
    <tr>
      <th>Policy</th>
      <th>Carrier</th>
      <th class="center">Ugly</th>
      <th class="center">Bad</th>
      <th class="center">Review</th>
      <th class="center">Good</th>
      <th class="right">Total</th>
    </tr>
  </thead>
  <tbody>
{''.join(rows)}
  </tbody>
</table>
"""


def _top_critical_callouts_html(top_findings: list) -> str:
    """Render top 3 Ugly findings as .callout.warm blocks."""
    out = []
    for f in top_findings:
        rt   = html.escape(f.get("requirement_type") or "(untitled)")
        rs   = f.get("risk_score")
        risk_str = f"Risk {rs}/25" if rs else ""
        # Pull a tight summary from gap_description (first 1-2 sentences)
        gd = (f.get("gap_description") or "").strip()
        summary = re.split(r"(?<=[.!?])\s+", gd)
        head = " ".join(summary[:2])[:600]
        head_escaped = html.escape(head)
        risk_pill = (
            f'<span class="tag warm">Ugly{(" · " + risk_str) if risk_str else ""}</span>'
        )
        out.append(
            f'<div class="callout warm">'
            f'<p>{risk_pill}<strong>{rt}</strong></p>'
            f'<p>{head_escaped}</p>'
            f'</div>'
        )
    return "\n".join(out)


def _executive_summary_html(
    section_num: str,
    n_findings: int,
    n_critical: int,
    n_policies: int,
    n_carriers: int,
    severity_table_html: str,
    top_critical_html: str,
    narrative: str,
) -> str:
    return f"""
<section id="exec" class="section">
  {_section_header_html(section_num, "Executive Summary")}

  <p style="font-size:1.05rem; color:var(--text); line-height:1.65; max-width:75ch;">
    {narrative}
  </p>

  <div class="grid-4">
    <div class="bignum-card">
      <div class="label">Findings</div>
      <div class="bignum">{n_findings}</div>
    </div>
    <div class="bignum-card">
      <div class="label">Critical (Ugly)</div>
      <div class="bignum ugly">{n_critical}</div>
    </div>
    <div class="bignum-card">
      <div class="label">Policies</div>
      <div class="bignum muted">{n_policies}</div>
    </div>
    <div class="bignum-card">
      <div class="label">Carriers</div>
      <div class="bignum warm">{n_carriers}</div>
    </div>
  </div>

  <h3 style="font-family:'DM Sans',sans-serif; font-size:1rem; font-weight:700; text-transform:uppercase; letter-spacing:0.1em; color:var(--accent); margin:2.5rem 0 0.5rem;">Severity by Policy</h3>
  {severity_table_html}

  <h3 style="font-family:'DM Sans',sans-serif; font-size:1rem; font-weight:700; text-transform:uppercase; letter-spacing:0.1em; color:var(--accent); margin:2.5rem 0 0.5rem;">Top Critical Exposures</h3>
  {top_critical_html}
</section>
"""


# ── Public entry ──────────────────────────────────────────────────
def render_audit_report(state: dict, policy_analyses: list, slug: str = "") -> str:
    """Render the dark-mode HTML audit report. Returns the full document string."""
    findings = state.get("findings") or []
    display_name = state.get("display_name") or slug or "Client"
    audit_date_iso = state.get("last_analysis_date") or state.get("last_modified") or ""
    audit_date = audit_date_iso[:10] if audit_date_iso else datetime.now().strftime("%Y-%m-%d")

    # Categorize findings
    program_findings = []
    by_policy: dict[str, list] = {}
    for f in findings:
        pf = (f.get("policy_file") or "").strip()
        if pf == "" or pf.upper() == "PROGRAM" or pf == "N/A":
            program_findings.append(f)
            continue
        for piece in _split_policy_file(pf):
            by_policy.setdefault(piece, []).append(f)

    # Determine policy display order: explicit DEFAULT_POLICY_ORDER first, then alphabetized rest
    policy_names = list(by_policy.keys())
    ordered = [n for n in DEFAULT_POLICY_ORDER if n in policy_names]
    rest    = sorted(n for n in policy_names if n not in DEFAULT_POLICY_ORDER)
    policy_names_ordered = ordered + rest

    # Lookup per-policy analysis by source_file
    pa_lookup: dict[str, dict] = {}
    for pa in policy_analyses or []:
        sf = pa.get("source_file") or pa.get("_source_file") or ""
        sf = Path(sf).name
        if sf:
            pa_lookup[sf] = pa

    # Counts for header and TOC
    counts = Counter()
    for f in findings:
        c = _category_of(f)
        if c in {"Ugly", "Bad", "Review", "Good"}:
            counts[c] += 1

    # ── Section numbering ─────────────────────────────────────
    # 00 Cover, 01 Executive Summary, 02 Program-Level, 03+ per policy
    n_policies   = len(policy_names_ordered)
    n_carriers   = _count_unique_carriers(policy_analyses)

    # Build TOC entries: (section_num, anchor_id, label, finding_count_or_None)
    toc_entries = [
        ("00", "cover", "Cover", None),
        ("01", "exec",  "Executive Summary", None),
    ]
    next_num = 2
    if program_findings:
        toc_entries.append((f"{next_num:02}", "program",
                            "Program-Level", len(program_findings)))
        program_section_num = f"{next_num:02}"
        next_num += 1
    else:
        program_section_num = None

    policy_section_nums: dict[str, str] = {}
    for n in policy_names_ordered:
        num = f"{next_num:02}"
        policy_section_nums[n] = num
        toc_entries.append((
            num,
            _anchor_slug(n),
            n.replace(".pdf", "").replace(" PEKIN 24", ""),
            len(by_policy[n]),
        ))
        next_num += 1

    # ── Build per-policy severity rows for the exec-summary table ──
    policy_rows = []
    for n in policy_names_ordered:
        pf_findings = by_policy[n]
        by_cat = Counter(_category_of(f) for f in pf_findings)
        carrier = (pa_lookup.get(n, {}).get("carrier") or "")
        carrier_short = _carrier_brand(carrier) or "—"
        # Map to display name (strip .pdf, drop " PEKIN 24" tail for display)
        disp = n.replace(".pdf", "").replace(" PEKIN 24", "")
        policy_rows.append((
            disp, carrier_short,
            by_cat.get("Ugly", 0),
            by_cat.get("Bad", 0),
            by_cat.get("Review", 0),
            by_cat.get("Good", 0),
            len(pf_findings),
        ))

    program_row = None
    if program_findings:
        by_cat = Counter(_category_of(f) for f in program_findings)
        program_row = (
            "Program-level", "—",
            by_cat.get("Ugly", 0),
            by_cat.get("Bad", 0),
            by_cat.get("Review", 0),
            by_cat.get("Good", 0),
            len(program_findings),
        )

    grand_totals = (
        counts.get("Ugly", 0),
        counts.get("Bad", 0),
        counts.get("Review", 0),
        counts.get("Good", 0),
        len(findings),
    )

    # ── Top 3 Ugly findings by risk_score ──────────────────────
    top3 = sorted(
        [f for f in findings if (f.get("category") or "") == "Ugly"],
        key=lambda f: -(f.get("risk_score") or 0),
    )[:3]

    # ── Narrative paragraph for exec summary ───────────────────
    n_critical = grand_totals[0]
    n_bad      = grand_totals[1]
    narrative = html.escape(
        f"This audit identified {len(findings)} findings across "
        f"{n_policies} {'policy' if n_policies == 1 else 'policies'} "
        f"({n_carriers} {'carrier' if n_carriers == 1 else 'carriers'}). "
        f"Of those, {n_critical} are critical exposures with material "
        f"claim-denial risk, {n_bad} are gaps that need attention but are "
        f"not catastrophic, and the remainder are confirm-with-carrier "
        f"items or coverage already in place."
    )

    # ── Build all section HTML ─────────────────────────────────
    cover_html = _cover_hero_html(
        display_name, audit_date,
        len(findings), n_critical, n_policies, n_carriers,
    )

    severity_table_html  = _severity_by_policy_table_html(
        policy_rows, program_row, grand_totals
    )
    top_critical_html    = _top_critical_callouts_html(top3)
    exec_summary_html    = _executive_summary_html(
        "01", len(findings), n_critical, n_policies, n_carriers,
        severity_table_html, top_critical_html, narrative,
    )

    program_html = (
        _program_section(program_findings, section_num=program_section_num)
        if program_findings and program_section_num else ""
    )

    policy_section_htmls = []
    for name in policy_names_ordered:
        pa = pa_lookup.get(name) or {}
        sec = _policy_section(
            name, by_policy[name], pa,
            section_num=policy_section_nums[name],
            section_id=_anchor_slug(name),
        )
        if sec:
            policy_section_htmls.append(sec)

    sidebar_html = _toc_sidebar_html(display_name, audit_date, toc_entries)

    # Multi-policy disclosure note (rendered as a small line under exec summary)
    n_multi = sum(
        1 for f in findings
        if len(_split_policy_file(f.get("policy_file") or "")) > 1
    )
    # Suppressed in this rebuild — exec summary's totals row already discloses
    # what the rendered section card counts will look like. If we want to
    # surface the multi-policy explanation later, drop a `.section-subtitle`
    # under the exec section header.

    # ── IntersectionObserver for active-section highlighting ───
    ix_script = """
<script>
(function() {
  const observer = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        const id = entry.target.id;
        document.querySelectorAll('.toc-list a').forEach(a => {
          a.classList.toggle('active', a.getAttribute('href') === '#' + id);
        });
      }
    });
  }, { rootMargin: '-30% 0px -60% 0px', threshold: 0 });
  document.querySelectorAll('section[id]').forEach(s => observer.observe(s));
})();
</script>
"""

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Insurance Audit — {html.escape(display_name)}</title>
<link href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=DM+Serif+Display&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
<style>{_CSS}</style>
</head>
<body>
{sidebar_html}
<main class="main">
{cover_html}
{exec_summary_html}
{program_html}
{''.join(policy_section_htmls)}
</main>
{ix_script}
</body>
</html>
"""
