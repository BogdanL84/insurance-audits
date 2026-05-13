"""
1_Client_Setup.py — Create a new client or edit an existing one.

Treatment A restyle (2026-05-13): full-width gradient hero strip,
floating stepper card, two form cards (Client Information +
Operations Detail). States picker uses skinned st.multiselect.
Risk Flags use categorized 3-column tile grid (Industry / Compliance
/ Operations) with the pill-toggle pattern.

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


# ── Risk Flag categories (Treatment A) ─────────────────────────────
_TA_RISK_GROUPS = [
    ("INDUSTRY", "industry", [
        "PE-backed / Private Equity",
        "Construction / Contracting",
        "Staffing / PEO",
        "Maritime / USL&H",
    ]),
    ("COMPLIANCE", "compliance", [
        "Government contracts",
        "Healthcare / Medical",
        "Hazardous materials",
        "Food & Beverage / Processing",
    ]),
    ("OPERATIONS", "operations", [
        "Multi-state operations",
        "Transportation / Trucking (MCS-90)",
        "Technology / SaaS",
        "International operations",
        "Real Estate / Property Management",
        "High-value equipment",
    ]),
]


# ── Session-state init (once per active client) ────────────────────
_init_marker = f"_ta_init_for_{selected or 'new'}"
if _init_marker not in st.session_state:
    st.session_state.cs_selected_risks = set(_get("special_risks", []))
    st.session_state.cs_states_ms      = list(_get("states", []))
    st.session_state[_init_marker]     = True


# ══════════════════════════════════════════════════════════════════
#  HERO STRIP (full-width gradient)
# ══════════════════════════════════════════════════════════════════
if is_edit:
    hero_title = f"Edit — {existing_state['display_name']}"
    hero_sub   = ("Update this audit's client details and key risk "
                  "markers so the AI can generate more accurate findings.")
else:
    hero_title = "New Client"
    hero_sub   = ("Set up a new commercial insurance audit. Capture "
                  "client details and key risk markers so the AI can "
                  "generate more accurate findings.")

st.markdown(
    f'<div class="ta-hero">'
    f'<div class="ta-hero-content">'
    f'<p class="ta-hero-eyebrow">STEP 1 OF 6 &middot; SETUP</p>'
    f'<h1 class="ta-hero-title">{hero_title}</h1>'
    f'<p class="ta-hero-sub">{hero_sub}</p>'
    f'<div class="ta-hero-chips">'
    f'<span class="ta-hero-chip">&#10003; Required: Name + Industry</span>'
    f'<span class="ta-hero-chip">&#9201; Takes ~2 min</span>'
    f'</div>'
    f'</div>'
    f'</div>',
    unsafe_allow_html=True,
)


# ══════════════════════════════════════════════════════════════════
#  CONTENT (pulls up over the hero edge via .st-key-ta_content CSS)
# ══════════════════════════════════════════════════════════════════
with st.container(key="ta_content"):

    # ── Stepper ───────────────────────────────────────────────────
    render_stepper(1)

    # ── Card 1: Client Information ────────────────────────────────
    with st.container(key="ta_card_info", border=True):
        st.markdown(
            '<div class="ta-card-head"><div>'
            '<h3 class="ta-card-title">Client Information</h3>'
            '<p class="ta-card-sub">Basic details about the company being audited</p>'
            '</div></div>',
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

    # ── Card 2: Operations Detail (Optional) ──────────────────────
    with st.container(key="ta_card_ops", border=True):
        st.markdown(
            '<div class="ta-card-head">'
            '<div>'
            '<h3 class="ta-card-title">Operations Detail</h3>'
            '<p class="ta-card-sub">Helps the AI generate more accurate findings</p>'
            '</div>'
            '<span class="cs-optional-badge">Optional</span>'
            '</div>',
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

        # ── States of Operation: skinned multiselect ──────────────
        st.markdown(
            "<div class='form-label' style='margin-top:0.6rem'>States of Operation</div>",
            unsafe_allow_html=True,
        )
        with st.container(key="ta_state_picker"):
            states = st.multiselect(
                "States of Operation",
                options=US_STATES,
                key="cs_states_ms",
                label_visibility="collapsed",
                placeholder="Type to search states (CA, TX, NY…)",
            )

        # ── Risk Flags: categorized tile grid ─────────────────────
        st.markdown(
            "<div class='form-label' style='margin-top:1rem'>Risk Flags</div>",
            unsafe_allow_html=True,
        )
        for group_label, group_slug, flags in _TA_RISK_GROUPS:
            st.markdown(
                f"<div class='ta-risk-group-label'>{group_label}</div>",
                unsafe_allow_html=True,
            )
            rows = [flags[i:i + 3] for i in range(0, len(flags), 3)]
            for row in rows:
                cols = st.columns(3)
                for col, flag in zip(cols, row):
                    with col:
                        is_on = flag in st.session_state.cs_selected_risks
                        if st.button(
                            flag,
                            key=f"ta_risk_{group_slug}_{flag}",
                            type="primary" if is_on else "secondary",
                            use_container_width=True,
                        ):
                            if is_on:
                                st.session_state.cs_selected_risks.discard(flag)
                            else:
                                st.session_state.cs_selected_risks.add(flag)
                            st.rerun()

        # ── Contract Parties (free-form) ──────────────────────────
        existing_parties = _get("contract_parties", [])
        contract_parties_raw = st.text_area(
            "Upstream Contract Parties",
            value="\n".join(existing_parties) if existing_parties else "",
            placeholder="One per line:\nABC General Contractor\nCity of Portland",
            height=90,
            help="Who is requiring insurance of this client?",
            key="cs_contract_parties",
        )

    # ── Action bar (white card with Cancel + Continue) ────────────
    with st.container(key="ta_action_bar", border=True):
        btn_cancel, btn_spacer, btn_save = st.columns([2, 5, 3])
        with btn_cancel:
            if st.button("← Cancel", key="cs_cancel", use_container_width=True):
                st.session_state.pop("cs_selected_risks", None)
                st.session_state.pop("cs_states_ms", None)
                st.session_state.pop(_init_marker, None)
                st.switch_page("app.py")
        with btn_save:
            save_label   = "Save Changes →" if is_edit else "Continue to Document Intake →"
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
        "states":           sorted(st.session_state.cs_states_ms or []),
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

    st.session_state.pop("cs_selected_risks", None)
    st.session_state.pop("cs_states_ms", None)
    st.session_state.pop(_init_marker, None)

    st.switch_page("pages/2_Document_Intake.py")
