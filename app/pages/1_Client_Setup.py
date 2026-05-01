"""
1_Client_Setup.py — Create a new client or edit an existing one.

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
    layout="centered",
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
from utils import render_sidebar, render_progress_bar, inject_css, render_breadcrumb

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


# ── Page header ────────────────────────────────────────────────────
if is_edit:
    render_breadcrumb(existing_state["display_name"], "Edit Client")
    st.title(f"Edit — {existing_state['display_name']}")
    render_progress_bar(existing_state.get("stage", "setup"), active_step=0)
else:
    st.title("New Client")
    render_progress_bar("setup", active_step=0)

st.divider()


# ── Form ───────────────────────────────────────────────────────────
with st.form("client_setup_form", border=False):

    # ── Core fields (always visible) ──────────────────────────────
    display_name = st.text_input(
        "Client Name *",
        value=existing_state.get("display_name", ""),
        placeholder="e.g. Acme Corporation",
    )

    col_ind, col_web = st.columns(2)
    with col_ind:
        industry = st.selectbox(
            "Industry *",
            options=["— select —"] + INDUSTRIES,
            index=_idx(["— select —"] + INDUSTRIES, _get("industry", "— select —")),
        )
    with col_web:
        website = st.text_input(
            "Website",
            value=_get("website", ""),
            placeholder="e.g. acmecorp.com",
        )

    st.markdown("<br>", unsafe_allow_html=True)

    notes = st.text_area(
        "Notes",
        value=_get("notes", ""),
        placeholder=(
            "Anything useful for the audit: PE-backed, prior claims, key exposures, "
            "contract relationships, what the CFO cares about, red flags, renewal history…"
        ),
        height=140,
        help=(
            "This text is included in every Claude Code prompt so the AI understands "
            "the client's context when analyzing contracts and policies."
        ),
    )

    # ── Advanced / optional fields ─────────────────────────────────
    st.markdown("<br>", unsafe_allow_html=True)
    with st.expander("Advanced — Revenue, Headcount, States, Risk Flags, Contract Parties"):
        col_rev, col_emp = st.columns(2)
        with col_rev:
            revenue = st.selectbox(
                "Annual Revenue",
                options=["— select —"] + REVENUE_RANGES,
                index=_idx(
                    ["— select —"] + REVENUE_RANGES,
                    _get("revenue", "— select —"),
                ),
            )
        with col_emp:
            employees = st.selectbox(
                "Employee Count",
                options=["— select —"] + EMPLOYEE_RANGES,
                index=_idx(
                    ["— select —"] + EMPLOYEE_RANGES,
                    _get("employees", "— select —"),
                ),
            )

        states = st.multiselect(
            "States of Operation",
            options=US_STATES,
            default=_get("states", []),
            help="All states where this client has employees, operations, or property.",
        )

        special_risks = st.multiselect(
            "Special Risk Flags",
            options=SPECIAL_RISK_FLAGS,
            default=_get("special_risks", []),
            help="Activates relevant checklist items in the Audit Workspace.",
        )

        existing_parties = _get("contract_parties", [])
        contract_parties_raw = st.text_area(
            "Upstream Contract Parties",
            value="\n".join(existing_parties) if existing_parties else "",
            placeholder="One per line:\nABC General Contractor\nCity of Portland",
            height=100,
            help="Who is requiring insurance of this client?",
        )

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Submit ─────────────────────────────────────────────────────
    btn_cancel, btn_spacer, btn_save = st.columns([1, 2, 1])
    with btn_cancel:
        cancel = st.form_submit_button("Cancel", use_container_width=True)
    with btn_save:
        label     = "Save Changes >" if is_edit else "Create Client >"
        submitted = st.form_submit_button(label, type="primary", use_container_width=True)


# ── Handle cancel ──────────────────────────────────────────────────
if cancel:
    st.switch_page("app.py")


# ── Handle submit ──────────────────────────────────────────────────
if submitted:
    errors = []

    # Required field checks
    if not display_name.strip():
        errors.append("Client Name is required.")
    if industry == "— select —":
        errors.append("Please select an Industry.")

    # Duplicate display name check (case-insensitive, excluding self when editing)
    if display_name.strip() and not errors:
        normalized_new = display_name.strip().lower()
        all_names = get_all_display_names(CLIENTS_DIR)
        for existing_slug, existing_name in all_names.items():
            # Skip self when editing
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
        "states":           states,
        "special_risks":    special_risks,
        "contract_parties": contract_parties,
        "notes":            notes.strip(),
    }

    slug = slugify(display_name.strip())

    # Slug collision check for new clients
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

    # Signal to Document Intake to show a welcome message
    if not is_edit:
        st.session_state.just_created = display_name.strip()

    # Auto-redirect to Document Intake
    st.switch_page("pages/2_Document_Intake.py")
