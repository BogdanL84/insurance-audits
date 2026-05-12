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
    """Read theme from settings.json on every call — not cached.
    Day-1 restyle (2026-05-11): default flipped to 'light'."""
    try:
        return json.loads(_SETTINGS_PATH.read_text(encoding="utf-8")).get("theme", "light")
    except Exception:
        return "light"


def _html_escape(s: str) -> str:
    """HTML-escape a string for safe inline rendering."""
    import html as _html
    return _html.escape(s) if s else ""


def _sidebar_status_pill(stage: str) -> tuple[str, str]:
    """Map audit stage → (CSS class suffix, display label) for the
    sidebar active-client status pill. Day-1 restyle (2026-05-11)."""
    if stage in ("findings_imported", "output_generated"):
        return "imported", "Findings Imported"
    if stage == "findings_reviewed":
        return "reviewed", "Reviewed"
    label = dict(STAGES).get(stage, stage)
    return "setup", label


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
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
"""

# ── Dark theme CSS variables (secondary toggle) ──────────────────
# Day-1 restyle (2026-05-11): true dark companion to the light theme.
# NOT the audit-report's warm-ink palette — the audit report is a
# separate visual product. Same vibrant blue/teal/gradient accents,
# inverted surfaces only.
_DARK_VARS = """
<style>
:root {
  /* Surfaces */
  --bg:                #0a0f1a;
  --bg-card:           #14191f;
  --bg-subtle:         #1a1f2c;
  --bg-input:          #14191f;
  --border:            #2a323d;
  --border-soft:       #1f2530;
  --border-strong:     #3a4451;
  /* Text */
  --text:              #f1f5f9;
  --text-soft:         #cbd5e1;
  --muted:             #94a3b8;
  --muted-light:       #64748b;
  /* Brand + accents — same as light, work on dark too */
  --primary:           #0176d3;
  --primary-light:     #1a8cf2;
  --primary-dark:      #014486;
  --teal:              #06b6d4;
  --teal-light:        #67e8f9;
  --indigo:            #6366f1;
  --purple:            #9333ea;
  --pink:              #ec4899;
  --orange:            #f97316;
  --amber:             #f59e0b;
  --green:             #10b981;
  --green-light:       #34d399;
  --red:               #ef4444;
  --red-soft:          #fb7185;
  /* Gradients — identical to light theme; gradients work on either bg */
  --grad-primary:      linear-gradient(135deg, #0176d3 0%, #06b6d4 100%);
  --grad-warm:         linear-gradient(135deg, #f97316 0%, #ec4899 100%);
  --grad-success:      linear-gradient(135deg, #10b981 0%, #06b6d4 100%);
  --grad-danger:       linear-gradient(135deg, #ef4444 0%, #f97316 100%);
  --grad-purple:       linear-gradient(135deg, #6366f1 0%, #9333ea 100%);
  --grad-amber:        linear-gradient(135deg, #f59e0b 0%, #f97316 100%);
  /* Chrome */
  --shadow-sm:       0 1px 2px rgba(0,0,0,0.5);
  --shadow:          0 2px 8px rgba(0,0,0,0.4), 0 1px 3px rgba(0,0,0,0.3);
  --radius:          8px;
  --radius-sm:       6px;
  --font-ui:         'Inter', system-ui, -apple-system, sans-serif;
  --font-mono:       'JetBrains Mono', 'DM Mono', 'Courier New', monospace;

  /* LEGACY ALIASES — old token names kept so the existing 900-
     line component CSS doesn't all break at once. Remove after
     a CSS audit, deferred. */
  --text-primary:      var(--text);
  --text-body:         var(--text);
  --text-secondary:    var(--muted);
  --text-muted:        var(--muted);
  --text-label:        var(--text-soft);
  --bg-app:            var(--bg);
  --bg-sidebar:        var(--bg-card);
  --bg-card-2:         var(--bg-subtle);
  --bg-hover:          var(--bg-subtle);
  --border-subtle:     var(--border-soft);
  --sidebar-text:      var(--text);
  --sidebar-muted:     var(--muted);
  --sidebar-link:      var(--muted);
  --sidebar-link-h:    var(--text);
  --accent:            var(--primary);
  --accent-hover:      var(--primary-light);
  --accent-subtle:     rgba(1, 118, 211, 0.1);
  --good:              var(--green);
  --bad:               var(--orange);
  --ugly:              var(--red);
  --review:            var(--amber);
  --good-bg:           rgba(16, 185, 129, 0.12);
  --bad-bg:            rgba(249, 115, 22, 0.12);
  --ugly-bg:           rgba(239, 68, 68, 0.12);
  --review-bg:         rgba(245, 158, 11, 0.14);
}
</style>
"""

# ── Light theme CSS variables (DEFAULT) ─────────────────────────────
# Day-1 restyle (2026-05-11): Salesforce-vibrant light-mode-first
# palette. Blue → teal gradient accent. Heavy gradient use on stat
# tiles, primary button, sidebar brand mark, hero strips. White cards
# on slightly-blue-tinted off-white background.
_LIGHT_VARS = """
<style>
:root {
  /* Surfaces */
  --bg:                #f7f8fc;
  --bg-card:           #ffffff;
  --bg-subtle:         #f1f4fa;
  --bg-input:          #fafbfd;
  --border:            #e4e8f0;
  --border-soft:       #eef1f6;
  --border-strong:     #d4dae5;
  /* Text */
  --text:              #1a2233;
  --text-soft:         #4a5568;
  --muted:             #8896ab;
  --muted-light:       #b4bdcc;
  /* Brand + accents */
  --primary:           #0176d3;
  --primary-light:     #1a8cf2;
  --primary-dark:      #014486;
  --teal:              #06b6d4;
  --teal-light:        #67e8f9;
  --indigo:            #6366f1;
  --purple:            #9333ea;
  --pink:              #ec4899;
  --orange:            #f97316;
  --amber:             #f59e0b;
  --green:             #10b981;
  --green-light:       #34d399;
  --red:               #ef4444;
  --red-soft:          #fb7185;
  /* Gradients */
  --grad-primary:      linear-gradient(135deg, #0176d3 0%, #06b6d4 100%);
  --grad-warm:         linear-gradient(135deg, #f97316 0%, #ec4899 100%);
  --grad-success:      linear-gradient(135deg, #10b981 0%, #06b6d4 100%);
  --grad-danger:       linear-gradient(135deg, #ef4444 0%, #f97316 100%);
  --grad-purple:       linear-gradient(135deg, #6366f1 0%, #9333ea 100%);
  --grad-amber:        linear-gradient(135deg, #f59e0b 0%, #f97316 100%);
  /* Chrome */
  --shadow-sm:       0 1px 2px rgba(0,0,0,0.06);
  --shadow:          0 2px 8px rgba(0,0,0,0.08), 0 1px 3px rgba(0,0,0,0.04);
  --radius:          8px;
  --radius-sm:       6px;
  --font-ui:         'Inter', system-ui, -apple-system, sans-serif;
  --font-mono:       'JetBrains Mono', 'DM Mono', 'Courier New', monospace;

  /* LEGACY ALIASES — old token names kept so the existing 900-
     line component CSS doesn't all break at once. Remove after
     a CSS audit, deferred. */
  --text-primary:      var(--text);
  --text-body:         var(--text);
  --text-secondary:    var(--muted);
  --text-muted:        var(--muted);
  --text-label:        var(--text-soft);
  --bg-app:            var(--bg);
  --bg-sidebar:        var(--bg-card);
  --bg-card-2:         var(--bg-subtle);
  --bg-hover:          var(--bg-subtle);
  --border-subtle:     var(--border-soft);
  --sidebar-text:      var(--text);
  --sidebar-muted:     var(--muted);
  --sidebar-link:      var(--muted);
  --sidebar-link-h:    var(--text);
  --accent:            var(--primary);
  --accent-hover:      var(--primary-light);
  --accent-subtle:     rgba(1, 118, 211, 0.1);
  --good:              var(--green);
  --bad:               var(--orange);
  --ugly:              var(--red);
  --review:            var(--amber);
  --good-bg:           rgba(16, 185, 129, 0.12);
  --bad-bg:            rgba(249, 115, 22, 0.12);
  --ugly-bg:           rgba(239, 68, 68, 0.12);
  --review-bg:         rgba(245, 158, 11, 0.14);
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
   SIDEBAR (Day-1 restyle: light-mode first)
═══════════════════════════════════════════════ */

[data-testid="stSidebar"] > div:first-child,
[data-testid="stSidebarContent"] {
  background-color: var(--bg-sidebar) !important;
  border-right: 1px solid var(--border) !important;
}

/* Sidebar text uses normal app text color in light mode */
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

/* Sidebar page-link rows: tighter, with hover wash */
[data-testid="stSidebar"] [data-testid="stPageLink-NavLink"] {
  border-radius: var(--radius-sm) !important;
  padding: 6px 10px !important;
  transition: background 0.15s ease, color 0.15s ease;
}
[data-testid="stSidebar"] [data-testid="stPageLink-NavLink"]:hover {
  background-color: rgba(1,118,211,0.06) !important;
  color: var(--primary) !important;
}

/* Sidebar selectbox: card-surface with subtle border (sits inside .sb-client-card) */
[data-testid="stSidebar"] [data-baseweb="select"] > div {
  background-color: var(--bg-card) !important;
  border-color: var(--border) !important;
  color: var(--text) !important;
}
/* Force the value text inside the select to use --text (baseweb sets
   nested colors that can override the ancestor rule) */
[data-testid="stSidebar"] [data-baseweb="select"] > div > div,
[data-testid="stSidebar"] [data-baseweb="select"] [data-baseweb="select-search"] input,
[data-testid="stSidebar"] [data-baseweb="select"] input {
  color: var(--text) !important;
}
[data-testid="stSidebar"] [data-baseweb="select"] svg {
  color: var(--muted) !important;
}

/* Sidebar secondary buttons (theme toggle) — transparent so the
   sidebar surface shows through; border defines the button. */
[data-testid="stSidebar"] [data-testid="stBaseButton-secondary"] {
  background-color: transparent !important;
  border: 1px solid var(--border) !important;
  color: var(--text) !important;
}
[data-testid="stSidebar"] [data-testid="stBaseButton-secondary"]:hover {
  background-color: rgba(1,118,211,0.06) !important;
  border-color: var(--primary) !important;
  color: var(--primary) !important;
}

/* Hide built-in nav */
[data-testid="stSidebarNav"] { display: none !important; }

/* ── Brand row (gradient mark + name) ─────────────── */
.sb-brand-row {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 14px 4px 18px;
}
.sb-brand-mark {
  width: 40px;
  height: 40px;
  border-radius: 10px;
  background: var(--grad-primary);
  color: #ffffff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 800;
  font-size: 0.95rem;
  letter-spacing: 0.02em;
  box-shadow: 0 4px 12px rgba(1,118,211,0.28);
  flex-shrink: 0;
}
.sb-brand-text { line-height: 1.15; }
.sb-brand-name {
  font-size: 0.95rem !important;
  font-weight: 700 !important;
  color: var(--text-primary) !important;
}
.sb-brand-sub {
  font-size: 0.72rem !important;
  color: var(--text-muted) !important;
  margin-top: 2px;
}

/* ── Active-client card ─────────────────────────── */
.sb-client-card {
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: 10px;
  padding: 10px 12px 12px;
  margin: 0 0 14px;
  box-shadow: var(--shadow-sm);
}
.sb-client-label {
  font-size: 0.65rem !important;
  font-weight: 700 !important;
  letter-spacing: 0.1em;
  color: var(--muted) !important;
  margin: 0 0 6px;
}
/* Pull the selectbox tighter inside the card */
.sb-client-card + div [data-baseweb="select"],
.sb-client-card [data-baseweb="select"] {
  margin-top: 0 !important;
}

.sb-client-status {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  margin-top: 8px;
  font-size: 0.72rem !important;
  font-weight: 600 !important;
  padding: 3px 9px;
  border-radius: 999px;
  background: rgba(148,163,184,0.14);
  color: var(--text-secondary) !important;
}
.sb-client-status::before {
  content: "";
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--text-muted);
}
.sb-client-status.setup    { background: rgba(148,163,184,0.16); color: var(--muted) !important; }
.sb-client-status.setup::before    { background: var(--muted); }
.sb-client-status.imported { background: rgba(249,115,22,0.14);  color: var(--orange) !important; }
.sb-client-status.imported::before { background: var(--orange); }
.sb-client-status.reviewed { background: rgba(16,185,129,0.14);  color: var(--green) !important; }
.sb-client-status.reviewed::before { background: var(--green); }

/* ── Nav section headers via :has() href-targeting ─ */
[data-testid="stSidebar"] [data-testid="stPageLink"]:has(a[href*="Client_Setup"])::before {
  content: "WORKFLOW";
  display: block;
  font-size: 0.65rem;
  font-weight: 700;
  letter-spacing: 0.12em;
  color: var(--text-muted);
  padding: 14px 10px 6px;
}
[data-testid="stSidebar"] [data-testid="stPageLink"]:has(a[href*="Settings"])::before {
  content: "CONFIGURATION";
  display: block;
  font-size: 0.65rem;
  font-weight: 700;
  letter-spacing: 0.12em;
  color: var(--text-muted);
  padding: 14px 10px 6px;
}

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
   DASHBOARD (Day-1 restyle, 2026-05-11)
═══════════════════════════════════════════════ */

/* Page hero: title + subtitle */
.page-hero {
  display: flex;
  flex-direction: column;
  gap: 4px;
  margin: 4px 0 18px;
}
.page-hero-title {
  font-size: 1.75rem !important;
  font-weight: 700 !important;
  letter-spacing: -0.02em;
  color: var(--text-primary) !important;
  margin: 0;
  line-height: 1.15;
}
.page-hero-sub {
  font-size: 0.9rem !important;
  color: var(--text-secondary) !important;
  margin: 0;
}

/* Gradient stat tiles */
.stat-tile {
  position: relative;
  padding: 18px 18px 16px;
  border-radius: 14px;
  color: #ffffff;            /* always white on gradient */
  overflow: hidden;
  min-height: 108px;
  box-shadow: var(--shadow);
}
.stat-tile.primary { background: var(--grad-primary); }
.stat-tile.warm    { background: var(--grad-warm); }
.stat-tile.danger  { background: var(--grad-danger); }
.stat-tile.success { background: var(--grad-success); }
.stat-tile.purple  { background: var(--grad-purple); }
.stat-tile.amber   { background: var(--grad-amber); }

.stat-tile .stat-label {
  font-size: 0.72rem !important;
  font-weight: 600 !important;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  color: rgba(255,255,255,0.85) !important;
  margin: 0 0 6px;
}
.stat-tile .stat-value {
  font-family: var(--font-mono) !important;
  font-size: 2.1rem !important;
  font-weight: 700 !important;
  line-height: 1 !important;
  color: #ffffff !important;
  margin: 0;
  letter-spacing: -0.02em;
}
.stat-tile .stat-trend {
  font-size: 0.72rem !important;
  font-weight: 500 !important;
  color: rgba(255,255,255,0.88) !important;
  margin: 8px 0 0;
}
.stat-tile .stat-glyph {
  position: absolute;
  right: 14px;
  top: 14px;
  width: 28px;
  height: 28px;
  border-radius: 8px;
  background: rgba(255,255,255,0.18);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 0.95rem;
  font-weight: 700;
  color: #ffffff;
}

/* Donut + Bars panels */
.panel-card {
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 16px 18px 18px;
  box-shadow: var(--shadow-sm);
}
.panel-title {
  font-size: 0.78rem !important;
  font-weight: 700 !important;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--text-secondary) !important;
  margin: 0 0 12px;
}
.donut-wrap {
  display: flex;
  align-items: center;
  gap: 18px;
}
.donut-wrap svg { flex-shrink: 0; }
.donut-legend {
  display: flex;
  flex-direction: column;
  gap: 6px;
  font-size: 0.82rem;
}
.donut-legend .row {
  display: flex;
  align-items: center;
  gap: 8px;
  color: var(--text-secondary);
}
.donut-legend .swatch {
  width: 10px;
  height: 10px;
  border-radius: 3px;
  flex-shrink: 0;
}
.donut-legend .count {
  margin-left: auto;
  font-family: var(--font-mono);
  font-weight: 600;
  color: var(--text-primary);
}

/* Stacked-bar (per-client) rows */
.client-bars { display: flex; flex-direction: column; gap: 12px; }
.client-bar-row {
  display: grid;
  grid-template-columns: 140px 1fr 56px;
  align-items: center;
  gap: 12px;
}
.client-bar-name {
  font-size: 0.82rem;
  font-weight: 600;
  color: var(--text-primary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.client-bar-track {
  display: flex;
  height: 10px;
  border-radius: 999px;
  overflow: hidden;
  background: var(--bg-subtle);
}
.client-bar-seg { height: 100%; }
.client-bar-seg.good  { background: var(--green); }
.client-bar-seg.bad   { background: var(--orange); }
.client-bar-seg.ugly  { background: var(--red); }
.client-bar-count {
  font-family: var(--font-mono);
  font-size: 0.78rem;
  font-weight: 600;
  color: var(--text-secondary);
  text-align: right;
}

/* Client cards (dashboard grid) */
.client-card {
  position: relative;
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 18px 18px 14px;
  overflow: hidden;
  transition: box-shadow 0.15s ease, transform 0.15s ease, border-color 0.15s ease;
  box-shadow: var(--shadow-sm);
  margin-bottom: 6px;
}
.client-card:hover {
  box-shadow: var(--shadow);
  transform: translateY(-2px);
  border-color: var(--border-strong);
}
.client-card .cc-strip {
  position: absolute;
  top: 0; left: 0; right: 0;
  height: 4px;
}
.client-card .cc-strip.primary { background: var(--grad-primary); }
.client-card .cc-strip.warm    { background: var(--grad-warm); }
.client-card .cc-strip.success { background: var(--grad-success); }
.client-card .cc-strip.danger  { background: var(--grad-danger); }
.client-card .cc-strip.purple  { background: var(--grad-purple); }
.client-card .cc-strip.neutral { background: linear-gradient(135deg, var(--muted) 0%, var(--muted-light) 100%); }

.client-card .cc-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 4px;
}
.client-card .cc-stage {
  font-size: 0.65rem;
  font-weight: 700;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  padding: 3px 9px;
  border-radius: 999px;
  background: rgba(148,163,184,0.16);
  color: var(--text-secondary);
}
.client-card .cc-stage.primary { background: rgba(1,118,211,0.12); color: var(--primary); }
.client-card .cc-stage.warm    { background: rgba(249,115,22,0.14); color: var(--orange); }
.client-card .cc-stage.success { background: rgba(16,185,129,0.14); color: var(--green); }
.client-card .cc-stage.danger  { background: rgba(239,68,68,0.14);  color: var(--red); }
.client-card .cc-date {
  font-size: 0.72rem;
  color: var(--text-muted);
}
.client-card .cc-name {
  font-size: 1.05rem !important;
  font-weight: 700 !important;
  color: var(--text-primary) !important;
  margin: 8px 0 2px;
  line-height: 1.2;
}
.client-card .cc-industry {
  font-size: 0.78rem;
  color: var(--text-secondary);
  margin: 0 0 10px;
}
.client-card .cc-docs {
  font-size: 0.78rem;
  color: var(--text-muted);
  margin: 0 0 8px;
}
.client-card .cc-policy-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 5px;
  margin-bottom: 10px;
}
.client-card .cc-policy-tag {
  font-size: 0.68rem;
  font-weight: 600;
  background: var(--bg-subtle);
  color: var(--text-secondary);
  padding: 2px 8px;
  border-radius: 999px;
  white-space: nowrap;
}

/* Findings strip inside client card */
.findings-strip {
  display: flex;
  gap: 8px;
  margin: 10px 0 4px;
}
.findings-strip .fchip {
  flex: 1;
  background: var(--bg-subtle);
  border-radius: 8px;
  padding: 8px 10px;
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.findings-strip .fchip .v {
  font-family: var(--font-mono);
  font-size: 1.1rem;
  font-weight: 700;
  line-height: 1;
}
.findings-strip .fchip .l {
  font-size: 0.65rem;
  font-weight: 600;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--text-muted);
}
.findings-strip .fchip.good .v { color: var(--green); }
.findings-strip .fchip.bad  .v { color: var(--orange); }
.findings-strip .fchip.ugly .v { color: var(--red); }
.findings-strip .fchip.empty {
  background: transparent;
  border: 1px dashed var(--border);
  align-items: center;
  justify-content: center;
}
.findings-strip .fchip.empty .l {
  color: var(--text-muted);
  font-weight: 500;
  letter-spacing: 0.04em;
  text-transform: none;
}

/* ═══════════════════════════════════════════════
   BUTTONS
═══════════════════════════════════════════════ */

[data-testid="stBaseButton-primary"] {
  background: var(--grad-primary) !important;
  border: none !important;
  color: #ffffff !important;
  border-radius: var(--radius) !important;
  font-family: var(--font-ui) !important;
  font-size: 0.875rem !important;
  font-weight: 600 !important;
  letter-spacing: 0.01em !important;
  padding: 0.5rem 1.1rem !important;
  transition: filter 0.15s ease, box-shadow 0.15s ease, transform 0.15s ease;
  box-shadow: 0 4px 14px rgba(1, 118, 211, 0.28) !important;
}
[data-testid="stBaseButton-primary"]:hover {
  filter: brightness(1.05);
  box-shadow: 0 6px 18px rgba(1, 118, 211, 0.36) !important;
  transform: translateY(-1px);
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
    """Render the standard sidebar. Day-1 restyle (2026-05-11):
    gradient brand mark + styled active-client card + status pill.
    Light-mode-first; dark toggle still available via theme button."""
    theme = _load_theme()

    with st.sidebar:
        # ── Brand row: gradient mark + name + sub ──────────────────
        brand_sub = _html_escape(BROKER_NAME) if BROKER_NAME else "Audit System"
        st.markdown(
            f"""<div class="sb-brand-row">
              <div class="sb-brand-mark">IA</div>
              <div class="sb-brand-text">
                <div class="sb-brand-name">Insurance Audit</div>
                <div class="sb-brand-sub">{brand_sub}</div>
              </div>
            </div>""",
            unsafe_allow_html=True,
        )

        # ── Active-client card: label + selectbox + status pill ─────
        clients = list_clients(CLIENTS_DIR)
        if clients:
            client_map   = {c["slug"]: c["display_name"] for c in clients}
            slugs        = list(client_map.keys())
            current_slug = st.session_state.get("selected_client")
            if current_slug not in slugs:
                current_slug = slugs[0]
            idx = slugs.index(current_slug)

            # Open the card visual chrome (closes after the status pill)
            st.markdown(
                "<div class='sb-client-card'>"
                "<div class='sb-client-label'>ACTIVE CLIENT</div>",
                unsafe_allow_html=True,
            )

            chosen = st.selectbox(
                "Quick-switch client",
                options=slugs,
                format_func=lambda x: client_map.get(x, x),
                index=idx,
                key="sidebar_client_selector",
                label_visibility="collapsed",
            )
            if chosen != st.session_state.get("selected_client"):
                st.session_state.selected_client = chosen
                st.rerun()

            active = next((c for c in clients if c["slug"] == chosen), None)
            if active:
                status_cls, status_label = _sidebar_status_pill(active["stage"])
                st.markdown(
                    f"<div class='sb-client-status {status_cls}'>{status_label}</div></div>",
                    unsafe_allow_html=True,
                )
            else:
                st.markdown("</div>", unsafe_allow_html=True)
        else:
            st.info("No clients yet.")

        # ── Nav (Streamlit page links; section headers via CSS) ─────
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
