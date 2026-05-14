"""Screenshot the Findings Dashboard in light + dark mode for Day 3 review.

Note: the user-provided template used Playwright's color_scheme="dark"
context option, which sets prefers-color-scheme on the browser. But
this app's dark theme is driven by settings.json (read on each page
load by inject_css), not by prefers-color-scheme. So this script
toggles settings.json between light and dark and restores the
original theme on exit, matching the pattern of the existing
scripts/screenshot_day2.py / screenshot_ta_*.py.
"""
import asyncio
import json
from pathlib import Path

from playwright.async_api import async_playwright

PORT     = 8508
PAGE_URL = f"http://localhost:{PORT}/Findings_Dashboard"
REPO     = Path(__file__).resolve().parents[1]
OUT_DIR  = REPO / "validation-2026-04-27"
SETTINGS = REPO / "settings.json"

OUT_DIR.mkdir(parents=True, exist_ok=True)


def set_theme(theme: str) -> None:
    data: dict = {}
    if SETTINGS.exists():
        try:
            data = json.loads(SETTINGS.read_text(encoding="utf-8"))
        except Exception:
            data = {}
    data["theme"] = theme
    SETTINGS.write_text(json.dumps(data, indent=2), encoding="utf-8")


HIDE_STREAMLIT_CHROME = """
    header[data-testid="stHeader"] { display: none !important; }
    [data-testid="stToolbar"] { display: none !important; }
"""


async def capture(browser, theme: str) -> None:
    set_theme(theme)
    ctx = await browser.new_context(
        viewport={"width": 1500, "height": 1700},
        device_scale_factor=1.5,
    )
    page = await ctx.new_page()
    await page.goto(PAGE_URL)
    await page.wait_for_load_state("networkidle")
    await page.wait_for_selector(".ta-hero-title", timeout=15000)
    await page.wait_for_selector(".st-key-ta_content", timeout=10000)
    await page.wait_for_timeout(2200)
    await page.add_style_tag(content=HIDE_STREAMLIT_CHROME)
    await page.wait_for_timeout(400)
    out = OUT_DIR / f"day3-findings-{theme}.png"
    await page.screenshot(path=str(out), full_page=True)
    await ctx.close()
    print(f"Saved: {out}")


async def run() -> None:
    orig_theme = "light"
    if SETTINGS.exists():
        try:
            orig_theme = json.loads(SETTINGS.read_text(encoding="utf-8")).get("theme", "light")
        except Exception:
            pass

    async with async_playwright() as p:
        browser = await p.chromium.launch()
        try:
            await capture(browser, "light")
            await capture(browser, "dark")
        finally:
            await browser.close()

    set_theme(orig_theme)
    print(f"Restored theme: {orig_theme}")


if __name__ == "__main__":
    asyncio.run(run())
