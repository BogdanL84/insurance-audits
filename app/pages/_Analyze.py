"""
3_Analyze.py — Run Full Audit via claude -p (Claude Code print mode).

Pipeline:
  1. Extract contract requirements  (skipped when not selected or synthesize_now)
  2. Analyze each selected policy   (chunked automatically for large policies)
  3. Synthesis + cross-policy pass  (deferred if not all policies are analyzed yet)
"""

import sys
import json
import math
import time
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import streamlit as st

st.set_page_config(
    page_title="Analyze — Insurance Audit",
    layout="wide",
    initial_sidebar_state="expanded",
)

from config import COLOR_GOOD, COLOR_BAD, COLOR_UGLY, COLOR_NAVY
from core import audit_state as ast
from core.claude_runner import (
    run_claude, extract_json,
    build_contract_prompt,
    build_policy_prompt, build_standalone_policy_prompt,
    build_policy_chunk_prompt, build_policy_merge_prompt,
    build_crossref_prompt, build_crosspolicy_prompt,
    chunk_text,
    RATE_LIMIT_DELAY, ANALYSIS_TIMEOUT,
)
from core.chunking import run_chunked_synthesis, SINGLE_CALL_THRESHOLD
from utils import (
    render_sidebar, require_client, render_progress_bar,
    inject_css, render_breadcrumb,
)

inject_css()
render_sidebar()

slug, client_path, state = require_client()
display_name = state.get("display_name", slug)

exchange_dir = client_path / "ai-exchange"
exchange_dir.mkdir(parents=True, exist_ok=True)

render_breadcrumb(display_name, "Analyze")
st.title("Policy Analysis")
st.caption(f"**{display_name}**")
render_progress_bar(state.get("stage", "text_extracted"), active_step=2)
st.divider()


# ── Helpers ─────────────────────────────────────────────────────────

def _read_extracted(name: str) -> str | None:
    """Read the extracted text file for a document from ai-exchange/."""
    path = exchange_dir / f"{Path(name).stem}-extracted.txt"
    return path.read_text(encoding="utf-8", errors="replace") if path.exists() else None


def _client_notes() -> str:
    """Return client-notes.md content, or a compact fallback."""
    notes_path = client_path / "client-notes.md"
    if notes_path.exists():
        return notes_path.read_text(encoding="utf-8", errors="replace")
    info = state.get("client_info", {})
    lines = [f"Client: {display_name}"]
    if info.get("industry"):
        lines.append(f"Industry: {info['industry']}")
    if info.get("notes"):
        lines.append(f"Notes: {info['notes']}")
    return "\n".join(lines)


def _analysis_json_path(name: str) -> Path:
    return exchange_dir / f"{slug}-policy-{Path(name).stem}-analysis.json"


def _chunk_estimate(name: str) -> int:
    """Estimate Claude call count by dividing extracted file size by 80k chars."""
    ext_path = exchange_dir / f"{Path(name).stem}-extracted.txt"
    if ext_path.exists():
        return max(1, math.ceil(ext_path.stat().st_size / 80_000))
    return 1


def _is_rate_limit(ok: bool, result: str) -> bool:
    return not ok and result.startswith("RATE_LIMIT:")


def _render_errors(errors: dict) -> None:
    """Render grouped error expander. errors = {doc_name: [error_str, ...]}"""
    if not errors:
        return
    total = sum(len(v) for v in errors.values())
    label = (
        f"Warnings / Errors — {total} issue{'s' if total != 1 else ''} "
        f"across {len(errors)} document{'s' if len(errors) != 1 else ''}"
    )
    with st.expander(label, expanded=False):
        for doc_name, doc_errors in errors.items():
            if len(doc_errors) == 1:
                st.warning(f"**{doc_name}**: {doc_errors[0]}")
            else:
                # First entry is the summary line; subsequent are chunk-level details
                st.warning(f"**{doc_name}**: {doc_errors[0]}")
                for e in doc_errors[1:]:
                    st.caption(f"\u00a0\u00a0\u00a0\u00a0{e}")


# ── Document inventory ───────────────────────────────────────────────

contracts      = state.get("contracts", {})
policies       = state.get("policies", {})
contract_ready = {n: m for n, m in contracts.items() if m.get("extracted")}
policy_ready   = {n: m for n, m in policies.items()  if m.get("extracted")}
contract_skip  = [n for n in contracts if not contracts[n].get("extracted")]
policy_skip    = [n for n in policies  if not policies[n].get("extracted")]
existing       = state.get("findings", [])
failed_set     = set(state.get("failed_policies") or [])


# ── Pre-flight: nothing extracted at all ─────────────────────────────

if not contract_ready and not policy_ready:
    st.markdown("<br>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        st.info(
            "**No extracted documents found.**\n\n"
            "Go to Document Intake, upload your contracts and policies — "
            "text extraction happens automatically on upload.",
        )
        if st.button("Back to Document Intake", type="primary", use_container_width=True):
            st.switch_page("pages/2_Document_Intake.py")
    st.stop()


# ══════════════════════════════════════════════════════════════════
#  SETUP UI  (shown when not running)
# ══════════════════════════════════════════════════════════════════

if not st.session_state.get("_run_audit"):

    # ── Counts (needed by both CTA and status bar) ─────────────────
    _n_pol_total    = len(policies)
    _n_pol_ready    = len(policy_ready)
    _n_pol_analyzed = sum(1 for n in policy_ready if _analysis_json_path(n).exists())
    _has_findings   = bool(existing)
    _can_synthesize = _n_pol_analyzed >= 2

    # ── Review Full Program — top-of-page CTA ─────────────────────

    _cta_btn_col, _cta_info_col = st.columns([2, 3])
    with _cta_btn_col:
        if st.button(
            "Review Full Program",
            type="primary",
            use_container_width=True,
            key="synth_top_btn",
            disabled=not _can_synthesize,
        ):
            st.session_state["_run_audit"]     = "synthesize_now"
            st.session_state["_selected_docs"] = []
            st.rerun()
        st.caption("Cross-references all analyzed policies to find gaps and overlaps.")
        if _has_findings:
            _f_ugly = sum(1 for _f in existing if _f.get("category") == "Ugly")
            _f_bad  = sum(1 for _f in existing if _f.get("category") == "Bad")
            _f_good = sum(1 for _f in existing if _f.get("category") == "Good")
            st.caption(
                f"Last review: {len(existing)} findings \u2014 "
                f"{_f_ugly} critical, {_f_bad} bad, {_f_good} good."
            )
    with _cta_info_col:
        if not _can_synthesize:
            if _n_pol_analyzed == 0:
                st.info(
                    "No policies read yet. Use **Read Policy** in the table below to get started, "
                    "then come back here to run a full cross-policy review."
                )
            else:
                _remaining = _n_pol_ready - _n_pol_analyzed
                _pol_word  = "policy" if _n_pol_ready == 1 else "policies"
                st.info(
                    f"{_n_pol_analyzed} of {_n_pol_ready} {_pol_word} read. "
                    f"Read at least 2 policies to activate this button."
                )
        else:
            _pol_word = "policy" if _n_pol_analyzed == 1 else "policies"
            st.success(
                f"\u2713 **{_n_pol_analyzed} {_pol_word} ready.** "
                f"Click **Review Full Program** to cross-reference all policies and generate findings."
            )
            if _has_findings:
                if st.button("View Findings \u2192", use_container_width=False, key="view_findings_top"):
                    st.switch_page("pages/3_Findings_Dashboard.py")

    st.divider()

    # ── Pipeline status bar ────────────────────────────────────────

    def _stage_html(icon: str, label: str, active: bool, done: bool) -> str:
        if done:
            color, weight = COLOR_GOOD, "700"
        elif active:
            color, weight = COLOR_NAVY, "700"
        else:
            color, weight = "#9E9E9E", "400"
        return (
            f"<span style='color:{color};font-weight:{weight};font-size:0.85rem'>"
            f"{icon} {label}</span>"
        )

    _s1 = _stage_html("✓", f"Extracted ({_n_pol_ready}/{_n_pol_total})",
                      active=True, done=bool(_n_pol_ready))
    _s2 = _stage_html(
        "✓" if _n_pol_analyzed == _n_pol_ready and _n_pol_ready else (
            "◑" if _n_pol_analyzed > 0 else "○"
        ),
        f"Analyzed ({_n_pol_analyzed}/{_n_pol_ready})",
        active=_n_pol_analyzed > 0,
        done=(_n_pol_analyzed == _n_pol_ready and _n_pol_ready > 0),
    )
    _s3 = _stage_html("✓" if _has_findings else "○",
                      "Synthesized" if _has_findings else "Not yet synthesized",
                      active=False, done=_has_findings)
    _s4 = _stage_html("✓" if _has_findings else "○",
                      f"Findings ({len(existing)})" if _has_findings else "No findings yet",
                      active=False, done=_has_findings)

    _arrow = "<span style='color:#BDBDBD;font-size:0.85rem;padding:0 6px'> → </span>"
    st.markdown(
        f"<div style='background:#F5F5F5;border-radius:6px;padding:0.5rem 1rem;"
        f"margin-bottom:0.75rem'>{_s1}{_arrow}{_s2}{_arrow}{_s3}{_arrow}{_s4}</div>",
        unsafe_allow_html=True,
    )

    st.divider()

    # ── Per-document status ────────────────────────────────────────

    def _doc_status(name: str, is_contract: bool = False):
        """Returns (status_key, display_label, color, analysis_date_str)."""
        if is_contract:
            req = exchange_dir / f"{slug}-contract-requirements.json"
            if req.exists():
                return "analyzed", "✓ Analyzed", COLOR_GOOD, None
            return "not_run", "⏳ Not run", "#9E9E9E", None

        anal = _analysis_json_path(name)
        # "Failed" only when the last run explicitly marked it failed AND no JSON exists
        if name in failed_set and not anal.exists():
            return "failed", "✗ Failed", COLOR_UGLY, None
        if anal.exists():
            adate = None
            try:
                data  = json.loads(anal.read_text(encoding="utf-8"))
                adate = (data.get("analysis_date")
                         or data.get("date")
                         or data.get("timestamp"))
            except Exception:
                pass
            return "analyzed", "✓ Analyzed", COLOR_GOOD, adate
        if name in failed_set:
            return "failed", "✗ Failed", COLOR_UGLY, None
        return "not_run", "⏳ Not run", "#9E9E9E", None

    # ── Build queue ────────────────────────────────────────────────

    queue: list[dict] = []

    for name, meta in contract_ready.items():
        sk, sl, sc, ad = _doc_status(name, is_contract=True)
        queue.append({
            "name": name, "kind": "contract",
            "status_key": sk, "status_label": sl, "status_color": sc,
            "type_label": "Contract", "type_color": "#1565C0",
            "pages": meta.get("page_count", 0),
            "chunks": 1,
            "analysis_date": ad,
        })

    for name, meta in policy_ready.items():
        sk, sl, sc, ad = _doc_status(name)
        chunks = _chunk_estimate(name)
        pol_type = None
        ap = _analysis_json_path(name)
        if ap.exists():
            try:
                pol_type = json.loads(ap.read_text(encoding="utf-8")).get("policy_type")
            except Exception:
                pass
        queue.append({
            "name": name, "kind": "policy",
            "status_key": sk, "status_label": sl, "status_color": sc,
            "type_label": pol_type or "Policy",
            "type_color": COLOR_NAVY if pol_type else "#546E7A",
            "pages": meta.get("page_count", 0),
            "chunks": chunks,
            "analysis_date": ad,
        })

    # Checkbox defaults — only policies have checkboxes; contracts are always included
    for item in queue:
        if item["kind"] == "contract":
            continue
        key = f"_sel_{item['name']}"
        if key not in st.session_state:
            st.session_state[key] = item["status_key"] != "analyzed"

    # ── Action Bar ─────────────────────────────────────────────────

    lnk1, lnk2, lnk3, _ = st.columns([1, 1.3, 1.3, 5])
    with lnk1:
        if st.button("Select All", key="qs_all", use_container_width=True):
            for item in queue:
                if item["kind"] == "policy":
                    st.session_state[f"_sel_{item['name']}"] = True
            st.rerun()
    with lnk2:
        if st.button("Failed Only", key="qs_failed", use_container_width=True):
            for item in queue:
                if item["kind"] == "policy":
                    st.session_state[f"_sel_{item['name']}"] = (
                        item["status_key"] in ("failed", "not_run")
                    )
            st.rerun()
    with lnk3:
        if st.button("Deselect All", key="qs_none", use_container_width=True):
            for item in queue:
                if item["kind"] == "policy":
                    st.session_state[f"_sel_{item['name']}"] = False
            st.rerun()

    # Contracts always included; policies included only when checked
    selected = [
        item for item in queue
        if item["kind"] == "contract" or st.session_state.get(f"_sel_{item['name']}")
    ]
    total_chunks = sum(item["chunks"] for item in selected)

    est_col, btn_col = st.columns([3, 2])
    with est_col:
        if total_chunks:
            st.caption(
                f"~{total_chunks} Claude call{'s' if total_chunks != 1 else ''} estimated "
                f"for {len(selected)} selected item{'s' if len(selected) != 1 else ''}."
            )
            if total_chunks > 8:
                st.warning(
                    "⚠ This may exceed your daily token limit. "
                    "Consider running in batches."
                )
        else:
            st.caption("No items selected.")

    with btn_col:
        if st.button(
            "Read Selected",
            type="primary",
            use_container_width=True,
            key="run_sel_btn",
            disabled=(len(selected) == 0 or not policy_ready),
            help="Sends the selected policies to Claude to find coverage gaps, exclusions, and problem endorsements.",
        ):
            st.session_state["_run_audit"]     = "analyze"
            st.session_state["_selected_docs"] = [item["name"] for item in selected]
            st.rerun()

    st.divider()

    # ── Queue Table ────────────────────────────────────────────────

    COLS = [0.4, 3.4, 1.8, 1.4, 1.6, 1.4, 2.2]
    hdr  = st.columns(COLS)
    for col, label in zip(hdr, ["", "Document", "Type", "Size", "Status", "Analyzed", ""]):
        with col:
            if label:
                st.markdown(
                    f"<span style='font-size:0.75rem;font-weight:700;color:#666;"
                    f"text-transform:uppercase;letter-spacing:0.05em'>{label}</span>",
                    unsafe_allow_html=True,
                )

    for item in queue:
        row = st.columns(COLS)
        with row[0]:
            if item["kind"] == "policy":
                st.checkbox("", key=f"_sel_{item['name']}", label_visibility="collapsed")
        with row[1]:
            st.markdown(f"**{item['name']}**")
        with row[2]:
            bg = item["type_color"] + "22"
            _tl = item["type_label"]
            if len(_tl) > 20:
                _tl = _tl[:18].rstrip() + "…"
            st.markdown(
                f"<span style='background:{bg};color:{item['type_color']};"
                f"padding:2px 6px;border-radius:4px;font-size:0.75rem;"
                f"font-weight:600;display:inline-block;max-width:100%;"
                f"overflow:hidden;text-overflow:ellipsis;white-space:nowrap'>{_tl}</span>",
                unsafe_allow_html=True,
            )
        with row[3]:
            parts = []
            if item["pages"]:
                parts.append(f"{item['pages']} pg")
            n = item["chunks"]
            parts.append(f"~{n} chunk{'s' if n != 1 else ''}")
            st.caption("  ·  ".join(parts))
        with row[4]:
            st.markdown(
                f"<span style='color:{item['status_color']};font-weight:600;"
                f"font-size:0.83rem'>{item['status_label']}</span>",
                unsafe_allow_html=True,
            )
        with row[5]:
            ad = item["analysis_date"]
            if ad:
                try:
                    dt = datetime.fromisoformat(ad)
                    st.caption(dt.strftime("%b %d, %Y"))
                except Exception:
                    st.caption(str(ad)[:10])
            else:
                st.caption("—")
        with row[6]:
            if item["kind"] == "policy":
                _already_read = item["status_key"] == "analyzed"
                _btn_label = "Re-read Policy" if _already_read else "Read Policy"
                _btn_help  = (
                    "Re-runs the policy reading. Use if the policy was updated or the previous read failed."
                    if _already_read else
                    "Sends this policy to Claude to find coverage gaps, bad exclusions, and problematic endorsements. Takes 2\u201330 min."
                )
                if st.button(
                    _btn_label,
                    key=f"read_pol_{item['name']}",
                    use_container_width=True,
                    help=_btn_help,
                ):
                    st.session_state["_run_audit"]     = "analyze"
                    st.session_state["_selected_docs"] = [item["name"]]
                    st.rerun()

    # Not-extracted files
    n_skip = len(contract_skip) + len(policy_skip)
    if n_skip:
        with st.expander(
            f"{n_skip} file{'s' if n_skip != 1 else ''} not extracted — cannot analyze",
            expanded=False,
        ):
            for name in contract_skip + policy_skip:
                st.caption(f"○ {name}")

    if not policy_ready:
        st.error("At least one extracted policy is required.")

    st.stop()


# ══════════════════════════════════════════════════════════════════
#  ANALYSIS PIPELINE
# ══════════════════════════════════════════════════════════════════

run_mode      = st.session_state.pop("_run_audit")
selected_docs = st.session_state.pop("_selected_docs", None)
client_notes  = _client_notes()
standalone_mode = not contract_ready

# Clear any leftover rate-limit flag from a previous run
st.session_state.pop("_rate_limited", None)

# Determine what to process
if run_mode == "synthesize_now":
    selected_contracts: list[str] = []
    selected_policies:  list[str] = []
else:
    if selected_docs is None:
        selected_contracts = list(contract_ready.keys())
        selected_policies  = [
            n for n in policy_ready if not _analysis_json_path(n).exists()
        ]
    else:
        selected_contracts = [n for n in selected_docs if n in contract_ready]
        selected_policies  = [n for n in selected_docs if n in policy_ready]

# Track per-run results
policies_just_analyzed: set[str] = set()

n_steps   = max(len(selected_contracts) + len(selected_policies), 1)
step_done = 0

prog           = st.progress(0.0, text="Starting...")
_start_time    = time.time()
_timer_display = st.empty()
log            = st.container()

requirements_data: dict = {"requirements": []}
policy_analyses:   list = []
errors:            dict = {}


def _rate_limited() -> bool:
    return st.session_state.get("_rate_limited", False)

def _set_rate_limited() -> None:
    st.session_state["_rate_limited"] = True

def _persist_stage_findings(stage_name: str, findings_list: list) -> None:
    """Save findings to disk after a successful pipeline stage.

    Writes clients/<slug>/output/findings_<stage_name>.json (or findings.json
    for stage_name="final") atomically via tempfile + Path.replace, then
    updates audit-state.json with the findings list and stage marker.

    Pipeline architecture: each stage's output is persisted IMMEDIATELY after
    that stage's findings are produced, before any subsequent stage starts.
    If a later stage hangs/fails, prior stages' work is recoverable from disk.
    Added 2026-05-01 after the Precision Aero post-cross-policy-pass hang.

    stage_name -> stage label written to audit-state.json:
      synthesis    -> "synthesized"
      crosspolicy  -> "cross_policy_reviewed"
      final        -> "audited"   (writes findings.json without _<stage> suffix)
    """
    output_dir = client_path / "output"
    output_dir.mkdir(parents=True, exist_ok=True)
    if stage_name == "final":
        target = output_dir / "findings.json"
        stage_label = "audited"
    else:
        target = output_dir / f"findings_{stage_name}.json"
        stage_label = {
            "synthesis":   "synthesized",
            "crosspolicy": "cross_policy_reviewed",
        }.get(stage_name, stage_name)

    payload = {
        "client":        slug,
        "stage":         stage_label,
        "saved_at":      datetime.now().isoformat(),
        "finding_count": len(findings_list),
        "findings":      findings_list,
    }
    tmp = target.with_suffix(target.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    tmp.replace(target)

    # Incremental audit-state update so later stages crash safely.
    state["findings"] = findings_list
    state["stage"]    = stage_label
    ast.save(client_path, state)
    try:
        _log_sub(
            f"💾 Saved {len(findings_list)} findings -> {target.name} "
            f"(stage: {stage_label})"
        )
    except Exception:
        pass


def _elapsed_str() -> str:
    secs = int(time.time() - _start_time)
    return f"{secs // 60}m {secs % 60}s"

def _advance(msg: str) -> None:
    global step_done
    step_done += 1
    prog.progress(min(step_done / n_steps, 0.99), text=msg)
    _timer_display.caption(f"\u23f1 Elapsed: {_elapsed_str()}")

def _log_step(msg: str) -> None:
    with log:
        st.markdown(
            f"<span style='color:{COLOR_NAVY};font-weight:600'>{msg} "
            f"<span style='font-weight:400;color:#888'>\u23f1 {_elapsed_str()}</span></span>",
            unsafe_allow_html=True,
        )

def _log_sub(msg: str) -> None:
    with log:
        st.markdown(
            f"<span style='color:#555;font-size:0.875rem'>"
            f"&nbsp;&nbsp;&nbsp;{msg}</span>",
            unsafe_allow_html=True,
        )

def _add_error(name: str, msg: str) -> None:
    errors.setdefault(name, []).append(msg)


# ── Pre-load existing policy analysis JSONs ───────────────────────
if run_mode == "synthesize_now":
    # Glob all analysis JSONs — more robust than iterating policy_ready
    for _jf in sorted(exchange_dir.glob(f"{slug}-policy-*-analysis.json")):
        try:
            _pa = json.loads(_jf.read_text(encoding="utf-8"))
            _pa.setdefault("_source_file", _jf.name)
            policy_analyses.append(_pa)
        except Exception:
            pass
else:
    for _name in policy_ready:
        _ap = _analysis_json_path(_name)
        if _ap.exists():
            try:
                _pa = json.loads(_ap.read_text(encoding="utf-8"))
                _pa["_source_file"] = _name
                policy_analyses.append(_pa)
            except Exception:
                pass

# Pre-load saved contract requirements when not re-extracting
if not selected_contracts:
    _req = exchange_dir / f"{slug}-contract-requirements.json"
    if _req.exists():
        try:
            requirements_data = json.loads(_req.read_text(encoding="utf-8"))
        except Exception:
            pass


# ══════════════════════════════════════════════════════════════════
#  MODE B: SYNTHESIS ONLY  (Review Full Program)
# ══════════════════════════════════════════════════════════════════

if run_mode == "synthesize_now":

    n_loaded = len(policy_analyses)
    prog.progress(0.1, text=f"Loading {n_loaded} policy {'analysis' if n_loaded == 1 else 'analyses'}...")
    _log_step(
        f"Loaded {n_loaded} policy {'analysis' if n_loaded == 1 else 'analyses'} from disk."
    )

    if not policy_analyses:
        with log:
            st.error(
                "No policy analysis files found in ai-exchange/. "
                "Read at least 2 policies first, then run Review Full Program."
            )
        prog.progress(1.0, text="Done.")
        st.stop()

    has_crossref = len(policy_analyses) > 1
    findings     = []

    if len(policy_analyses) < len(policy_ready):
        with log:
            st.warning(
                f"Synthesizing from {n_loaded} of {len(policy_ready)} policies \u2014 "
                f"{len(policy_ready) - n_loaded} not yet analyzed. Findings may be incomplete."
            )

    # Synthesis call (1 of 2) - auto-chunked for large programs.
    #
    # 2026-05-01: replaced single-call synthesis with run_chunked_synthesis,
    # which auto-detects whether the all-policies prompt is small enough for
    # a single call (<130 KB) or needs chunking. The chunked path partitions
    # policies by coverage cluster (Core Liability / Pro+Cyber / ML / WC /
    # Property / Pollution / other), bin-packs into <=140 KB-prompt chunks,
    # and merges per-chunk findings with cross-chunk dedup of Bad/Ugly.
    # Background: v3e validation confirmed prompts >170 KB hit truncation /
    # silent hangs on the 2.1.121 binary; chunking keeps every call safe.
    prog.progress(0.25, text="Synthesizing findings...")
    _log_step("Synthesizing findings across all analyzed policies...")
    synthesis_reqs = {
        "client":        (requirements_data or {}).get("client"),
        "analysis_date": (requirements_data or {}).get("analysis_date"),
        "requirements":  (requirements_data or {}).get("requirements") or [],
    }

    def _synth_progress(label: str, frac: float) -> None:
        prog.progress(0.25 + 0.4 * frac, text=label)
        _log_sub(label)

    findings, synth_meta = run_chunked_synthesis(
        client_notes,
        slug,
        synthesis_reqs,
        policy_analyses,
        timeout=ANALYSIS_TIMEOUT,
        progress_callback=_synth_progress,
    )

    rate_limited = any("RATE_LIMIT" in (msg or "") for _, msg in synth_meta.get("errors", []))
    if rate_limited:
        _set_rate_limited()
        with log:
            st.error(
                "🚫 Daily usage limit reached during synthesis. "
                "Policy analyses are saved — try again tomorrow."
            )
        findings = state.get("findings", [])
    elif synth_meta.get("ok") and findings:
        with log:
            n_ugly   = sum(1 for f in findings if f.get("category") == "Ugly")
            n_bad    = sum(1 for f in findings if f.get("category") == "Bad")
            n_review = sum(1 for f in findings if f.get("category") in ("Review", "Needs Review"))
            n_good   = sum(1 for f in findings if f.get("category") == "Good")
            mode     = synth_meta.get("mode", "?")
            n_chunks = len(synth_meta.get("chunks") or [])
            n_dups   = len(synth_meta.get("duplicates_collapsed") or [])
            n_errs   = len(synth_meta.get("errors") or [])
            chunk_summary = (
                f" ({n_chunks} chunks; {n_dups} duplicates collapsed"
                f"{f'; {n_errs} chunk errors' if n_errs else ''})"
                if mode == "chunked" else ""
            )
            st.success(
                f"Synthesis complete — {len(findings)} findings: "
                f"{n_ugly} critical, {n_bad} bad, {n_review} review, {n_good} good"
                f"{chunk_summary}."
            )
            if mode == "chunked":
                _log_sub(
                    f"Chunked synthesis: {n_chunks} chunks "
                    f"({', '.join(c['name'] for c in synth_meta['chunks'])}); "
                    f"all-policies prompt would have been "
                    f"{synth_meta.get('all_policies_prompt_chars', 0):,} chars"
                )

        # Persist after-synthesis findings to disk before the cross-policy
        # pass starts. If the cross-policy pass hangs, synthesis output is
        # not lost.
        try:
            _persist_stage_findings("synthesis", findings)
        except Exception as _exc:
            _log_sub(f"(synthesis persistence warning: {_exc})")

    else:
        findings = state.get("findings", [])
        err_msgs = synth_meta.get("errors") or []
        with log:
            if err_msgs:
                first_err = err_msgs[0][1] if err_msgs else "(unknown)"
                raw_path = exchange_dir / f"{slug}-crossref-raw.txt"
                try:
                    raw_path.write_text(
                        json.dumps(synth_meta, indent=2, ensure_ascii=False)
                            if not isinstance(first_err, str) else first_err,
                        encoding="utf-8",
                    )
                except Exception:
                    pass
                if findings:
                    st.info(
                        f"Synthesis returned no findings ({len(err_msgs)} chunk error(s); "
                        f"first: {str(first_err)[:200]}). Kept {len(findings)} prior findings."
                    )
                else:
                    st.error(
                        f"Synthesis failed across all chunks. First error: {str(first_err)[:300]}"
                    )
            elif findings:
                st.info(f"Synthesis returned no findings. Kept {len(findings)} prior findings.")
            else:
                st.error("Synthesis returned no findings.")

    # Cross-policy intelligence pass (2 of 2)
    if has_crossref and findings and not _rate_limited():
        prog.progress(0.7, text="Running cross-policy intelligence pass...")
        _log_sub("Running cross-policy intelligence review...")
        time.sleep(RATE_LIMIT_DELAY)
        compressed = [
            {
                "id":                      f.get("id"),
                "requirement_type":        f.get("requirement_type"),
                "category":                f.get("category"),
                "policy_file":             f.get("policy_file"),
                "policy_page":             f.get("policy_page"),
                "likelihood":              f.get("likelihood"),
                "severity":                f.get("severity"),
                "risk_score":              f.get("risk_score"),
                "covered_by_other_policy": f.get("covered_by_other_policy"),
                "covered_by_which_policy": f.get("covered_by_which_policy"),
                "gap_description":         str(f.get("gap_description") or ""),
            }
            for f in findings
        ]
        cp_prompt  = build_crosspolicy_prompt(compressed, policy_analyses)
        ok, result = run_claude(cp_prompt, timeout=300)
        if ok:
            parsed = extract_json(result)
            if parsed and "findings" in parsed:
                updated = parsed["findings"]
                for f in updated:
                    like = f.get("likelihood")
                    sev  = f.get("severity")
                    if like and sev:
                        f["risk_score"] = int(like) * int(sev)
                    elif "risk_score" not in f:
                        f["risk_score"] = None
                findings = updated
                n_covered = sum(1 for f in findings if f.get("covered_by_other_policy"))
                with log:
                    st.success(
                        f"Cross-policy pass complete \u2014 "
                        f"{n_covered} finding{'s' if n_covered != 1 else ''} "
                        "found covered by other policies."
                    )

                # Persist after-cross-policy-pass findings before the matrix
                # pass starts. If the matrix pass hangs, cross-policy output
                # is not lost. (This is the failure mode that bit Precision
                # Aero on 2026-05-01.)
                try:
                    _persist_stage_findings("crosspolicy", findings)
                except Exception as _exc:
                    _log_sub(f"(cross-policy persistence warning: {_exc})")

            else:
                _add_error("Cross-policy pass", "JSON parse failed \u2014 using synthesis findings.")
                _log_sub("Cross-policy pass: JSON parse failed \u2014 using synthesis findings.")
        else:
            _add_error("Cross-policy pass", result[:200])
            _log_sub(f"Cross-policy pass failed: {result[:120]} \u2014 using synthesis findings.")

    # ── NEW Step 5: Cross-policy matrix pass (GAP-01/17/20/21) ─────
    if has_crossref and findings and not _rate_limited():
        prog.progress(0.85, text="Running cross-policy matrix pass (GAP-01/17/20/21)...")
        _log_sub("Building entity + contract-compliance + NOC matrices...")

        from core.cross_policy import (
            build_entity_matrix,
            build_contract_compliance_matrix,
            build_designated_entity_noc_matrix,
            load_universal_kb_block,
            build_cross_policy_matrix_prompt,
        )

        contracts_data = (requirements_data or {}).get("contracts", {}) or {}

        em = build_entity_matrix(policy_analyses)
        cm = build_contract_compliance_matrix(contracts_data, policy_analyses)
        nm = build_designated_entity_noc_matrix(contracts_data, policy_analyses)

        # Persist matrices regardless of whether the AI pass fires (per refinement).
        try:
            (exchange_dir / f"{slug}-entity-matrix.json").write_text(
                json.dumps(em, indent=2, ensure_ascii=False), encoding="utf-8")
            (exchange_dir / f"{slug}-compliance-matrix.json").write_text(
                json.dumps(cm, indent=2, ensure_ascii=False), encoding="utf-8")
            (exchange_dir / f"{slug}-noc-matrix.json").write_text(
                json.dumps(nm, indent=2, ensure_ascii=False), encoding="utf-8")
        except Exception as exc:
            _log_sub(f"(matrix persistence warning: {exc})")

        # Flagship Maricopa Auto cell — explicit log line per refinement 1
        for _row in cm.get("rows", []):
            if ("maricopa" in (_row.get("contract") or "").lower()
                    and _row.get("coverage_line") == "auto_liability"):
                for _src, _cell in (_row.get("policy_check") or {}).items():
                    req_val = _row.get("requirement_summary", "(unknown)")
                    actual  = _cell.get("primary_limit_value")
                    actual_s = f"${actual:,}" if isinstance(actual, (int, float)) else "n/a"
                    umb = _row.get("umbrella_may_satisfy_minimum")
                    umb_s = "permitted" if umb else "barred"
                    _log_sub(
                        f"Flagship test — Maricopa Auto: {req_val} required, "
                        f"{actual_s} actual, umbrella {umb_s}, "
                        f"verdict: {_cell.get('verdict')}."
                    )
                break

        n_inc   = len(em.get("inconsistencies", []))
        s_summ  = cm.get("summary", {}) or {}
        n_short = s_summ.get("shortfall", 0)
        n_viol  = s_summ.get("violation", 0)
        n_miss  = s_summ.get("missing_policy", 0)
        n_asym  = len(nm.get("asymmetries", []))
        _log_sub(
            f"Matrix construction: {n_inc} entity inconsistencies, "
            f"{n_short} shortfalls + {n_viol} violations + {n_miss} missing-policy gaps, "
            f"{n_asym} NOC asymmetries."
        )

        if n_inc + n_short + n_viol + n_miss + n_asym == 0:
            _log_sub("No cross-cutting defects in matrices — skipping AI pass.")
        else:
            time.sleep(RATE_LIMIT_DELAY)
            kb        = load_universal_kb_block()
            cp_prompt = build_cross_policy_matrix_prompt(
                client_notes, slug, em, cm, nm, kb, findings, policy_analyses, contracts_data,
            )
            ok, result = run_claude(cp_prompt, timeout=ANALYSIS_TIMEOUT)
            if _is_rate_limit(ok, result):
                _set_rate_limited()
                _add_error("Cross-policy matrix pass", "Skipped — usage limit reached.")
            elif ok:
                parsed = extract_json(result)
                if parsed and "findings" in parsed:
                    new_findings   = parsed["findings"]
                    existing_keys  = {
                        (f.get("requirement_type"), f.get("policy_file"), f.get("policy_page"))
                        for f in findings
                    }
                    added = 0
                    for nf in new_findings:
                        key = (nf.get("requirement_type"), nf.get("policy_file"), nf.get("policy_page"))
                        if key in existing_keys:
                            continue
                        nf.setdefault("tags", [])
                        if "cross-policy-matrix" not in nf["tags"]:
                            nf["tags"].append("cross-policy-matrix")
                        like, sev = nf.get("likelihood"), nf.get("severity")
                        if like and sev:
                            nf["risk_score"] = int(like) * int(sev)
                        elif "risk_score" not in nf:
                            nf["risk_score"] = None
                        findings.append(nf)
                        added += 1
                    with log:
                        st.success(
                            f"Cross-policy matrix pass: {added} new finding"
                            f"{'s' if added != 1 else ''} added."
                        )
                else:
                    raw_path = exchange_dir / f"{slug}-crosspolicy-matrix-raw.txt"
                    try:
                        raw_path.write_text(result or "", encoding="utf-8")
                    except Exception:
                        pass
                    _add_error("Cross-policy matrix pass", "JSON parse failed.")
                    _log_sub(
                        f"Cross-policy matrix pass: JSON parse failed, "
                        f"raw saved to {raw_path.name}."
                    )
            else:
                _add_error("Cross-policy matrix pass", result[:200])
                _log_sub(f"Cross-policy matrix pass failed: {result[:120]}.")
    # === Persist final findings ===
    if findings:
        # Compute auxiliary state (prior_runs, policy_type_counts) BEFORE the
        # final save so audit-state.json captures everything in one atomic write.
        prior_findings = state.get("findings", [])
        if prior_findings and prior_findings is not findings:
            prior_runs = state.setdefault("prior_runs", [])
            prior_runs.append({
                "timestamp":     datetime.now().isoformat(),
                "finding_count": len(prior_findings),
                "ugly_count":    sum(1 for f in prior_findings if f.get("category") == "Ugly"),
                "bad_count":     sum(1 for f in prior_findings if f.get("category") == "Bad"),
                "good_count":    sum(1 for f in prior_findings if f.get("category") == "Good"),
                "findings":      prior_findings,
            })
            state["prior_runs"] = prior_runs[-5:]
        policy_type_counts: dict = {}
        for pa in policy_analyses:
            pt = pa.get("policy_type") or "Unknown"
            policy_type_counts[pt] = policy_type_counts.get(pt, 0) + 1
        state["policy_type_counts"] = policy_type_counts
        state["last_analysis_date"] = datetime.now().isoformat()

        # Final canonical save: writes clients/<slug>/output/findings.json
        # AND updates audit-state.json with stage="audited" + findings list.
        try:
            _persist_stage_findings("final", findings)
        except Exception as _exc:
            _log_sub(f"(final persistence warning: {_exc})")

        # Legacy ai-exchange copy retained for any downstream tooling that
        # reads it; the canonical path is now output/findings.json.
        try:
            (exchange_dir / f"{slug}-findings.json").write_text(
                json.dumps({"client": slug, "findings": findings}, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
        except Exception:
            pass
    else:
        ast.save(client_path, state)
    prog.progress(1.0, text=f"Done. Total time: {_elapsed_str()}")

    # ── Final status ───────────────────────────────────────────────
    st.markdown("<br>", unsafe_allow_html=True)
    st.divider()
    _render_errors(errors)

    findings = state.get("findings", [])
    if findings:
        ugly_n = sum(1 for f in findings if f.get("category") == "Ugly")
        bad_n  = sum(1 for f in findings if f.get("category") == "Bad")
        good_n = sum(1 for f in findings if f.get("category") == "Good")
        st.success(
            f"**{len(findings)} findings generated** \u2014 "
            f"{ugly_n} critical, {bad_n} bad, {good_n} good. Ready for review."
        )
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("View Findings Dashboard", type="primary", key="goto_findings_btn"):
            st.switch_page("pages/3_Findings_Dashboard.py")
        if st.button("Back to Queue", key="back_queue_after_synth"):
            st.session_state.pop("_rate_limited", None)
            st.rerun()
    else:
        st.error("No findings were generated. Check the warnings above.")
        if st.button("Back to Queue", key="back_queue_final"):
            st.session_state.pop("_rate_limited", None)
            st.rerun()

    st.stop()


# ══════════════════════════════════════════════════════════════════
#  MODE A: ANALYZE SELECTED POLICIES
# ══════════════════════════════════════════════════════════════════

if run_mode == "analyze":

    # ── Step 1: Extract contract requirements (one Claude call per contract) ─
    if selected_contracts and not _rate_limited():
        _log_step(
            f"Extracting contract requirements from "
            f"{len(selected_contracts)} contract{'s' if len(selected_contracts) != 1 else ''}..."
        )

        per_contract_data: dict = {}    # filename → structured contract result
        flat_requirements:  list = []   # legacy aggregated requirements list

        for c_idx, name in enumerate(selected_contracts):
            if _rate_limited():
                _add_error(name, "Skipped — daily usage limit reached.")
                break

            text = _read_extracted(name)
            if not text:
                with log:
                    st.warning(f"{name}: extracted text not found — skipping.")
                _add_error(name, "Extracted file not found.")
                continue

            _log_sub(f"Contract {c_idx + 1}/{len(selected_contracts)}: {name}...")
            prompt     = build_contract_prompt(name, text, client_notes)
            ok, result = run_claude(prompt, timeout=ANALYSIS_TIMEOUT)

            if _is_rate_limit(ok, result):
                _set_rate_limited()
                _add_error(name, "Skipped — daily usage limit reached.")
                break
            elif ok:
                parsed = extract_json(result)
                if parsed:
                    parsed.setdefault("source_file", name)
                    per_contract_data[name] = parsed
                    flat_requirements.extend(parsed.get("requirements", []) or [])
                    has_ip = parsed.get("has_insurance_provisions", True)
                    by_cov = parsed.get("by_coverage") or {}
                    n_lines = sum(1 for v in by_cov.values() if v)
                    n_reqs  = len(parsed.get("requirements", []) or [])
                    with log:
                        if has_ip is False or (n_lines == 0 and n_reqs == 0):
                            st.info(
                                f"{name}: no insurance provisions in this document "
                                "(e.g., amendment without insurance schedule)."
                            )
                        else:
                            st.success(
                                f"{name}: {n_lines} coverage line{'s' if n_lines != 1 else ''} "
                                f"+ {n_reqs} requirement{'s' if n_reqs != 1 else ''} extracted."
                            )
                else:
                    raw_path = exchange_dir / f"{slug}-contract-{Path(name).stem}-raw.txt"
                    try:
                        raw_path.write_text(result or "", encoding="utf-8")
                    except Exception:
                        pass
                    with log:
                        st.warning(
                            f"{name}: could not parse JSON. "
                            f"Raw response saved to {raw_path.name}. Continuing."
                        )
                    _add_error(name, "JSON parse failed.")
            else:
                with log:
                    st.warning(f"{name}: {result[:200]}")
                _add_error(name, result[:400])

            if c_idx < len(selected_contracts) - 1 and not _rate_limited():
                time.sleep(RATE_LIMIT_DELAY)

        # Aggregate into the requirements_data structure used downstream
        if per_contract_data:
            requirements_data = {
                "client":        slug,
                "analysis_date": datetime.now().date().isoformat(),
                "contracts":     per_contract_data,    # NEW: per-contract structured
                "requirements":  flat_requirements,    # legacy flat list (for build_crossref_prompt)
            }
            (exchange_dir / f"{slug}-contract-requirements.json").write_text(
                json.dumps(requirements_data, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
            with log:
                n_c = len(per_contract_data)
                n_r = len(flat_requirements)
                st.success(
                    f"Contract extraction complete: {n_c} contract{'s' if n_c != 1 else ''}, "
                    f"{n_r} total requirement{'s' if n_r != 1 else ''}."
                )

        _advance("Contract requirements done.")
        if not _rate_limited():
            time.sleep(RATE_LIMIT_DELAY)

    # ── Step 2: Analyze each selected policy ──────────────────────
    for idx, name in enumerate(selected_policies):
        if _rate_limited():
            _add_error(name, "Skipped \u2014 daily usage limit reached.")
            break

        suffix = " (standalone)" if standalone_mode else ""
        _log_step(f"Analyzing {name}{suffix}...")
        pol_start = time.time()

        def _pol_elapsed(start: float = pol_start) -> str:
            secs = int(time.time() - start)
            return f"{secs // 60}m {secs % 60}s"

        try:
            text = _read_extracted(name)
            if not text:
                with log:
                    st.warning(f"{name}: extracted text not found \u2014 skipping.")
                _add_error(name, "Extracted file not found.")
                _advance(f"Skipped {name}.")
                continue

            chunks = chunk_text(text)

            # ── Single-chunk path ──────────────────────────────────
            if len(chunks) == 1:
                if standalone_mode:
                    prompt = build_standalone_policy_prompt(name, text, client_notes)
                else:
                    prompt = build_policy_prompt(name, text, client_notes, requirements_data)

                ok, result = run_claude(prompt, timeout=ANALYSIS_TIMEOUT)

                if _is_rate_limit(ok, result):
                    _set_rate_limited()
                    _add_error(name, "Skipped \u2014 daily usage limit reached.")
                    break
                elif ok:
                    parsed = extract_json(result)
                    if parsed:
                        parsed["_source_file"] = name
                        policy_analyses[:] = [
                            pa for pa in policy_analyses if pa.get("_source_file") != name
                        ]
                        policy_analyses.append(parsed)
                        (exchange_dir / f"{slug}-policy-{Path(name).stem}-analysis.json").write_text(
                            json.dumps(parsed, indent=2, ensure_ascii=False), encoding="utf-8"
                        )
                        policies_just_analyzed.add(name)
                        with log:
                            ptype = parsed.get("policy_type", "policy")
                            st.success(f"{name}: {ptype} analyzed in {_pol_elapsed()}.")
                    else:
                        with log:
                            st.warning(f"{name}: could not parse analysis JSON \u2014 skipping.")
                        _add_error(name, "JSON parse failed.")
                else:
                    with log:
                        st.warning(f"{name}: {result[:200]} \u2014 skipping.")
                    _add_error(name, result[:400])

            # ── Multi-chunk path ───────────────────────────────────
            else:
                n_chunks = len(chunks)
                _log_sub(
                    f"{name}: {len(text):,} chars \u2014 {n_chunks} chunks "
                    f"({', '.join(lbl for _, lbl in chunks)})"
                )
                chunk_analyses: list = []
                chunk_errors:   list = []

                for chunk_idx, (chunk_t, page_range) in enumerate(chunks):
                    if _rate_limited():
                        chunk_errors.append(f"Chunk {chunk_idx + 1}: skipped (usage limit)")
                        break

                    _log_sub(
                        f"Chunk {chunk_idx + 1}/{n_chunks}: {page_range} "
                        f"({len(chunk_t):,} chars) \u23f1 {_pol_elapsed()}..."
                    )
                    req_arg = None if standalone_mode else requirements_data
                    prompt  = build_policy_chunk_prompt(
                        name, chunk_t, page_range, client_notes, req_arg
                    )
                    ok, result = run_claude(prompt, timeout=ANALYSIS_TIMEOUT)

                    if _is_rate_limit(ok, result):
                        _set_rate_limited()
                        chunk_errors.append(f"Chunk {chunk_idx + 1}: usage limit reached")
                        break
                    elif ok:
                        parsed = extract_json(result)
                        if parsed:
                            chunk_analyses.append(parsed)
                        else:
                            chunk_errors.append(f"Chunk {chunk_idx + 1}/{n_chunks}: JSON parse failed")
                            _log_sub(f"Chunk {chunk_idx + 1}: JSON parse failed \u2014 continuing.")
                    else:
                        chunk_errors.append(f"Chunk {chunk_idx + 1}/{n_chunks}: {result[:120]}")
                        _log_sub(f"Chunk {chunk_idx + 1}: {result[:120]} \u2014 continuing.")

                    if chunk_idx < n_chunks - 1 and not _rate_limited():
                        time.sleep(RATE_LIMIT_DELAY)

                if chunk_errors:
                    n_fail = len(chunk_errors)
                    _add_error(name, f"{n_fail}/{n_chunks} chunk{'s' if n_fail != 1 else ''} failed")
                    for ce in chunk_errors:
                        _add_error(name, f"  \u21b3 {ce}")

                if chunk_analyses and not _rate_limited():
                    _log_sub(f"Merging {len(chunk_analyses)}/{n_chunks} chunk analyses \u23f1 {_pol_elapsed()}...")
                    time.sleep(RATE_LIMIT_DELAY)
                    merge_prompt = build_policy_merge_prompt(name, chunk_analyses, client_notes)
                    ok, result   = run_claude(merge_prompt, timeout=ANALYSIS_TIMEOUT)

                    if _is_rate_limit(ok, result):
                        _set_rate_limited()
                        _add_error(name, "Merge call: usage limit reached.")
                    elif ok:
                        parsed = extract_json(result)
                        if parsed:
                            parsed["_source_file"] = name
                            policy_analyses[:] = [
                                pa for pa in policy_analyses if pa.get("_source_file") != name
                            ]
                            policy_analyses.append(parsed)
                            (exchange_dir / f"{slug}-policy-{Path(name).stem}-analysis.json").write_text(
                                json.dumps(parsed, indent=2, ensure_ascii=False), encoding="utf-8"
                            )
                            policies_just_analyzed.add(name)
                            with log:
                                ptype = parsed.get("policy_type", "policy")
                                st.success(
                                    f"{name}: {ptype} analyzed "
                                    f"({n_chunks} chunks merged) in {_pol_elapsed()}."
                                )
                        else:
                            with log:
                                st.warning(f"{name}: merge JSON parse failed \u2014 skipping.")
                            _add_error(name, "Merge JSON parse failed.")
                    else:
                        with log:
                            st.warning(f"{name}: merge failed: {result[:200]}")
                        _add_error(name, f"Merge failed: {result[:200]}")

                elif not chunk_analyses:
                    with log:
                        st.warning(f"{name}: all chunks failed \u2014 skipping.")

        except Exception as exc:
            with log:
                st.warning(f"{name}: unexpected error ({exc}) \u2014 skipping.")
            _add_error(name, f"Unexpected error: {exc}")

        _advance(f"{name} done.")

        if idx < len(selected_policies) - 1 and not _rate_limited():
            time.sleep(RATE_LIMIT_DELAY)

    # ── Save failed_policies ───────────────────────────────────────
    new_failed = [n for n in policy_ready if not _analysis_json_path(n).exists()]
    state["failed_policies"] = new_failed
    ast.save(client_path, state)

    prog.progress(1.0, text=f"Done. Total time: {_elapsed_str()}")
    st.markdown("<br>", unsafe_allow_html=True)
    st.divider()

    # ── Post-analysis summary ──────────────────────────────────────
    n_total    = len(policy_ready)
    n_analyzed = n_total - len(new_failed)
    all_done   = (n_analyzed == n_total)

    # Rate-limit banner (if hit)
    if _rate_limited():
        n_skipped = len(new_failed)
        st.error(
            f"\U0001f6ab Daily usage limit reached \u2014 resets at 2pm Phoenix time. "
            f"{len(policies_just_analyzed)} polic{'y' if len(policies_just_analyzed) == 1 else 'ies'} "
            f"completed this run, {n_skipped} still not analyzed. "
            "Come back after reset and use \u2018Read Selected\u2019 to run only the remaining policies."
        )

    # Per-policy status list
    st.markdown("**Policy analysis results:**")
    for name in policy_ready:
        if name in policies_just_analyzed:
            st.markdown(
                f"<span style='color:{COLOR_GOOD}'>\u2705</span> **{name}** \u2014 "
                f"<span style='color:{COLOR_GOOD}'>analyzed this run</span>",
                unsafe_allow_html=True,
            )
        elif _analysis_json_path(name).exists():
            st.markdown(
                f"<span style='color:{COLOR_GOOD}'>\u2713</span> {name} \u2014 "
                f"<span style='color:#888'>already analyzed</span>",
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                f"<span style='color:{COLOR_UGLY}'>\u2717</span> **{name}** \u2014 "
                f"<span style='color:{COLOR_UGLY}'>not analyzed</span>",
                unsafe_allow_html=True,
            )

    st.markdown("<br>", unsafe_allow_html=True)
    _render_errors(errors)

    # Synthesize button block
    if n_analyzed > 0:
        if all_done:
            st.success(
                f"\u2705 All {n_total} {'policy' if n_total == 1 else 'policies'} analyzed. "
                "Ready to synthesize and generate findings."
            )
        else:
            n_missing = len(new_failed)
            st.warning(
                f"**{n_analyzed} of {n_total} {'policy' if n_total == 1 else 'policies'} analyzed.** "
                f"{n_missing} still missing \u2014 findings will be incomplete without them. "
                "You can synthesize now or analyze the remaining policies first."
            )

        sc1, sc2, _ = st.columns([2.5, 1.5, 3])
        with sc1:
            if st.button(
                "Review Full Program",
                type="primary",
                key="synth_after_analysis",
                use_container_width=True,
                help="Compares all policies together to check if gaps in one policy are covered by another. Run this after all policies are read.",
            ):
                st.session_state["_run_audit"]     = "synthesize_now"
                st.session_state["_selected_docs"] = []
                st.rerun()
        with sc2:
            if st.button("Back to Queue", key="back_queue_post_analysis", use_container_width=True):
                st.session_state.pop("_rate_limited", None)
                st.rerun()
    else:
        st.error("No policies were successfully analyzed.")
        if st.button("Back to Queue", key="back_queue_all_failed"):
            st.session_state.pop("_rate_limited", None)
            st.rerun()

    st.stop()
