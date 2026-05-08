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
    "BOP.pdf",
    "UMBRELLA.pdf",
    "WC PEKIN 24.pdf",
    "AUTO.pdf",
    "USLI EPLI.pdf",
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

    meta_pieces = []
    if page:
        meta_pieces.append(page)
    if multi_note:
        meta_pieces.append(multi_note)
    if risk_badge:
        meta_pieces.append(risk_badge)
    meta_html = (
        f'<div class="finding-meta">{" · ".join(meta_pieces)}</div>'
        if meta_pieces else ""
    )

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


def _policy_section(pdf_name: str, findings: list, pa: dict) -> str:
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
        return ""  # nothing to show

    title_suffix = pa.get("policy_type") or ""
    carrier      = pa.get("carrier") or ""
    if carrier and title_suffix:
        h2 = f"{html.escape(pdf_name)} — {html.escape(carrier)} {html.escape(title_suffix)}"
    elif carrier:
        h2 = f"{html.escape(pdf_name)} — {html.escape(carrier)}"
    else:
        h2 = html.escape(pdf_name)

    meta_dl = _policy_meta_dl(pa)

    return f"""\
  <section class="policy">
    <div class="policy-header">
      <h2>{h2}</h2>
      {meta_dl}
    </div>
{blocks_html}
  </section>
"""


def _program_section(findings: list) -> str:
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
    return f"""\
  <section class="policy program-level">
    <div class="policy-header">
      <h2>Program-Level Findings</h2>
      <div class="program-subtitle">
        Issues that span the program — missing coverage types, cross-policy entity
        gaps, named-insured inconsistencies — and items not anchored to a specific policy.
      </div>
    </div>
{blocks_html}
  </section>
"""


# ── CSS (inline, single source of truth) ──────────────────────────
_CSS = """
:root {
  --bg:           #1a1a1a;
  --bg-card:      #232323;
  --bg-card-soft: #2a2a2a;
  --text:         #e8e8e8;
  --text-muted:   #9a9a9a;
  --border:       #333;
  --accent:       #6db1ff;
  --ugly:         #ff4d4d;
  --bad:          #ff9933;
  --review:       #ffd966;
  --good:         #5fdb7d;
}
* { box-sizing: border-box; }
html, body {
  margin: 0; padding: 0;
  background: var(--bg);
  color: var(--text);
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
  font-size: 16px;
  line-height: 1.6;
  -webkit-font-smoothing: antialiased;
}
.page { max-width: 980px; margin: 0 auto; padding: 2.5rem 1.5rem 6rem; }

/* Document header */
.doc-header { border-bottom: 1px solid var(--border); padding-bottom: 1.5rem; margin-bottom: 2.5rem; }
.doc-header h1 { margin: 0 0 0.25rem; font-size: 28px; color: var(--accent); letter-spacing: -0.01em; }
.doc-header .subtitle { color: var(--text-muted); font-size: 15px; }
.doc-header .totals { display: flex; gap: 1.25rem; flex-wrap: wrap; margin-top: 1.25rem; }
.doc-header .multi-note { color: var(--text-muted); font-size: 13px; margin-top: 0.85rem; line-height: 1.5; }
.totals .pill { padding: 0.4rem 0.85rem; border-radius: 999px; font-weight: 600; font-size: 14px; background: var(--bg-card); border: 1px solid var(--border); }
.totals .pill.ugly  { color: var(--ugly);   border-color: rgba(255, 77, 77, 0.4); }
.totals .pill.bad   { color: var(--bad);    border-color: rgba(255,153, 51, 0.4); }
.totals .pill.review{ color: var(--review); border-color: rgba(255,217,102, 0.45); }
.totals .pill.good  { color: var(--good);   border-color: rgba(95,219,125, 0.4); }

/* Table of contents */
.toc { background: var(--bg-card); border: 1px solid var(--border); border-radius: 8px; padding: 1rem 1.25rem; margin-bottom: 2.5rem; }
.toc h3 { margin: 0 0 0.5rem; font-size: 14px; text-transform: uppercase; letter-spacing: 0.06em; color: var(--text-muted); font-weight: 700; }
.toc ul { margin: 0; padding-left: 1.2rem; }
.toc li { margin: 0.2rem 0; font-size: 15px; }
.toc a { color: var(--accent); text-decoration: none; }
.toc a:hover { text-decoration: underline; }
.toc .toc-counts { color: var(--text-muted); font-size: 13px; margin-left: 0.5rem; }

/* Policy section */
.policy { margin-top: 2.5rem; scroll-margin-top: 1rem; }
.policy.program-level { margin-top: 1rem; }
.policy-header { background: var(--bg-card); border: 1px solid var(--border); border-radius: 8px; padding: 1.25rem 1.5rem; margin-bottom: 1.5rem; }
.policy-header h2 { margin: 0 0 0.5rem; font-size: 22px; color: var(--accent); }
.policy-header .program-subtitle { color: var(--text-muted); font-size: 14px; line-height: 1.55; }
.policy-meta { display: grid; grid-template-columns: max-content 1fr; gap: 0.4rem 1.25rem; color: var(--text-muted); font-size: 14px; margin: 0.75rem 0 0; }
.policy-meta dt { color: var(--text-muted); }
.policy-meta dd { color: var(--text); margin: 0; }

/* Severity subsection */
.severity-block { margin-top: 1.5rem; }
.severity-block h3 { margin: 0 0 0.75rem; font-size: 16px; text-transform: uppercase; letter-spacing: 0.06em; font-weight: 700; }
.severity-block.ugly h3   { color: var(--ugly); }
.severity-block.bad h3    { color: var(--bad); }
.severity-block.review h3 { color: var(--review); }
.severity-block.good h3   { color: var(--good); }
.severity-block h3 .count { color: var(--text-muted); font-weight: 500; font-size: 14px; margin-left: 0.4rem; letter-spacing: 0; }

/* Finding card */
.finding { background: var(--bg-card); border: 1px solid var(--border); border-left-width: 4px; border-radius: 6px; padding: 1rem 1.25rem; margin-bottom: 0.85rem; }
.finding.ugly   { border-left-color: var(--ugly); }
.finding.bad    { border-left-color: var(--bad); }
.finding.review { border-left-color: var(--review); }
.finding.good   { border-left-color: var(--good); }
.finding-title { font-weight: 600; font-size: 17px; margin: 0 0 0.35rem; color: var(--text); }
.finding-meta { color: var(--text-muted); font-size: 13px; margin-bottom: 0.75rem; }
.finding-meta .risk { display: inline-block; margin-left: 0.6rem; padding: 1px 8px; border-radius: 4px; background: var(--bg-card-soft); color: var(--text); font-weight: 600; }
.finding-meta .risk.ugly   { color: var(--ugly); }
.finding-meta .risk.bad    { color: var(--bad); }
.finding-meta .risk.review { color: var(--review); }
.finding-meta .shared-note { color: var(--accent); }
.finding-body { color: var(--text); font-size: 15px; line-height: 1.65; }
.finding-body p { margin: 0 0 0.6rem; }
.finding-body p:last-child { margin-bottom: 0; }
.finding-body .finding-empty { color: var(--text-muted); font-style: italic; }
.finding-recommendation { margin-top: 0.85rem; padding-top: 0.85rem; border-top: 1px solid var(--border); font-size: 14px; color: var(--text-muted); }
.finding-recommendation strong { color: var(--accent); font-weight: 600; }
.finding-recommendation p { margin: 0 0 0.4rem; color: var(--text-muted); }
.finding-recommendation p:first-of-type { display: inline; }

/* Print stylesheet — flips to ink-friendly white background */
@media print {
  html, body { background: white; color: black; }
  .doc-header h1, .policy-header h2, .toc a { color: #000; }
  .finding, .policy-header, .toc { background: white; border-color: #ccc; }
  .finding-meta, .policy-meta dt, .doc-header .subtitle, .toc .toc-counts,
  .policy-header .program-subtitle, .finding-recommendation, .finding-body .finding-empty
    { color: #555; }
  .severity-block.ugly h3   { color: #b00020; }
  .severity-block.bad h3    { color: #c75300; }
  .severity-block.review h3 { color: #8a6a00; }
  .severity-block.good h3   { color: #1f7a3d; }
  .totals .pill { background: white; }
  .totals .pill.ugly   { color: #b00020; }
  .totals .pill.bad    { color: #c75300; }
  .totals .pill.review { color: #8a6a00; }
  .totals .pill.good   { color: #1f7a3d; }
}
"""


def _toc_html(program_count: int, policy_sections: list[tuple[str, int, dict]]) -> str:
    """policy_sections is a list of (pdf_name, finding_count, by_cat_counts)."""
    items = []
    if program_count:
        items.append(
            f'<li><a href="#program">Program-Level Findings</a>'
            f'<span class="toc-counts">({program_count})</span></li>'
        )
    for pdf_name, n, by_cat in policy_sections:
        slug = _anchor_slug(pdf_name)
        breakdown_parts = []
        for c in CAT_ORDER:
            v = by_cat.get(c, 0)
            if v:
                breakdown_parts.append(f"{v} {c}")
        breakdown = (" · ".join(breakdown_parts)) if breakdown_parts else "no findings"
        items.append(
            f'<li><a href="#{slug}">{html.escape(pdf_name)}</a>'
            f'<span class="toc-counts">({n} — {breakdown})</span></li>'
        )
    if not items:
        return ""
    return f"""\
  <nav class="toc">
    <h3>Sections</h3>
    <ul>{"".join(items)}</ul>
  </nav>
"""


def _anchor_slug(pdf_name: str) -> str:
    s = pdf_name.lower()
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    return s or "policy"


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

    # Build TOC entries with breakdown
    toc_policy_entries = []
    for n in policy_names_ordered:
        pf_findings = by_policy[n]
        by_cat = Counter(_category_of(f) for f in pf_findings)
        toc_policy_entries.append((n, len(pf_findings), dict(by_cat)))

    # Build sections
    sections = []
    if program_findings:
        sections.append(_program_section(program_findings).replace(
            '<section class="policy program-level">',
            '<section class="policy program-level" id="program">'
        ))
    for n in policy_names_ordered:
        pa = pa_lookup.get(n) or {}
        section = _policy_section(n, by_policy[n], pa)
        if section:
            section = section.replace(
                '<section class="policy">',
                f'<section class="policy" id="{_anchor_slug(n)}">'
            )
            sections.append(section)

    sections_html = "".join(sections)
    toc_html      = _toc_html(len(program_findings), toc_policy_entries)

    n_policies = len(policy_names_ordered)
    pill_total = (
        f'<span class="pill">{len(findings)} unique findings · '
        f'{n_policies} {"policy" if n_policies == 1 else "policies"}</span>'
    )

    # Multi-policy findings are rendered once per affected policy section so
    # each policy's review is self-contained. Disclose this so totals don't
    # confuse the reader (header counts unique findings; section card counts
    # may exceed unique counts for multi-policy items).
    n_multi = sum(
        1 for f in findings
        if len(_split_policy_file(f.get("policy_file") or "")) > 1
    )
    multi_note_html = (
        f'<div class="multi-note">{n_multi} finding{"s" if n_multi != 1 else ""} '
        f"affect multiple policies and appear in each affected section "
        f'(annotated <span class="shared-note">Shared with…</span>).</div>'
        if n_multi else ""
    )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Insurance Audit — {html.escape(display_name)}</title>
<style>{_CSS}</style>
</head>
<body>
<div class="page">

  <header class="doc-header">
    <h1>Insurance Program Audit — {html.escape(display_name)}</h1>
    <div class="subtitle">
      Prepared by Bogdan Laza, CLCS · Patriot Growth Insurance Services ·
      Audit date {html.escape(audit_date)}
    </div>
    <div class="totals">
      <span class="pill ugly">{counts.get('Ugly', 0)} Ugly</span>
      <span class="pill bad">{counts.get('Bad', 0)} Bad</span>
      <span class="pill review">{counts.get('Review', 0)} Needs Review</span>
      <span class="pill good">{counts.get('Good', 0)} Good</span>
      {pill_total}
    </div>
    {multi_note_html}
  </header>

{toc_html}
{sections_html}

</div>
</body>
</html>
"""
