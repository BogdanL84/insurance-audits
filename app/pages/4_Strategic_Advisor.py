"""
6_Strategic_Advisor.py — CAUA-informed strategic positioning and win strategy.

Uses the CAUA / TBV framework to generate:
  1. TBV Positioning — provocation narrative and analogy selection
  2. PCT Playbook — each finding packaged for presentation (laymen's title, cost of doing nothing, conviction evidence)
  3. Broker A vs. B — competitive differentiation script
  4. Win Strategy — 5 organizing principals + final meeting outline
  5. Progress Report — agenda for middle meeting dress rehearsal

FIX 1: Cache plan to ai-exchange/strategic-plan.json; only call Claude when button clicked.
FIX 2: Accept markdown response — render with st.markdown(); download as .md.
FIX 3: Client Web Research section with URL input, cached to ai-exchange/client-research.md.
"""

import sys
import json
import time
from datetime import datetime, date
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import streamlit as st

st.set_page_config(
    page_title="Strategic Advisor — Insurance Audit",
    layout="wide",
    initial_sidebar_state="expanded",
)

from config import CLIENTS_DIR, COLOR_NAVY, COLOR_GOOD, COLOR_BAD, COLOR_UGLY
from core import audit_state as ast
from core.claude_runner import (
    build_strategic_advisor_prompt,
    build_client_research_prompt,
    run_claude,
    extract_json,
    ANALYSIS_TIMEOUT,
)
from utils import (
    render_sidebar, require_client, render_progress_bar,
    inject_css, render_breadcrumb,
)

inject_css()
render_sidebar()

slug, client_path, state = require_client()
display_name = state.get("display_name", slug)
ai_exchange  = client_path / "ai-exchange"
ai_exchange.mkdir(parents=True, exist_ok=True)

PLAN_CACHE_FILE     = ai_exchange / "strategic-plan.json"
RESEARCH_CACHE_FILE = ai_exchange / "client-research.md"

render_breadcrumb(display_name, "Strategic Advisor")
st.title("Strategic Advisor")
st.caption(f"**{display_name}** — Creating an Unfair Advantage / Trust But Verify Positioning & Win Strategy")
render_progress_bar(state.get("stage", "findings_reviewed"), active_step=4)
st.divider()


# ══════════════════════════════════════════════════════════════════
#  SECTION 1 — CLIENT WEB RESEARCH (FIX 3)
# ══════════════════════════════════════════════════════════════════
with st.expander("Research Client (Web Intelligence)", expanded=False):
    st.caption(
        "Let Claude research the prospect company before your meeting. "
        "Results are cached — click Update to refresh."
    )

    ci = state.get("client_info", {})
    default_name = display_name
    default_url  = ""
    default_ind  = ci.get("industry", "")

    rc1, rc2, rc3 = st.columns([3, 3, 2])
    with rc1:
        research_company = st.text_input("Company Name", value=default_name, key="research_company")
    with rc2:
        research_url = st.text_input("Website URL", value=default_url, placeholder="https://...", key="research_url")
    with rc3:
        research_industry = st.text_input("Industry", value=default_ind, key="research_industry")

    # Load cached research
    cached_research = None
    if RESEARCH_CACHE_FILE.exists():
        try:
            cached_research = RESEARCH_CACHE_FILE.read_text(encoding="utf-8")
        except OSError:
            cached_research = None

    has_research = bool(cached_research and cached_research.strip())

    btn_label = "Update Research" if has_research else "Research Client"
    if st.button(btn_label, key="research_btn", type="primary" if not has_research else "secondary"):
        if not research_company.strip():
            st.warning("Enter a company name to research.")
        else:
            prompt = build_client_research_prompt(
                research_company.strip(),
                research_url.strip(),
                research_industry.strip(),
            )
            with st.spinner(f"Researching {research_company}... (may take 30-60 seconds)"):
                ok, result = run_claude(prompt, timeout=120)
            if ok:
                # result is the raw text (markdown report)
                # Strip JSON envelope if present
                raw_text = result.strip()
                try:
                    envelope = json.loads(raw_text)
                    if isinstance(envelope, dict) and "result" in envelope:
                        raw_text = str(envelope["result"]).strip()
                except (json.JSONDecodeError, TypeError):
                    pass

                # Add timestamp header
                ts = datetime.now().strftime("%Y-%m-%d %H:%M")
                report_md = f"*Last updated: {ts}*\n\n" + raw_text
                try:
                    RESEARCH_CACHE_FILE.write_text(report_md, encoding="utf-8")
                    cached_research = report_md
                    has_research = True
                    st.success("Research complete and saved.")
                except OSError as e:
                    st.error(f"Could not save research: {e}")
            else:
                st.error(f"Research failed: {result}")

    if has_research and cached_research:
        st.markdown("---")
        st.markdown(cached_research)

        st.markdown("---")
        ucol1, ucol2 = st.columns([2, 5])
        with ucol1:
            if st.button("Update Client Profile with Research", key="update_profile_btn"):
                # Append research summary to client_info.notes
                existing_notes = ci.get("notes", "").strip()
                research_note = (
                    "\n\n---\n**Web Research (auto-generated)**\n\n"
                    + (cached_research or "")
                )
                if "Web Research (auto-generated)" in existing_notes:
                    # Replace existing research section
                    parts = existing_notes.split("---\n**Web Research (auto-generated)**")
                    updated_notes = parts[0].strip() + research_note
                else:
                    updated_notes = existing_notes + research_note

                state["client_info"]["notes"] = updated_notes
                ast.save(client_path, state)
                ast.write_client_notes(client_path, state)
                st.success("Client profile updated.")
        with ucol2:
            st.download_button(
                label="Download Research (.md)",
                data=cached_research.encode("utf-8"),
                file_name=f"{slug}-client-research.md",
                mime="text/markdown",
                key="dl_research",
            )


st.markdown("<br>", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════
#  EMPTY STATE — no findings
# ══════════════════════════════════════════════════════════════════
findings = state.get("findings", [])

if not findings:
    st.markdown("<br>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        st.markdown(
            "<div style='text-align:center;padding:2rem 0'>"
            "<div style='font-size:3rem'>&#127944;</div>"
            "<h3>No findings yet</h3>"
            "<p style='color:#666'>Run the full audit analysis before generating strategic advice.</p>"
            "</div>",
            unsafe_allow_html=True,
        )
        if st.button("Run Analysis", type="primary", use_container_width=True):
            st.switch_page("pages/2_Document_Intake.py")
    st.stop()


# ══════════════════════════════════════════════════════════════════
#  FINDINGS SUMMARY BAR
# ══════════════════════════════════════════════════════════════════
ugly_ct = sum(1 for f in findings if f.get("category") == "Ugly")
bad_ct  = sum(1 for f in findings if f.get("category") == "Bad")
good_ct = sum(1 for f in findings if f.get("category") == "Good")

st.markdown(
    f"<div style='font-size:0.875rem;color:#555;margin-bottom:1.5rem'>"
    f"Building strategy from <strong>{len(findings)} findings</strong>: "
    f"<span style='color:{COLOR_UGLY}'>{ugly_ct} critical</span> &middot; "
    f"<span style='color:{COLOR_BAD}'>{bad_ct} bad</span> &middot; "
    f"<span style='color:{COLOR_GOOD}'>{good_ct} good</span>"
    f"</div>",
    unsafe_allow_html=True,
)


# ══════════════════════════════════════════════════════════════════
#  FIX 1 — CACHE LOAD + CONDITIONAL GENERATE BUTTON
# ══════════════════════════════════════════════════════════════════
def _load_plan_cache() -> tuple[dict | None, str | None, str | None]:
    """
    Load strategic plan from disk cache.
    Returns (plan_dict_or_None, raw_text_or_None, timestamp_or_None).
    """
    if not PLAN_CACHE_FILE.exists():
        return None, None, None
    try:
        data = json.loads(PLAN_CACHE_FILE.read_text(encoding="utf-8"))
        ts   = data.get("timestamp", "")
        plan = data.get("plan")       # dict if JSON was parsed
        raw  = data.get("raw")        # str if markdown fallback
        return plan, raw, ts
    except (json.JSONDecodeError, OSError):
        return None, None, None


def _save_plan_cache(plan: dict | None, raw: str | None) -> None:
    ts = datetime.now().isoformat()
    data: dict = {"timestamp": ts}
    if plan:
        data["plan"] = plan
    if raw:
        data["raw"] = raw
    try:
        PLAN_CACHE_FILE.write_text(
            json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8"
        )
    except OSError:
        pass


cached_plan, cached_raw, cached_ts = _load_plan_cache()

# If raw text is actually JSON (Claude returned JSON but extract_json missed it),
# rescue it into cached_plan so the structured renderer is used instead of
# rendering raw JSON text as markdown.
if cached_raw and not cached_plan:
    _raw_stripped = cached_raw.strip()
    if _raw_stripped.startswith("{"):
        try:
            _rescued = json.loads(_raw_stripped)
            # Accept if it has at least one expected strategic plan key
            _PLAN_KEYS = {"tbv_positioning","pct_playbook","broker_a_vs_b",
                          "five_principals","final_meeting_outline","progress_report_agenda"}
            if isinstance(_rescued, dict) and _PLAN_KEYS.intersection(_rescued.keys()):
                cached_plan = _rescued
                cached_raw  = None
                _save_plan_cache(cached_plan, None)
        except (json.JSONDecodeError, TypeError):
            pass

has_cache = cached_plan is not None or bool(cached_raw)

# Format timestamp for display
cached_ts_display = ""
if cached_ts:
    try:
        dt = datetime.fromisoformat(cached_ts)
        cached_ts_display = dt.strftime("%b %d, %Y at %I:%M %p")
    except ValueError:
        cached_ts_display = cached_ts

gen_col, ts_col = st.columns([2, 5])
with gen_col:
    if has_cache:
        generate = st.button(
            "Re-generate Strategic Plan",
            key="gen_strategic_btn",
            type="secondary",
            use_container_width=True,
        )
    else:
        generate = st.button(
            "Generate Strategic Plan",
            key="gen_strategic_btn",
            type="primary",
            use_container_width=True,
        )

with ts_col:
    if cached_ts_display:
        st.markdown(
            f"<div style='padding-top:0.6rem;font-size:0.8rem;color:#888'>"
            f"Last generated: {cached_ts_display}</div>",
            unsafe_allow_html=True,
        )

# Generate if button clicked
if generate:
    client_notes = state.get("client_info", {}).get("notes", "")
    prompt = build_strategic_advisor_prompt(state, client_notes)

    with st.status("Building strategic plan...", expanded=True) as _status:
        _prog = st.progress(0, text="Sending request to Claude...")

        ok, result = run_claude(prompt, timeout=ANALYSIS_TIMEOUT)

        _prog.progress(50, text="Analyzing findings...")

        if ok:
            # ── Parse: try extract_json first, then manual fence-strip ──────
            import re as _re2
            plan_data = extract_json(result)

            if not plan_data:
                raw_text = result.strip()
                raw_text = _re2.sub(r'^[ \t]*```[a-zA-Z]*\s*\n?', '', raw_text)
                raw_text = _re2.sub(r'\n?[ \t]*```\s*$', '', raw_text).strip()
                if raw_text.startswith('{'):
                    try:
                        plan_data = json.loads(raw_text)
                    except json.JSONDecodeError as je:
                        st.warning(f"JSON parse failed: {je}. Saving raw string.")
                        plan_data = None

            _prog.progress(100, text="Finalizing plan...")

            # ── Save — always persist something so the page can display it ─
            if plan_data:
                state["strategic_plan"] = plan_data          # dict → renders as expanders
                _save_plan_cache(plan_data, None)
            else:
                state["strategic_plan"] = result.strip()     # raw string → displayed as-is
                _save_plan_cache(None, result.strip())

            ast.save(client_path, state)
            _status.update(label="Strategic plan ready.", state="complete", expanded=False)
        else:
            _status.update(label="Generation failed.", state="error", expanded=True)

    # ── Debug: always show raw output so we can see what Claude returned ──
    with st.expander("🔍 Debug — Raw Claude output", expanded=not ok):
        st.write(f"**ok:** `{ok}`")
        st.write(f"**result length:** `{len(result) if result else 0}` chars")
        st.write(f"**first 800 chars:**")
        st.text(result[:800] if result else "(empty)")

    if not ok:
        st.error(f"Strategic plan generation failed: {result}")
        st.stop()

    st.rerun()

# ══════════════════════════════════════════════════════════════════
#  LOAD — audit state first, cache file fallback
# ══════════════════════════════════════════════════════════════════
_stored = state.get("strategic_plan")

# Normalise: if it's a JSON string, parse it now
plan_dict = None
plan_raw  = None

if isinstance(_stored, dict) and _stored:
    plan_dict = _stored
elif isinstance(_stored, str) and _stored.strip():
    import re as _re3
    _rt = _stored.strip()
    _rt = _re3.sub(r'^[ \t]*```[a-zA-Z]*\s*\n?', '', _rt)
    _rt = _re3.sub(r'\n?[ \t]*```\s*$', '', _rt).strip()
    try:
        plan_dict = json.loads(_rt) if _rt.startswith('{') else None
    except json.JSONDecodeError:
        plan_dict = None
    if not plan_dict:
        plan_raw = _stored   # show as raw text

# Fall back to cache file if audit state has nothing
if not plan_dict and not plan_raw:
    if cached_plan:
        plan_dict = cached_plan
    elif cached_raw:
        plan_raw = cached_raw

if not plan_dict and not plan_raw:
    st.info("Click **Generate Strategic Plan** to build your Creating an Unfair Advantage presentation strategy.")
    st.stop()


# ══════════════════════════════════════════════════════════════════
#  DISPLAY — one expander per top-level key
# ══════════════════════════════════════════════════════════════════

# Full-phrase labels for each plan section (no abbreviations in the UI)
_SECTION_LABELS: dict[str, str] = {
    "tbv_positioning":        "Trust But Verify Positioning",
    "pct_playbook":           "Poorly Constructed Terms Playbook",
    "broker_a_vs_b":          "Broker A vs. Broker B",
    "five_principals":        "Five Organizing Principals",
    "final_meeting_outline":  "Final Meeting Outline",
    "progress_report_agenda": "Progress Report Agenda",
}

# Sub-key label overrides within sections (expand any abbreviations here)
_SUB_LABELS: dict[str, str] = {
    "tbv_recap":             "Trust But Verify Recap",
    "pct_entries":           "Poorly Constructed Terms Entries",
    "caua_summary":          "Creating an Unfair Advantage Summary",
}


def _render_section(key: str, value) -> None:
    """Render a single plan section value inside an expander."""
    label = _SECTION_LABELS.get(key, key.replace("_", " ").title())
    with st.expander(label, expanded=True):
        try:
            if isinstance(value, list):
                for item in value:
                    if isinstance(item, dict):
                        for k, v in item.items():
                            st.markdown(f"**{k.replace('_', ' ').title()}:** {v}")
                        st.markdown("---")
                    else:
                        st.markdown(f"- {item}")
            elif isinstance(value, dict):
                for k, v in value.items():
                    sub_label = k.replace("_", " ").title()
                    if isinstance(v, list):
                        st.markdown(f"**{sub_label}:**")
                        for item in v:
                            st.markdown(f"- {item}")
                    else:
                        st.markdown(f"**{sub_label}:** {v}")
            else:
                st.markdown(str(value))
        except Exception as exc:
            st.error(f"Could not render section '{key}': {exc}\n\nRaw value: {value!r}")


if plan_dict:
    try:
        for section_key, section_value in plan_dict.items():
            if section_value:
                _render_section(section_key, section_value)
    except Exception as exc:
        st.error(f"Failed to render strategic plan: {exc}")
        st.markdown(str(plan_dict))
elif plan_raw:
    st.warning("Strategic plan could not be parsed as JSON — showing raw output.")
    st.markdown(plan_raw)

st.markdown("<br>", unsafe_allow_html=True)
st.divider()
_n1, _n2, _ = st.columns([2, 2, 5])
with _n1:
    if st.button("Back to Report Builder", use_container_width=True, key="back_nav"):
        st.switch_page("pages/_Report_Builder.py")
with _n2:
    if st.button("Dashboard", use_container_width=True, key="dash_nav"):
        st.switch_page("app.py")
