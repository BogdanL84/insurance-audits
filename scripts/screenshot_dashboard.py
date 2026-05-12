"""Headless Chromium screenshots of the Streamlit dashboard in both themes.

Day-1 restyle review aid — toggles settings.json between light and
dark, captures a 1500x1100 viewport screenshot of each, restores
the original theme. Saves to validation-2026-04-27/.
"""
import json
import sys
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

REPO    = Path(__file__).resolve().parents[1]
URL     = "http://localhost:8599/"
OUT_DIR = REPO / "validation-2026-04-27"
SETTINGS = REPO / "settings.json"

OUT_DIR.mkdir(parents=True, exist_ok=True)


def set_theme(theme: str) -> None:
    data = {}
    if SETTINGS.exists():
        try:
            data = json.loads(SETTINGS.read_text(encoding="utf-8"))
        except Exception:
            data = {}
    data["theme"] = theme
    SETTINGS.write_text(json.dumps(data, indent=2), encoding="utf-8")


def capture(page, out_path: Path) -> None:
    page.goto(URL, wait_until="load", timeout=30000)
    page.wait_for_selector(".page-hero-title", timeout=30000)
    page.wait_for_selector(".sb-brand-mark", timeout=10000)
    try:
        page.wait_for_selector(".stat-tile", timeout=5000)
    except Exception:
        pass
    time.sleep(1.4)
    page.screenshot(path=str(out_path), full_page=False)
    print(f"Saved: {out_path}")


# Remember original theme so we don't surprise Bogdan after the run
orig = "light"
if SETTINGS.exists():
    try:
        orig = json.loads(SETTINGS.read_text(encoding="utf-8")).get("theme", "light")
    except Exception:
        pass

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    ctx = browser.new_context(
        viewport={"width": 1500, "height": 1100},
        device_scale_factor=1.5,
    )
    page = ctx.new_page()

    set_theme("light")
    capture(page, OUT_DIR / "day1-dashboard-light.png")

    set_theme("dark")
    capture(page, OUT_DIR / "day1-dashboard-dark.png")

    browser.close()

# Restore
set_theme(orig)
print(f"Restored theme to: {orig}")
