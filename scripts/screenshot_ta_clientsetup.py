"""Treatment A Client Setup capture — pre-selects three risk
flags (one from each category) then screenshots in both themes
so all four tile states are visible in a single shot."""
import json
import sys
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

REPO    = Path(__file__).resolve().parents[1]
SETTINGS = REPO / "settings.json"
OUT_DIR = REPO / "validation-2026-04-27"
OUT_DIR.mkdir(parents=True, exist_ok=True)

# One risk per category so the three gradient color treatments show
PRESELECT = [
    "PE-backed / Private Equity",   # Industry → orange/pink
    "Government contracts",          # Compliance → indigo/purple
    "Multi-state operations",        # Operations → blue/teal
]


def set_theme(theme: str) -> None:
    data = {}
    if SETTINGS.exists():
        try:
            data = json.loads(SETTINGS.read_text(encoding="utf-8"))
        except Exception:
            data = {}
    data["theme"] = theme
    SETTINGS.write_text(json.dumps(data, indent=2), encoding="utf-8")


orig_theme = "light"
if SETTINGS.exists():
    try:
        orig_theme = json.loads(SETTINGS.read_text(encoding="utf-8")).get("theme", "light")
    except Exception:
        pass


with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    ctx = browser.new_context(
        viewport={"width": 1500, "height": 2200},
        device_scale_factor=1.5,
    )
    page = ctx.new_page()

    for theme in ("light", "dark"):
        set_theme(theme)
        page.goto("http://localhost:8599/Client_Setup",
                  wait_until="load", timeout=30000)
        page.wait_for_selector(".sb-brand-mark", timeout=15000)
        page.wait_for_selector(".ta-hero-title", timeout=10000)
        time.sleep(1.6)

        for label in PRESELECT:
            page.get_by_role("button", name=label, exact=True).click()
            time.sleep(1.7)  # wait for Streamlit rerun

        # Final settle to ensure all primary-state classes are applied
        time.sleep(1.6)

        out_path = OUT_DIR / f"day2v2-ta-client-setup-{theme}.png"
        page.screenshot(path=str(out_path), full_page=False)
        print(f"Saved: {out_path}")

    browser.close()

set_theme(orig_theme)
print(f"Restored theme: {orig_theme}")
