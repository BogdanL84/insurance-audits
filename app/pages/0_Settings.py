"""
0_Settings.py — Broker branding and application settings.

Saves to insurance-audits/settings.json.
All report generators, email drafts, and PDF covers read from this file.
"""

import sys
import shutil
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import streamlit as st

st.set_page_config(
    page_title="Settings — Insurance Audit",
    layout="wide",
    initial_sidebar_state="expanded",
)

from core.settings import load as load_settings, save as save_settings
from config import ASSETS_DIR
from utils import render_sidebar, inject_css

inject_css()
render_sidebar()

st.title("Settings")
st.caption("Broker branding used on all reports, emails, and PDF covers.")
st.divider()

settings = load_settings()

ASSETS_DIR.mkdir(parents=True, exist_ok=True)


# ══════════════════════════════════════════════════════════════════
#  BROKER INFO FORM
# ══════════════════════════════════════════════════════════════════
st.subheader("Broker Information")
st.markdown("<br>", unsafe_allow_html=True)

with st.form("settings_form"):
    c1, c2 = st.columns(2)

    with c1:
        broker_name = st.text_input(
            "Broker Name (with designations)",
            value=settings.get("broker_name", ""),
            placeholder="e.g. Jane Smith, CLCS",
        )
        broker_company = st.text_input(
            "Company Name",
            value=settings.get("broker_company", ""),
            placeholder="e.g. Acme Insurance Services",
        )
        broker_email = st.text_input(
            "Email",
            value=settings.get("broker_email", ""),
            placeholder="name@company.com",
        )

    with c2:
        broker_title = st.text_input(
            "Title / Designation",
            value=settings.get("broker_title", ""),
            placeholder="e.g. Strategic Risk Consultant | Property & Casualty",
        )
        broker_phone = st.text_input(
            "Phone",
            value=settings.get("broker_phone", ""),
            placeholder="e.g. (555) 123-4567",
        )

    st.markdown("<br>", unsafe_allow_html=True)
    saved = st.form_submit_button("Save Settings", type="primary")

if saved:
    new_settings = {
        "broker_name":    broker_name.strip(),
        "broker_title":   broker_title.strip(),
        "broker_company": broker_company.strip(),
        "broker_email":   broker_email.strip(),
        "broker_phone":   broker_phone.strip(),
        "logo_filename":  settings.get("logo_filename"),
    }
    try:
        save_settings(new_settings)
        st.success("Settings saved. Changes take effect on the next app restart.")
    except RuntimeError as e:
        st.error(str(e))

st.divider()


# ══════════════════════════════════════════════════════════════════
#  LOGO UPLOAD
# ══════════════════════════════════════════════════════════════════
st.subheader("Company Logo")
st.caption(
    "Upload a PNG or JPG logo. It will be used on PDF cover pages. "
    "Saved to `app/assets/`."
)
st.markdown("<br>", unsafe_allow_html=True)

current_logo = settings.get("logo_filename")
if current_logo:
    logo_path = ASSETS_DIR / current_logo
    if logo_path.exists():
        st.markdown("**Current logo:**")
        st.image(str(logo_path), width=200)
        if st.button("Remove Logo", key="remove_logo"):
            settings["logo_filename"] = None
            save_settings(settings)
            st.success("Logo removed.")
            st.rerun()
    else:
        st.caption(f"*Logo file `{current_logo}` not found in assets/.*")

uploaded = st.file_uploader(
    "Upload new logo (PNG, JPG, max 2MB)",
    type=["png", "jpg", "jpeg"],
    key="logo_uploader",
)
if uploaded:
    if uploaded.size > 2 * 1024 * 1024:
        st.error("Logo file is too large. Maximum size is 2MB.")
    else:
        ext = Path(uploaded.name).suffix.lower()
        logo_filename = f"broker-logo{ext}"
        dest = ASSETS_DIR / logo_filename
        dest.write_bytes(uploaded.read())
        settings["logo_filename"] = logo_filename
        save_settings(settings)
        st.success(f"Logo saved as `assets/{logo_filename}`.")
        st.rerun()

st.divider()


# ══════════════════════════════════════════════════════════════════
#  PREVIEW
# ══════════════════════════════════════════════════════════════════
st.subheader("Report Signature Preview")
st.caption("This is how your signature block will appear on reports and emails.")

current = load_settings()
sig_text = (
    f"---\n"
    f"{current['broker_name']}\n"
    f"{current['broker_title']}\n"
    f"{current['broker_company']}\n"
    f"{current['broker_email']} | {current['broker_phone']}"
)
st.code(sig_text, language=None)

st.divider()
st.caption(
    "Settings are stored in `insurance-audits/settings.json`. "
    "A full app restart is required for changes to take effect everywhere."
)
