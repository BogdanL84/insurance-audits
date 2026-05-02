"""
4_Findings_Dashboard.py — View, filter, and edit imported findings.

Features:
- Program Overview tab (policy summary table) — FEATURE 2
- Finding cards with Edit, Delete, Mark Reviewed — FEATURE 1
- + Add Finding button with manual ID generation — FEATURE 1
- Reviewed X of Y counter — FEATURE 1
- Interactive 5×5 risk matrix
- History tab with prior run comparisons — FEATURE 4
"""

import sys
import json
import re
import html as _html
from pathlib import Path
from datetime import datetime
sys.path.insert(0, str(Path(__file__).parent.parent))

import streamlit as st

st.set_page_config(
    page_title="Findings — Insurance Audit",
    layout="wide",
    initial_sidebar_state="expanded",
)

from config import (
    CLIENTS_DIR, COLOR_GOOD, COLOR_BAD, COLOR_UGLY, COLOR_NAVY, COLOR_AMBER,
    SCORE_LOW, SCORE_HIGH,
)

COLOR_REVIEW = "#d4a017"  # amber/gold for Review findings
from core import audit_state as ast
from core.pdf_annotator import annotate_all_policies
from utils import (
    render_sidebar, require_client, render_progress_bar,
    inject_css, render_breadcrumb, category_badge,
)

inject_css()
render_sidebar()

slug, client_path, state = require_client()
display_name = state.get("display_name", slug)

render_breadcrumb(display_name, "Findings Dashboard")
st.title("Findings Dashboard")
st.caption(f"**{display_name}**")
render_progress_bar(state.get("stage", "findings_imported"), active_step=3)
st.divider()


# ── Orphan-findings cleanup ─────────────────────────────────────────
# Remove findings whose source policy file is no longer in the policy library.
# Preserves:
#   - PROGRAM-level findings (cross-policy matrix output, no single PDF home)
#   - Findings tagged "cross-policy-matrix" (Stage 1 cross-policy findings)
#   - Multi-policy findings whose policy_file is a semicolon-delimited list of
#     filenames — keep if AT LEAST ONE piece is in the registered library.
_uploaded_filenames = set(state.get("policies", {}).keys())
_all_findings = state.get("findings", [])


def _is_orphan(f: dict, uploaded: set) -> bool:
    pf = (f.get("policy_file") or "").strip()
    if not pf:
        return False  # No policy_file claim — manual finding or unattached
    # Program-level findings are legitimate (cross-policy matrix output)
    if pf.upper() == "PROGRAM":
        return False
    # Cross-policy matrix findings preserved regardless of policy_file shape
    if "cross-policy-matrix" in (f.get("tags") or []):
        return False
    # Split semicolon-delimited multi-policy strings; keep if ANY piece is valid
    pieces = [Path(p.strip()).name for p in pf.split(";") if p.strip()]
    if any(p in uploaded for p in pieces):
        return False
    return True


if _all_findings:
    _orphaned = [f for f in _all_findings if _is_orphan(f, _uploaded_filenames)]
    if _orphaned:
        _removed_names = {f["policy_file"] for f in _orphaned}
        state["findings"] = [f for f in _all_findings if f not in _orphaned]
        ast.refresh_stage(state)
        ast.save(client_path, state)
        _n = len(_orphaned)
        _files = ", ".join(sorted(_removed_names))
        st.info(
            f"{_n} finding{'s' if _n != 1 else ''} removed — "
            f"source {'files' if _n != 1 else 'file'} no longer in policy library: {_files}"
        )


# ── Sort helpers ────────────────────────────────────────────────────
def sort_findings_by_risk(flist: list) -> list:
    def _key(f):
        cat = f.get("category", "Good")
        # Treat "Review" and "Needs Review" as the same category
        if cat == "Needs Review":
            cat = "Review"
        order = {"Ugly": 0, "Bad": 1, "Review": 2, "Good": 3}.get(cat, 4)
        return (order, -(f.get("risk_score") or 0))
    return sorted(flist, key=_key)


def severity_label(score) -> str:
    if score is None:
        return ""
    if score <= 5:   return "Low"
    if score <= 14:  return "Medium"
    if score <= 19:  return "High"
    return "Critical"


def _next_manual_id(findings: list) -> str:
    """Find the next available manual-NNN id."""
    pat = re.compile(r"^manual-(\d+)$")
    nums = []
    for f in findings:
        m = pat.match(str(f.get("id", "")))
        if m:
            nums.append(int(m.group(1)))
    n = max(nums, default=0) + 1
    return f"manual-{n:03d}"


# ── Load findings ───────────────────────────────────────────────────
findings = state.get("findings", [])

ugly_findings   = sort_findings_by_risk([f for f in findings if f.get("category") == "Ugly"])
bad_findings    = sort_findings_by_risk([f for f in findings if f.get("category") == "Bad"])
review_findings = sort_findings_by_risk([f for f in findings if f.get("category") in ("Review", "Needs Review")])
good_findings   = [f for f in findings if f.get("category") == "Good"]
all_sorted      = sort_findings_by_risk(findings)

reviewed_ct = sum(1 for f in findings if f.get("reviewed"))


# ══════════════════════════════════════════════════════════════════
#  TOP BAR: SUMMARY METRICS + REVIEW COUNTER + ADD FINDING
# ══════════════════════════════════════════════════════════════════
if findings:
    risk_scores = [f.get("risk_score") for f in findings if f.get("risk_score") is not None]
    avg_score   = round(sum(risk_scores) / len(risk_scores), 1) if risk_scores else 0
    max_score   = max(risk_scores) if risk_scores else 0

    m1, m2, m3, m4, m5, m6, m7 = st.columns(7)
    m1.metric("Total Findings",          len(findings))
    m2.metric("Critical (Ugly)",         len(ugly_findings))
    m3.metric("Needs Attention (Bad)",   len(bad_findings))
    m4.metric("Needs Review",            len(review_findings))
    m5.metric("Compliant (Good)",        len(good_findings))
    m6.metric("Avg Risk Score",          avg_score, help=f"Max: {max_score}/25")
    m7.metric("Reviewed",                f"{reviewed_ct}/{len(findings)}")

    # Reviewed progress bar
    if findings:
        pct          = reviewed_ct / len(findings)
        span_color   = COLOR_GOOD if pct == 1.0 else "#555"
        pct_display  = f"{pct*100:.0f}"
        st.markdown(
            f"<div style='display:flex;align-items:center;gap:0.5rem;margin-top:-0.75rem;"
            f"margin-bottom:0.5rem;font-size:0.8rem;color:#555'>"
            f"<span>Review progress:</span>"
            f"<div style='flex:1;background:#E0E0E0;border-radius:4px;height:8px;max-width:300px'>"
            f"<div style='width:{pct_display}%;background:{COLOR_GOOD};height:8px;"
            f"border-radius:4px'></div></div>"
            f"<span style='color:{span_color}'>"
            f"{reviewed_ct}/{len(findings)} reviewed</span>"
            f"</div>",
            unsafe_allow_html=True,
        )
    st.divider()


# ══════════════════════════════════════════════════════════════════
#  + ADD FINDING
# ══════════════════════════════════════════════════════════════════
add_open_key = "add_finding_open"

add_col, _ = st.columns([2, 5])
with add_col:
    if st.button("+ Add Finding", key="add_finding_btn", type="primary" if not findings else "secondary"):
        st.session_state[add_open_key] = not st.session_state.get(add_open_key, False)
        st.rerun()

if st.session_state.get(add_open_key, False):
    st.markdown("### Add New Finding")
    with st.form("add_finding_form"):
        af_cat   = st.selectbox("Category", ["Ugly", "Bad", "Needs Review", "Good", "Informational"],
                                index=1, key="af_cat")
        af_title = st.text_input("Finding Title / Requirement Type", key="af_title",
                                 placeholder="e.g. Additional Insured — Completed Operations")

        ac1, ac2 = st.columns(2)
        with ac1:
            af_like = st.selectbox("Likelihood (1-5)", [None,1,2,3,4,5],
                                   format_func=lambda x: "—" if x is None else str(x),
                                   key="af_like")
        with ac2:
            af_sev  = st.selectbox("Severity (1-5)", [None,1,2,3,4,5],
                                   format_func=lambda x: "—" if x is None else str(x),
                                   key="af_sev")

        af_gap    = st.text_area("Technical Analysis", height=100, key="af_gap")
        af_plain  = st.text_area("Plain English Explanation (CFO-friendly)", height=80, key="af_plain")
        af_rec    = st.text_area("Recommendation", height=70, key="af_rec")

        ac3, ac4 = st.columns(2)
        with ac3:
            af_pfile  = st.text_input("Policy Filename", key="af_pfile",
                                      placeholder="policy.pdf")
            af_ppage  = st.text_input("Policy Page Reference", key="af_ppage",
                                      placeholder="Page 42 of 89")
        with ac4:
            af_cfile  = st.text_input("Contract Filename", key="af_cfile",
                                      placeholder="contract.pdf")
            af_cpage  = st.text_input("Contract Page Reference", key="af_cpage",
                                      placeholder="Section 12.3, Page 8")

        af_tags_str = st.text_input("Tags (comma-separated)", key="af_tags",
                                    placeholder="e.g. additional-insured, completed-ops")

        sb1, sb2, _ = st.columns([1, 1, 4])
        with sb1:
            do_add    = st.form_submit_button("Add Finding", type="primary",
                                              use_container_width=True)
        with sb2:
            do_cancel = st.form_submit_button("Cancel", use_container_width=True)

    if do_add:
        if not af_title.strip():
            st.error("Finding title is required.")
        else:
            tags = [t.strip() for t in af_tags_str.split(",") if t.strip()]
            risk_score = (af_like * af_sev) if (af_like and af_sev) else None
            new_finding = {
                "id":               _next_manual_id(state.get("findings", [])),
                "requirement_type": af_title.strip(),
                "category":         af_cat,
                "likelihood":       af_like,
                "severity":         af_sev,
                "risk_score":       risk_score,
                "gap_description":  af_gap.strip(),
                "plain_english":    af_plain.strip(),
                "recommendation":   af_rec.strip(),
                "policy_file":      af_pfile.strip(),
                "policy_page":      af_ppage.strip(),
                "contract_file":    af_cfile.strip(),
                "contract_page":    af_cpage.strip(),
                "tags":             tags,
                "reviewed":         False,
                "manual":           True,
            }
            state.setdefault("findings", []).append(new_finding)
            ast.refresh_stage(state)
            ast.save(client_path, state)
            del st.session_state[add_open_key]
            st.rerun()

    if do_cancel:
        del st.session_state[add_open_key]
        st.rerun()

st.markdown("<br>", unsafe_allow_html=True)




# ══════════════════════════════════════════════════════════════════
#  TABS
# ══════════════════════════════════════════════════════════════════
tab_overview, tab_ugly, tab_bad, tab_review, tab_good, tab_all, tab_by_policy, tab_what_changed, tab_history = st.tabs([
    "Program Overview",
    f"Critical ({len(ugly_findings)})",
    f"Bad ({len(bad_findings)})",
    f"⚠ Needs Review ({len(review_findings)})",
    f"Good ({len(good_findings)})",
    f"All ({len(findings)})",
    "By Policy",
    "What Changed",
    "History",
])


# ══════════════════════════════════════════════════════════════════
#  TAB 1 — PROGRAM OVERVIEW (FEATURE 2)
# ══════════════════════════════════════════════════════════════════
with tab_overview:
    st.subheader("Insurance Program Overview")
    st.caption(
        "Summary of all policies analyzed. Extracted from policy declaration pages."
    )
    st.markdown("<br>", unsafe_allow_html=True)

    exchange_dir = client_path / "ai-exchange"
    policies_dir = client_path / "policies"
    output_dir   = client_path / "output"

    # Load policy analyses from ai-exchange/
    policy_analyses = []
    if exchange_dir.exists():
        for p in sorted(exchange_dir.glob(f"{slug}-policy-*-analysis.json")):
            try:
                pa = json.loads(p.read_text(encoding="utf-8", errors="replace"))
                pa["_source_filename"] = p.name
                policy_analyses.append(pa)
            except Exception:
                pass

    if not policy_analyses:
        st.info(
            "No policy analyses found. Run the audit analysis first to populate this view."
        )
        if st.button("Run Analysis", type="primary", key="overview_run_analysis"):
            st.switch_page("pages/2_Document_Intake.py")
    else:
        # Color map by policy type keyword
        _TYPE_COLORS = {
            "general liability":    "#1565C0",
            "workers":              "#2E7D32",
            "auto":                 "#E65100",
            "umbrella":             "#6A1B9A",
            "excess":               "#6A1B9A",
            "professional":         "#00695C",
            "errors":               "#00695C",
            "e&o":                  "#00695C",
            "cyber":                "#0277BD",
            "directors":            "#4527A0",
            "d&o":                  "#4527A0",
            "employment":           "#AD1457",
            "epli":                 "#AD1457",
            "crime":                "#37474F",
            "property":             "#558B2F",
            "pollution":            "#5D4037",
            "inland marine":        "#795548",
            "management liability": "#4527A0",
        }

        def _type_color(policy_type: str) -> str:
            pt = (policy_type or "").lower()
            for key, color in _TYPE_COLORS.items():
                if key in pt:
                    return color
            return "#9E9E9E"

        def _fmt_limit(val) -> str:
            if not val:
                return "—"
            try:
                n = int(val)
                if n >= 1_000_000:
                    return f"${n/1_000_000:.1f}M"
                if n >= 1_000:
                    return f"${n/1_000:.0f}K"
                return f"${n:,}"
            except (TypeError, ValueError):
                return str(val)

        carriers  = set()
        premiums  = []
        row_htmls = []

        header = (
            "<tr style='background:#F5F5F5;font-size:0.75rem;font-weight:700;"
            "color:#555;text-transform:uppercase;letter-spacing:0.04em'>"
            "<th style='padding:8px 12px;text-align:left;border-bottom:2px solid #E0E0E0'>Policy File</th>"
            "<th style='padding:8px 12px;text-align:left;border-bottom:2px solid #E0E0E0'>Type</th>"
            "<th style='padding:8px 12px;text-align:left;border-bottom:2px solid #E0E0E0'>Carrier</th>"
            "<th style='padding:8px 12px;text-align:left;border-bottom:2px solid #E0E0E0'>Policy #</th>"
            "<th style='padding:8px 12px;text-align:left;border-bottom:2px solid #E0E0E0'>Effective</th>"
            "<th style='padding:8px 12px;text-align:left;border-bottom:2px solid #E0E0E0'>Expires</th>"
            "<th style='padding:8px 12px;text-align:right;border-bottom:2px solid #E0E0E0'>Occ Limit</th>"
            "<th style='padding:8px 12px;text-align:right;border-bottom:2px solid #E0E0E0'>Agg Limit</th>"
            "</tr>"
        )

        for pa in policy_analyses:
            ptype    = pa.get("policy_type") or "Unknown"
            carrier  = pa.get("carrier") or "—"
            pol_num  = pa.get("policy_number") or "—"
            eff      = pa.get("effective_date") or "—"
            exp      = pa.get("expiry_date") or "—"
            limits   = pa.get("limits") or {}
            source   = pa.get("source_file") or pa.get("_source_file") or "—"
            color    = _type_color(ptype)

            occ_lim  = _fmt_limit(limits.get("each_occurrence") or limits.get("per_occurrence"))
            agg_lim  = _fmt_limit(limits.get("general_aggregate") or limits.get("aggregate"))

            if carrier and carrier != "—":
                carriers.add(carrier)

            # Dates: shorten to YYYY-MM-DD if ISO
            def _short_date(d):
                if not d or d == "—":
                    return "—"
                return str(d)[:10]

            badge = (
                f"<span style='background:{color};color:white;padding:2px 8px;"
                f"border-radius:10px;font-size:0.72rem;white-space:nowrap'>{ptype}</span>"
            )
            row_htmls.append(
                f"<tr style='border-bottom:1px solid #F0F0F0;font-size:0.8rem'>"
                f"<td style='padding:8px 12px;color:#333;max-width:180px;"
                f"word-break:break-all'>{source}</td>"
                f"<td style='padding:8px 12px'>{badge}</td>"
                f"<td style='padding:8px 12px;color:#444'>{carrier}</td>"
                f"<td style='padding:8px 12px;color:#444;font-family:monospace'>{pol_num}</td>"
                f"<td style='padding:8px 12px;color:#444'>{_short_date(eff)}</td>"
                f"<td style='padding:8px 12px;color:#444'>{_short_date(exp)}</td>"
                f"<td style='padding:8px 12px;text-align:right;color:#333;font-weight:600'>{occ_lim}</td>"
                f"<td style='padding:8px 12px;text-align:right;color:#333;font-weight:600'>{agg_lim}</td>"
                f"</tr>"
            )

        table_html = (
            "<div style='overflow-x:auto'>"
            "<table style='border-collapse:collapse;width:100%;font-size:0.875rem'>"
            f"<thead>{header}</thead>"
            f"<tbody>{''.join(row_htmls)}</tbody>"
            "</table></div>"
        )
        st.markdown(table_html, unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)

        # Totals row
        t1, t2, t3 = st.columns(3)
        t1.metric("Total Policies", len(policy_analyses))
        t2.metric("Unique Carriers", len(carriers))
        t3.metric("Policy Types", len({pa.get("policy_type","?") for pa in policy_analyses}))

        # Endorsement quick-view
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("**Endorsements Summary**")
        for pa in policy_analyses:
            ends = pa.get("endorsements", [])
            if not ends:
                continue
            source = pa.get("source_file") or pa.get("_source_file") or "Policy"
            ptype  = pa.get("policy_type") or "Unknown"
            color  = _type_color(ptype)
            with st.expander(
                f"{source} — {len(ends)} endorsement{'s' if len(ends) != 1 else ''}",
                expanded=False,
            ):
                for e in ends:
                    form = e.get("form_number", "")
                    name = e.get("name", "")
                    page = e.get("page", "")
                    note = e.get("notes", "")
                    st.markdown(
                        f"<div style='display:flex;gap:0.5rem;padding:4px 0;"
                        f"border-bottom:1px solid #F5F5F5;font-size:0.8rem'>"
                        f"<span style='font-family:monospace;color:{color};min-width:100px'>"
                        f"{form or '—'}</span>"
                        f"<span style='color:#333;flex:1'>{name}</span>"
                        + (f"<span style='color:#888'>p.{page}</span>" if page else "")
                        + "</div>",
                        unsafe_allow_html=True,
                    )
                    if note:
                        st.markdown(
                            f"<div style='font-size:0.78rem;color:#666;"
                            f"padding:2px 0 4px 108px;font-style:italic'>{note}</div>",
                            unsafe_allow_html=True,
                        )


# ══════════════════════════════════════════════════════════════════
#  GENERATE MARKED-UP PDFs (collapsed expander)
# ══════════════════════════════════════════════════════════════════
def _load_policy_analyses_local(ex_dir: Path) -> list:
    analyses = []
    for p in ex_dir.glob(f"{slug}-policy-*-analysis.json"):
        try:
            analyses.append(json.loads(p.read_text(encoding="utf-8", errors="replace")))
        except Exception:
            pass
    return analyses


# ══════════════════════════════════════════════════════════════════
#  FINDING CARD (FEATURE 1 — expanded with delete, more fields)
# ══════════════════════════════════════════════════════════════════
def render_finding_card(f: dict, idx: int, prefix: str = "") -> None:
    fid      = f.get("id", f"finding-{idx}")
    req_type = f.get("requirement_type", "Unknown Requirement")
    cat      = f.get("category", "Good")
    score    = f.get("risk_score")
    like     = f.get("likelihood")
    sev      = f.get("severity")
    is_manual = f.get("manual", False)

    cat_colors = {
        "Ugly": COLOR_UGLY, "Bad": COLOR_BAD,
        "Good": COLOR_GOOD,
        "Review": COLOR_REVIEW, "Needs Review": COLOR_REVIEW,
        "Informational": "#1565C0",
    }
    cat_color  = cat_colors.get(cat, "#9E9E9E")
    cat_icons  = {
        "Ugly": "&#128308;", "Bad": "&#128993;",
        "Good": "&#128994;",
        "Review": "&#9888;", "Needs Review": "&#9888;",
        "Informational": "&#8505;",
    }
    cat_icon   = cat_icons.get(cat, "")

    reviewed_mark = " &#10003;" if f.get("reviewed") else ""
    manual_mark   = " [M]" if is_manual else ""
    score_str = f" \u2014 Score: {score}/25 ({severity_label(score)})" if score is not None else ""
    label     = f"{cat_icon} [{cat}] {req_type}{score_str}{reviewed_mark}{manual_mark}"

    # Base key — prefix + fid + idx ensures uniqueness across all render contexts
    _k       = f"{prefix}_{fid}_{idx}"
    edit_key = f"editing_{_k}"
    del_key  = f"delete_confirm_{_k}"

    with st.expander(label, expanded=False):

        # ── Delete confirmation overlay ────────────────────────────
        if st.session_state.get(del_key, False):
            st.markdown(
                f"<div style='background:#FFEBEE;border-radius:6px;padding:0.75rem;"
                f"margin-bottom:0.5rem'>"
                f"<strong style='color:#B71C1C'>Delete this finding?</strong><br>"
                f"<span style='font-size:0.875rem;color:#555'>{req_type}</span>"
                f"</div>",
                unsafe_allow_html=True,
            )
            dc1, dc2, _ = st.columns([1, 1, 4])
            with dc1:
                if st.button("Yes, Delete", key=f"del_yes_{_k}",
                             type="primary", use_container_width=True):
                    state["findings"] = [
                        x for x in state.get("findings", [])
                        if x.get("id") != fid
                    ]
                    ast.refresh_stage(state)
                    ast.save(client_path, state)
                    del st.session_state[del_key]
                    st.rerun()
            with dc2:
                if st.button("Cancel", key=f"del_no_{_k}",
                             use_container_width=True):
                    del st.session_state[del_key]
                    st.rerun()
            return

        # ── VIEW mode ─────────────────────────────────────────────
        if not st.session_state.get(edit_key, False):
            badge_label = "⚠ Needs Review" if cat in ("Review", "Needs Review") else cat
            badge_html = (
                f"<span style='background:{cat_color};color:white;padding:2px 10px;"
                f"border-radius:10px;font-size:0.8rem;font-weight:600'>{badge_label}</span>"
            )
            if score is not None:
                badge_html += (
                    f" &nbsp;<span style='font-size:0.875rem;color:#555'>"
                    f"Risk Score: <strong>{score}/25</strong> — {severity_label(score)}</span>"
                )
            if like is not None and sev is not None:
                badge_html += (
                    f" &nbsp;<span style='font-size:0.8rem;color:#777'>(L:{like} × S:{sev})</span>"
                )
            if is_manual:
                badge_html += " &nbsp;<span style='background:#E3F2FD;color:#1565C0;padding:1px 6px;border-radius:8px;font-size:0.72rem'>manual</span>"
            st.markdown(badge_html + "<br>", unsafe_allow_html=True)

            # Contract quote
            cquote = str(f.get("contract_quote", "") or "").strip()
            cpage  = str(f.get("contract_page", "") or "").strip()
            cfile  = str(f.get("contract_file", "") or "").strip()
            if cquote:
                cite = " — ".join(filter(None, [cfile, cpage]))
                st.markdown(
                    f"<div style='background:#FFF8E1;border-left:4px solid #FF8F00;"
                    f"padding:0.75rem;border-radius:0 6px 6px 0;margin-bottom:0.5rem'>"
                    f"<span style='font-size:0.75rem;color:#F57F17;font-weight:700;"
                    f"text-transform:uppercase;letter-spacing:0.05em'>Contract Requires</span><br>"
                    f"<span style='font-size:0.875rem'>{_html.escape(cquote).replace(chr(10), '<br>')}</span>"
                    + (f"<br><span style='font-size:0.8rem;color:#888'>{_html.escape(cite)}</span>" if cite else "")
                    + "</div>",
                    unsafe_allow_html=True,
                )

            # Policy quote
            pquote = str(f.get("policy_quote", "") or "").strip()
            ppage  = str(f.get("policy_page", "") or "").strip()
            pfile  = str(f.get("policy_file", "") or "").strip()
            if pquote:
                cite = " — ".join(filter(None, [pfile, ppage]))
                st.markdown(
                    f"<div style='background:#E3F2FD;border-left:4px solid #1565C0;"
                    f"padding:0.75rem;border-radius:0 6px 6px 0;margin-bottom:0.5rem'>"
                    f"<span style='font-size:0.75rem;color:#1565C0;font-weight:700;"
                    f"text-transform:uppercase;letter-spacing:0.05em'>Policy Provides</span><br>"
                    f"<span style='font-size:0.875rem'>{_html.escape(pquote).replace(chr(10), '<br>')}</span>"
                    + (f"<br><span style='font-size:0.8rem;color:#888'>{_html.escape(cite)}</span>" if cite else "")
                    + "</div>",
                    unsafe_allow_html=True,
                )

            # Gap description
            gap = str(f.get("gap_description", "") or "").strip()
            if gap and cat not in ("Good",):
                st.markdown(
                    "<div style='margin-bottom:0.25rem'>"
                    "<span style='font-size:0.75rem;color:#E0E0E0;font-weight:700;"
                    "text-transform:uppercase;letter-spacing:0.05em'>Technical Analysis</span>"
                    "</div>",
                    unsafe_allow_html=True,
                )
                st.markdown(gap)
                if pfile or ppage:
                    cite_parts = filter(None, [pfile, f"Page {ppage}" if ppage else None])
                    cite_text  = " · ".join(cite_parts)
                    st.markdown(
                        f"<div style='border-left:3px solid {COLOR_NAVY};padding:2px 8px;"
                        f"margin:2px 0 0.5rem;font-size:0.8rem;color:#888'>&#128196; {cite_text}</div>",
                        unsafe_allow_html=True,
                    )

            # Plain English
            plain = str(f.get("plain_english", "") or "").strip()
            if plain:
                st.markdown(
                    f"<div style='background:#F5F5F5;padding:0.75rem;"
                    f"border-radius:6px;margin-bottom:0.5rem'>"
                    f"<span style='font-size:0.75rem;color:#555;font-weight:700;"
                    f"text-transform:uppercase;letter-spacing:0.05em'>"
                    f"What This Means for the Business</span><br>"
                    f"<span style='font-size:0.875rem;font-style:italic;word-break:break-word'>"
                    f"{_html.escape(plain).replace(chr(13), '').replace(chr(10), '<br>')}"
                    f"</span></div>",
                    unsafe_allow_html=True,
                )

            # Covered by other policy
            if f.get("covered_by_other_policy"):
                cb_file = str(f.get("covered_by_which_policy", "") or "").strip()
                cb_page = str(f.get("covered_by_page", "") or "").strip()
                if cb_file:
                    cite_parts = [f"&#128196; {_html.escape(cb_file)}"]
                    if cb_page:
                        cite_parts.append(_html.escape(cb_page))
                    citation_html = (
                        f"<br><span style='font-size:0.78rem;opacity:0.85'>"
                        f"{' &middot; '.join(cite_parts)}</span>"
                    )
                else:
                    citation_html = ""
                st.markdown(
                    f"<div style='background:#1a2e1a;border:1px solid #2d5a2d;padding:0.5rem;"
                    f"border-radius:6px;margin-bottom:0.5rem;font-size:0.875rem;color:#90EE90'>"
                    f"&#10003; <strong>Covered by another policy</strong>"
                    f"{citation_html}</div>",
                    unsafe_allow_html=True,
                )

            # Recommendation
            rec = str(f.get("recommendation", "") or "").strip()
            if rec:
                rec_color = (
                    COLOR_UGLY if cat == "Ugly" else
                    COLOR_BAD if cat == "Bad" else
                    COLOR_REVIEW if cat in ("Review", "Needs Review") else
                    COLOR_GOOD
                )
                st.markdown(
                    f"<div style='background:#FAFAFA;border-left:4px solid {rec_color};"
                    f"padding:0.75rem;border-radius:0 6px 6px 0;margin-bottom:0.5rem'>"
                    f"<span style='font-size:0.75rem;color:{rec_color};font-weight:700;"
                    f"text-transform:uppercase;letter-spacing:0.05em'>Recommendation</span><br>"
                    f"<span style='font-size:0.875rem'>{_html.escape(rec).replace(chr(10), '<br>')}</span></div>",
                    unsafe_allow_html=True,
                )

            # Discovery Questions
            dqs = f.get("discoveryQuestions", [])
            if dqs:
                st.markdown(
                    "<div style='background:#EEF3FF;border-left:4px solid #4A7FE5;"
                    "padding:0.6rem 0.75rem;border-radius:0 6px 6px 0;margin-bottom:0.25rem'>"
                    "<span style='font-size:0.75rem;color:#4A7FE5;font-weight:700;"
                    "text-transform:uppercase;letter-spacing:0.05em'>Discovery Questions</span>"
                    "<span style='font-size:0.72rem;color:#8898C4;margin-left:0.5rem'>"
                    "— check off during client meeting</span>"
                    "</div>",
                    unsafe_allow_html=True,
                )
                for _qi, _q in enumerate(dqs):
                    _ck_key = f"dq_{_k}_{_qi}"
                    st.checkbox(_q, key=_ck_key)
                st.markdown("<div style='margin-bottom:0.25rem'></div>", unsafe_allow_html=True)

            # Tags
            tags = f.get("tags", [])
            if tags:
                tag_html = " ".join(
                    f"<span style='background:#E0E0E0;color:#555;padding:2px 8px;"
                    f"border-radius:12px;font-size:0.75rem'>{t}</span>"
                    for t in tags
                )
                st.markdown(tag_html, unsafe_allow_html=True)

            if f.get("reviewed"):
                st.markdown(
                    "<span style='color:#2E7D32;font-size:0.8rem'>&#10003; Reviewed</span>",
                    unsafe_allow_html=True,
                )

            st.markdown("<br>", unsafe_allow_html=True)
            # Action buttons: Edit | Delete | Mark Reviewed
            btn1, btn2, btn3, _ = st.columns([1, 1, 1.5, 3])
            with btn1:
                if st.button("Edit", key=f"edit_btn_{_k}"):
                    st.session_state[edit_key] = True
                    st.rerun()
            with btn2:
                if st.button("Delete", key=f"del_btn_{_k}"):
                    st.session_state[del_key] = True
                    st.rerun()
            with btn3:
                lbl = "Unmark Reviewed" if f.get("reviewed") else "Mark Reviewed"
                if st.button(lbl, key=f"review_btn_{_k}"):
                    f["reviewed"] = not f.get("reviewed", False)
                    ast.save(client_path, state)
                    st.rerun()

        # ── EDIT mode ─────────────────────────────────────────────
        else:
            with st.form(key=f"edit_form_{_k}"):
                ec1, ec2 = st.columns(2)
                with ec1:
                    _cat_opts = ["Good", "Bad", "Needs Review", "Ugly", "Informational"]
                new_cat = st.selectbox(
                        "Category",
                        options=_cat_opts,
                        index=_cat_opts.index(cat) if cat in _cat_opts else 1,
                    )
                with ec2:
                    new_req = st.text_input("Requirement Type / Title", value=req_type)

                sc1, sc2 = st.columns(2)
                with sc1:
                    new_like = st.selectbox(
                        "Likelihood (1-5)", [None, 1, 2, 3, 4, 5],
                        index=([None,1,2,3,4,5].index(like) if like in [None,1,2,3,4,5] else 0),
                        format_func=lambda x: "—" if x is None else str(x),
                    )
                with sc2:
                    new_sev = st.selectbox(
                        "Severity (1-5)", [None, 1, 2, 3, 4, 5],
                        index=([None,1,2,3,4,5].index(sev) if sev in [None,1,2,3,4,5] else 0),
                        format_func=lambda x: "—" if x is None else str(x),
                    )

                new_gap   = st.text_area("Technical Analysis",
                                         value=str(f.get("gap_description","") or ""), height=90)
                new_plain = st.text_area("Plain English Explanation",
                                         value=str(f.get("plain_english","") or ""), height=80)
                new_rec   = st.text_area("Recommendation",
                                         value=str(f.get("recommendation","") or ""), height=70)

                pe1, pe2 = st.columns(2)
                with pe1:
                    new_pfile = st.text_input("Policy Filename",
                                              value=str(f.get("policy_file","") or ""))
                    new_ppage = st.text_input("Policy Page Ref",
                                              value=str(f.get("policy_page","") or ""))
                with pe2:
                    new_cfile = st.text_input("Contract Filename",
                                              value=str(f.get("contract_file","") or ""))
                    new_cpage = st.text_input("Contract Page Ref",
                                              value=str(f.get("contract_page","") or ""))

                cur_tags = ", ".join(f.get("tags", []))
                new_tags_str = st.text_input("Tags (comma-separated)", value=cur_tags)

                sf1, sf2, _ = st.columns([1, 1, 4])
                with sf1:
                    save_edit   = st.form_submit_button("Save", type="primary",
                                                        use_container_width=True)
                with sf2:
                    cancel_edit = st.form_submit_button("Cancel", use_container_width=True)

            if save_edit:
                f["category"]         = new_cat
                f["requirement_type"] = new_req.strip()
                f["likelihood"]       = new_like
                f["severity"]         = new_sev
                f["risk_score"]       = (new_like * new_sev) if (new_like and new_sev) else None
                f["gap_description"]  = new_gap.strip()
                f["plain_english"]    = new_plain.strip()
                f["recommendation"]   = new_rec.strip()
                f["policy_file"]      = new_pfile.strip()
                f["policy_page"]      = new_ppage.strip()
                f["contract_file"]    = new_cfile.strip()
                f["contract_page"]    = new_cpage.strip()
                f["tags"]             = [t.strip() for t in new_tags_str.split(",") if t.strip()]
                ast.refresh_stage(state)
                ast.save(client_path, state)
                del st.session_state[edit_key]
                st.rerun()

            if cancel_edit:
                del st.session_state[edit_key]
                st.rerun()


# ══════════════════════════════════════════════════════════════════
#  TAB 2-5 — FINDING LISTS
# ══════════════════════════════════════════════════════════════════

# Empty state — shown inside finding tabs if no findings
def _empty_findings_msg():
    st.markdown(
        "<div style='text-align:center;padding:2rem;color:#888'>No findings here.</div>",
        unsafe_allow_html=True,
    )


with tab_ugly:
    if not findings:
        _empty_findings_msg()
    else:
        if not ugly_findings:
            st.markdown(
                "<div style='text-align:center;padding:2rem;color:#888'>No critical findings.</div>",
                unsafe_allow_html=True,
            )
        else:
            for i, f in enumerate(ugly_findings):
                render_finding_card(f, i, "ugly")

with tab_bad:
    if not findings:
        _empty_findings_msg()
    else:
        if not bad_findings:
            st.markdown(
                "<div style='text-align:center;padding:2rem;color:#888'>No bad findings.</div>",
                unsafe_allow_html=True,
            )
        else:
            for i, f in enumerate(bad_findings):
                render_finding_card(f, i, "bad")

with tab_review:
    if not findings:
        _empty_findings_msg()
    else:
        if not review_findings:
            st.markdown(
                "<div style='text-align:center;padding:2rem;color:#888'>No findings needing verification.</div>",
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                f"<div style='background:#2a2200;border:1px solid #5a4800;border-radius:6px;"
                f"padding:0.6rem 0.875rem;margin-bottom:0.75rem;font-size:0.875rem;"
                f"color:{COLOR_REVIEW}'>"
                f"&#9888; These findings could not be confirmed or ruled out from the documents provided. "
                f"Each one requires a call or email to the carrier or broker before the audit is final.</div>",
                unsafe_allow_html=True,
            )
            for i, f in enumerate(review_findings):
                render_finding_card(f, i, "review")

with tab_good:
    if not findings:
        _empty_findings_msg()
    else:
        if not good_findings:
            st.markdown(
                "<div style='text-align:center;padding:2rem;color:#888'>No good findings.</div>",
                unsafe_allow_html=True,
            )
        else:
            for i, f in enumerate(good_findings):
                render_finding_card(f, i, "good")

with tab_all:
    if not findings:
        st.markdown("<br>", unsafe_allow_html=True)
        c1, c2, c3 = st.columns([1, 2, 1])
        with c2:
            st.markdown(
                "<div style='text-align:center;padding:2rem 0'>"
                "<div style='font-size:3rem'>&#128202;</div>"
                "<h3>No findings yet</h3>"
                "<p style='color:#666'>Run the full audit analysis to generate findings.</p>"
                "</div>",
                unsafe_allow_html=True,
            )
            if st.button("Run Analysis", type="primary", use_container_width=True, key="all_run"):
                st.switch_page("pages/2_Document_Intake.py")
    else:
        st.markdown("<br>", unsafe_allow_html=True)
        for i, f in enumerate(all_sorted):
            render_finding_card(f, i, "all")


# ══════════════════════════════════════════════════════════════════
#  TAB 6 — BY POLICY
# ══════════════════════════════════════════════════════════════════
with tab_by_policy:
    if not findings:
        _empty_findings_msg()
    else:
        # Group findings by policy_file, sorted severity-first within each group
        policy_groups: dict = {}
        for f in all_sorted:
            key = f.get("policy_file") or "No Policy / Manual"
            policy_groups.setdefault(key, []).append(f)

        for policy_name in sorted(policy_groups.keys()):
            group  = policy_groups[policy_name]
            n_ugly   = sum(1 for f in group if f.get("category") == "Ugly")
            n_bad    = sum(1 for f in group if f.get("category") == "Bad")
            n_review = sum(1 for f in group if f.get("category") in ("Review", "Needs Review"))
            n_good   = sum(1 for f in group if f.get("category") == "Good")

            badge_parts = []
            if n_ugly:
                badge_parts.append(
                    f"<span style='color:{COLOR_UGLY};font-weight:700'>{n_ugly} Critical</span>"
                )
            if n_bad:
                badge_parts.append(
                    f"<span style='color:{COLOR_BAD};font-weight:700'>{n_bad} Bad</span>"
                )
            if n_review:
                badge_parts.append(
                    f"<span style='color:{COLOR_REVIEW};font-weight:700'>{n_review} Review</span>"
                )
            if n_good:
                badge_parts.append(
                    f"<span style='color:{COLOR_GOOD};font-weight:700'>{n_good} Good</span>"
                )
            badge_html = " &nbsp;·&nbsp; ".join(badge_parts) if badge_parts else f"{len(group)} findings"

            with st.expander(policy_name, expanded=(n_ugly > 0 or n_bad > 0)):
                st.markdown(
                    f"<div style='font-size:0.8rem;margin-bottom:0.75rem'>{badge_html}</div>",
                    unsafe_allow_html=True,
                )
                for _bp_idx, f in enumerate(group):
                    render_finding_card(f, _bp_idx, f"bp_{policy_name}")


# ══════════════════════════════════════════════════════════════════
#  TAB 7 — WHAT CHANGED
# ══════════════════════════════════════════════════════════════════
with tab_what_changed:

    # ── Helpers ────────────────────────────────────────────────────

    def _wc_title_words(f_dict: dict) -> set:
        return set(
            re.sub(r"[^a-z0-9 ]", "", str(f_dict.get("requirement_type", "")).lower()).split()
        )

    def _wc_match(curr_f: dict, prior_list: list) -> tuple:
        """
        Find the best match for curr_f in prior_list.
        Returns (matched_finding, index) or (None, -1).
        Prefers exact ID match; falls back to 2+ word title overlap.
        """
        curr_id    = curr_f.get("id", "")
        curr_words = _wc_title_words(curr_f)

        best_idx     = -1
        best_overlap = 1          # minimum threshold
        for i, pf in enumerate(prior_list):
            if curr_id and pf.get("id") == curr_id:
                return pf, i
            overlap = len(curr_words & _wc_title_words(pf))
            if overlap > best_overlap:
                best_overlap = overlap
                best_idx     = i

        if best_idx >= 0:
            return prior_list[best_idx], best_idx
        return None, -1

    def _cat_rank(cat: str) -> int:
        # Treat "Review" and "Needs Review" identically.
        if cat == "Needs Review":
            cat = "Review"
        return {"Good": 0, "Informational": 0, "Review": 1, "Bad": 2, "Ugly": 3}.get(cat, 0)

    def _score_str(score) -> str:
        return f"{score}/25" if score is not None else "—"

    def _wc_card(title: str, prior_score, curr_score, prior_cat: str,
                 curr_cat: str, accent: str, icon: str, note: str = "") -> None:
        """Render a compact diff card for one finding."""
        cat_colors = {"Ugly": COLOR_UGLY, "Bad": COLOR_BAD,
                      "Good": COLOR_GOOD, "Informational": "#1565C0"}
        curr_color  = cat_colors.get(curr_cat, "#9E9E9E")
        prior_color = cat_colors.get(prior_cat, "#9E9E9E")

        # Score delta arrow
        if curr_score is not None and prior_score is not None:
            delta = curr_score - prior_score
            if delta > 0:
                delta_html = (
                    f"<span style='color:{COLOR_UGLY};font-weight:700'> ↑+{delta}</span>"
                )
            elif delta < 0:
                delta_html = (
                    f"<span style='color:{COLOR_GOOD};font-weight:700'> ↓{delta}</span>"
                )
            else:
                delta_html = "<span style='color:#888'> =</span>"
        else:
            delta_html = ""

        prior_str = _score_str(prior_score)
        curr_str  = _score_str(curr_score)

        score_section = (
            f"<span style='color:{prior_color}'>{prior_str}</span>"
            f" → "
            f"<span style='color:{curr_color};font-weight:700'>{curr_str}</span>"
            f"{delta_html}"
        ) if prior_cat or curr_cat else curr_str

        note_html = (
            f"<div style='font-size:0.75rem;color:#888;margin-top:2px'>{note}</div>"
            if note else ""
        )

        st.markdown(
            f"<div style='border-left:3px solid {accent};padding:0.5rem 0.75rem;"
            f"margin-bottom:0.4rem;border-radius:0 4px 4px 0;background:#FAFAFA'>"
            f"<div style='display:flex;align-items:baseline;gap:0.5rem;flex-wrap:wrap'>"
            f"<span style='font-size:1rem'>{icon}</span>"
            f"<span style='font-size:0.875rem;font-weight:600;flex:1'>{title}</span>"
            f"<span style='font-size:0.8rem;color:#666'>{score_section}</span>"
            f"</div>"
            f"{note_html}"
            f"</div>",
            unsafe_allow_html=True,
        )

    def _wc_section(label: str, items: list, accent: str, icon: str,
                    render_fn, expanded: bool = True) -> None:
        """Render a collapsible category section with a count badge."""
        if not items:
            return
        badge = (
            f"<span style='background:{accent};color:white;border-radius:10px;"
            f"padding:1px 8px;font-size:0.8rem;font-weight:700;margin-left:0.4rem'>"
            f"{len(items)}</span>"
        )
        with st.expander(f"{label}  {len(items)}", expanded=expanded):
            st.markdown(
                f"<div style='font-size:0.75rem;color:{accent};font-weight:700;"
                f"text-transform:uppercase;letter-spacing:0.05em;margin-bottom:0.5rem'>"
                f"{label.upper()} — {len(items)} FINDING{'S' if len(items)!=1 else ''}"
                f"</div>",
                unsafe_allow_html=True,
            )
            for item in items:
                render_fn(item)

    # ── Data: load prior run ───────────────────────────────────────
    prior_runs = state.get("prior_runs", [])
    use_stub   = not prior_runs

    if use_stub:
        # ── STUB DATA — visible/testable when no real prior run ───
        st.info(
            "No prior run yet — showing sample data so you can preview this view. "
            "Run a second audit after your next renewal to see real changes.",
            icon="ℹ️",
        )
        _stub_resolved = [
            {
                "title": "Additional Insured — Completed Operations",
                "prior_cat": "Ugly", "curr_cat": "Good",
                "prior_score": 16, "curr_score": None,
                "note": "Endorsement CG 20 37 added at renewal",
            },
            {
                "title": "Waiver of Subrogation — Commercial Auto",
                "prior_cat": "Bad", "curr_cat": "Good",
                "prior_score": 9, "curr_score": None,
                "note": "Blanket waiver endorsed on renewal policy",
            },
            {
                "title": "Primary & Noncontributory — GL",
                "prior_cat": "Bad", "curr_cat": "Good",
                "prior_score": 6, "curr_score": None,
                "note": "CG 20 01 added; language now matches contract requirement",
            },
        ]
        _stub_new = [
            {
                "title": "Cyber Liability — Social Engineering Sub-limit",
                "prior_cat": None, "curr_cat": "Ugly",
                "prior_score": None, "curr_score": 20,
                "note": "New carrier; social engineering now sublimited at $100K vs. $1M contract requirement",
            },
            {
                "title": "Workers Comp — Missing State (FL)",
                "prior_cat": None, "curr_cat": "Ugly",
                "prior_score": None, "curr_score": 16,
                "note": "Florida operations added since last audit; WC policy not updated",
            },
            {
                "title": "Professional Services Exclusion — GL Policy",
                "prior_cat": None, "curr_cat": "Bad",
                "prior_score": None, "curr_score": 12,
                "note": "Newly identified — exclusion present since policy inception",
            },
        ]
        _stub_worse = [
            {
                "title": "Umbrella — Schedule of Underlying Policies",
                "prior_cat": "Bad", "curr_cat": "Ugly",
                "prior_score": 8, "curr_score": 16,
                "note": "New GL carrier not listed on umbrella schedule",
            },
            {
                "title": "General Liability — Per-Occurrence Limit",
                "prior_cat": "Bad", "curr_cat": "Bad",
                "prior_score": 6, "curr_score": 10,
                "note": "Contract now requires $2M occ; GL still at $1M",
            },
            {
                "title": "D&O — Prior Acts Date Gap",
                "prior_cat": "Bad", "curr_cat": "Bad",
                "prior_score": 4, "curr_score": 9,
                "note": "Retroactive date moved forward 18 months at renewal",
            },
        ]
        _stub_unchanged = [
            {
                "title": "Commercial Property — Coinsurance Clause",
                "prior_cat": "Bad", "curr_cat": "Bad",
                "prior_score": 6, "curr_score": 6,
                "note": "80% coinsurance remains; no change from prior year",
            },
            {
                "title": "EPLI — Wage & Hour Defense Costs Only",
                "prior_cat": "Bad", "curr_cat": "Bad",
                "prior_score": 4, "curr_score": 4,
                "note": "Market standard; no admitted alternative identified",
            },
            {
                "title": "Hired & Non-Owned Auto — Sublimit",
                "prior_cat": "Bad", "curr_cat": "Bad",
                "prior_score": 6, "curr_score": 6,
                "note": "HNOA limit $1M; contract requires $2M — unchanged",
            },
        ]

        def _render_stub_resolved(item):
            _wc_card(
                item["title"], item["prior_score"], item["curr_score"],
                item["prior_cat"], item["curr_cat"] or "",
                COLOR_GOOD, "✅", item.get("note", ""),
            )

        def _render_stub_new(item):
            _wc_card(
                item["title"], item["prior_score"], item["curr_score"],
                item["prior_cat"] or "", item["curr_cat"],
                COLOR_UGLY, "🆕", item.get("note", ""),
            )

        def _render_stub_worse(item):
            _wc_card(
                item["title"], item["prior_score"], item["curr_score"],
                item["prior_cat"], item["curr_cat"],
                COLOR_BAD, "⬆️", item.get("note", ""),
            )

        def _render_stub_unchanged(item):
            _wc_card(
                item["title"], item["prior_score"], item["curr_score"],
                item["prior_cat"], item["curr_cat"],
                "#9E9E9E", "➡️", item.get("note", ""),
            )

        _wc_section("Resolved", _stub_resolved, COLOR_GOOD, "✅",
                    _render_stub_resolved, expanded=True)
        _wc_section("New Issues", _stub_new, COLOR_UGLY, "🆕",
                    _render_stub_new, expanded=True)
        _wc_section("Worse", _stub_worse, COLOR_BAD, "⬆️",
                    _render_stub_worse, expanded=True)
        _wc_section("Unchanged", _stub_unchanged, "#9E9E9E", "➡️",
                    _render_stub_unchanged, expanded=False)

    else:
        # ── REAL COMPARISON ───────────────────────────────────────
        prior_run      = prior_runs[-1]
        prior_findings = prior_run.get("findings", [])

        ts_raw = prior_run.get("timestamp", "")
        try:
            ts_label = datetime.fromisoformat(ts_raw).strftime("%b %d, %Y")
        except (ValueError, TypeError):
            ts_label = ts_raw[:10] if ts_raw else "prior run"

        if not prior_findings:
            st.info(
                "Prior run found but it contains no finding snapshots. "
                "Re-run the analysis to capture a full snapshot for comparison."
            )
        else:
            st.caption(f"Comparing current findings against the run from **{ts_label}**.")
            st.markdown("<br>", unsafe_allow_html=True)

            # Build comparison
            resolved_items  = []
            new_items       = []
            worse_items     = []
            unchanged_items = []

            prior_matched_indices: set = set()

            for cf in findings:
                pf, pi = _wc_match(cf, prior_findings)
                if pi >= 0:
                    prior_matched_indices.add(pi)

                curr_cat   = cf.get("category", "Good")
                curr_score = cf.get("risk_score")

                if pf is not None:
                    prior_cat   = pf.get("category", "Good")
                    prior_score = pf.get("risk_score")

                    pr = _cat_rank(prior_cat)
                    cr = _cat_rank(curr_cat)

                    if cr > pr or (
                        curr_score is not None
                        and prior_score is not None
                        and curr_score - prior_score > 2
                    ):
                        worse_items.append({
                            "title": cf.get("requirement_type", "Unknown"),
                            "prior_cat": prior_cat, "curr_cat": curr_cat,
                            "prior_score": prior_score, "curr_score": curr_score,
                            "note": (
                                f"Category: {prior_cat} → {curr_cat}"
                                if cr != pr else
                                f"Score: {_score_str(prior_score)} → {_score_str(curr_score)}"
                            ),
                        })
                    elif cr < pr or (
                        curr_cat == "Good" and prior_cat in ("Bad", "Ugly")
                    ):
                        resolved_items.append({
                            "title": cf.get("requirement_type", "Unknown"),
                            "prior_cat": prior_cat, "curr_cat": curr_cat,
                            "prior_score": prior_score, "curr_score": curr_score,
                            "note": f"Improved: {prior_cat} → {curr_cat}",
                        })
                    elif curr_cat in ("Bad", "Ugly"):
                        note = ""
                        if curr_score is not None and prior_score is not None:
                            delta = curr_score - prior_score
                            if delta < 0:
                                note = f"Score improved slightly: {_score_str(prior_score)} → {_score_str(curr_score)}"
                        unchanged_items.append({
                            "title": cf.get("requirement_type", "Unknown"),
                            "prior_cat": prior_cat, "curr_cat": curr_cat,
                            "prior_score": prior_score, "curr_score": curr_score,
                            "note": note,
                        })
                else:
                    # No prior match
                    if curr_cat in ("Bad", "Ugly"):
                        new_items.append({
                            "title": cf.get("requirement_type", "Unknown"),
                            "prior_cat": None, "curr_cat": curr_cat,
                            "prior_score": None, "curr_score": curr_score,
                            "note": "Not present in prior run",
                        })

            # Prior findings with no current match → resolved / gone
            for pi, pf in enumerate(prior_findings):
                if pi not in prior_matched_indices and pf.get("category") in ("Bad", "Ugly"):
                    resolved_items.append({
                        "title": pf.get("requirement_type", "Unknown"),
                        "prior_cat": pf.get("category", "Bad"),
                        "curr_cat": None,
                        "prior_score": pf.get("risk_score"),
                        "curr_score": None,
                        "note": "No longer present in current run",
                    })

            if not any([resolved_items, new_items, worse_items, unchanged_items]):
                st.success(
                    "No differences found between the current run and the prior run. "
                    "The finding set appears identical."
                )
            else:
                def _render_real(item):
                    _wc_card(
                        item["title"],
                        item["prior_score"], item["curr_score"],
                        item.get("prior_cat") or "",
                        item.get("curr_cat") or "",
                        COLOR_GOOD, "✅", item.get("note", ""),
                    )

                def _render_new(item):
                    _wc_card(
                        item["title"],
                        item["prior_score"], item["curr_score"],
                        item.get("prior_cat") or "",
                        item.get("curr_cat") or "",
                        COLOR_UGLY, "🆕", item.get("note", ""),
                    )

                def _render_worse(item):
                    _wc_card(
                        item["title"],
                        item["prior_score"], item["curr_score"],
                        item.get("prior_cat") or "",
                        item.get("curr_cat") or "",
                        COLOR_BAD, "⬆️", item.get("note", ""),
                    )

                def _render_unch(item):
                    _wc_card(
                        item["title"],
                        item["prior_score"], item["curr_score"],
                        item.get("prior_cat") or "",
                        item.get("curr_cat") or "",
                        "#9E9E9E", "➡️", item.get("note", ""),
                    )

                _wc_section("Resolved", resolved_items, COLOR_GOOD, "✅",
                            _render_real, expanded=True)
                _wc_section("New Issues", new_items, COLOR_UGLY, "🆕",
                            _render_new, expanded=True)
                _wc_section("Worse", worse_items, COLOR_BAD, "⬆️",
                            _render_worse, expanded=True)
                _wc_section("Unchanged", unchanged_items, "#9E9E9E", "➡️",
                            _render_unch, expanded=False)

                # Summary bar
                st.markdown("<br>", unsafe_allow_html=True)
                total_changed = len(resolved_items) + len(new_items) + len(worse_items)
                if total_changed:
                    parts = []
                    if resolved_items:
                        parts.append(
                            f"<span style='color:{COLOR_GOOD};font-weight:700'>"
                            f"{len(resolved_items)} resolved</span>"
                        )
                    if new_items:
                        parts.append(
                            f"<span style='color:{COLOR_UGLY};font-weight:700'>"
                            f"{len(new_items)} new</span>"
                        )
                    if worse_items:
                        parts.append(
                            f"<span style='color:{COLOR_BAD};font-weight:700'>"
                            f"{len(worse_items)} worse</span>"
                        )
                    if unchanged_items:
                        parts.append(
                            f"<span style='color:#888'>{len(unchanged_items)} unchanged</span>"
                        )
                    st.markdown(
                        "<div style='font-size:0.875rem;padding:0.5rem 0'>"
                        + " &nbsp;·&nbsp; ".join(parts)
                        + f" since {ts_label}</div>",
                        unsafe_allow_html=True,
                    )

    if not prior_runs and not use_stub:
        st.info(
            "Run a second audit after your next renewal to see what improved, "
            "got worse, or is new."
        )


# ══════════════════════════════════════════════════════════════════
#  TAB 8 — HISTORY (FEATURE 4)
# ══════════════════════════════════════════════════════════════════
with tab_history:
    st.subheader("Analysis History")
    st.caption("Prior analysis runs archived here before each re-run.")
    st.markdown("<br>", unsafe_allow_html=True)

    prior_runs = state.get("prior_runs", [])

    if not prior_runs:
        st.info(
            "No prior runs saved yet. When you re-run analysis, the current findings "
            "will be archived here for comparison."
        )
    else:
        # Current run summary
        curr_ugly   = len(ugly_findings)
        curr_bad    = len(bad_findings)
        curr_review = len(review_findings)
        curr_good   = len(good_findings)
        last_date = state.get("last_analysis_date", "")
        last_date_str = ""
        if last_date:
            try:
                last_date_str = datetime.fromisoformat(last_date).strftime("%b %d, %Y at %I:%M %p")
            except ValueError:
                last_date_str = last_date[:16]

        st.markdown(
            f"<div style='background:#F0F4FF;border:1px solid #C5CAE9;border-radius:8px;"
            f"padding:0.75rem 1rem;margin-bottom:1rem'>"
            f"<div style='font-size:0.75rem;font-weight:700;color:{COLOR_NAVY};"
            f"letter-spacing:0.05em;margin-bottom:4px'>CURRENT RUN"
            + (f" — {last_date_str}" if last_date_str else "")
            + f"</div>"
            f"<span style='font-size:0.9rem'>{len(findings)} findings: "
            f"<span style='color:{COLOR_UGLY};font-weight:700'>{curr_ugly} critical</span>"
            f" &middot; "
            f"<span style='color:{COLOR_BAD};font-weight:700'>{curr_bad} bad</span>"
            f" &middot; "
            f"<span style='color:{COLOR_GOOD};font-weight:700'>{curr_good} good</span>"
            f"</span></div>",
            unsafe_allow_html=True,
        )

        # Prior runs in reverse chronological order
        for run in reversed(prior_runs):
            ts_raw = run.get("timestamp", "")
            try:
                ts_str = datetime.fromisoformat(ts_raw).strftime("%b %d, %Y at %I:%M %p")
            except ValueError:
                ts_str = ts_raw[:16]

            run_ct    = run.get("finding_count", 0)
            run_ugly  = run.get("ugly_count", 0)
            run_bad   = run.get("bad_count",  0)
            run_good  = run.get("good_count", 0)

            # Compute comparison
            delta_total = len(findings) - run_ct
            delta_ugly  = curr_ugly - run_ugly
            delta_bad   = curr_bad  - run_bad
            delta_good  = curr_good - run_good

            def _delta_str(d: int, positive_good: bool = False) -> str:
                if d == 0:
                    return "<span style='color:#888'>±0</span>"
                sign = "+" if d > 0 else ""
                # For ugly/bad: going up is bad; for good: going up is good
                if positive_good:
                    color = COLOR_GOOD if d > 0 else COLOR_BAD
                else:
                    color = COLOR_BAD if d > 0 else COLOR_GOOD
                return f"<span style='color:{color};font-weight:700'>{sign}{d}</span>"

            # Simple title overlap similarity for matched/new/resolved
            def _title_words(f_dict):
                return set(re.sub(r"[^a-z0-9 ]", "", str(f_dict.get("requirement_type","")).lower()).split())

            curr_titles = [_title_words(f) for f in findings]
            prev_titles = [_title_words(f) for f in run.get("findings", [])]

            def _is_match(pw, curr_list):
                for cw in curr_list:
                    if len(pw & cw) >= 2:
                        return True
                return False

            new_ct      = sum(1 for cw in curr_titles if not _is_match(cw, prev_titles))
            resolved_ct = sum(1 for pw in prev_titles if not _is_match(pw, curr_titles))

            with st.container(border=True):
                st.markdown(
                    f"<div style='font-size:0.75rem;font-weight:700;color:#888;"
                    f"letter-spacing:0.04em;margin-bottom:6px'>PRIOR RUN — {ts_str}</div>"
                    f"<span style='font-size:0.875rem'>{run_ct} findings: "
                    f"<span style='color:{COLOR_UGLY}'>{run_ugly} critical</span>"
                    f" &middot; "
                    f"<span style='color:{COLOR_BAD}'>{run_bad} bad</span>"
                    f" &middot; "
                    f"<span style='color:{COLOR_GOOD}'>{run_good} good</span>"
                    f"</span>",
                    unsafe_allow_html=True,
                )
                st.markdown(
                    f"<div style='font-size:0.8rem;color:#555;margin-top:6px'>"
                    f"vs. current run: "
                    f"total {_delta_str(delta_total)} &nbsp;·&nbsp; "
                    f"critical {_delta_str(delta_ugly)} &nbsp;·&nbsp; "
                    f"bad {_delta_str(delta_bad)} &nbsp;·&nbsp; "
                    f"good {_delta_str(delta_good, True)}"
                    f"<br><span style='color:#666;margin-top:2px;display:block'>"
                    f"~{new_ct} new findings &nbsp;·&nbsp; ~{resolved_ct} resolved findings</span>"
                    f"</div>",
                    unsafe_allow_html=True,
                )

                if run.get("findings"):
                    with st.expander("View prior findings list", expanded=False):
                        for pf in run["findings"][:20]:
                            pcat  = pf.get("category", "?")
                            ptit  = pf.get("requirement_type", "Unknown")
                            psc   = pf.get("risk_score")
                            pclr  = {"Ugly": COLOR_UGLY, "Bad": COLOR_BAD,
                                     "Good": COLOR_GOOD}.get(pcat, "#9E9E9E")
                            st.markdown(
                                f"<div style='font-size:0.8rem;padding:3px 0;"
                                f"border-bottom:1px solid #F5F5F5'>"
                                f"<span style='color:{pclr};font-weight:700'>[{pcat}]</span>"
                                f" {ptit}"
                                + (f" <span style='color:#888'>({psc}/25)</span>" if psc else "")
                                + "</div>",
                                unsafe_allow_html=True,
                            )
                        if len(run["findings"]) > 20:
                            st.caption(f"... and {len(run['findings']) - 20} more.")


# ══════════════════════════════════════════════════════════════════
#  GENERATE MARKED-UP PDFs expander (in tab_ugly context it's here)
# ══════════════════════════════════════════════════════════════════
st.markdown("<br>", unsafe_allow_html=True)

with st.expander("Generate Marked-up PDFs", expanded=False):
    st.caption(
        "Annotates each policy PDF with highlights, sticky notes, bookmarks, "
        "and a cover page. Saved to the client's `output/` folder."
    )
    exchange_dir_pdf = client_path / "ai-exchange"
    policies_dir_pdf = client_path / "policies"
    output_dir_pdf   = client_path / "output"

    existing_pdfs = sorted(output_dir_pdf.glob("*-AUDITED.pdf")) if output_dir_pdf.exists() else []
    if existing_pdfs:
        st.markdown("**Previously generated:**")

        # Issue 3: Download All as ZIP (rendered first so it's prominent)
        import io as _io
        import zipfile as _zip
        _zip_buf = _io.BytesIO()
        with _zip.ZipFile(_zip_buf, "w", _zip.ZIP_DEFLATED) as _zf:
            for _ep in existing_pdfs:
                _zf.write(_ep, arcname=_ep.name)
        st.download_button(
            label     = f"Download All as ZIP ({len(existing_pdfs)} file"
                         f"{'s' if len(existing_pdfs) != 1 else ''})",
            data      = _zip_buf.getvalue(),
            file_name = f"{slug}-audited-pdfs.zip",
            mime      = "application/zip",
            key       = "dl_all_zip",
            use_container_width=True,
        )
        st.markdown("<br>", unsafe_allow_html=True)

        for ep in existing_pdfs:
            col_name, col_dl = st.columns([4, 1])
            with col_name:
                # Issue 1: show generated timestamp (mtime) under each filename
                try:
                    _mtime    = datetime.fromtimestamp(ep.stat().st_mtime)
                    _mtime_s  = _mtime.strftime("%b %d, %Y %I:%M %p").lstrip("0").replace(" 0", " ")
                except OSError:
                    _mtime_s = "unknown"
                st.markdown(
                    f"<div style='font-size:0.875rem'>&#128196; {ep.name}</div>"
                    f"<div style='font-size:0.75rem;color:#777;margin-left:1.4em'>"
                    f"Generated: {_mtime_s}</div>",
                    unsafe_allow_html=True,
                )
            with col_dl:
                st.download_button(
                    label     = "Download",
                    data      = ep.read_bytes(),
                    file_name = ep.name,
                    mime      = "application/pdf",
                    key       = f"dl_existing_{ep.stem}",
                    use_container_width=True,
                )
        st.markdown("<br>", unsafe_allow_html=True)

    if not policies_dir_pdf.exists() or not any(policies_dir_pdf.glob("*.pdf")):
        st.warning("No policy PDFs found in the client's policies/ folder.")
    else:
        if st.button("Generate Marked-up PDFs", type="primary", key="generate_pdfs_btn"):
            pa_list = _load_policy_analyses_local(exchange_dir_pdf)
            # Build the set of policies referenced by at least one finding.
            # policy_file may be a single filename, "PROGRAM" (skipped here),
            # or a comma-OR-semicolon-delimited list. Models emit either
            # separator inconsistently. Heuristic: only count pieces ending
            # in .pdf (case-insensitive); fall back to whole string if none.
            policies_with_findings: set = set()
            for f in findings:
                pf = str(f.get("policy_file", "") or "").strip()
                if not pf or pf.upper() == "PROGRAM":
                    continue
                _normalized = pf.replace(";", ",")
                _raw = [p.strip() for p in _normalized.split(",") if p.strip()]
                _pdf_pieces = [Path(p).name for p in _raw if p.lower().endswith(".pdf")]
                for piece in (_pdf_pieces or [Path(pf).name]):
                    policies_with_findings.add(piece)
            pdf_list = (
                [policies_dir_pdf / name for name in policies_with_findings
                 if (policies_dir_pdf / name).exists()]
                if policies_with_findings
                else list(policies_dir_pdf.glob("*.pdf"))
            )
            if not pdf_list:
                st.error("No matching policy PDFs found to annotate.")
            else:
                prog_bar = st.progress(0.0, text="Starting...")
                results  = annotate_all_policies(
                    policies_dir    = policies_dir_pdf,
                    findings        = findings,
                    policy_analyses = pa_list,
                    client_name     = display_name,
                    output_dir      = output_dir_pdf,
                )
                completed = []
                warnings  = []
                for i, (fname, out_path, n_f, err) in enumerate(results):
                    prog_bar.progress((i + 1) / max(len(results), 1),
                                      text=f"Processing {fname}...")
                    if err:
                        warnings.append((fname, err))
                    else:
                        completed.append((fname, str(out_path), n_f))
                prog_bar.progress(1.0, text="Done.")
                # Issue 2: stash results in session state so download buttons survive reruns
                st.session_state["_pdf_gen_results"] = {
                    "completed": completed,
                    "warnings":  warnings,
                    "timestamp": datetime.now().isoformat(),
                }
                st.rerun()

    # Issue 2 (cont): render persisted results from session state on every visit/rerun
    _pdf_results = st.session_state.get("_pdf_gen_results")
    if _pdf_results:
        _completed = _pdf_results.get("completed") or []
        _warnings  = _pdf_results.get("warnings")  or []

        if _warnings:
            for _fname, _err in _warnings:
                st.warning(f"{_fname}: {_err}")

        if _completed:
            _hdr_col, _clear_col = st.columns([4, 1])
            with _hdr_col:
                st.success(
                    f"Generated {len(_completed)} marked-up PDF(s) "
                    f"this session. Click Download below."
                )
            with _clear_col:
                if st.button("Clear", key="clear_pdf_gen", use_container_width=True):
                    st.session_state.pop("_pdf_gen_results", None)
                    st.rerun()

            for _fname, _out_path_str, _n_f in _completed:
                _out_path = Path(_out_path_str)
                _dl_col, _info_col = st.columns([2, 3])
                with _dl_col:
                    if _out_path.exists():
                        st.download_button(
                            label     = f"Download {_out_path.name}",
                            data      = _out_path.read_bytes(),
                            file_name = _out_path.name,
                            mime      = "application/pdf",
                            key       = f"dl_new_{_out_path.stem}",
                            use_container_width=True,
                        )
                    else:
                        st.caption("(file no longer on disk)")
                with _info_col:
                    st.caption(
                        f"{_fname} → {_out_path.name} "
                        f"({_n_f} finding{'s' if _n_f != 1 else ''} annotated)"
                    )


# ══════════════════════════════════════════════════════════════════
#  NAVIGATION
# ══════════════════════════════════════════════════════════════════
st.divider()

nav_l, nav_r = st.columns(2)
with nav_l:
    if st.button("Re-run Analysis", use_container_width=True):
        st.switch_page("pages/2_Document_Intake.py")
with nav_r:
    if st.button("Build Report", type="primary", use_container_width=True):
        st.switch_page("pages/_Report_Builder.py")
