"""
app.py — Dashboard (home page)

Day-1 restyle (2026-05-11): Salesforce-vibrant light-mode-first.
Gradient hero, 4 gradient stat tiles, inline-SVG donut +
per-client stacked-bar panel, gradient-strip client cards.
Audit-report visual product (core/html_report.py) is untouched.
"""

import html as _html
import math
import re as _re
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

import streamlit as st

st.set_page_config(
    page_title="Insurance Audit System",
    page_icon="&#128737;",
    layout="wide",
    initial_sidebar_state="expanded",
)

from config import (
    CLIENTS_DIR, BROKER_NAME, BROKER_TITLE, BROKER_COMPANY,
    BROKER_EMAIL, BROKER_PHONE,
    STAGES,
)
from core.audit_state import list_clients, delete_client
from utils import render_sidebar, inject_css, _mark_active_nav

inject_css()
render_sidebar()
_mark_active_nav("")  # Dashboard is the root path


# ── Helpers ────────────────────────────────────────────────────────
def _esc(s) -> str:
    return _html.escape(str(s)) if s is not None else ""

def _md(html: str) -> None:
    """st.markdown(unsafe_allow_html=True) but with leading whitespace
    collapsed so multi-line f-string HTML isn't parsed as code blocks
    by Streamlit's markdown processor (>=4-space indent → <pre><code>)."""
    st.markdown(_re.sub(r"\n\s*", "", html), unsafe_allow_html=True)

def _stage_label(stage: str) -> str:
    return dict(STAGES).get(stage, stage)

def _stage_pill_class(stage: str) -> str:
    if stage in ("findings_reviewed", "output_generated"):
        return "success"
    if stage == "findings_imported":
        return "warm"
    if stage in ("docs_uploaded", "text_extracted"):
        return "primary"
    return ""

def _strip_class(client: dict) -> str:
    s = client["summary"]
    stage = client["stage"]
    if s["ugly"] > 0:
        return "danger"
    if s["bad"] > 0:
        return "warm"
    if s["total_findings"] > 0:
        return "success"
    if stage in ("docs_uploaded", "text_extracted", "findings_imported"):
        return "primary"
    return "neutral"


# ── Load clients ───────────────────────────────────────────────────
clients = list_clients(CLIENTS_DIR)


# ── Hero header ────────────────────────────────────────────────────
total_findings = sum(c["summary"]["total_findings"] for c in clients)
total_good     = sum(c["summary"]["good"]  for c in clients)
total_bad      = sum(c["summary"]["bad"]   for c in clients)
total_ugly     = sum(c["summary"]["ugly"]  for c in clients)
clients_with_findings = sum(1 for c in clients if c["summary"]["total_findings"] > 0)

if clients:
    sub_parts = [f"{len(clients)} client{'s' if len(clients) != 1 else ''}"]
    if total_findings:
        sub_parts.append(f"{total_findings} total findings")
    if total_ugly:
        sub_parts.append(f"{total_ugly} critical exposure{'s' if total_ugly != 1 else ''}")
    subtitle = " · ".join(sub_parts)
else:
    subtitle = "Create your first audit to get started."

col_title, col_btn = st.columns([7, 2])
with col_title:
    _md(
        f"""<div class="page-hero">
          <h1 class="page-hero-title">Audit Dashboard</h1>
          <p class="page-hero-sub">{_esc(subtitle)}</p>
        </div>"""
    )
with col_btn:
    st.write("")  # vertical spacer
    if st.button("+ New Client", type="primary", use_container_width=True):
        st.session_state.selected_client  = None
        st.session_state.client_edit_mode = "new"
        st.switch_page("pages/1_Client_Setup.py")


# ── Empty state ────────────────────────────────────────────────────
if not clients:
    st.markdown("<br>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        st.markdown(
            "<div style='text-align:center;padding:2rem 0'>"
            "<div style='font-size:3rem'>&#128196;</div>"
            "<h3>No clients yet</h3>"
            "<p style='color:var(--text-secondary)'>Create your first audit to get started. "
            "Each client gets its own folder for contracts, policies, and findings.</p>"
            "</div>",
            unsafe_allow_html=True,
        )
        if st.button("+ Create First Client", type="primary", use_container_width=True):
            st.session_state.selected_client  = None
            st.session_state.client_edit_mode = "new"
            st.switch_page("pages/1_Client_Setup.py")
    st.stop()


# ── Stat tiles (4 gradient tiles) ──────────────────────────────────
clean_clients = clients_with_findings - sum(
    1 for c in clients if c["summary"]["ugly"] > 0 or c["summary"]["bad"] > 0
)
clean_clients = max(clean_clients, 0)

tiles_html = f"""
<div class="stat-tile primary">
  <div class="stat-glyph">&#128202;</div>
  <p class="stat-label">Active Audits</p>
  <p class="stat-value">{clients_with_findings}</p>
  <p class="stat-trend">of {len(clients)} total clients</p>
</div>
"""
tile2 = f"""
<div class="stat-tile warm">
  <div class="stat-glyph">&#9888;</div>
  <p class="stat-label">Findings Generated</p>
  <p class="stat-value">{total_findings}</p>
  <p class="stat-trend">{total_bad} need attention</p>
</div>
"""
tile3 = f"""
<div class="stat-tile danger">
  <div class="stat-glyph">&#128293;</div>
  <p class="stat-label">Critical Exposures</p>
  <p class="stat-value">{total_ugly}</p>
  <p class="stat-trend">requires immediate action</p>
</div>
"""
tile4 = f"""
<div class="stat-tile success">
  <div class="stat-glyph">&#10004;</div>
  <p class="stat-label">Compliant Items</p>
  <p class="stat-value">{total_good}</p>
  <p class="stat-trend">good across all programs</p>
</div>
"""

t1, t2, t3, t4 = st.columns(4)
with t1: _md(tiles_html)
with t2: _md(tile2)
with t3: _md(tile3)
with t4: _md(tile4)

st.markdown("<div style='height:18px'></div>", unsafe_allow_html=True)


# ── Findings overview row: donut + per-client bars ─────────────────
if total_findings > 0:
    # Donut SVG (Good / Bad / Ugly distribution)
    R = 40
    CIRC = 2 * math.pi * R
    total = total_good + total_bad + total_ugly
    g_len = (total_good / total) * CIRC if total else 0
    b_len = (total_bad  / total) * CIRC if total else 0
    u_len = (total_ugly / total) * CIRC if total else 0

    # Each segment: stroke-dasharray "seg_len gap_len" + dashoffset for position.
    # All segments start at 12 o'clock via the transform rotate(-90).
    def _seg(color: str, length: float, offset: float) -> str:
        return (
            f'<circle cx="60" cy="60" r="{R}" fill="none" '
            f'stroke="{color}" stroke-width="14" '
            f'stroke-dasharray="{length:.2f} {CIRC - length:.2f}" '
            f'stroke-dashoffset="{-offset:.2f}" '
            f'transform="rotate(-90 60 60)" />'
        )

    donut_svg = f"""
    <svg width="120" height="120" viewBox="0 0 120 120">
      <circle cx="60" cy="60" r="{R}" fill="none"
              stroke="var(--bg-subtle)" stroke-width="14" />
      {_seg("#10b981", g_len, 0)}
      {_seg("#f97316", b_len, g_len)}
      {_seg("#ef4444", u_len, g_len + b_len)}
      <text x="60" y="58" text-anchor="middle"
            font-family="JetBrains Mono, monospace" font-size="20"
            font-weight="700" fill="var(--text-primary)">{total_findings}</text>
      <text x="60" y="74" text-anchor="middle"
            font-family="Inter, sans-serif" font-size="9"
            font-weight="600" fill="var(--text-muted)"
            letter-spacing="0.1em">FINDINGS</text>
    </svg>
    """

    donut_legend = f"""
    <div class="donut-legend">
      <div class="row"><span class="swatch" style="background:#10b981"></span>
        Good<span class="count">{total_good}</span></div>
      <div class="row"><span class="swatch" style="background:#f97316"></span>
        Bad<span class="count">{total_bad}</span></div>
      <div class="row"><span class="swatch" style="background:#ef4444"></span>
        Ugly<span class="count">{total_ugly}</span></div>
    </div>
    """

    # Per-client stacked bars — top 6 by total findings
    rated = [c for c in clients if c["summary"]["total_findings"] > 0]
    rated.sort(key=lambda c: c["summary"]["total_findings"], reverse=True)
    rated = rated[:6]
    max_total = max((c["summary"]["total_findings"] for c in rated), default=1)

    bar_rows = []
    for c in rated:
        s = c["summary"]
        tot = s["total_findings"]
        # Track width relative to max
        track_pct = (tot / max_total) * 100 if max_total else 0
        # Within the track, segments are proportions of THIS client's total
        g_pct = (s["good"] / tot) * 100 if tot else 0
        b_pct = (s["bad"]  / tot) * 100 if tot else 0
        u_pct = (s["ugly"] / tot) * 100 if tot else 0
        bar_rows.append(f"""
          <div class="client-bar-row">
            <div class="client-bar-name" title="{_esc(c['display_name'])}">{_esc(c['display_name'])}</div>
            <div class="client-bar-track" style="width:{track_pct:.1f}%">
              <div class="client-bar-seg good" style="width:{g_pct:.1f}%"></div>
              <div class="client-bar-seg bad"  style="width:{b_pct:.1f}%"></div>
              <div class="client-bar-seg ugly" style="width:{u_pct:.1f}%"></div>
            </div>
            <div class="client-bar-count">{tot}</div>
          </div>
        """)

    bars_html = "<div class='client-bars'>" + "".join(bar_rows) + "</div>"

    col_a, col_b = st.columns([1, 2])
    with col_a:
        _md(
            f"""<div class="panel-card">
              <p class="panel-title">Findings Mix</p>
              <div class="donut-wrap">{donut_svg}{donut_legend}</div>
            </div>"""
        )
    with col_b:
        _md(
            f"""<div class="panel-card">
              <p class="panel-title">Top Clients by Findings</p>
              {bars_html}
            </div>"""
        )

    st.markdown("<div style='height:22px'></div>", unsafe_allow_html=True)


# ── Client card renderer ───────────────────────────────────────────
def render_card(client: dict) -> None:
    s           = client["summary"]
    stage       = client["stage"]
    stage_label = _stage_label(stage)
    stage_cls   = _stage_pill_class(stage)
    strip_cls   = _strip_class(client)
    slug        = client["slug"]

    confirm_key   = f"confirm_delete_{slug}"
    is_confirming = st.session_state.get(confirm_key, False)

    if is_confirming:
        # ── Delete confirmation overlay ────────────────────────────
        with st.container(border=True):
            st.markdown(
                f"<div style='background:rgba(239,68,68,0.08);border-radius:8px;padding:0.75rem;"
                f"margin-bottom:0.5rem'>"
                f"<strong style='color:var(--red)'>Delete {_esc(client['display_name'])}?</strong><br>"
                f"<span style='font-size:0.875rem;color:var(--text-secondary)'>"
                f"This will permanently delete all documents, findings, and data "
                f"for this client. This cannot be undone.</span>"
                f"</div>",
                unsafe_allow_html=True,
            )
            del_col1, del_col2 = st.columns(2)
            with del_col1:
                if st.button(
                    "Yes, Delete",
                    key=f"confirm_yes_{slug}",
                    type="primary",
                    use_container_width=True,
                ):
                    deleted = delete_client(CLIENTS_DIR, slug)
                    if deleted:
                        if st.session_state.get("selected_client") == slug:
                            st.session_state.selected_client = None
                        del st.session_state[confirm_key]
                        st.rerun()
                    else:
                        st.error("Could not delete client folder.")
            with del_col2:
                if st.button(
                    "Cancel",
                    key=f"confirm_no_{slug}",
                    use_container_width=True,
                ):
                    del st.session_state[confirm_key]
                    st.rerun()
        return

    # ── Normal card body (HTML hero) + Streamlit action buttons ────
    ptc = client.get("policy_type_counts", {})
    policy_tags_html = ""
    if ptc:
        tags = "".join(
            f'<span class="cc-policy-tag">{_esc(pt)} ({cnt})</span>'
            for pt, cnt in sorted(ptc.items())
        )
        policy_tags_html = f'<div class="cc-policy-tags">{tags}</div>'

    doc_parts = []
    if s["contracts"]:
        doc_parts.append(f"{s['contracts']} contract{'s' if s['contracts'] != 1 else ''}")
    if s["policies"]:
        doc_parts.append(f"{s['policies']} polic{'ies' if s['policies'] != 1 else 'y'}")
    docs_line = " · ".join(doc_parts) if doc_parts else "No documents uploaded yet"

    if s["total_findings"] > 0:
        findings_strip = f"""
        <div class="findings-strip">
          <div class="fchip good"><span class="v">{s['good']}</span><span class="l">Good</span></div>
          <div class="fchip bad"><span class="v">{s['bad']}</span><span class="l">Bad</span></div>
          <div class="fchip ugly"><span class="v">{s['ugly']}</span><span class="l">Ugly</span></div>
        </div>
        """
    else:
        findings_strip = """
        <div class="findings-strip">
          <div class="fchip empty"><span class="l">No findings yet</span></div>
        </div>
        """

    industry_html = (
        f'<p class="cc-industry">{_esc(client["industry"])}</p>'
        if client.get("industry") else ""
    )

    _md(
        f"""<div class="client-card">
          <div class="cc-strip {strip_cls}"></div>
          <div class="cc-head">
            <span class="cc-stage {stage_cls}">{_esc(stage_label)}</span>
            <span class="cc-date">{_esc(client['last_modified'])}</span>
          </div>
          <h3 class="cc-name">{_esc(client['display_name'])}</h3>
          {industry_html}
          <p class="cc-docs">{_esc(docs_line)}</p>
          {policy_tags_html}
          {findings_strip}
        </div>"""
    )

    # Action buttons (Streamlit, post-card so they're clickable)
    btn_open, btn_edit, btn_del = st.columns([3, 2, 1])
    with btn_open:
        if st.button(
            "Open &rarr;",
            key=f"open_{slug}",
            use_container_width=True,
            type="primary",
        ):
            st.session_state.selected_client = slug
            st.switch_page("pages/2_Document_Intake.py")
    with btn_edit:
        if st.button(
            "Edit",
            key=f"edit_{slug}",
            use_container_width=True,
        ):
            st.session_state.selected_client  = slug
            st.session_state.client_edit_mode = "edit"
            st.switch_page("pages/1_Client_Setup.py")
    with btn_del:
        if st.button(
            "&#128465;",
            key=f"delete_{slug}",
            use_container_width=True,
            help="Delete this client",
        ):
            st.session_state[confirm_key] = True
            st.rerun()


# ── 3-column grid ──────────────────────────────────────────────────
COLS = 3
rows = [clients[i:i + COLS] for i in range(0, len(clients), COLS)]

for row in rows:
    cols = st.columns(COLS)
    for col, client in zip(cols, row):
        with col:
            render_card(client)


# ── Footer ─────────────────────────────────────────────────────────
st.divider()
st.caption(
    f"{BROKER_NAME} &middot; {BROKER_TITLE} &middot; "
    f"{BROKER_EMAIL} &middot; {BROKER_PHONE}"
)
