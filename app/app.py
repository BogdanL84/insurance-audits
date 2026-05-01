"""
app.py — Dashboard (home page)

Displays all clients as cards with stage indicators and finding counts.
Supports inline delete with confirmation.
"""

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
    COLOR_GOOD, COLOR_BAD, COLOR_UGLY, COLOR_NAVY,
    STAGE_COLORS, STAGES,
)
from core.audit_state import list_clients, delete_client
from utils import render_sidebar, stage_badge, inject_css

inject_css()
render_sidebar()


# ── Header ─────────────────────────────────────────────────────────
col_title, col_btn = st.columns([7, 2])
with col_title:
    st.markdown(
        "<h1 style='margin-bottom:0'>Insurance Audit System</h1>"
        f"<p style='color:#666;margin-top:2px;font-size:0.875rem'>"
        f"{BROKER_NAME} &middot; {BROKER_COMPANY}</p>",
        unsafe_allow_html=True,
    )
with col_btn:
    st.write("")  # vertical spacer
    if st.button("+ New Client", type="primary", use_container_width=True):
        st.session_state.selected_client  = None
        st.session_state.client_edit_mode = "new"
        st.switch_page("pages/1_Client_Setup.py")

st.divider()


# ── Load clients ───────────────────────────────────────────────────
clients = list_clients(CLIENTS_DIR)


# ── Empty state ────────────────────────────────────────────────────
if not clients:
    st.markdown("<br>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        st.markdown(
            "<div style='text-align:center;padding:2rem 0'>"
            "<div style='font-size:3rem'>&#128196;</div>"
            "<h3>No clients yet</h3>"
            "<p style='color:#666'>Create your first audit to get started. "
            "Each client gets its own folder for contracts, policies, and findings.</p>"
            "</div>",
            unsafe_allow_html=True,
        )
        if st.button("+ Create First Client", type="primary", use_container_width=True):
            st.session_state.selected_client  = None
            st.session_state.client_edit_mode = "new"
            st.switch_page("pages/1_Client_Setup.py")
    st.stop()


# ── Stats bar ──────────────────────────────────────────────────────
total_findings = sum(c["summary"]["total_findings"] for c in clients)
total_good     = sum(c["summary"]["good"]  for c in clients)
total_bad      = sum(c["summary"]["bad"]   for c in clients)
total_ugly     = sum(c["summary"]["ugly"]  for c in clients)

# Count clients at each stage bracket
clients_with_findings = sum(1 for c in clients if c["summary"]["total_findings"] > 0)
clients_critical      = sum(1 for c in clients if c["summary"]["ugly"] > 0)

m1, m2, m3, m4, m5 = st.columns(5)
m1.metric("Total Clients",    len(clients))
m2.metric("Active Audits",    clients_with_findings)
m3.metric("Critical Issues",  total_ugly,  delta=None,
          help="Total Ugly findings across all clients")
m4.metric("Gaps to Address",  total_bad,
          help="Total Bad findings across all clients")
m5.metric("Compliant Items",  total_good,
          help="Total Good findings across all clients")

st.markdown("<br>", unsafe_allow_html=True)


# ── Client card renderer ───────────────────────────────────────────
def render_card(client: dict) -> None:
    s           = client["summary"]
    stage       = client["stage"]
    color       = STAGE_COLORS.get(stage, "#9E9E9E")
    stage_label = dict(STAGES).get(stage, stage)
    slug        = client["slug"]

    # Check if delete confirmation is active for this card
    confirm_key = f"confirm_delete_{slug}"
    is_confirming = st.session_state.get(confirm_key, False)

    with st.container(border=True):
        if is_confirming:
            # ── Delete confirmation overlay ────────────────────────
            st.markdown(
                f"<div style='background:#FFEBEE;border-radius:6px;padding:0.75rem;"
                f"margin-bottom:0.5rem'>"
                f"<strong style='color:#B71C1C'>Delete {client['display_name']}?</strong><br>"
                f"<span style='font-size:0.875rem;color:#555'>"
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
                        # Clear selected client if it was this one
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

        # ── Normal card view ───────────────────────────────────────

        # Stage pill + date row
        col_stage, col_date = st.columns([3, 2])
        with col_stage:
            st.markdown(
                f"<span style='background:{color};color:white;padding:2px 9px;"
                f"border-radius:10px;font-size:0.75rem;font-weight:600;"
                f"-webkit-font-smoothing:antialiased'>{stage_label}</span>",
                unsafe_allow_html=True,
            )
        with col_date:
            st.markdown(
                f"<span style='font-size:0.75rem;color:#888'>"
                f"{client['last_modified']}</span>",
                unsafe_allow_html=True,
            )

        # Client name
        st.markdown(
            f"<h3 style='margin:6px 0 2px'>{client['display_name']}</h3>",
            unsafe_allow_html=True,
        )
        if client["industry"]:
            st.caption(client["industry"])

        st.markdown("<br>", unsafe_allow_html=True)

        # Document counts
        doc_parts = []
        if s["contracts"]:
            doc_parts.append(
                f"{s['contracts']} contract{'s' if s['contracts'] != 1 else ''}"
            )
        if s["policies"]:
            doc_parts.append(
                f"{s['policies']} polic{'ies' if s['policies'] != 1 else 'y'}"
            )
        if doc_parts:
            st.caption(" · ".join(doc_parts))
        else:
            st.caption("No documents uploaded yet")

        # Program-at-a-Glance: policy type badges
        ptc = client.get("policy_type_counts", {})
        if ptc:
            _type_colors = {
                "gl": "#1565C0", "general liability": "#1565C0",
                "wc": "#2E7D32", "workers": "#2E7D32",
                "auto": "#E65100", "commercial auto": "#E65100",
                "umbrella": "#6A1B9A", "excess": "#6A1B9A",
                "cyber": "#00838F", "professional": "#00695C",
                "e&o": "#00695C", "d&o": "#4527A0",
                "management": "#4527A0", "epli": "#880E4F",
                "crime": "#BF360C", "property": "#558B2F",
            }
            def _pt_color(pt):
                ptl = pt.lower()
                for kw, clr in _type_colors.items():
                    if kw in ptl:
                        return clr
                return "#607D8B"

            badges_html = " ".join(
                f"<span style='background:{_pt_color(pt)};color:white;"
                f"padding:1px 7px;border-radius:9px;font-size:0.7rem;font-weight:600;"
                f"white-space:nowrap;overflow:hidden;text-overflow:ellipsis;"
                f"max-width:200px'>{pt} ({cnt})</span>"
                for pt, cnt in sorted(ptc.items())
            )
            st.markdown(
                f"<div style='margin:4px 0 2px;display:flex;flex-wrap:wrap;gap:4px'>"
                f"{badges_html}</div>",
                unsafe_allow_html=True,
            )

        # Finding counts
        if s["total_findings"] > 0:
            c_good, c_bad, c_ugly = st.columns(3)
            with c_good:
                st.markdown(
                    f"<div style='text-align:center'>"
                    f"<span style='font-size:1.5rem;font-weight:700;color:{COLOR_GOOD}'>"
                    f"{s['good']}</span><br>"
                    f"<span style='font-size:0.75rem;color:#666'>Good</span></div>",
                    unsafe_allow_html=True,
                )
            with c_bad:
                st.markdown(
                    f"<div style='text-align:center'>"
                    f"<span style='font-size:1.5rem;font-weight:700;color:{COLOR_BAD}'>"
                    f"{s['bad']}</span><br>"
                    f"<span style='font-size:0.75rem;color:#666'>Bad</span></div>",
                    unsafe_allow_html=True,
                )
            with c_ugly:
                st.markdown(
                    f"<div style='text-align:center'>"
                    f"<span style='font-size:1.5rem;font-weight:700;color:{COLOR_UGLY}'>"
                    f"{s['ugly']}</span><br>"
                    f"<span style='font-size:0.75rem;color:#666'>Ugly</span></div>",
                    unsafe_allow_html=True,
                )
        else:
            st.markdown(
                "<span style='font-size:0.875rem;color:#bbb'>No findings yet</span>",
                unsafe_allow_html=True,
            )

        # Quick stats line
        qs_parts = []
        if s["policies"]:
            qs_parts.append(f"{s['policies']} polic{'ies' if s['policies'] != 1 else 'y'} analyzed")
        if s["total_findings"]:
            qs_parts.append(f"{s['total_findings']} findings")
        if s["ugly"]:
            qs_parts.append(f"<span style='color:{COLOR_UGLY};font-weight:600'>{s['ugly']} critical</span>")
        last_run = client.get("last_analysis_date", "")
        if last_run:
            qs_parts.append(f"Last run: {last_run}")
        if qs_parts:
            st.markdown(
                f"<div style='font-size:0.75rem;color:#888;margin-top:4px'>"
                f"{'&nbsp;&middot;&nbsp;'.join(qs_parts)}</div>",
                unsafe_allow_html=True,
            )

        st.markdown("<br>", unsafe_allow_html=True)

        # Action buttons: Open | Edit | Delete
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
