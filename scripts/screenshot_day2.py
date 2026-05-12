"""Day-2 page screenshots (light + dark) for Client Setup
and Document Intake.

Run after launching Streamlit on port 8599. Toggles settings.json
between light/dark, restores original on exit. Saves PNGs to
validation-2026-04-27/.
"""
import json
import sys
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

REPO    = Path(__file__).resolve().parents[1]
BASE    = "http://localhost:8599"
OUT_DIR = REPO / "validation-2026-04-27"
SETTINGS = REPO / "settings.json"

OUT_DIR.mkdir(parents=True, exist_ok=True)

# Pages to capture: (route_path, slug-for-filename, sentinel-selector)
PAGES = [
    ("/Client_Setup",  "client-setup",  ".stepper .step.active"),
    ("/Document_Intake","intake",       ".stepper .step.active"),
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


def capture(page, url: str, sentinel: str, out_path: Path) -> None:
    page.goto(url, wait_until="load", timeout=30000)
    page.wait_for_selector(".sb-brand-mark", timeout=15000)
    try:
        page.wait_for_selector(sentinel, timeout=15000)
    except Exception:
        pass
    # Wait for the LAST element on the page (action bar / submit button)
    # so a full-page screenshot includes the bottom of the page.
    try:
        page.wait_for_selector(
            '[data-testid="stElementContainer"].st-key-cs_submit, '
            '[data-testid="stElementContainer"].st-key-di_continue',
            timeout=10000,
        )
    except Exception:
        pass
    time.sleep(1.6)
    page.screenshot(path=str(out_path), full_page=True)
    print(f"Saved: {out_path}")


# Save original theme so we can restore
orig = "light"
if SETTINGS.exists():
    try:
        orig = json.loads(SETTINGS.read_text(encoding="utf-8")).get("theme", "light")
    except Exception:
        pass

# Take only requested pages (default: all). Pass page-slug args to filter.
requested = set(sys.argv[1:]) if len(sys.argv) > 1 else None

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    # Tall viewport so the entire page is captured without relying on
    # full_page=True (Streamlit's inner scroll container breaks
    # Playwright's scrollHeight measurement).
    ctx = browser.new_context(
        viewport={"width": 1500, "height": 2200},
        device_scale_factor=1.5,
    )
    page = ctx.new_page()

    for theme in ("light", "dark"):
        set_theme(theme)
        for route, slug, sentinel in PAGES:
            if requested and slug not in requested:
                continue
            capture(
                page,
                BASE + route,
                sentinel,
                OUT_DIR / f"day2-{slug}-{theme}.png",
            )

    browser.close()

set_theme(orig)
print(f"Restored theme to: {orig}")
