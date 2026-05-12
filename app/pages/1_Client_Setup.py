"""
1_Client_Setup.py — Create a new client or edit an existing one.

Day-2 restyle (2026-05-12): wide layout with page hero,
6-step stepper, two cards (Client Information + Operations Detail
with Optional badge), pill-toggle States + Risk Flags backed by
session-state sets, ghost-style top Cancel.

Creates:
  clients/[slug]/contracts/
  clients/[slug]/policies/
  clients/[slug]/references/
  clients/[slug]/ai-exchange/
  clients/[slug]/output/
  clients/[slug]/client-notes.md
  clients/[slug]/output/audit-state.json
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import streamlit as st

st.set_page_config(
    page_title="Client Setup — Insurance Audit",
    page_icon="&#128100;",
    layout="wide",
    initial_sidebar_state="expanded",
)

from config import (
    CLIENTS_DIR, INDUSTRIES, REVENUE_RANGES,
    EMPLOYEE_RANGES, US_STATES, SPECIAL_RISK_FLAGS,
)
from core.audit_state import (
    load, save, initialize, slugify, slug_exists,
    create_client_folders, write_client_notes, get_all_display_names,
)
from utils import render_sidebar, render_stepper, inject_css

inject_css()
render_sidebar()


# ── Determine mode: new or edit ────────────────────────────────────
edit_mode = st.session_state.get("client_edit_mode", "new")
selected  = st.session_state.get("selected_client")

existing_state = {}
if edit_mode == "edit" and selected:
    client_path    = CLIENTS_DIR / selected
    existing_state = load(client_path) if client_path.exists() else {}

is_edit = bool(existing_state.get("display_name"))


# ── Pre-fill helpers ───────────────────────────────────────────────
def _get(key, default=""):
    return existing_state.get("client_info", {}).get(key, default)

def _idx(lst, val):
    try:
        return lst.index(val)
    except ValueError:
        return 0


# ── Pill-set session-state initialization (once per client) ────────
# Re-seed only when the active client changes, so navigating away
# and back doesn't reset in-progress edits.
_init_marker = f"_cs_init_for_{selected or 'new'}"
if _init_marker not in st.session_state:
    st.session_state.cs_selected_states = set(_get("states", []))
    st.session_state.cs_selected_risks  = set(_get("special_risks", []))
    st.session_state[_init_marker] = True


def _render_pill_row(
    options: list[str],
    state_key: str,
    key_prefix: str,
    per_row: int,
) -> None:
    """Render a wrapped grid of pill toggle buttons backed by a
    session-state set. Clicking a pill toggles its membership and
    triggers a rerun so the pill's style flips (secondary/primary)."""
    selected_set: set = st.session_state[state_key]
    for row_start in range(0, len(options), per_row):
        row_options = options[row_start:row_start + per_row]
        cols = st.columns(per_row)
        for col, opt in zip(cols, row_options):
            with col:
                is_on = opt in selected_set
                if st.button(
                    opt,
                    key=f"{key_prefix}_{opt}",
                    type="primary" if is_on else "secondary",
                ):
                    if is_on:
                        selected_set.discard(opt)
                    else:
                        selected_set.add(opt)
                    st.rerun()


# ── Page hero (title + Cancel ghost) ───────────────────────────────
if is_edit:
    page_title = f"Edit — {existing_state['display_name']}"
    page_sub   = "Update this commercial insurance audit's setup"
else:
    page_title = "New Client"
    page_sub   = "Set up a new commercial insurance audit"

col_hero, col_cancel_top = st.columns([8, 1])
with col_hero:
    st.markdown(
        f'<div class="page-hero">'
        f'<h1 class="page-hero-title">{page_title}</h1>'
        f'<p class="page-hero-sub">{page_sub}</p>'
        f'</div>',
        unsafe_allow_html=True,
    )
with col_cancel_top:
    st.write("")
    if st.button("Cancel", key="cs_cancel_top", use_container_width=True):
        # Drop any in-progress pill edits on cancel
        st.session_state.pop("cs_selected_states", None)
        st.session_state.pop("cs_selected_risks",  None)
        st.session_state.pop(_init_marker, None)
        st.switch_page("app.py")


# ── Stepper: Setup is step 1 ───────────────────────────────────────
render_stepper(1)


# ── Card 1: Client Information ─────────────────────────────────────
with st.container(border=True):
    st.markdown(
        "<h3 style='margin:0 0 2px;font-size:1rem;font-weight:700'>"
        "Client Information</h3>"
        "<p style='margin:0 0 1rem;font-size:0.78rem;color:var(--muted)'>"
        "Basic details about the company being audited"
        "</p>",
        unsafe_allow_html=True,
    )

    display_name = st.text_input(
        "Client Name *",
        value=existing_state.get("display_name", ""),
        placeholder="e.g. Acme Corporation",
        key="cs_display_name",
    )

    col_ind, col_web = st.columns(2)
    with col_ind:
        industry = st.selectbox(
            "Industry *",
            options=["— select —"] + INDUSTRIES,
            index=_idx(["— select —"] + INDUSTRIES, _get("industry", "— select —")),
            key="cs_industry",
        )
    with col_web:
        website = st.text_input(
            "Website",
            value=_get("website", ""),
            placeholder="e.g. acmecorp.com",
            key="cs_website",
        )

    notes = st.text_area(
        "Notes",
        value=_get("notes", ""),
        placeholder=(
            "Anything useful for the audit — PE-backed, prior claims, "
            "key exposures, what the CFO cares about."
        ),
        height=130,
        help=(
            "Anything useful for the audit: PE-backed, prior claims, key "
            "exposures, contract relationships, what the CFO cares about, "
            "red flags, renewal history."
        ),
        key="cs_notes",
    )

st.markdown("<div style='height:14px'></div>", unsafe_allow_html=True)


# ── Card 2: Operations Detail (Optional) ───────────────────────────
with st.container(border=True):
    head_l, head_r = st.columns([6, 1])
    with head_l:
        st.markdown(
            "<h3 style='margin:0 0 2px;font-size:1rem;font-weight:700'>"
            "Operations Detail</h3>"
            "<p style='margin:0 0 1rem;font-size:0.78rem;color:var(--muted)'>"
            "Helps the AI generate more accurate findings"
            "</p>",
            unsafe_allow_html=True,
        )
    with head_r:
        st.markdown(
            "<div style='text-align:right;padding-top:4px'>"
            "<span class='cs-optional-badge'>Optional</span>"
            "</div>",
            unsafe_allow_html=True,
        )

    col_rev, col_emp = st.columns(2)
    with col_rev:
        revenue = st.selectbox(
            "Annual Revenue",
            options=["— select —"] + REVENUE_RANGES,
            index=_idx(
                ["— select —"] + REVENUE_RANGES,
                _get("revenue", "— select —"),
            ),
            key="cs_revenue",
        )
    with col_emp:
        employees = st.selectbox(
            "Employees",
            options=["— select —"] + EMPLOYEE_RANGES,
            index=_idx(
                ["— select —"] + EMPLOYEE_RANGES,
                _get("employees", "— select —"),
            ),
            key="cs_employees",
        )

    # ── Pill toggle: States of Operation ───────────────────────────
    st.markdown(
        "<div class='form-label' style='margin-top:0.75rem'>"
        "States of Operation</div>",
        unsafe_allow_html=True,
    )
    _render_pill_row(US_STATES, "cs_selected_states", "cs_pill_state", per_row=12)

    # ── Pill toggle: Risk Flags ────────────────────────────────────
    st.markdown(
        "<div class='form-label' style='margin-top:0.85rem'>"
        "Risk Flags</div>",
        unsafe_allow_html=True,
    )
    _render_pill_row(SPECIAL_RISK_FLAGS, "cs_selected_risks", "cs_pill_risk", per_row=4)

    # ── Contract Parties (free-form textarea) ──────────────────────
    existing_parties = _get("contract_parties", [])
    contract_parties_raw = st.text_area(
        "Upstream Contract Parties",
        value="\n".join(existing_parties) if existing_parties else "",
        placeholder="One per line:\nABC General Contractor\nCity of Portland",
        height=90,
        help="Who is requiring insurance of this client?",
        key="cs_contract_parties",
    )

st.markdown("<div style='height:18px'></div>", unsafe_allow_html=True)


# ── Action bar ─────────────────────────────────────────────────────
btn_cancel, btn_spacer, btn_save = st.columns([2, 5, 3])
with btn_cancel:
    if st.button("← Cancel", key="cs_cancel_bottom", use_container_width=True):
        st.session_state.pop("cs_selected_states", None)
        st.session_state.pop("cs_selected_risks",  None)
        st.session_state.pop(_init_marker, None)
        st.switch_page("app.py")

with btn_save:
    save_label = "Save Changes →" if is_edit else "Continue to Document Intake →"
    submit_clicked = st.button(
        save_label,
        key="cs_submit",
        type="primary",
        use_container_width=True,
    )


# ── Handle submit ──────────────────────────────────────────────────
if submit_clicked:
    errors = []

    if not display_name.strip():
        errors.append("Client Name is required.")
    if industry == "— select —":
        errors.append("Please select an Industry.")

    if display_name.strip() and not errors:
        normalized_new = display_name.strip().lower()
        all_names = get_all_display_names(CLIENTS_DIR)
        for existing_slug, existing_name in all_names.items():
            if is_edit and existing_slug == selected:
                continue
            if existing_name.strip().lower() == normalized_new:
                errors.append(
                    f"A client named **{existing_name}** already exists "
                    f"(folder: `{existing_slug}`). "
                    "Please use a different name or edit the existing client."
                )
                break

    if errors:
        for e in errors:
            st.error(e)
        st.stop()

    contract_parties = [
        p.strip() for p in contract_parties_raw.splitlines() if p.strip()
    ]

    client_info = {
        "industry":         industry,
        "website":          website.strip(),
        "revenue":          "" if revenue == "— select —" else revenue,
        "employees":        "" if employees == "— select —" else employees,
        "states":           sorted(st.session_state.cs_selected_states),
        "special_risks":    sorted(st.session_state.cs_selected_risks),
        "contract_parties": contract_parties,
        "notes":            notes.strip(),
    }

    slug = slugify(display_name.strip())

    if not is_edit and slug_exists(CLIENTS_DIR, slug):
        st.error(
            f"A client folder named **{slug}** already exists. "
            "Edit the existing client or use a different name."
        )
        st.stop()

    client_path = create_client_folders(CLIENTS_DIR, slug)

    if is_edit and existing_state:
        existing_state["display_name"] = display_name.strip()
        existing_state["client_info"]  = client_info
        state = existing_state
    else:
        state = initialize(slug, display_name.strip(), client_info)

    save(client_path, state)
    write_client_notes(client_path, state)

    st.session_state.selected_client  = slug
    st.session_state.client_edit_mode = "edit"

    if not is_edit:
        st.session_state.just_created = display_name.strip()

    # Clear pill-set state so a future visit re-seeds from disk
    st.session_state.pop("cs_selected_states", None)
    st.session_state.pop("cs_selected_risks",  None)
    st.session_state.pop(_init_marker, None)

    st.switch_page("pages/2_Document_Intake.py")
