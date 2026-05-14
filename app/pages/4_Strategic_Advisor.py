"""
Strategic Advisor — Day 3 (Treatment A: Tabbed Insight Dashboard).

Six tabs across the top, one per section of the strategic plan schema.
Playbook tab uses a swap-into-top "active entry" interaction: clicking
any row in the list swaps that entry into the featured slot at top.

Cached plan renders immediately. Re-generate is a button at page bottom.

Schema (from _STRATEGIC_ADVISOR_SCHEMA in claude_runner.py):
  tbv_positioning           dict (headline, narrative, analogy, objections)
  pct_playbook              list[dict] (70 entries ordered by sequence)
  broker_a_vs_b             dict (incumbent_evidence, our_differentiation, transition_script)
  five_principals           dict (product/price/relationship/qualification/strategy)
  final_meeting_outline     dict (opening_script, section_sequence, trial_close, closing, leave_behind)
  progress_report_agenda    list[str] (3 mid-meeting trial-close items)

Severity for playbook badges resolves via:
  1. finding_id exact match in state["findings"] → use that finding's category
  2. finding_id ends with -ugly/-bad/-good/-review → strip suffix as category
  3. keyword-scan severity_framing + worst_case_scenario
  4. default "Bad"
"""
from __future__ import annotations

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import html as _html
import json
import re as _re
from datetime import datetime, timezone

import streamlit as st

st.set_page_config(
    page_title="Strategic Advisor · Insurance Audit",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded",
)

from utils import (
    inject_css, render_sidebar, render_stepper, require_client, _md, _mark_active_nav,
)
from core import audit_state as ast
from core.claude_runner import (
    build_strategic_advisor_prompt, run_claude, extract_json, ANALYSIS_TIMEOUT,
)

inject_css()
render_sidebar()
_mark_active_nav("Strategic_Advisor")

slug, client_path, state = require_client()
display_name: str = state.get("display_name", slug)
findings: list[dict] = state.get("findings", []) or []

# Hydrate plan: state slot first, disk fallback second.
plan: dict = state.get("strategic_plan", {}) or {}
plan_timestamp = ""
disk_cache_path = client_path / "ai-exchange" / "strategic-plan.json"
if disk_cache_path.exists():
    try:
        disk_data = json.loads(disk_cache_path.read_text(encoding="utf-8"))
        if not plan:
            plan = disk_data.get("plan", {}) or {}
            if plan:
                state["strategic_plan"] = plan
                ast.save(client_path, state)
        plan_timestamp = disk_data.get("timestamp", "")
    except Exception:
        pass


# ── HELPERS ─────────────────────────────────────────────────────────
def _esc(s) -> str:
    return _html.escape(str(s)) if s is not None else ""


_TABS = [
    ("positioning", "Positioning", "TBV Frame"),
    ("playbook",    "Playbook",    "70 entries"),
    ("broker",      "Broker A vs B", "Differentiation"),
    ("principals",  "Principals",  "P/P/R/Q/S"),
    ("meeting",     "Meeting",     "Outline"),
    ("mid_meeting", "Mid-Meeting", "Trial closes"),
]
_SEC_KEYS = {
    "positioning": "tbv_positioning",
    "playbook":    "pct_playbook",
    "broker":      "broker_a_vs_b",
    "principals":  "five_principals",
    "meeting":     "final_meeting_outline",
    "mid_meeting": "progress_report_agenda",
}
_CATEGORY_TO_SEV_CLASS = {
    "Ugly": "ugly", "Bad": "bad",
    "Review": "review", "Needs Review": "review",
    "Good": "good",
}
_FINDINGS_BY_ID = {f.get("id"): f for f in findings if f.get("id")}


def _resolve_severity(entry: dict) -> str:
    """Return Category label ('Ugly'/'Bad'/'Review'/'Good') using the
    3-step fallback chain agreed in Step A."""
    fid = (entry.get("finding_id") or "").strip()
    # Step 1: exact match
    if fid in _FINDINGS_BY_ID:
        cat = _FINDINGS_BY_ID[fid].get("category")
        if cat in ("Ugly", "Bad", "Review", "Needs Review", "Good"):
            return "Review" if cat == "Needs Review" else cat
    # Step 2: suffix strip
    m = _re.search(r"-(ugly|bad|good|review)$", fid, _re.IGNORECASE)
    if m:
        return m.group(1).capitalize()
    # Step 3: keyword scan on severity_framing + worst_case
    text = ((entry.get("severity_framing") or "") + " " +
            (entry.get("worst_case_scenario") or "")).lower()
    if any(kw in text for kw in [
        "denied", "zero coverage", "no coverage", "excluded", "barred",
        "expressly", "absolute",
    ]):
        return "Ugly"
    if any(kw in text for kw in ["limited", "sublimit", "partial", "narrow"]):
        return "Bad"
    if any(kw in text for kw in ["verify", "confirm", "review", "unclear", "ambiguous"]):
        return "Review"
    return "Bad"  # default


def _fmt_age(ts_iso: str) -> str:
    if not ts_iso:
        return ""
    try:
        dt = datetime.fromisoformat(ts_iso.replace("Z", "+00:00"))
        now = datetime.now(timezone.utc)
        # Normalize naive to UTC
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        delta = now - dt
        if delta.days > 1:
            return f"Generated {delta.days}d ago"
        if delta.days == 1:
            return "Generated yesterday"
        if delta.seconds > 3600:
            return f"Generated {delta.seconds // 3600}h ago"
        return "Generated just now"
    except Exception:
        return ""


# ── SESSION STATE ───────────────────────────────────────────────────
ss = st.session_state
ss.setdefault("advisor_active_tab", "positioning")
ss.setdefault("advisor_active_playbook_seq", 1)
ss.setdefault("advisor_playbook_show_all", False)


# ── GENERATE / REGENERATE flow (shared by empty-state button + bottom-of-page button)
def _generate_plan() -> None:
    """Run the LLM and persist results. Called from both buttons."""
    with st.spinner("Generating strategic plan (this takes ~30-60s)..."):
        client_notes = state.get("client_info", {}).get("notes", "")
        prompt = build_strategic_advisor_prompt(state, client_notes)
        ok, raw = run_claude(prompt, timeout=ANALYSIS_TIMEOUT)
        if not ok:
            st.error("Generation failed. Try again.")
            return
        new_plan = extract_json(raw)
        if not isinstance(new_plan, dict):
            # Fence-strip fallback (existing pattern)
            try:
                cleaned = raw.strip()
                if cleaned.startswith("```"):
                    cleaned = _re.sub(r"^```(?:json)?\s*", "", cleaned)
                    cleaned = _re.sub(r"\s*```\s*$", "", cleaned)
                new_plan = json.loads(cleaned)
            except Exception:
                st.error("Generation produced malformed JSON. Try Re-generate.")
                return
        ts_now = datetime.now(timezone.utc).isoformat()
        state["strategic_plan"] = new_plan
        ast.save(client_path, state)
        # Write disk fallback (source of truth for timestamp)
        disk_cache_path.parent.mkdir(parents=True, exist_ok=True)
        disk_cache_path.write_text(
            json.dumps({"plan": new_plan, "timestamp": ts_now, "raw": raw}, indent=2),
            encoding="utf-8",
        )
        st.rerun()


# ── HERO ───────────────────────────────────────────────────────────
plan_age = _fmt_age(plan_timestamp)
playbook_entries = plan.get("pct_playbook", []) if plan else []

if plan:
    hero_sub = (
        f"{_esc(display_name)} &middot; complete broker meeting playbook "
        f"synthesized from {len(playbook_entries)} finding entries."
    )
    chips = []
    if plan_age:
        chips.append(f'<span class="ta-hero-chip">&#128203; {plan_age}</span>')
    chips.append(f'<span class="ta-hero-chip">&#9889; {len(playbook_entries)}-entry playbook</span>')
    hero_chips = "".join(chips)
else:
    hero_sub = (
        f"{_esc(display_name)} &middot; no strategic plan generated yet. "
        f"Synthesize one from {len(findings)} audit findings."
    )
    hero_chips = ""

_md(f"""
<div class="adv-hero-purple">
<div class="ta-hero">
  <div class="ta-hero-content">
    <p class="ta-hero-eyebrow">STEP 5 OF 6 &middot; STRATEGIC ADVISOR</p>
    <h1 class="ta-hero-title">Strategic Advisor</h1>
    <p class="ta-hero-sub">{hero_sub}</p>
    <div class="ta-hero-chips">{hero_chips}</div>
  </div>
</div>
</div>
""")


# ── PER-TAB RENDER FUNCTIONS ────────────────────────────────────────
def _render_positioning(data: dict) -> None:
    _md("""
    <div class="adv-sec-head">
      <div class="adv-sec-title-block">
        <div class="adv-sec-icon">🎯</div>
        <div>
          <div class="adv-sec-name">Trust But Verify <span class="accent">positioning</span></div>
          <div class="adv-sec-sub">Frame for the opening 5 minutes of the broker meeting</div>
        </div>
      </div>
    </div>
    """)
    headline = _esc(data.get("headline", ""))
    narrative = _esc(data.get("provocation_narrative", ""))
    analogy = _esc(data.get("recommended_analogy", ""))
    analogy_rat = _esc(data.get("analogy_rationale", ""))
    objections = data.get("two_objections_prep", []) or []

    objections_html = ""
    if objections:
        items = []
        for o in objections:
            if isinstance(o, dict):
                lbl = _esc(o.get("objection", ""))
                resp = _esc(o.get("response", ""))
                items.append(f"<li><strong>{lbl}</strong>{' — ' + resp if resp else ''}</li>")
            else:
                items.append(f"<li>{_esc(o)}</li>")
        objections_html = f'<div class="adv-field-label" style="margin-top:18px">Objections to prepare for</div><ul style="margin-left:18px;line-height:1.7">{"".join(items)}</ul>'

    _md(f"""
    <div class="adv-narrative">
      <div class="adv-field">
        <div class="adv-field-label">Headline</div>
        <div class="adv-field-value"><strong>{headline}</strong></div>
      </div>
      <div class="adv-field">
        <div class="adv-field-label">Provocation Narrative</div>
        <div class="adv-narrative-body"><p>{narrative}</p></div>
      </div>
      <div class="adv-field">
        <div class="adv-field-label">Recommended Analogy</div>
        <div class="adv-field-value"><em>{analogy}</em> — {analogy_rat}</div>
      </div>
      {objections_html}
    </div>
    """)


def _render_featured_playbook_entry(e: dict) -> None:
    seq = e.get("presentation_sequence", 0)
    cat = _resolve_severity(e)
    sev_class = _CATEGORY_TO_SEV_CLASS.get(cat, "review")
    title = _esc(e.get("finding_title", ""))
    laymen = _esc(e.get("laymen_title", ""))
    framing = _esc(e.get("severity_framing", ""))
    worst = _esc(e.get("worst_case_scenario", ""))
    cost = _esc(e.get("cost_of_doing_nothing", ""))
    solution = _esc(e.get("our_solution", ""))
    finding_id = _esc(e.get("finding_id", ""))

    _md(f"""
    <div class="pb-featured">
      <div class="pb-featured-badge">Active entry &middot; SEQ {seq:02d}</div>
      <div class="pb-featured-head">
        <span class="pb-seq">SEQ {seq:02d}</span>
        <span class="pb-sev {sev_class}">{_esc(cat)}</span>
        <span class="pb-policy">{finding_id}</span>
      </div>
      <div class="pb-featured-title">{title}</div>
      <div class="pb-featured-laymen">"{laymen}"</div>
      <div class="pb-featured-body">
        <div>
          <div class="pb-block-title">Severity Framing</div>
          <div class="pb-block-content">{framing}</div>
          <div class="pb-block-title">Worst-Case Scenario</div>
          <div class="pb-block-content">{worst}</div>
        </div>
        <div>
          <div class="pb-cost-callout">
            <div class="pb-block-title">Cost of Doing Nothing</div>
            <div class="pb-cost-amount">{cost}</div>
          </div>
          <div class="pb-solution-callout">
            <div class="pb-block-title">Our Solution</div>
            <div class="pb-solution-content">{solution}</div>
          </div>
        </div>
      </div>
    </div>
    """)


def _render_playbook_row(e: dict, is_active: bool) -> None:
    seq = e.get("presentation_sequence", 0)
    title = e.get("finding_title", "")
    laymen = e.get("laymen_title", "")
    cat = _resolve_severity(e)
    sev_class = _CATEGORY_TO_SEV_CLASS.get(cat, "review")

    container_key = f"pb_row_{seq}_active" if is_active else f"pb_row_{seq}"
    with st.container(key=container_key):
        cols = st.columns([0.6, 5, 1, 0.9])
        cols[0].markdown(
            f'<div class="pb-row-seq">{seq:02d}</div>',
            unsafe_allow_html=True,
        )
        cols[1].markdown(
            f'<div class="pb-row-title">{_esc(title)}</div>'
            f'<div class="pb-row-laymen">"{_esc(laymen)}"</div>',
            unsafe_allow_html=True,
        )
        cols[2].markdown(
            f'<span class="pb-sev {sev_class}">{_esc(cat)}</span>',
            unsafe_allow_html=True,
        )
        if is_active:
            cols[3].markdown(
                '<div style="text-align:center;color:var(--purple);font-weight:700;font-size:0.78rem;padding-top:6px">Active ●</div>',
                unsafe_allow_html=True,
            )
        else:
            if cols[3].button("View →", key=f"pb_view_{seq}", use_container_width=True):
                ss.advisor_active_playbook_seq = seq
                st.rerun()


def _render_playbook(entries: list) -> None:
    entries_sorted = sorted(entries, key=lambda e: e.get("presentation_sequence", 999))
    if not entries_sorted:
        _md('<div class="adv-narrative"><p style="color:var(--muted)">No playbook entries.</p></div>')
        return

    active_seq = ss.advisor_active_playbook_seq
    active_entry = next(
        (e for e in entries_sorted if e.get("presentation_sequence") == active_seq),
        entries_sorted[0],
    )

    _md(f"""
    <div class="adv-sec-head">
      <div class="adv-sec-title-block">
        <div class="adv-sec-icon">📖</div>
        <div>
          <div class="adv-sec-name">Presentation <span class="accent">playbook</span></div>
          <div class="adv-sec-sub">{len(entries_sorted)} entries ordered by presentation sequence</div>
        </div>
      </div>
      <div class="adv-sec-meta">Click any row to swap into the featured slot above</div>
    </div>
    """)

    _render_featured_playbook_entry(active_entry)

    _md('<div class="pb-divider">All entries · click any row to view</div>')

    visible = entries_sorted if ss.advisor_playbook_show_all else entries_sorted[:15]
    for entry in visible:
        seq = entry.get("presentation_sequence", 0)
        _render_playbook_row(entry, is_active=(seq == active_seq))

    if not ss.advisor_playbook_show_all and len(entries_sorted) > 15:
        with st.container(key="pb_show_all_btn"):
            if st.button(
                f"Show all {len(entries_sorted)} entries  ↓",
                key="pb_show_all",
                use_container_width=True,
            ):
                ss.advisor_playbook_show_all = True
                st.rerun()


def _render_broker(data: dict) -> None:
    _md("""
    <div class="adv-sec-head">
      <div class="adv-sec-title-block">
        <div class="adv-sec-icon">⚖️</div>
        <div>
          <div class="adv-sec-name">Incumbent vs <span class="accent">us</span></div>
          <div class="adv-sec-sub">Differentiation evidence and transition script</div>
        </div>
      </div>
    </div>
    """)
    incumbent = _esc(data.get("incumbent_evidence", ""))
    diff = _esc(data.get("our_differentiation", ""))
    script = _esc(data.get("transition_script", ""))
    _md(f"""
    <div class="adv-narrative">
      <div class="adv-field">
        <div class="adv-field-label">Incumbent Evidence</div>
        <div class="adv-field-value">{incumbent}</div>
      </div>
      <div class="adv-field">
        <div class="adv-field-label">Our Differentiation</div>
        <div class="adv-field-value">{diff}</div>
      </div>
      <div class="adv-field">
        <div class="adv-field-label">Transition Script</div>
        <div class="adv-narrative-body"><div class="quote">{script}</div></div>
      </div>
    </div>
    """)


def _render_principals(data: dict) -> None:
    _md("""
    <div class="adv-sec-head">
      <div class="adv-sec-title-block">
        <div class="adv-sec-icon">🧭</div>
        <div>
          <div class="adv-sec-name">Five <span class="accent">principals</span></div>
          <div class="adv-sec-sub">Product · Price · Relationship · Qualification · Strategy</div>
        </div>
      </div>
    </div>
    """)
    cards = []
    for key in ["product", "price", "relationship", "qualification", "strategy"]:
        body = _esc(data.get(key, ""))
        cls = "adv-principal-card full-width" if key == "strategy" else "adv-principal-card"
        cards.append(
            f'<div class="{cls}">'
            f'<div class="adv-principal-card-title">{key.title()}</div>'
            f'<div class="adv-principal-card-body">{body}</div>'
            f'</div>'
        )
    _md(f"""
    <div class="adv-narrative">
      <div class="adv-principals">{''.join(cards)}</div>
    </div>
    """)


def _render_meeting(data: dict) -> None:
    _md("""
    <div class="adv-sec-head">
      <div class="adv-sec-title-block">
        <div class="adv-sec-icon">📅</div>
        <div>
          <div class="adv-sec-name">First meeting <span class="accent">outline</span></div>
          <div class="adv-sec-sub">Opening through close, with leave-behind</div>
        </div>
      </div>
    </div>
    """)
    opening = _esc(data.get("opening_script", ""))
    sequence = data.get("section_sequence", []) or []
    trial = _esc(data.get("mid_meeting_trial_close", ""))
    closing = _esc(data.get("closing_statement", ""))
    leave = _esc(data.get("leave_behind_summary", ""))
    seq_html = "<br>".join(f"• {_esc(s)}" for s in sequence)
    _md(f"""
    <div class="adv-narrative">
      <div class="adv-outline-step">
        <div class="adv-outline-num">1</div>
        <div class="adv-outline-step-content">
          <div class="adv-outline-step-name">Opening</div>
          <div class="adv-outline-step-body">{opening}</div>
        </div>
      </div>
      <div class="adv-outline-step">
        <div class="adv-outline-num">2</div>
        <div class="adv-outline-step-content">
          <div class="adv-outline-step-name">Section sequence</div>
          <div class="adv-outline-step-body">{seq_html}</div>
        </div>
      </div>
      <div class="adv-outline-step">
        <div class="adv-outline-num">3</div>
        <div class="adv-outline-step-content">
          <div class="adv-outline-step-name">Mid-meeting trial close</div>
          <div class="adv-outline-step-body">{trial}</div>
        </div>
      </div>
      <div class="adv-outline-step">
        <div class="adv-outline-num">4</div>
        <div class="adv-outline-step-content">
          <div class="adv-outline-step-name">Closing statement</div>
          <div class="adv-outline-step-body">{closing}</div>
        </div>
      </div>
      <div class="adv-outline-step">
        <div class="adv-outline-num">5</div>
        <div class="adv-outline-step-content">
          <div class="adv-outline-step-name">Leave-behind summary</div>
          <div class="adv-outline-step-body">{leave}</div>
        </div>
      </div>
    </div>
    """)


def _render_mid_meeting(data) -> None:
    _md("""
    <div class="adv-sec-head">
      <div class="adv-sec-title-block">
        <div class="adv-sec-icon">🎯</div>
        <div>
          <div class="adv-sec-name">Mid-meeting <span class="accent">trial closes</span></div>
          <div class="adv-sec-sub">Items to test second-meeting commitment</div>
        </div>
      </div>
    </div>
    """)
    items = data if isinstance(data, list) else (data.get("items", []) if isinstance(data, dict) else [])
    items_html = "".join(f"<li>{_esc(s)}</li>" for s in items)
    _md(f"""
    <div class="adv-narrative">
      <div class="adv-trial-list">
        <div class="adv-trial-title">Trial Close Items</div>
        <ul>{items_html}</ul>
      </div>
    </div>
    """)


_RENDERERS = {
    "positioning": _render_positioning,
    "playbook":    _render_playbook,
    "broker":      _render_broker,
    "principals":  _render_principals,
    "meeting":     _render_meeting,
    "mid_meeting": _render_mid_meeting,
}


# ── PAGE BODY ──────────────────────────────────────────────────────
with st.container(key="ta_content"):
    render_stepper(5)

    # Empty state — no plan yet
    if not plan:
        _md("""
        <div class="adv-empty">
          <div class="adv-empty-icon">🎯</div>
          <div class="adv-empty-title">No strategic plan yet</div>
          <div class="adv-empty-sub">Synthesize a complete broker meeting playbook from this client's audit findings. Takes ~30-60 seconds.</div>
        </div>
        """)
        cols = st.columns([3, 2, 3])
        with cols[1]:
            if st.button("Generate Strategic Plan", type="primary", use_container_width=True):
                _generate_plan()
        st.stop()

    # Tab bar
    with st.container(key="adv_tabs"):
        cols = st.columns(6)
        for i, (key, label, meta) in enumerate(_TABS):
            active = ss.advisor_active_tab == key
            # Streamlit button labels don't render HTML; two-line label via newline
            btn_label = f"{label}\n{meta}"
            if cols[i].button(
                btn_label,
                key=f"adv_tab_btn_{key}",
                type="primary" if active else "secondary",
                use_container_width=True,
            ):
                ss.advisor_active_tab = key
                st.rerun()

    # Active tab content
    section_data = plan.get(_SEC_KEYS[ss.advisor_active_tab], {})
    _RENDERERS[ss.advisor_active_tab](section_data)

    # Re-generate at bottom
    st.markdown("<br>", unsafe_allow_html=True)
    cols = st.columns([4, 2, 4])
    with cols[1]:
        if st.button("🔄 Re-generate Plan", key="adv_regen", use_container_width=True):
            _generate_plan()
