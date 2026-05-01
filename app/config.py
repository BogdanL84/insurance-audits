import json as _json
from pathlib import Path

# ── Paths ──────────────────────────────────────────────────────────
APP_DIR        = Path(__file__).parent
BASE_DIR       = APP_DIR.parent          # insurance-audits/
CLIENTS_DIR    = BASE_DIR / "clients"
KNOWLEDGE_BASE = BASE_DIR / "knowledge-base"
ASSETS_DIR     = APP_DIR / "assets"

# Ensure clients directory exists
CLIENTS_DIR.mkdir(exist_ok=True)

# ── Broker Info — loaded from settings.json, falls back to defaults ─
_SETTINGS_FILE = BASE_DIR / "settings.json"
_SETTINGS: dict = {}
if _SETTINGS_FILE.exists():
    try:
        _SETTINGS = _json.loads(_SETTINGS_FILE.read_text(encoding="utf-8"))
    except Exception:
        pass

BROKER_NAME    = _SETTINGS.get("broker_name",    "")
BROKER_TITLE   = _SETTINGS.get("broker_title",   "")
BROKER_COMPANY = _SETTINGS.get("broker_company", "")
BROKER_EMAIL   = _SETTINGS.get("broker_email",   "")
BROKER_PHONE   = _SETTINGS.get("broker_phone",   "")
BROKER_LOGO    = _SETTINGS.get("logo_filename",  None)

# ── Colors ─────────────────────────────────────────────────────────
COLOR_GOOD  = "#2E7D32"
COLOR_BAD   = "#E65100"
COLOR_UGLY  = "#B71C1C"
COLOR_NAVY  = "#1A237E"
COLOR_AMBER = "#FF8F00"
COLOR_GRAY  = "#757575"

# ── Risk Score Thresholds (likelihood × severity) ──────────────────
SCORE_LOW    = 6    # < 6  : monitor
SCORE_MEDIUM = 14   # 6-14 : address soon
SCORE_HIGH   = 15   # ≥ 15 : critical

# ── PDF Processing ─────────────────────────────────────────────────
MAX_PDF_MB       = 50
CHUNK_SIZE_PAGES = 20

# ── Workflow Stages ────────────────────────────────────────────────
STAGES = [
    ("setup",             "Setup"),
    ("docs_uploaded",     "Docs Uploaded"),
    ("text_extracted",    "Text Extracted"),
    ("findings_imported", "Findings Imported"),
    ("findings_reviewed", "Findings Reviewed"),
    ("output_generated",  "Output Generated"),
]

STAGE_COLORS = {
    "setup":             "#9E9E9E",
    "docs_uploaded":     "#1565C0",
    "text_extracted":    "#1565C0",
    "findings_imported": "#E65100",
    "findings_reviewed": "#2E7D32",
    "output_generated":  "#2E7D32",
}

# ── Form Options ───────────────────────────────────────────────────
INDUSTRIES = [
    "Construction",
    "Manufacturing",
    "Technology / SaaS",
    "Professional Services",
    "Healthcare",
    "Transportation / Logistics",
    "Food & Beverage",
    "Real Estate",
    "Retail",
    "Hospitality",
    "Financial Services",
    "Non-profit",
    "Government / Public Sector",
    "Security Services",
    "Staffing / PEO",
    "Other",
]

REVENUE_RANGES = [
    "Under $1M",
    "$1M – $5M",
    "$5M – $25M",
    "$25M – $100M",
    "$100M – $500M",
    "Over $500M",
]

EMPLOYEE_RANGES = [
    "Under 10",
    "10 – 50",
    "50 – 200",
    "200 – 500",
    "500 – 2,000",
    "Over 2,000",
]

US_STATES = [
    "AL","AK","AZ","AR","CA","CO","CT","DE","FL","GA",
    "HI","ID","IL","IN","IA","KS","KY","LA","ME","MD",
    "MA","MI","MN","MS","MO","MT","NE","NV","NH","NJ",
    "NM","NY","NC","ND","OH","OK","OR","PA","RI","SC",
    "SD","TN","TX","UT","VT","VA","WA","WV","WI","WY",
]

SPECIAL_RISK_FLAGS = [
    "PE-backed / Private Equity",
    "Construction / Contracting",
    "Staffing / PEO",
    "Maritime / USL&H",
    "Government contracts",
    "Healthcare / Medical",
    "Transportation / Trucking (MCS-90)",
    "Technology / SaaS",
    "Food & Beverage / Processing",
    "Real Estate / Property Management",
    "Multi-state operations",
    "International operations",
    "Hazardous materials",
    "High-value equipment",
]

COVERAGE_TYPES = [
    "General Liability (GL)",
    "Workers' Compensation (WC)",
    "Commercial Auto (CA)",
    "Professional Liability / E&O",
    "Directors & Officers (D&O)",
    "Cyber Liability",
    "Employment Practices Liability (EPLI)",
    "Umbrella / Excess",
    "Crime / Fidelity",
    "Property",
    "Inland Marine",
    "Pollution",
    "Management Liability (Package)",
]
