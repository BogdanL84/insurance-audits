"""
Findings Dashboard — Day 3 (Treatment A: Dense Command Center).

Full-width gradient hero, .ta-content wrapper with -16px pull-up so
the stepper card straddles the hero edge, then a 3-column summary
row (severity tiles + risk donut + per-policy stacked bars), a
severity-filter pill row, results meta, and a list of severity-
ringed finding rows.

Data shape (from require_client() → audit-state.json):
  state["findings"]: list[dict]
  Each finding dict uses:
    - category:           "Ugly" | "Bad" | "Good" | "Review" | "Needs Review"
    - requirement_type:   headline / title
    - gap_description:    detailed body
    - plain_english:      CFO-friendly summary
    - recommendation:     what to do
    - likelihood:         1-5
    - severity:           1-5
    - risk_score:         usually likelihood*severity
    - policy_file:        source filename (or "PROGRAM" or "a; b" multi)
    - policy_page, policy_quote
    - contract_file, contract_page, contract_quote
    - covered_by_other_policy + covered_by_which_policy + covered_by_page
    - tags:               list[str]
    - reviewed:           bool
    - manual:             bool

The data's native severity language (Ugly / Bad / Review / Good) is
mapped onto the template's CSS severity buckets via _CATEGORY_TO_SEV.
The tag column shows the RAW category text so the auditor sees the
language they use day-to-day.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import html as _html
import streamlit as st

st.set_page_config(
    page_title="Findings · Insurance Audit",
    page_icon="&#128203;",
    layout="wide",
    initial_sidebar_state="expanded",
)

from utils import inject_css, render_sidebar, render_stepper, require_client, _md, _mark_active_nav

inject_css()
render_sidebar()
_mark_active_nav("Findings_Dashboard")

slug, client_path, state = require_client()
findings: list[dict]      = state.get("findings", []) or []
active_client: str        = state.get("display_name", slug)
policies_loaded: list[str] = list(state.get("policies", {}).keys())


# ── Severity bucket mapping (Ugly/Bad/Review/Good → crit/high/med/low)
_SEV_ORDER = ["critical", "high", "medium", "low"]
_SEV_CSS_CLS = {"critical": "crit", "high": "high", "medium": "med", "low": "low"}
_CATEGORY_TO_SEV = {
    "Ugly":         "critical",
    "Bad":          "high",
    "Review":       "medium",
    "Needs Review": "medium",
    "Good":         "low",
}


def _sev(f: dict) -> str:
    return _CATEGORY_TO_SEV.get((f.get("category") or "").strip(), "medium")


def _sev_counts(items: list[dict]) -> dict[str, int]:
    out = {k: 0 for k in _SEV_ORDER}
    for f in items:
        out[_sev(f)] = out.get(_sev(f), 0) + 1
    return out


def _policy_counts(items: list[dict]) -> dict[str, dict[str, int]]:
    """Per-policy severity counts for the chart. Excludes findings with
    no policy_file or "PROGRAM"-tagged findings so the chart shows only
    real-policy columns (those findings still appear in the main list)."""
    out: dict[str, dict[str, int]] = {}
    for f in items:
        doc = (f.get("policy_file") or "").strip()
        if not doc or doc.upper() == "PROGRAM":
            continue
        # multi-policy "a; b" → first only for chart aggregation
        if ";" in doc:
            doc = doc.split(";", 1)[0].strip()
        if doc not in out:
            out[doc] = {k: 0 for k in _SEV_ORDER}
        out[doc][_sev(f)] += 1
    return out


def _risk_score(c: dict[str, int]) -> int:
    """Weighted severity index 0-100. Each finding contributes a weight
    by severity; score = weighted average / max-possible-weight (1.0)
    expressed as a percentage. Precision Aero (22/48/36/22) → ~50.
    All-critical → 100. All-low → 10. Scales with audit size."""
    total = c["critical"] + c["high"] + c["medium"] + c["low"]
    if total == 0:
        return 0
    weighted = (
        c["critical"] * 1.0
        + c["high"]   * 0.6
        + c["medium"] * 0.3
        + c["low"]    * 0.1
    )
    return round(weighted / total * 100)


def _esc(s) -> str:
    return _html.escape(str(s)) if s is not None else ""


counts = _sev_counts(findings)
total  = sum(counts.values())
score  = _risk_score(counts)


# ══════════════════════════════════════════════════════════════════
#  TREATMENT A HERO STRIP (full-width gradient)
# ══════════════════════════════════════════════════════════════════
if findings:
    hero_sub = (
        f"{_esc(active_client)} &middot; {total} findings across "
        f"{len(policies_loaded)} polic"
        f"{'ies' if len(policies_loaded) != 1 else 'y'}. "
        "Triage, assign, and resolve before renewal."
    )
    hero_chips_html = (
        f'<span class="ta-hero-chip">&#9888; {counts["critical"]} critical</span>'
        f'<span class="ta-hero-chip">&#9888; {counts["high"]} high</span>'
        f'<span class="ta-hero-chip">&#10003; Audit complete</span>'
    )
else:
    hero_sub = "Run an audit on the Analyze page to surface findings here."
    hero_chips_html = ""

_md(f"""
<div class="ta-hero">
  <div class="ta-hero-content">
    <p class="ta-hero-eyebrow">STEP 4 OF 6 &middot; FINDINGS</p>
    <h1 class="ta-hero-title">Findings</h1>
    <p class="ta-hero-sub">{hero_sub}</p>
    <div class="ta-hero-chips">{hero_chips_html}</div>
  </div>
</div>
""")


# ══════════════════════════════════════════════════════════════════
#  CONTENT (.ta-content pulls up over the hero edge)
# ══════════════════════════════════════════════════════════════════
with st.container(key="ta_content"):

    render_stepper(4)

    # ── Empty state ────────────────────────────────────────────────
    if not findings:
        _md("""
        <div class="findings-empty">
          <div class="findings-empty-icon">&#128203;</div>
          <div class="findings-empty-title">No findings loaded yet</div>
          <div class="findings-empty-sub">Run an audit on the Analyze page to surface findings here.</div>
        </div>
        """)
        st.stop()

    # ── Summary row: severity tiles + risk donut + per-policy bars ─
    pc = _policy_counts(findings)
    max_policy_total = max((sum(v.values()) for v in pc.values()), default=1)

    sev_tiles_html = "".join(
        f'<div class="sev-tile {sev}">'
        f'<div class="sev-tile-count">{counts[sev]}</div>'
        f'<div class="sev-tile-label">{sev.capitalize()}</div>'
        f'</div>'
        for sev in _SEV_ORDER
    )

    donut_offset   = 314 * (1 - score / 100)
    risk_band      = "elevated" if score >= 50 else "moderate" if score >= 25 else "healthy"
    risk_band_text = {
        "elevated": "&#9650; Elevated",
        "moderate": "&#9650; Moderate",
        "healthy":  "&#10003; Healthy",
    }[risk_band]

    # Top 6 policies by total finding count, descending
    sorted_pc = sorted(
        pc.items(),
        key=lambda kv: sum(kv[1].values()),
        reverse=True,
    )[:6]

    policy_cols_html = ""
    for doc, dcounts in sorted_pc:
        if sum(dcounts.values()) == 0:
            continue
        doc_label = doc.replace(".pdf", "").replace(".PDF", "").upper()[:8]
        scale = 90 / max_policy_total
        segs_html = "".join(
            f'<div class="policy-bar {_SEV_CSS_CLS[sev]}" '
            f'style="height:{dcounts[sev] * scale:.1f}%"></div>'
            for sev in _SEV_ORDER if dcounts[sev] > 0
        )
        policy_cols_html += (
            f'<div class="policy-col">'
            f'<div class="policy-stack">{segs_html}</div>'
            f'<div class="policy-label">{_esc(doc_label)}</div>'
            f'</div>'
        )

    _md(f"""
    <div class="findings-summary">
      <div class="findings-card">
        <div class="findings-card-head">
          <div class="findings-card-title">Findings by Severity</div>
          <div class="findings-card-meta">{total} total</div>
        </div>
        <div class="sev-grid">{sev_tiles_html}</div>
      </div>
      <div class="risk-card">
        <div class="findings-card-head"><div class="findings-card-title">Risk Score</div></div>
        <div class="risk-donut-wrap">
          <svg class="risk-donut-svg" viewBox="0 0 120 120">
            <circle cx="60" cy="60" r="50" fill="none" stroke="var(--bg-subtle)" stroke-width="12"/>
            <circle cx="60" cy="60" r="50" fill="none" stroke="url(#riskGrad)" stroke-width="12"
                    stroke-linecap="round" stroke-dasharray="314"
                    stroke-dashoffset="{donut_offset:.1f}"/>
            <defs>
              <linearGradient id="riskGrad" x1="0%" y1="0%" x2="100%" y2="100%">
                <stop offset="0%" stop-color="#ef4444"/>
                <stop offset="100%" stop-color="#f97316"/>
              </linearGradient>
            </defs>
          </svg>
          <div class="risk-donut-center">
            <div class="risk-score">{score}</div>
            <div class="risk-score-label">/100</div>
          </div>
        </div>
        <div class="risk-badge {risk_band}">{risk_band_text}</div>
      </div>
      <div class="policy-chart">
        <div class="findings-card-head">
          <div class="findings-card-title">Findings by Policy</div>
          <div class="findings-card-meta">{len(pc)} polic{'ies' if len(pc) != 1 else 'y'}</div>
        </div>
        <div class="policy-bars">{policy_cols_html}</div>
      </div>
    </div>
    """)

    # ── Severity filter row ────────────────────────────────────────
    if "findings_filter_sev" not in st.session_state:
        st.session_state.findings_filter_sev = "all"

    with st.container(key="findings_filter_severity"):
        sev_options = [
            ("all",      f"All ({total})"),
            ("critical", f"Critical ({counts['critical']})"),
            ("high",     f"High ({counts['high']})"),
            ("medium",   f"Medium ({counts['medium']})"),
            ("low",      f"Low ({counts['low']})"),
        ]
        cols = st.columns([1.4, 1.2, 1.4, 1.2, 1.2, 6])
        cols[0].markdown(
            '<div class="findings-filter-label" style="padding-top:6px">Severity</div>',
            unsafe_allow_html=True,
        )
        for i, (key, label) in enumerate(sev_options):
            active = st.session_state.findings_filter_sev == key
            if cols[i + 1].button(
                label,
                key=f"sev_btn_{key}",
                type="primary" if active else "secondary",
                use_container_width=True,
            ):
                st.session_state.findings_filter_sev = key
                st.rerun()

    visible = list(findings)
    if st.session_state.findings_filter_sev != "all":
        visible = [f for f in visible if _sev(f) == st.session_state.findings_filter_sev]

    crit_remaining = sum(1 for f in visible if _sev(f) == "critical")
    # NOTE: `_md` collapses `\n\s*` to nothing, which would eat the
    # single space between {crit_remaining} and "critical" if we
    # line-wrapped the template. Keep this on one line.
    _meta_text = (
        f'<strong>{len(visible)} findings</strong> &middot; '
        f'{crit_remaining}&nbsp;critical require action before renewal'
    )
    _md(f"""
    <div class="findings-results-meta">
      <div class="findings-results-count">{_meta_text}</div>
      <div class="findings-results-sort">Sort by: <strong>Severity &darr;</strong></div>
    </div>
    """)

    sev_rank = {s: i for i, s in enumerate(_SEV_ORDER)}
    visible.sort(key=lambda f: (sev_rank.get(_sev(f), 99), -(f.get("risk_score") or 0)))

    # ── Finding rows (first 30) ───────────────────────────────────
    rows_html = []
    for f in visible[:30]:
        sev = _sev(f)
        sev_icon = "!" if sev in ("critical", "high") else "i"
        title = _esc(f.get("requirement_type") or "(no title)")
        sub_raw = (f.get("gap_description") or f.get("plain_english") or "")
        sub = _esc(sub_raw[:140] + ("…" if len(sub_raw) > 140 else ""))
        doc = _esc((f.get("policy_file") or "—").split(";", 1)[0].strip())
        page = _esc(f.get("policy_page") or "—")
        # Raw category as tag (auditor's language: Ugly / Bad / Review / Good)
        tag = _esc(f.get("category") or "—")

        impact_fill = {"critical": 5, "high": 4, "medium": 3, "low": 2}[sev]
        impact_dots = "".join(
            '<div class="on"></div>' if i < impact_fill else '<div></div>'
            for i in range(5)
        )
        impact_class = "crit" if sev == "critical" else "high" if sev == "high" else ""

        rows_html.append(f"""
        <div class="finding-row {sev}">
          <div class="finding-row-sev">{sev_icon}</div>
          <div>
            <div class="finding-row-title">{title}</div>
            <div class="finding-row-sub">{sub}</div>
          </div>
          <div class="finding-row-meta">
            <div class="finding-row-meta-strong">{doc}</div>
            <div class="finding-row-sub">p. {page}</div>
          </div>
          <div><span class="finding-row-tag">{tag}</span></div>
          <div class="finding-row-impact {impact_class}">{impact_dots}</div>
          <div class="finding-row-action">Review &rarr;</div>
        </div>
        """)

    _md(f'<div class="findings-list">{"".join(rows_html)}</div>')
