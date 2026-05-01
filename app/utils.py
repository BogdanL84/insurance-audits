"""
utils.py — Shared UI helpers used across all pages.

Import pattern in each page:
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))
    import streamlit as st
    st.set_page_config(...)          # must be first Streamlit call
    from utils import render_sidebar, require_client, render_progress_bar, inject_css
"""

import json
import streamlit as st
from pathlib import Path
from config import (
    CLIENTS_DIR, BROKER_NAME, BROKER_COMPANY,
    COLOR_GOOD, COLOR_BAD, COLOR_UGLY, COLOR_NAVY,
    STAGE_COLORS, STAGES,
)
from core.audit_state import list_clients, load as load_state

# ── Settings file (theme lives here, read directly to bypass module cache) ──
_SETTINGS_PATH = Path(__file__).parent.parent / "settings.json"


def _load_theme() -> str:
    """Read theme from settings.json on every call — not cached."""
    try:
        return json.loads(_SETTINGS_PATH.read_text(encoding="utf-8")).get("theme", "dark")
    except Exception:
        return "dark"


def _save_theme(theme: str) -> None:
    """Write theme back to settings.json."""
    try:
        data = json.loads(_SETTINGS_PATH.read_text(encoding="utf-8"))
        data["theme"] = theme
        _SETTINGS_PATH.write_text(
            json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8"
        )
    except Exception:
        pass


# ══════════════════════════════════════════════════════════════════
#  CSS DESIGN SYSTEM
# ══════════════════════════════════════════════════════════════════

# ── Google Fonts ──────────────────────────────────────────────────
_FONTS_HTML = """
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=DM+Sans:ital,opsz,wght@0,9..40,300;0,9..40,400;0,9..40,500;0,9..40,600;0,9..40,700;1,9..40,400&family=DM+Mono:ital,wght@0,400;0,500;1,400&display=swap" rel="stylesheet">
"""

# ── Dark theme CSS variables ──────────────────────────────────────
_DARK_VARS = """
<style>
:root {
  --bg-app:          #0d1117;
  --bg-sidebar:      #0d1421;
  --bg-card:         #161b27;
  --bg-card-2:       #1c2333;
  --bg-input:        #1c2333;
  --bg-hover:        #21273a;
  --border:          #2a3347;
  --border-subtle:   #1e2d3d;
  --text-primary:    #e8edf5;
  --text-body:       #c9d1d9;
  --text-secondary:  #8b949e;
  --text-muted:      #8b949e;
  --text-label:      #b1bac4;
  --sidebar-text:    #d8dee8;
  --sidebar-muted:   #8b949e;
  --sidebar-link:    #8b949e;
  --sidebar-link-h:  #e6edf3;
  --accent:          #388bfd;
  --accent-hover:    #58a6ff;
  --accent-subtle:   rgba(56, 139, 253, 0.12);
  --good:            #3fb950;
  --bad:             #f0883e;
  --ugly:            #f85149;
  --review:          #d4a017;
  --good-bg:         rgba(63, 185, 80, 0.12);
  --bad-bg:          rgba(240, 136, 62, 0.12);
  --ugly-bg:         rgba(248, 81, 73, 0.12);
  --review-bg:       rgba(212, 160, 23, 0.14);
  --shadow-sm:       0 1px 2px rgba(0,0,0,0.5);
  --shadow:          0 2px 8px rgba(0,0,0,0.4), 0 1px 3px rgba(0,0,0,0.3);
  --radius:          8px;
  --radius-sm:       6px;
  --font-ui:         'DM Sans', system-ui, -apple-system, sans-serif;
  --font-mono:       'DM Mono', 'JetBrains Mono', 'Courier New', monospace;
}
</style>
"""

# ── Light theme CSS variables ─────────────────────────────────────
_LIGHT_VARS = """
<style>
:root {
  --bg-app:          #f4f6f8;
  --bg-sidebar:      #0d1421;
  --bg-card:         #ffffff;
  --bg-card-2:       #f8fafc;
  --bg-input:        #ffffff;
  --bg-hover:        #f1f5f9;
  --border:          #e2e8f0;
  --border-subtle:   #f1f5f9;
  --text-primary:    #032d60;
  --text-body:       #032d60;
  --text-secondary:  #4a6276;
  --text-muted:      #6b7280;
  --text-label:      #4a6276;
  --sidebar-text:    #d8dee8;
  --sidebar-muted:   #8b949e;
  --sidebar-link:    #8b949e;
  --sidebar-link-h:  #e6edf3;
  --accent:          #0176d3;
  --accent-hover:    #0284c7;
  --accent-subtle:   rgba(1, 118, 211, 0.1);
  --good:            #2e844a;
  --bad:             #dd7a06;
  --ugly:            #ba0517;
  --review:          #a06800;
  --good-bg:         rgba(46, 132, 74, 0.1);
  --bad-bg:          rgba(221, 122, 6, 0.1);
  --ugly-bg:         rgba(186, 5, 23, 0.1);
  --review-bg:       rgba(160, 104, 0, 0.1);
  --shadow-sm:       0 1px 2px rgba(0,0,0,0.08);
  --shadow:          0 2px 8px rgba(0,0,0,0.1), 0 1px 3px rgba(0,0,0,0.06);
  --radius:          8px;
  --radius-sm:       6px;
  --font-ui:         'DM Sans', system-ui, -apple-system, sans-serif;
  --font-mono:       'DM Mono', 'JetBrains Mono', 'Courier New', monospace;
}
</style>
"""

# ── Component styles (use var() — theme-agnostic) ─────────────────
_COMPONENT_CSS = """
<style>

/* ═══════════════════════════════════════════════
   TYPOGRAPHY
═══════════════════════════════════════════════ */

*, *::before, *::after {
  box-sizing: border-box;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}

html, body,
[data-testid="stAppViewContainer"],
.stApp {
  font-family: var(--font-ui) !important;
}

body, p, div, span, li {
  font-size: 14px !important;
  line-height: 1.55 !important;
  color: var(--text-body);
}

h1 {
  font-family: var(--font-ui) !important;
  font-size: 1.625rem !important;
  font-weight: 700 !important;
  line-height: 1.2 !important;
  letter-spacing: -0.02em !important;
  color: var(--text-primary) !important;
}
h2 {
  font-family: var(--font-ui) !important;
  font-size: 1.25rem !important;
  font-weight: 600 !important;
  line-height: 1.3 !important;
  letter-spacing: -0.01em !important;
  color: var(--text-primary) !important;
}
h3 {
  font-family: var(--font-ui) !important;
  font-size: 1.0625rem !important;
  font-weight: 600 !important;
  line-height: 1.35 !important;
  color: var(--text-primary) !important;
}

/* Labels / captions */
label,
.stCaption,
[data-testid="stCaptionContainer"],
[data-testid="stWidgetLabel"] {
  font-family: var(--font-ui) !important;
  font-size: 0.8125rem !important;
  font-weight: 500 !important;
  color: var(--text-label) !important;
  letter-spacing: 0.01em;
}

/* Metrics — monospace numbers */
[data-testid="stMetricValue"] {
  font-family: var(--font-mono) !important;
  font-size: 1.625rem !important;
  font-weight: 500 !important;
  color: var(--text-primary) !important;
}
[data-testid="stMetricLabel"] {
  font-family: var(--font-ui) !important;
  font-size: 0.75rem !important;
  font-weight: 500 !important;
  color: var(--text-secondary) !important;
  text-transform: uppercase !important;
  letter-spacing: 0.06em !important;
}
[data-testid="stMetricDelta"] {
  font-family: var(--font-mono) !important;
  font-size: 0.8125rem !important;
}

/* Monospace text areas / code */
textarea, code, pre,
[data-testid="stCode"] {
  font-family: var(--font-mono) !important;
  font-size: 0.8125rem !important;
}

small, .small-text, .stCaption {
  font-size: 0.75rem !important;
  color: var(--text-muted) !important;
}

/* ═══════════════════════════════════════════════
   LAYOUT
═══════════════════════════════════════════════ */

/* App background */
.stApp,
section[data-testid="stMain"],
[data-testid="stAppViewContainer"] {
  background-color: var(--bg-app) !important;
}

/* Main content padding */
.block-container {
  padding-top: 1.25rem !important;
  padding-bottom: 2rem !important;
  max-width: 1200px;
}

/* Divider */
hr {
  border: none !important;
  border-top: 1px solid var(--border) !important;
  margin: 0.5rem 0 !important;
  opacity: 1 !important;
}

/* ═══════════════════════════════════════════════
   SIDEBAR (always dark)
═══════════════════════════════════════════════ */

[data-testid="stSidebar"] > div:first-child {
  background-color: var(--bg-sidebar) !important;
  border-right: 1px solid rgba(255,255,255,0.06) !important;
}

[data-testid="stSidebarContent"] {
  background-color: var(--bg-sidebar) !important;
}

/* All text in sidebar stays light */
[data-testid="stSidebar"] p,
[data-testid="stSidebar"] span,
[data-testid="stSidebar"] div,
[data-testid="stSidebar"] label,
[data-testid="stSidebar"] [data-testid="stWidgetLabel"],
[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] {
  color: var(--sidebar-text) !important;
}

/* Sidebar links */
[data-testid="stSidebar"] a {
  color: var(--sidebar-link) !important;
  text-decoration: none !important;
  font-size: 0.875rem !important;
  transition: color 0.15s ease;
}
[data-testid="stSidebar"] a:hover {
  color: var(--sidebar-link-h) !important;
}

/* Sidebar page links */
[data-testid="stSidebar"] [data-testid="stPageLink-NavLink"] {
  border-radius: var(--radius-sm) !important;
  padding: 4px 8px !important;
  transition: background 0.15s ease;
}
[data-testid="stSidebar"] [data-testid="stPageLink-NavLink"]:hover {
  background-color: rgba(255,255,255,0.08) !important;
}

/* Sidebar selectbox */
[data-testid="stSidebar"] [data-baseweb="select"] > div {
  background-color: rgba(255,255,255,0.06) !important;
  border-color: rgba(255,255,255,0.12) !important;
  color: var(--sidebar-text) !important;
}
[data-testid="stSidebar"] [data-baseweb="select"] svg {
  color: var(--sidebar-muted) !important;
}

/* Sidebar buttons */
[data-testid="stSidebar"] [data-testid="stBaseButton-secondary"] {
  background-color: rgba(255,255,255,0.06) !important;
  border-color: rgba(255,255,255,0.12) !important;
  color: var(--sidebar-text) !important;
}
[data-testid="stSidebar"] [data-testid="stBaseButton-secondary"]:hover {
  background-color: rgba(255,255,255,0.1) !important;
  border-color: rgba(255,255,255,0.2) !important;
}

/* Hide built-in nav */
[data-testid="stSidebarNav"] { display: none !important; }

/* ═══════════════════════════════════════════════
   CARDS
═══════════════════════════════════════════════ */

[data-testid="stVerticalBlockBorderWrapper"] > div {
  background-color: var(--bg-card) !important;
  border: 1px solid var(--border) !important;
  border-radius: var(--radius) !important;
  box-shadow: var(--shadow-sm) !important;
  transition: box-shadow 0.15s ease, border-color 0.15s ease;
}
[data-testid="stVerticalBlockBorderWrapper"] > div:hover {
  border-color: var(--border) !important;
  box-shadow: var(--shadow) !important;
}

/* ═══════════════════════════════════════════════
   BUTTONS
═══════════════════════════════════════════════ */

[data-testid="stBaseButton-primary"] {
  background: var(--accent) !important;
  border: 1px solid var(--accent) !important;
  color: #ffffff !important;
  border-radius: var(--radius) !important;
  font-family: var(--font-ui) !important;
  font-size: 0.875rem !important;
  font-weight: 600 !important;
  letter-spacing: 0.01em !important;
  padding: 0.375rem 1rem !important;
  transition: background 0.15s ease, box-shadow 0.15s ease;
  box-shadow: 0 1px 3px rgba(56, 139, 253, 0.25) !important;
}
[data-testid="stBaseButton-primary"]:hover {
  background: var(--accent-hover) !important;
  border-color: var(--accent-hover) !important;
  box-shadow: 0 2px 8px rgba(56, 139, 253, 0.35) !important;
}

[data-testid="stBaseButton-secondary"] {
  background: transparent !important;
  border: 1px solid var(--border) !important;
  color: var(--text-primary) !important;
  border-radius: var(--radius) !important;
  font-family: var(--font-ui) !important;
  font-size: 0.875rem !important;
  font-weight: 500 !important;
  padding: 0.375rem 1rem !important;
  transition: background 0.15s ease, border-color 0.15s ease;
}
[data-testid="stBaseButton-secondary"]:hover {
  background: var(--bg-hover) !important;
  border-color: var(--accent) !important;
}

[data-testid="stBaseButton-tertiary"] {
  background: transparent !important;
  border: none !important;
  color: var(--accent) !important;
  border-radius: var(--radius) !important;
  font-family: var(--font-ui) !important;
  font-size: 0.875rem !important;
  font-weight: 500 !important;
  padding: 0.375rem 0.75rem !important;
}
[data-testid="stBaseButton-tertiary"]:hover {
  background: var(--accent-subtle) !important;
}

/* Download button */
[data-testid="stBaseButton-downloadButton"] {
  background: transparent !important;
  border: 1px solid var(--border) !important;
  color: var(--accent) !important;
  border-radius: var(--radius) !important;
  font-family: var(--font-ui) !important;
  font-size: 0.875rem !important;
  font-weight: 500 !important;
}
[data-testid="stBaseButton-downloadButton"]:hover {
  background: var(--accent-subtle) !important;
  border-color: var(--accent) !important;
}

/* ═══════════════════════════════════════════════
   TABS
═══════════════════════════════════════════════ */

[data-testid="stTabs"] [data-baseweb="tab-list"] {
  background: transparent !important;
  border-bottom: 1px solid var(--border) !important;
  gap: 0 !important;
  padding: 0 !important;
}

[data-testid="stTabs"] [data-baseweb="tab"] {
  background: transparent !important;
  border: none !important;
  border-bottom: 2px solid transparent !important;
  border-radius: 0 !important;
  color: var(--text-secondary) !important;
  font-family: var(--font-ui) !important;
  font-size: 0.875rem !important;
  font-weight: 500 !important;
  padding: 0.625rem 1rem !important;
  margin-bottom: -1px !important;
  transition: color 0.15s ease, border-color 0.15s ease;
}
[data-testid="stTabs"] [data-baseweb="tab"]:hover {
  color: var(--text-primary) !important;
  background: var(--bg-hover) !important;
}
[data-testid="stTabs"] [aria-selected="true"][data-baseweb="tab"] {
  color: var(--accent) !important;
  border-bottom: 2px solid var(--accent) !important;
  font-weight: 600 !important;
}

[data-testid="stTabs"] [data-baseweb="tab-panel"] {
  padding: 1rem 0 0 !important;
}

/* ═══════════════════════════════════════════════
   EXPANDERS
═══════════════════════════════════════════════ */

[data-testid="stExpander"] {
  background-color: var(--bg-card) !important;
  border: 1px solid var(--border) !important;
  border-radius: var(--radius) !important;
  box-shadow: var(--shadow-sm) !important;
}
[data-testid="stExpander"] summary {
  font-family: var(--font-ui) !important;
  font-size: 0.875rem !important;
  font-weight: 500 !important;
  color: var(--text-primary) !important;
  padding: 0.625rem 0.875rem !important;
}
[data-testid="stExpander"] summary:hover {
  background: var(--bg-hover) !important;
  border-radius: var(--radius) var(--radius) 0 0;
}
[data-testid="stExpanderDetails"] {
  padding: 0.5rem 0.875rem 0.875rem !important;
  border-top: 1px solid var(--border-subtle) !important;
}

/* ═══════════════════════════════════════════════
   INPUTS
═══════════════════════════════════════════════ */

/* Text input / number input */
[data-baseweb="input"] > div,
[data-baseweb="textarea"] > div {
  background-color: var(--bg-input) !important;
  border-color: var(--border) !important;
  border-radius: var(--radius-sm) !important;
  color: var(--text-primary) !important;
  font-family: var(--font-ui) !important;
  font-size: 0.875rem !important;
  transition: border-color 0.15s ease, box-shadow 0.15s ease;
}
[data-baseweb="input"] > div:focus-within,
[data-baseweb="textarea"] > div:focus-within {
  border-color: var(--accent) !important;
  box-shadow: 0 0 0 2px var(--accent-subtle) !important;
}

/* Select / Selectbox */
[data-baseweb="select"] > div:first-child {
  background-color: var(--bg-input) !important;
  border-color: var(--border) !important;
  border-radius: var(--radius-sm) !important;
  color: var(--text-primary) !important;
  font-family: var(--font-ui) !important;
  font-size: 0.875rem !important;
}
[data-baseweb="select"] > div:focus-within {
  border-color: var(--accent) !important;
  box-shadow: 0 0 0 2px var(--accent-subtle) !important;
}

/* Dropdown menu */
[data-baseweb="popover"] [role="listbox"] {
  background-color: var(--bg-card-2) !important;
  border: 1px solid var(--border) !important;
  border-radius: var(--radius-sm) !important;
  box-shadow: var(--shadow) !important;
}
[data-baseweb="popover"] [role="option"] {
  background-color: transparent !important;
  color: var(--text-primary) !important;
  font-family: var(--font-ui) !important;
  font-size: 0.875rem !important;
  padding: 6px 12px !important;
}
[data-baseweb="popover"] [role="option"]:hover,
[data-baseweb="popover"] [role="option"][aria-selected="true"] {
  background-color: var(--bg-hover) !important;
}

/* Textarea */
textarea {
  background-color: var(--bg-input) !important;
  border-color: var(--border) !important;
  border-radius: var(--radius-sm) !important;
  color: var(--text-primary) !important;
  font-family: var(--font-mono) !important;
  font-size: 0.8125rem !important;
  resize: vertical;
}

/* Checkbox */
[data-baseweb="checkbox"] span {
  border-color: var(--border) !important;
  border-radius: 4px !important;
  background-color: var(--bg-input) !important;
}
[data-baseweb="checkbox"][aria-checked="true"] span {
  background-color: var(--accent) !important;
  border-color: var(--accent) !important;
}

/* Radio */
[data-baseweb="radio"] span:first-child {
  border-color: var(--border) !important;
  background-color: var(--bg-input) !important;
}

/* File uploader */
[data-testid="stFileUploader"] {
  background-color: var(--bg-card) !important;
  border: 1px dashed var(--border) !important;
  border-radius: var(--radius) !important;
  transition: border-color 0.15s ease, background 0.15s ease;
}
[data-testid="stFileUploader"]:hover {
  border-color: var(--accent) !important;
  background-color: var(--accent-subtle) !important;
}
[data-testid="stFileUploader"] [data-testid="stFileUploaderDropzone"] {
  background: transparent !important;
}

/* ═══════════════════════════════════════════════
   ALERTS / STATUS BOXES
═══════════════════════════════════════════════ */

[data-testid="stAlert"] {
  border-radius: var(--radius) !important;
  border: 1px solid var(--border) !important;
  font-family: var(--font-ui) !important;
  font-size: 0.875rem !important;
}
[data-testid="stAlert"][data-baseweb="notification"] {
  background-color: var(--bg-card) !important;
}

/* Status widget */
[data-testid="stStatus"] {
  background-color: var(--bg-card) !important;
  border: 1px solid var(--border) !important;
  border-radius: var(--radius) !important;
}

/* ═══════════════════════════════════════════════
   PROGRESS BAR (native Streamlit)
═══════════════════════════════════════════════ */

[data-testid="stProgressBar"] > div {
  background-color: var(--border) !important;
  border-radius: 99px !important;
  height: 4px !important;
}
[data-testid="stProgressBar"] > div > div {
  background: linear-gradient(90deg, var(--accent), var(--accent-hover)) !important;
  border-radius: 99px !important;
  transition: width 0.3s ease !important;
}

/* ═══════════════════════════════════════════════
   DATAFRAMES / TABLES
═══════════════════════════════════════════════ */

[data-testid="stDataFrame"] iframe {
  border-radius: var(--radius) !important;
  border: 1px solid var(--border) !important;
}

/* ═══════════════════════════════════════════════
   TOAST / SPINNER
═══════════════════════════════════════════════ */

[data-testid="stToast"] {
  background-color: var(--bg-card-2) !important;
  border: 1px solid var(--border) !important;
  border-radius: var(--radius) !important;
  color: var(--text-primary) !important;
  font-family: var(--font-ui) !important;
  box-shadow: var(--shadow) !important;
}

/* ═══════════════════════════════════════════════
   FINDING CARD SEVERITY BORDERS
   (used via .sev-* HTML class injection)
═══════════════════════════════════════════════ */

.sev-ugly {
  border-left: 3px solid var(--ugly) !important;
  padding-left: 0.6rem !important;
  margin-bottom: 0.5rem;
}
.sev-bad {
  border-left: 3px solid var(--bad) !important;
  padding-left: 0.6rem !important;
  margin-bottom: 0.5rem;
}
.sev-good {
  border-left: 3px solid var(--good) !important;
  padding-left: 0.6rem !important;
  margin-bottom: 0.5rem;
}
.sev-review {
  border-left: 3px solid var(--review) !important;
  padding-left: 0.6rem !important;
  margin-bottom: 0.5rem;
}

/* ═══════════════════════════════════════════════
   BADGES / PILLS
   (.badge-good, .badge-bad, .badge-ugly, .badge-info)
═══════════════════════════════════════════════ */

.badge {
  display: inline-block;
  padding: 2px 9px;
  border-radius: 99px;
  font-family: var(--font-mono);
  font-size: 0.7rem;
  font-weight: 500;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  line-height: 1.6;
  white-space: nowrap;
}
.badge-good   { background: var(--good-bg);   color: var(--good);   }
.badge-bad    { background: var(--bad-bg);    color: var(--bad);    }
.badge-ugly   { background: var(--ugly-bg);   color: var(--ugly);   }
.badge-review { background: var(--review-bg); color: var(--review); }
.badge-info  {
  background: var(--accent-subtle);
  color: var(--accent);
}
.badge-muted {
  background: rgba(139,148,158,0.15);
  color: var(--text-secondary);
}

/* Stage badge — inline pill with bg-color passed via style */
.stage-badge {
  display: inline-block;
  padding: 2px 9px;
  border-radius: 99px;
  font-family: var(--font-ui);
  font-size: 0.75rem;
  font-weight: 600;
  color: #ffffff;
  white-space: nowrap;
}

/* ═══════════════════════════════════════════════
   STEP PROGRESS BAR
   (.step-bar > .step-connector + .step)
═══════════════════════════════════════════════ */

@keyframes pulse-ring {
  0%   { box-shadow: 0 0 0 0 rgba(56,139,253,0.45); }
  70%  { box-shadow: 0 0 0 6px rgba(56,139,253,0); }
  100% { box-shadow: 0 0 0 0 rgba(56,139,253,0); }
}

.step-bar {
  display: flex;
  align-items: flex-start;
  padding: 0.75rem 0 0.25rem;
  margin-bottom: 0.5rem;
}

.step {
  text-align: center;
  flex: 1;
  min-width: 0;
}

.step-circle {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-family: var(--font-mono);
  font-size: 0.75rem;
  font-weight: 600;
  margin-bottom: 4px;
}
.step-done .step-circle {
  background: var(--good);
  color: #ffffff;
}
.step-active .step-circle {
  background: var(--accent);
  color: #ffffff;
  animation: pulse-ring 2s ease-out infinite;
}
.step-future .step-circle {
  background: var(--border);
  color: var(--text-muted);
}

.step-label {
  display: block;
  font-family: var(--font-ui);
  font-size: 0.6875rem;
  white-space: nowrap;
  letter-spacing: 0.01em;
}
.step-done .step-label   { color: var(--good);   font-weight: 600; }
.step-active .step-label { color: var(--accent); font-weight: 700; }
.step-future .step-label { color: var(--text-muted); font-weight: 400; }

.step-connector {
  flex: 1;
  height: 2px;
  background: var(--border);
  margin-top: 13px;
  min-width: 8px;
  max-width: 40px;
}

/* ═══════════════════════════════════════════════
   BREADCRUMB
═══════════════════════════════════════════════ */

.breadcrumb {
  font-family: var(--font-ui);
  font-size: 0.875rem;
  color: var(--text-muted);
  margin-bottom: 0.25rem;
  display: flex;
  align-items: center;
  gap: 0.375rem;
  flex-wrap: wrap;
}
.breadcrumb a {
  color: var(--text-muted) !important;
  text-decoration: none !important;
  transition: color 0.15s ease;
}
.breadcrumb a:hover {
  color: var(--text-secondary) !important;
}
.breadcrumb .bc-sep  { color: var(--text-muted); }
.breadcrumb .bc-curr { color: var(--accent); font-weight: 600; }

/* ═══════════════════════════════════════════════
   MISC POLISH
═══════════════════════════════════════════════ */

/* Scrollbar (Webkit) */
::-webkit-scrollbar       { width: 6px; height: 6px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb {
  background: var(--border);
  border-radius: 3px;
}
::-webkit-scrollbar-thumb:hover { background: var(--text-muted); }

/* Selection highlight */
::selection {
  background: var(--accent-subtle);
  color: var(--text-primary);
}

/* Streamlit default bottom padding */
footer { display: none !important; }
#MainMenu { display: none !important; }

/* Page link text in sidebar */
[data-testid="stSidebar"] [data-testid="stPageLink"] p {
  font-size: 0.875rem !important;
  font-weight: 400 !important;
  color: var(--sidebar-link) !important;
}

</style>
"""


def inject_css() -> None:
    """Inject Google Fonts, theme CSS variables, and component styles. Call at top of every page."""
    theme = _load_theme()
    st.markdown(_FONTS_HTML, unsafe_allow_html=True)
    st.markdown(_DARK_VARS if theme == "dark" else _LIGHT_VARS, unsafe_allow_html=True)
    st.markdown(_COMPONENT_CSS, unsafe_allow_html=True)


# ── Finding card severity helper ────────────────────────────────────
def render_severity_bar(category: str) -> None:
    """
    Render a colored left-border accent badge inside a card container.

    Call this as the first item inside an ``st.container(border=True)``
    block to add a color-coded severity indicator:

        with st.container(border=True):
            render_severity_bar(finding["category"])
            ...rest of card...
    """
    css_class = {
        "Ugly": "badge-ugly", "Bad": "badge-bad",
        "Good": "badge-good",
        "Review": "badge-review", "Needs Review": "badge-review",
    }.get(category, "badge-muted")
    border_class = {
        "Ugly": "sev-ugly", "Bad": "sev-bad",
        "Good": "sev-good",
        "Review": "sev-review", "Needs Review": "sev-review",
    }.get(category, "")
    label = "⚠ Needs Review" if category in ("Review", "Needs Review") else category
    st.markdown(
        f"<div class='{border_class}'>"
        f"<span class='badge {css_class}'>{label}</span>"
        f"</div>",
        unsafe_allow_html=True,
    )


# ── Progress bar ───────────────────────────────────────────────────
_PROGRESS_STEPS = [
    ("setup",             "1", "Setup",            "pages/1_Client_Setup.py"),
    ("docs_uploaded",     "2", "Upload",            "pages/2_Document_Intake.py"),
    ("text_extracted",    "3", "Analyze",           "pages/_Analyze.py"),
    ("findings_imported", "4", "Findings",          "pages/3_Findings_Dashboard.py"),
    ("findings_reviewed", "5", "Strategic Advisor", "pages/4_Strategic_Advisor.py"),
    ("output_generated",  "6", "Report",            "pages/_Report_Builder.py"),
]

_STAGE_ORDER = {
    "setup":             0,
    "docs_uploaded":     1,
    "text_extracted":    2,
    "findings_imported": 3,
    "findings_reviewed": 4,
    "output_generated":  5,
}


def render_progress_bar(current_stage: str, active_step: int = None) -> None:
    if active_step is None:
        active_step = _STAGE_ORDER.get(current_stage, 0)

    step_htmls = []
    for i, (_stage, num, label, _page) in enumerate(_PROGRESS_STEPS):
        if i < active_step:
            state_cls = "step-done"
            circle_text = "&#10003;"
        elif i == active_step:
            state_cls = "step-active"
            circle_text = num
        else:
            state_cls = "step-future"
            circle_text = num

        step_htmls.append(
            f"<div class='step {state_cls}'>"
            f"<div class='step-circle'>{circle_text}</div>"
            f"<span class='step-label'>{label}</span>"
            f"</div>"
        )

    connector = "<div class='step-connector'></div>"
    interleaved = []
    for i, s in enumerate(step_htmls):
        interleaved.append(s)
        if i < len(step_htmls) - 1:
            interleaved.append(connector)

    st.markdown(
        "<div class='step-bar'>" + "".join(interleaved) + "</div>",
        unsafe_allow_html=True,
    )


# ── Breadcrumb ─────────────────────────────────────────────────────
def render_breadcrumb(client_name: str, page_title: str) -> None:
    st.markdown(
        f"<div class='breadcrumb'>"
        f"<a href='/' target='_self'>Dashboard</a>"
        f"<span class='bc-sep'>&rsaquo;</span>"
        f"<span>{client_name}</span>"
        f"<span class='bc-sep'>&rsaquo;</span>"
        f"<span class='bc-curr'>{page_title}</span>"
        f"</div>",
        unsafe_allow_html=True,
    )


# ── Sidebar ────────────────────────────────────────────────────────
def render_sidebar() -> None:
    """Render the standard sidebar: branding, theme toggle, client quick-switch, nav."""
    theme = _load_theme()

    # Branding colors depend on theme
    if theme == "dark":
        title_color  = "#ffffff"
        broker_color = "#d0d0d0"
        company_color = "#aaaaaa"
    else:
        title_color  = "#1a1a2e"
        broker_color = "#374151"
        company_color = "#6b7280"

    with st.sidebar:
        # Branding
        broker_lines = ""
        if BROKER_NAME:
            broker_lines += (
                f"<br><span style='font-size:0.875rem;color:{broker_color}'>"
                f"{BROKER_NAME}</span>"
            )
        if BROKER_COMPANY:
            broker_lines += (
                f"<br><span style='font-size:0.8rem;color:{company_color}'>"
                f"{BROKER_COMPANY}</span>"
            )
        st.markdown(
            f"<div style='padding:0.5rem 0 0.25rem'>"
            f"<span style='font-size:1.2rem;font-weight:700;color:{title_color}'>"
            f"&#128737;&nbsp;Audit System</span>"
            f"{broker_lines}"
            f"</div>",
            unsafe_allow_html=True,
        )
        st.divider()

        # Client quick-switch
        clients = list_clients(CLIENTS_DIR)
        if clients:
            client_map   = {c["slug"]: c["display_name"] for c in clients}
            slugs        = list(client_map.keys())
            current_slug = st.session_state.get("selected_client")
            if current_slug not in slugs:
                current_slug = slugs[0]
            idx = slugs.index(current_slug)

            chosen = st.selectbox(
                "Quick-switch client",
                options=slugs,
                format_func=lambda x: client_map.get(x, x),
                index=idx,
                key="sidebar_client_selector",
                help="Switch the active client without going back to the dashboard.",
            )
            if chosen != st.session_state.get("selected_client"):
                st.session_state.selected_client = chosen
                st.rerun()

            active = next((c for c in clients if c["slug"] == chosen), None)
            if active:
                stage_label = dict(STAGES).get(active["stage"], active["stage"])
                color       = STAGE_COLORS.get(active["stage"], "#9E9E9E")
                st.markdown(
                    f"<span class='stage-badge' style='background:{color}'>"
                    f"{stage_label}</span>",
                    unsafe_allow_html=True,
                )
        else:
            st.info("No clients yet.")

        st.divider()

        st.page_link("app.py",                           label="Dashboard")
        st.page_link("pages/1_Client_Setup.py",          label="1. Client Setup")
        st.page_link("pages/2_Document_Intake.py",       label="2. Document Intake")
        st.page_link("pages/_Analyze.py",                label="3. Analyze")
        st.page_link("pages/3_Findings_Dashboard.py",    label="4. Findings")
        st.page_link("pages/4_Strategic_Advisor.py",     label="5. Strategic Advisor")

        st.divider()

        # Theme toggle
        toggle_label = "Light Mode" if theme == "dark" else "Dark Mode"
        if st.button(toggle_label, key="theme_toggle_btn", use_container_width=True):
            _save_theme("light" if theme == "dark" else "dark")
            st.rerun()

        st.page_link("pages/0_Settings.py", label="Settings")


# ── Client guard ───────────────────────────────────────────────────
def require_client() -> tuple:
    slug = st.session_state.get("selected_client")
    if not slug:
        clients = list_clients(CLIENTS_DIR)
        if clients:
            slug = clients[0]["slug"]
            st.session_state.selected_client = slug
        else:
            st.markdown("<br>", unsafe_allow_html=True)
            c1, c2, c3 = st.columns([1, 2, 1])
            with c2:
                st.info(
                    "**No client selected.**\n\n"
                    "Go back to the dashboard and click a client card, or "
                    "use the sidebar dropdown to pick a client.",
                )
                if st.button("&#8592; Back to Dashboard", use_container_width=True):
                    st.switch_page("app.py")
            st.stop()

    client_path = CLIENTS_DIR / slug
    if not client_path.exists():
        st.error(
            f"Client folder `{slug}` not found. It may have been moved or deleted."
        )
        if st.button("&#8592; Back to Dashboard"):
            st.session_state.selected_client = None
            st.switch_page("app.py")
        st.stop()

    state = load_state(client_path)
    return slug, client_path, state


# ── Badge helpers ──────────────────────────────────────────────────
def category_badge(category: str) -> str:
    css_class = {
        "Good": "badge-good", "Bad": "badge-bad",
        "Ugly": "badge-ugly",
        "Review": "badge-review", "Needs Review": "badge-review",
    }.get(category, "badge-muted")
    label = "⚠ Needs Review" if category in ("Review", "Needs Review") else category
    return f"<span class='badge {css_class}'>{label}</span>"


def stage_badge(stage: str) -> str:
    label = dict(STAGES).get(stage, stage)
    color = STAGE_COLORS.get(stage, "#9E9E9E")
    return f"<span class='stage-badge' style='background:{color}'>{label}</span>"


# ── Backward-compat alias ──────────────────────────────────────────
GLOBAL_CSS = _COMPONENT_CSS  # kept for any direct references; inject_css() supersedes it
