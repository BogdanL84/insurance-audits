"""
2_Document_Intake.py — Upload documents and enter metadata.

Five tabs:
  1. Policies      — insurance policy PDFs with coverage metadata
  2. Contracts     — MSAs, subcontracts, leases with contract metadata
  3. Loss Runs     — loss history PDFs/Excel + manual entry + EMOD
  4. COPE          — property schedules and SOVs
  5. Notes         — broker notes and risk flags
"""

import sys
import json
import time
import threading
from datetime import datetime
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import streamlit as st

st.set_page_config(
    page_title="Document Intake — Insurance Audit",
    page_icon="&#128193;",
    layout="wide",
    initial_sidebar_state="expanded",
)

from config import MAX_PDF_MB, COLOR_GOOD, COLOR_BAD, COLOR_UGLY, COLOR_NAVY
from core import audit_state as ast
from core.pdf_extractor import (
    extract, extract_with_info, get_page_count, get_file_size_mb, format_size,
    get_word_count, save_extracted_text, is_image,
    EXTRACTABLE_TYPES, IMAGE_TYPES,
)
from core.claude_runner import (
    run_claude, extract_json,
    build_policy_prompt, build_standalone_policy_prompt,
    build_policy_chunk_prompt, build_policy_merge_prompt,
    chunk_text, ANALYSIS_TIMEOUT, RATE_LIMIT_DELAY,
)
from utils import render_sidebar, require_client, render_stepper, inject_css

inject_css()
render_sidebar()

# ── Client + dirs ──────────────────────────────────────────────────
slug, client_path, state = require_client()
display_name = state.get("display_name", slug)

contracts_dir  = client_path / "contracts"
policies_dir   = client_path / "policies"
references_dir = client_path / "references"
loss_runs_dir  = client_path / "loss-runs"
cope_dir       = client_path / "cope"
exchange_dir   = client_path / "ai-exchange"

for _d in (contracts_dir, policies_dir, references_dir,
           loss_runs_dir, cope_dir, exchange_dir):
    _d.mkdir(parents=True, exist_ok=True)

if st.session_state.get("just_created"):
    name = st.session_state.pop("just_created")
    st.success(f"**{name}** created. Upload their documents below.")


# ══════════════════════════════════════════════════════════════════
#  TREATMENT A HERO STRIP (full-width gradient)
# ══════════════════════════════════════════════════════════════════
st.markdown(
    f'<div class="ta-hero">'
    f'<div class="ta-hero-content">'
    f'<p class="ta-hero-eyebrow">STEP 2 OF 6 &middot; UPLOAD</p>'
    f'<h1 class="ta-hero-title">Document Intake</h1>'
    f'<p class="ta-hero-sub">{display_name} &middot; '
    f'Upload policies, contracts, and supporting docs to power the audit.</p>'
    f'<div class="ta-hero-chips">'
    f'<span class="ta-hero-chip">&#128196; 5 file types accepted</span>'
    f'<span class="ta-hero-chip">&#9921; Up to {MAX_PDF_MB}MB each</span>'
    f'</div>'
    f'</div>'
    f'</div>',
    unsafe_allow_html=True,
)

# ══════════════════════════════════════════════════════════════════
#  CONSTANTS
# ══════════════════════════════════════════════════════════════════
POLICY_TYPES = [
    "GL — General Liability",
    "Auto — Commercial Auto",
    "WC — Workers Compensation",
    "Umbrella / Excess",
    "Property",
    "Pollution",
    "Inland Marine",
    "Cyber Liability",
    "D&O / EPLI",
    "Professional Liability / E&O",
    "Other",
]
CONTRACT_TYPES = [
    "MSA / Master Service Agreement",
    "Subcontractor Agreement",
    "Lease Agreement",
    "Service Contract",
    "Vendor Agreement",
    "Purchase Order / SOW",
    "Other",
]
POLICY_LINES = ["GL", "Auto", "WC", "Property", "Cyber", "Other"]
CONSTRUCTION_TYPES = [
    "Frame (Wood)",
    "Masonry",
    "Steel Frame",
    "Reinforced Concrete",
    "Mixed / Other",
]
FLAG_DEFS = [
    ("multi_entity",       "Multi-entity structure (subsidiaries, joint ventures, affiliates)"),
    ("hazmat",             "Hazmat / hazardous materials operations"),
    ("multi_state",        "Multi-state operations"),
    ("govt_contracts",     "Government contracts (federal, state, or local)"),
    ("prior_large_losses", "Prior losses >$500k in any single occurrence"),
]
EXTRACTABLE_EXT = [e.lstrip(".") for e in sorted(EXTRACTABLE_TYPES)]


# ══════════════════════════════════════════════════════════════════
#  HELPERS
# ══════════════════════════════════════════════════════════════════
def file_icon(filename: str) -> str:
    return {
        ".pdf": "&#128196;", ".docx": "&#128221;", ".doc": "&#128221;",
        ".xlsx": "&#128202;", ".xls": "&#128202;",
        ".txt": "&#128203;", ".md": "&#128203;",
    }.get(Path(filename).suffix.lower(), "&#128206;")


def _fkey(filename: str) -> str:
    return filename.replace(".", "_").replace(" ", "_").replace("-", "_")


def save_doc(uf, dest_dir: Path, category: str) -> bool:
    """Save uploaded file, register in state. Returns True if newly saved."""
    dest = dest_dir / uf.name
    if dest.exists():
        return False
    dest.write_bytes(uf.getbuffer())
    size_mb    = uf.size / (1024 * 1024)
    page_count = 0 if is_image(dest) else get_page_count(dest)
    doc_type   = "contract" if category == "contract" else "policy"
    ast.register_document(state, uf.name, doc_type, size_mb, page_count)
    docs = state.setdefault("documents", {})
    if uf.name not in docs:
        docs[uf.name] = {}
    docs[uf.name]["category"] = category
    ast.refresh_stage(state)
    ast.save(client_path, state)
    return True


# ── Analysis helpers ──────────────────────────────────────────────

def _analysis_json_path(name: str) -> Path:
    return exchange_dir / f"{slug}-policy-{Path(name).stem}-analysis.json"


def _fmt_elapsed(secs: int) -> str:
    return f"{secs // 60}m {secs % 60}s"


def _client_notes_for_analysis() -> str:
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


def _read_extracted_text(name: str) -> str | None:
    path = exchange_dir / f"{Path(name).stem}-extracted.txt"
    return path.read_text(encoding="utf-8", errors="replace") if path.exists() else None


def analyze_policy_card(name: str, timer_ph) -> tuple[bool, str, int]:
    """
    Run single-policy analysis inline with a live elapsed timer.
    Returns (ok, message, elapsed_seconds).
    message on success = policy_type string; on failure = error string.
    """
    contract_ready    = {n: m for n, m in state.get("contracts", {}).items() if m.get("extracted")}
    standalone_mode   = not contract_ready
    client_notes      = _client_notes_for_analysis()
    requirements_data: dict = {"requirements": []}

    if not standalone_mode:
        _req = exchange_dir / f"{slug}-contract-requirements.json"
        if _req.exists():
            try:
                requirements_data = json.loads(_req.read_text(encoding="utf-8"))
            except Exception:
                pass

    text = _read_extracted_text(name)
    if not text:
        return False, "Extracted text file not found.", 0

    chunks = chunk_text(text)
    start  = time.time()

    def _elapsed() -> str:
        return _fmt_elapsed(int(time.time() - start))

    def _run_threaded(prompt: str, label: str = "Analyzing") -> tuple[bool, str]:
        """Run run_claude in a background thread, update timer_ph until done."""
        holder: list = [None, None]
        def _worker():
            holder[0], holder[1] = run_claude(prompt, timeout=ANALYSIS_TIMEOUT)
        t = threading.Thread(target=_worker, daemon=True)
        t.start()
        while t.is_alive():
            timer_ph.markdown(
                f"<span style='color:#555;font-size:0.875rem'>{label}... {_elapsed()}</span>",
                unsafe_allow_html=True,
            )
            time.sleep(1)
        t.join()
        return holder[0], holder[1]

    # ── Single-chunk path ──────────────────────────────────────────
    if len(chunks) == 1:
        if standalone_mode:
            prompt = build_standalone_policy_prompt(name, text, client_notes)
        else:
            prompt = build_policy_prompt(name, text, client_notes, requirements_data)

        ok, result = _run_threaded(prompt, "Reading policy")
        elapsed    = int(time.time() - start)
        timer_ph.empty()

        if not ok:
            msg = ("Daily usage limit reached \u2014 try again after 2pm Phoenix time."
                   if result.startswith("RATE_LIMIT:") else result[:400])
            return False, msg, elapsed

        parsed = extract_json(result)
        if not parsed:
            return False, "Could not parse analysis JSON from Claude response.", elapsed

        parsed["_source_file"] = name
        _analysis_json_path(name).write_text(
            json.dumps(parsed, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        return True, parsed.get("policy_type", "policy"), elapsed

    # ── Multi-chunk path ───────────────────────────────────────────
    n_chunks       = len(chunks)
    chunk_analyses = []

    for chunk_idx, (chunk_t, page_range) in enumerate(chunks):
        req_arg = None if standalone_mode else requirements_data
        prompt  = build_policy_chunk_prompt(name, chunk_t, page_range, client_notes, req_arg)

        holder: list = [None, None]
        def _chunk_worker(p=prompt):
            holder[0], holder[1] = run_claude(p, timeout=ANALYSIS_TIMEOUT)
        t = threading.Thread(target=_chunk_worker, daemon=True)
        t.start()
        while t.is_alive():
            timer_ph.markdown(
                f"<span style='color:#555;font-size:0.875rem'>"
                f"Chunk {chunk_idx+1}/{n_chunks} ({page_range})... {_elapsed()}</span>",
                unsafe_allow_html=True,
            )
            time.sleep(1)
        t.join()
        ok, result = holder[0], holder[1]

        if not ok:
            if result.startswith("RATE_LIMIT:"):
                timer_ph.empty()
                return False, "Daily usage limit reached \u2014 try again after 2pm Phoenix time.", int(time.time() - start)
            continue  # non-fatal chunk error

        parsed = extract_json(result)
        if parsed:
            chunk_analyses.append(parsed)

        if chunk_idx < n_chunks - 1:
            time.sleep(RATE_LIMIT_DELAY)

    if not chunk_analyses:
        timer_ph.empty()
        return False, f"All {n_chunks} chunks failed to analyze.", int(time.time() - start)

    # Merge chunks
    merge_prompt = build_policy_merge_prompt(name, chunk_analyses, client_notes)
    holder2: list = [None, None]
    def _merge_worker():
        holder2[0], holder2[1] = run_claude(merge_prompt, timeout=ANALYSIS_TIMEOUT)
    t = threading.Thread(target=_merge_worker, daemon=True)
    t.start()
    while t.is_alive():
        timer_ph.markdown(
            f"<span style='color:#555;font-size:0.875rem'>"
            f"Merging {len(chunk_analyses)}/{n_chunks} chunks... {_elapsed()}</span>",
            unsafe_allow_html=True,
        )
        time.sleep(1)
    t.join()
    ok, result = holder2[0], holder2[1]
    elapsed    = int(time.time() - start)
    timer_ph.empty()

    if not ok:
        msg = ("Daily usage limit reached \u2014 try again after 2pm Phoenix time."
               if result.startswith("RATE_LIMIT:") else f"Merge failed: {result[:400]}")
        return False, msg, elapsed

    parsed = extract_json(result)
    if not parsed:
        return False, "Merge JSON parse failed.", elapsed

    parsed["_source_file"] = name
    _analysis_json_path(name).write_text(
        json.dumps(parsed, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    return True, parsed.get("policy_type", "policy"), elapsed


def extract_doc(filename: str, source_dir: Path, category: str) -> tuple:
    source = source_dir / filename
    if not source.exists():
        return False, f"File not found: {filename}"
    actual_mb = get_file_size_mb(source)
    if actual_mb > MAX_PDF_MB:
        return False, f"File too large: {actual_mb:.1f} MB (limit is {MAX_PDF_MB} MB). Consider splitting the PDF."
    try:
        extracted, info = extract_with_info(source)
        words           = get_word_count(extracted)
        pages           = len(extracted)
        method          = info.get("method", "pdf_text")
        out_path        = exchange_dir / f"{source.stem}-extracted.txt"
        save_extracted_text(extracted, out_path)
        doc_type        = "contract" if category == "contract" else "policy"
        ast.mark_extracted(state, filename, doc_type, words, method)
        ast.refresh_stage(state)
        ast.save(client_path, state)
        suffix = " (OCR'd)" if method == "ocr" else ""
        return True, f"{pages} pages · {words:,} words{suffix}"
    except Exception as e:
        return False, str(e)


def get_tab_files(source_dir: Path, category: str) -> list:
    """Files on disk in source_dir, matched against the correct state key."""
    state_key  = "contracts" if category == "contract" else "policies"
    state_docs = state.get(state_key, {})
    files      = []
    if not source_dir.exists():
        return files
    for f in sorted(source_dir.iterdir()):
        if not f.is_file() or f.name.startswith("."):
            continue
        if f.suffix.lower() not in EXTRACTABLE_TYPES:
            continue
        meta = state_docs.get(f.name, {})
        files.append({
            "name":              f.name,
            "path":              f,
            "size_str":          format_size(f),
            "page_count":        meta.get("page_count", 0),
            "extracted":         meta.get("extracted", False),
            "word_count":        meta.get("word_count", 0),
            "extraction_method": meta.get("extraction_method", "pdf_text"),
        })
    return files


def _get_saved_meta(filename: str) -> dict:
    return state.get("documents", {}).get(filename, {})


def save_doc_meta(filename: str, updates: dict) -> None:
    docs = state.setdefault("documents", {})
    if filename not in docs:
        docs[filename] = {}
    docs[filename].update({k: v for k, v in updates.items() if v is not None})
    ast.save(client_path, state)


_FILE_ICON_CLS = {
    ".pdf":  ("",     "PDF"),
    ".docx": ("docx", "DOCX"),
    ".doc":  ("docx", "DOC"),
    ".xlsx": ("xlsx", "XLSX"),
    ".xls":  ("xlsx", "XLS"),
    ".txt":  ("txt",  "TXT"),
    ".md":   ("txt",  "MD"),
}


def _status_pills_html(f: dict, category: str) -> str:
    """Render the 1-2 status pills for a file row.
    States: pending, extracted, analyzed, failed."""
    if not f["extracted"]:
        return '<span class="file-row-status pending">Pending</span>'

    pills = ['<span class="file-row-status extracted">Extracted</span>']
    if category == "policy":
        failed_pol = state.get("failed_policies") or []
        anal_file  = _analysis_json_path(f["name"])
        if f["name"] in failed_pol and not anal_file.exists():
            pills.append('<span class="file-row-status failed">Failed</span>')
        elif anal_file.exists():
            pills.append('<span class="file-row-status analyzed">Analyzed</span>')
        else:
            pills.append('<span class="file-row-status pending">Pending</span>')
    return " ".join(pills)


def render_doc_card(f: dict, category: str, source_dir: Path, meta_fields_fn) -> None:
    fk = _fkey(f["name"])
    with st.container(key=f"file_row_{fk}", border=True):
        # Full-width error banner (analysis failure persisted across rerun)
        _anal_err_key = f"anal_error_{fk}"
        if _anal_err_key in st.session_state:
            err_msg, err_elapsed = st.session_state.pop(_anal_err_key)
            st.error(f"\u2717 Failed after {_fmt_elapsed(err_elapsed)} \u2014 {err_msg}")

        # Timer placeholder shown above the row during analysis
        _timer_ph = st.empty()

        # File-row layout (Day-2 restyle): icon + name/meta + status pills + button
        ext_cls, ext_label = _FILE_ICON_CLS.get(
            Path(f["name"]).suffix.lower(), ("", "FILE"),
        )

        _is_pol_extracted = (category == "policy" and f["extracted"])
        col_icon, col_text, col_status, btn_col = st.columns(
            [0.5, 4.5, 2, 2.2] if _is_pol_extracted else [0.5, 4.5, 2, 1],
        )
        with col_icon:
            st.markdown(
                f'<div class="file-row-icon {ext_cls}">{ext_label}</div>',
                unsafe_allow_html=True,
            )
        with col_text:
            meta_parts = [f["size_str"]]
            if f.get("page_count"):
                meta_parts.append(f"{f['page_count']} pg")
            if f.get("word_count"):
                _method = f.get("extraction_method", "pdf_text")
                if _method == "ocr":
                    meta_parts.append(f"{f['word_count']:,} words (OCR'd)")
                elif _method == "ocr_failed":
                    meta_parts.append(f"{f['word_count']:,} words — OCR failed")
                elif _method == "empty":
                    meta_parts.append("0 words — extraction failed")
                else:
                    meta_parts.append(f"{f['word_count']:,} words (PDF text)")
            elif f.get("extracted"):
                meta_parts.append("0 words — extraction failed")
            _meta_str = "  ·  ".join(meta_parts)
            st.markdown(
                f'<div class="file-row-name">{f["name"]}</div>'
                f'<div class="file-row-meta">{_meta_str}</div>',
                unsafe_allow_html=True,
            )
        with col_status:
            st.markdown(_status_pills_html(f, category), unsafe_allow_html=True)

        with btn_col:
            if _is_pol_extracted:
                _anal_file  = _analysis_json_path(f["name"])
                _already_read = _anal_file.exists()
                _anal_label = "Re-read Policy" if _already_read else "Read Policy"
                _anal_help  = (
                    "Re-runs the policy reading. Use if the policy was updated or the previous read failed."
                    if _already_read else
                    "Sends this policy to Claude to find coverage gaps, bad exclusions, and problematic endorsements. Takes 2\u201330 min."
                )
                b_analyze, b_del = st.columns([2, 1])
                with b_analyze:
                    if st.button(_anal_label, key=f"anal_{fk}",
                                 use_container_width=True, help=_anal_help):
                        ok, msg, elapsed = analyze_policy_card(f["name"], _timer_ph)
                        if ok:
                            docs = state.setdefault("documents", {})
                            docs.setdefault(f["name"], {})["analysis_duration"] = elapsed
                            fp = state.get("failed_policies") or []
                            if f["name"] in fp:
                                state["failed_policies"] = [n for n in fp if n != f["name"]]
                            ast.save(client_path, state)
                            st.toast(f"\u2713 {f['name']} read in {_fmt_elapsed(elapsed)}.")
                            st.rerun()
                        else:
                            st.session_state[_anal_err_key] = (msg, elapsed)
                            st.rerun()
                with b_del:
                    if st.button("&#128465;", key=f"del_{fk}", help="Delete"):
                        st.session_state[f"confirm_{fk}"] = True
            else:
                if st.button("&#128465;", key=f"del_{fk}", help="Delete"):
                    st.session_state[f"confirm_{fk}"] = True

        if st.session_state.get(f"confirm_{fk}"):
            st.warning(f"Delete **{f['name']}**? This cannot be undone.")
            c1, c2, _ = st.columns([1, 1, 4])
            with c1:
                if st.button("Delete", key=f"yes_{fk}", type="primary"):
                    f["path"].unlink(missing_ok=True)
                    (exchange_dir / f"{Path(f['name']).stem}-extracted.txt").unlink(
                        missing_ok=True)
                    state_key = "contracts" if category == "contract" else "policies"
                    state.get(state_key, {}).pop(f["name"], None)
                    state.get("documents", {}).pop(f["name"], None)
                    removed = ast.purge_policy_findings(state, f["name"])
                    ast.refresh_stage(state)
                    ast.save(client_path, state)
                    del st.session_state[f"confirm_{fk}"]
                    if removed:
                        st.toast(f"Policy deleted \u2014 {removed} finding{'s' if removed != 1 else ''} removed.")
                    else:
                        st.toast(f"{f['name']} deleted.")
                    st.rerun()
            with c2:
                if st.button("Cancel", key=f"no_{fk}"):
                    del st.session_state[f"confirm_{fk}"]
                    st.rerun()

        if meta_fields_fn is not None:
            saved  = _get_saved_meta(f["name"])
            _META_KEYS = ("policy_type", "carrier", "counterparty", "policy_line",
                          "policy_period", "contract_type", "building_count")
            has_meta   = any(saved.get(k) for k in _META_KEYS)
            with st.expander("Metadata (saved)" if has_meta else "Add metadata",
                             expanded=False):
                meta_fields_fn(f["name"], saved, fk)


# ── Per-category metadata field renderers ──────────────────────────

def _policy_meta_fields(filename, saved, fk):
    c1, c2, c3 = st.columns(3)
    with c1:
        pt_idx = POLICY_TYPES.index(saved["policy_type"]) if saved.get("policy_type") in POLICY_TYPES else None
        ptype   = st.selectbox("Policy Type", POLICY_TYPES, index=pt_idx,
                               placeholder="Select type...", key=f"ptype_{fk}")
        carrier = st.text_input("Carrier", value=saved.get("carrier", ""), key=f"car_{fk}")
    with c2:
        pol_num  = st.text_input("Policy Number", value=saved.get("policy_number", ""), key=f"pnum_{fk}")
        eff_date = st.text_input("Effective Date", value=saved.get("effective_date", ""),
                                  placeholder="YYYY-MM-DD", key=f"eff_{fk}")
    with c3:
        exp_date = st.text_input("Expiration Date", value=saved.get("expiration_date", ""),
                                  placeholder="YYYY-MM-DD", key=f"exp_{fk}")
        premium  = st.text_input("Total Premium ($)", value=saved.get("total_premium", ""),
                                  placeholder="e.g. 24500", key=f"prem_{fk}")
    if st.button("Save metadata", key=f"savemeta_{fk}"):
        save_doc_meta(filename, {
            "policy_type": ptype, "carrier": carrier, "policy_number": pol_num,
            "effective_date": eff_date, "expiration_date": exp_date, "total_premium": premium,
        })
        st.toast("Metadata saved.")


def _contract_meta_fields(filename, saved, fk):
    c1, c2, c3 = st.columns(3)
    with c1:
        ct_idx = CONTRACT_TYPES.index(saved["contract_type"]) if saved.get("contract_type") in CONTRACT_TYPES else None
        ctype  = st.selectbox("Contract Type", CONTRACT_TYPES, index=ct_idx,
                              placeholder="Select type...", key=f"ctype_{fk}")
    with c2:
        counterparty = st.text_input("Counterparty Name", value=saved.get("counterparty", ""),
                                      key=f"cparty_{fk}")
    with c3:
        cdate = st.text_input("Contract Date", value=saved.get("contract_date", ""),
                               placeholder="YYYY-MM-DD", key=f"cdate_{fk}")
    if st.button("Save metadata", key=f"savemeta_{fk}"):
        save_doc_meta(filename, {
            "contract_type": ctype, "counterparty": counterparty, "contract_date": cdate,
        })
        st.toast("Metadata saved.")


def _loss_run_meta_fields(filename, saved, fk):
    c1, c2, c3 = st.columns(3)
    with c1:
        pl_idx   = POLICY_LINES.index(saved["policy_line"]) if saved.get("policy_line") in POLICY_LINES else None
        pol_line = st.selectbox("Policy Line", POLICY_LINES, index=pl_idx,
                                placeholder="Select...", key=f"plline_{fk}")
        carrier  = st.text_input("Carrier", value=saved.get("carrier", ""), key=f"lrcar_{fk}")
    with c2:
        period   = st.text_input("Policy Period (Year)", value=saved.get("policy_period", ""),
                                  placeholder="e.g. 2024", key=f"lrper_{fk}")
        incurred = st.text_input("Total Incurred ($)", value=saved.get("total_incurred", ""),
                                  placeholder="e.g. 45000", key=f"lrinc_{fk}")
    with c3:
        paid   = st.text_input("Total Paid ($)", value=saved.get("total_paid", ""),
                                placeholder="e.g. 32000", key=f"lrpaid_{fk}")
        open_c = st.text_input("Open Claims Count", value=saved.get("open_claims_count", ""),
                                placeholder="e.g. 2", key=f"lropen_{fk}")
    if st.button("Save metadata", key=f"savemeta_{fk}"):
        save_doc_meta(filename, {
            "policy_line": pol_line, "carrier": carrier, "policy_period": period,
            "total_incurred": incurred, "total_paid": paid, "open_claims_count": open_c,
        })
        st.toast("Metadata saved.")


def _cope_meta_fields(filename, saved, fk):
    c1, c2 = st.columns(2)
    with c1:
        bldg_count = st.text_input("Building Count", value=saved.get("building_count", ""),
                                    placeholder="e.g. 3", key=f"bldg_{fk}")
        tiv        = st.text_input("Total Insured Value (TIV $)", value=saved.get("tiv", ""),
                                    placeholder="e.g. 4500000", key=f"tiv_{fk}")
    with c2:
        location   = st.text_input("Primary Location Address",
                                    value=saved.get("primary_location", ""), key=f"loc_{fk}")
        ct_idx     = CONSTRUCTION_TYPES.index(saved["construction_type"]) \
                     if saved.get("construction_type") in CONSTRUCTION_TYPES else None
        const_type = st.selectbox("Construction Type", CONSTRUCTION_TYPES, index=ct_idx,
                                   placeholder="Select...", key=f"const_{fk}")
    if st.button("Save metadata", key=f"savemeta_{fk}"):
        save_doc_meta(filename, {
            "building_count": bldg_count, "tiv": tiv,
            "primary_location": location, "construction_type": const_type,
        })
        st.toast("Metadata saved.")


# ══════════════════════════════════════════════════════════════════
#  UPLOAD ZONE + STATUS BANNER HELPERS (Day-2 restyle, 2026-05-12)
# ══════════════════════════════════════════════════════════════════
def _render_upload_zone(
    title: str,
    sub: str,
    uploader_key: str,
    source_dir: Path,
    category: str,
) -> bool:
    """Render the styled upload zone wrapping a Streamlit file_uploader.
    Returns True if new files were saved (caller should st.rerun)."""
    with st.container(key=f"upload_zone_{category}"):
        st.markdown(
            f'<div class="upload-zone-title">{title}</div>'
            f'<div class="upload-zone-sub">{sub}</div>',
            unsafe_allow_html=True,
        )
        ups = st.file_uploader(
            "Drop files",
            type=EXTRACTABLE_EXT,
            accept_multiple_files=True,
            key=uploader_key,
            label_visibility="collapsed",
        )
    if not ups:
        return False
    added, oversized = 0, []
    for u in ups:
        if u.size > MAX_PDF_MB * 1024 * 1024:
            oversized.append(u.name); continue
        if save_doc(u, source_dir, category):
            extract_doc(u.name, source_dir, category)
            added += 1
    if oversized:
        st.warning(f"Skipped (too large): {', '.join(oversized)}")
    return added > 0


def _render_status_banner(files: list[dict], category_label: str) -> None:
    """Render the green (all extracted) or amber (pending) status banner
    above a file list. category_label is e.g. 'policies' or 'contracts'."""
    if not files:
        return
    total     = len(files)
    extracted = sum(1 for f in files if f["extracted"])
    word = "file" if total == 1 else "files"
    if extracted == total:
        st.markdown(
            f'<div class="status-banner">'
            f'<div class="status-banner-check">&#10003;</div>'
            f'<div>'
            f'<div class="status-banner-title">{total} {word} uploaded — all extracted</div>'
            f'<div class="status-banner-sub">All {category_label} ready for synthesis</div>'
            f'</div>'
            f'</div>',
            unsafe_allow_html=True,
        )
    else:
        pending = total - extracted
        pword   = "file" if pending == 1 else "files"
        st.markdown(
            f'<div class="status-banner pending">'
            f'<div class="status-banner-check">!</div>'
            f'<div>'
            f'<div class="status-banner-title">{total} {word} — {pending} {pword} pending extraction</div>'
            f'<div class="status-banner-sub">If a file stays pending, try deleting and re-uploading.</div>'
            f'</div>'
            f'</div>',
            unsafe_allow_html=True,
        )


# ══════════════════════════════════════════════════════════════════
#  TABS — count-suffixed labels (Streamlit strips HTML from tab
#  labels, so counts are plain text in parens, not pill badges).
# ══════════════════════════════════════════════════════════════════
def _count_files(folder: Path) -> int:
    if not folder.exists():
        return 0
    return sum(
        1 for f in folder.iterdir()
        if f.is_file() and not f.name.startswith(".")
        and f.suffix.lower() in EXTRACTABLE_TYPES
    )

_pol_n  = _count_files(policies_dir)
_con_n  = _count_files(contracts_dir)
_lr_n   = _count_files(loss_runs_dir)
_cope_n = _count_files(cope_dir)

def _tab_label(label: str, count: int) -> str:
    return f"{label} ({count})" if count else label

with st.container(key="ta_content"):
    render_stepper(2)

    tab_pol, tab_con, tab_lr, tab_cope_tab, tab_notes = st.tabs([
        _tab_label("Policies",               _pol_n),
        _tab_label("Contracts & Agreements", _con_n),
        _tab_label("Loss Runs & EMOD",       _lr_n),
        _tab_label("COPE / Property",        _cope_n),
        "Notes & Context",
    ])


    # ══════════════════════════════════════════════════════════════════
    #  TAB 1: POLICIES
    # ══════════════════════════════════════════════════════════════════
    with tab_pol:
        pol_files = get_tab_files(policies_dir, "policy")

        if _render_upload_zone(
            title="Drop policy PDFs here, or click to browse",
            sub=f"PDF, DOCX, MD, TXT, XLS, XLSX · up to {MAX_PDF_MB}MB each",
            uploader_key="policy_uploader",
            source_dir=policies_dir,
            category="policy",
        ):
            st.rerun()

        _render_status_banner(pol_files, "policies")

        if pol_files:
            for f in pol_files:
                render_doc_card(f, "policy", policies_dir, None)
        else:
            st.caption("No policy files uploaded yet.")


    # ══════════════════════════════════════════════════════════════════
    #  TAB 2: CONTRACTS & AGREEMENTS
    # ══════════════════════════════════════════════════════════════════
    with tab_con:
        con_files = get_tab_files(contracts_dir, "contract")

        if _render_upload_zone(
            title="Drop contracts here, or click to browse",
            sub=f"PDF, DOCX, MD, TXT, XLS, XLSX · up to {MAX_PDF_MB}MB each",
            uploader_key="contract_uploader",
            source_dir=contracts_dir,
            category="contract",
        ):
            st.rerun()

        _render_status_banner(con_files, "contracts")

        if con_files:
            for f in con_files:
                render_doc_card(f, "contract", contracts_dir, _contract_meta_fields)
        else:
            st.caption("No contracts uploaded yet.")


    # ══════════════════════════════════════════════════════════════════
    #  TAB 3: LOSS RUNS & EMOD
    # ══════════════════════════════════════════════════════════════════
    with tab_lr:
        lr_files = get_tab_files(loss_runs_dir, "loss_run")

        if _render_upload_zone(
            title="Drop loss run PDFs or Excel files here",
            sub=f"PDF, DOCX, MD, TXT, XLS, XLSX · up to {MAX_PDF_MB}MB each",
            uploader_key="loss_run_uploader",
            source_dir=loss_runs_dir,
            category="loss_run",
        ):
            st.rerun()

        _render_status_banner(lr_files, "loss runs")

        if lr_files:
            for f in lr_files:
                render_doc_card(f, "loss_run", loss_runs_dir, _loss_run_meta_fields)
        else:
            st.caption("No loss run files uploaded yet.")

        st.divider()

        # ── Manual entry table ─────────────────────────────────────────
        st.markdown("**Manual Loss History Entry**")
        st.caption(
            "Enter historical loss data directly if you have the data but not a formal loss run."
        )

        if "lr_manual_rows" not in st.session_state:
            st.session_state.lr_manual_rows = list(state.get("loss_runs", []))

        # Column header labels
        if st.session_state.lr_manual_rows:
            hc1, hc2, hc3, hc4, hc5, hc6, _ = st.columns([1.6, 1.8, 1.1, 1.5, 1.5, 1.2, 0.5])
            with hc1: st.caption("Policy Line")
            with hc2: st.caption("Carrier")
            with hc3: st.caption("Year")
            with hc4: st.caption("Total Incurred $")
            with hc5: st.caption("Total Paid $")
            with hc6: st.caption("Open Claims")

        rows_to_delete = []
        for ri, row in enumerate(st.session_state.lr_manual_rows):
            with st.container(border=True):
                c1, c2, c3, c4, c5, c6, cdel = st.columns([1.6, 1.8, 1.1, 1.5, 1.5, 1.2, 0.5])
                with c1:
                    st.selectbox("Line", POLICY_LINES,
                        index=POLICY_LINES.index(row.get("policy_line","GL"))
                              if row.get("policy_line","") in POLICY_LINES else 0,
                        key=f"lr_line_{ri}", label_visibility="collapsed")
                with c2:
                    st.text_input("Carrier", value=row.get("carrier",""),
                        key=f"lr_car_{ri}", placeholder="Carrier",
                        label_visibility="collapsed")
                with c3:
                    st.text_input("Year", value=row.get("policy_period",""),
                        key=f"lr_yr_{ri}", placeholder="Year",
                        label_visibility="collapsed")
                with c4:
                    st.text_input("Incurred", value=row.get("total_incurred",""),
                        key=f"lr_inc_{ri}", placeholder="e.g. 45000",
                        label_visibility="collapsed")
                with c5:
                    st.text_input("Paid", value=row.get("total_paid",""),
                        key=f"lr_paid_{ri}", placeholder="e.g. 32000",
                        label_visibility="collapsed")
                with c6:
                    st.text_input("Open", value=row.get("open_claims_count",""),
                        key=f"lr_open_{ri}", placeholder="# claims",
                        label_visibility="collapsed")
                with cdel:
                    st.markdown("<br>", unsafe_allow_html=True)
                    if st.button("&#128465;", key=f"lr_del_{ri}", help="Remove row"):
                        rows_to_delete.append(ri)

        if rows_to_delete:
            for ri in sorted(rows_to_delete, reverse=True):
                st.session_state.lr_manual_rows.pop(ri)
            st.rerun()

        if not st.session_state.lr_manual_rows:
            st.caption("No manual entries yet.")

        col_add, col_save, _ = st.columns([1.2, 1.2, 4])
        with col_add:
            if st.button("+ Add Row", key="lr_add_row"):
                st.session_state.lr_manual_rows.append({
                    "policy_line": "GL", "carrier": "", "policy_period": "",
                    "total_incurred": "", "total_paid": "", "open_claims_count": "",
                })
                st.rerun()
        with col_save:
            if st.button("Save Table", key="lr_save_manual", type="primary"):
                n = len(st.session_state.lr_manual_rows)
                state["loss_runs"] = [
                    {
                        "policy_line":       st.session_state.get(f"lr_line_{ri}", ""),
                        "carrier":           st.session_state.get(f"lr_car_{ri}",  ""),
                        "policy_period":     st.session_state.get(f"lr_yr_{ri}",   ""),
                        "total_incurred":    st.session_state.get(f"lr_inc_{ri}",  ""),
                        "total_paid":        st.session_state.get(f"lr_paid_{ri}", ""),
                        "open_claims_count": st.session_state.get(f"lr_open_{ri}", ""),
                    }
                    for ri in range(n)
                ]
                ast.save(client_path, state)
                st.toast("Loss history saved.")

        st.divider()

        # ── EMOD ──────────────────────────────────────────────────────
        st.markdown("**Experience Modification Rate (EMOD)**")
        saved_emod = state.get("emod", {})
        ec1, ec2, ec3, ec4 = st.columns(4)
        with ec1:
            cur_emod = st.text_input("Current EMOD", value=saved_emod.get("current", ""),
                                      placeholder="e.g. 0.92", key="emod_cur")
        with ec2:
            p1_emod  = st.text_input("Prior Year 1", value=saved_emod.get("prior_1", ""),
                                      placeholder="e.g. 0.95", key="emod_p1")
        with ec3:
            p2_emod  = st.text_input("Prior Year 2", value=saved_emod.get("prior_2", ""),
                                      placeholder="e.g. 0.98", key="emod_p2")
        with ec4:
            p3_emod  = st.text_input("Prior Year 3", value=saved_emod.get("prior_3", ""),
                                      placeholder="e.g. 1.02", key="emod_p3")
        if st.button("Save EMOD", key="save_emod"):
            state["emod"] = {
                "current": cur_emod, "prior_1": p1_emod,
                "prior_2": p2_emod,  "prior_3": p3_emod,
            }
            ast.save(client_path, state)
            st.toast("EMOD saved.")


    # ══════════════════════════════════════════════════════════════════
    #  TAB 4: COPE / PROPERTY SCHEDULE
    # ══════════════════════════════════════════════════════════════════
    with tab_cope_tab:
        cope_files = get_tab_files(cope_dir, "cope")

        if _render_upload_zone(
            title="Drop property schedules, SOVs, or COPE data here",
            sub=f"PDF, DOCX, MD, TXT, XLS, XLSX · up to {MAX_PDF_MB}MB each",
            uploader_key="cope_uploader",
            source_dir=cope_dir,
            category="cope",
        ):
            st.rerun()

        _render_status_banner(cope_files, "property docs")

        if cope_files:
            for f in cope_files:
                render_doc_card(f, "cope", cope_dir, _cope_meta_fields)
        else:
            st.caption("No COPE / property files uploaded yet.")


    # ══════════════════════════════════════════════════════════════════
    #  TAB 5: NOTES & CONTEXT
    # ══════════════════════════════════════════════════════════════════
    with tab_notes:
        st.subheader("Notes & Context")
        st.caption(
            "Broker observations, risk context, client quirks, and flags "
            "that inform the analysis but don't come from a document."
        )
        st.markdown("<br>", unsafe_allow_html=True)

        saved_notes = state.get("broker_notes", {})

        notes_text = st.text_area(
            "Broker Notes",
            value=saved_notes.get("notes", state.get("client_info", {}).get("notes", "")),
            height=200,
            placeholder=(
                "Add context here: special risk situations, prior incidents, "
                "client concerns, upcoming changes, contract negotiations in progress..."
            ),
            key="broker_notes_text",
        )

        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("**Risk Flags**")
        st.caption("These flags are passed to the analysis engine.")

        saved_flags = saved_notes.get("flags", {})
        flag_values = {
            key: st.checkbox(label, value=saved_flags.get(key, False), key=f"flag_{key}")
            for key, label in FLAG_DEFS
        }

        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("Save Notes & Flags", key="save_notes", type="primary"):
            state["broker_notes"] = {"notes": notes_text, "flags": flag_values}
            state.setdefault("client_info", {})["notes"] = notes_text
            ast.save(client_path, state)
            st.toast("Notes and flags saved.")


    # ── Action bar (white card with Back + Continue) ──────────
    with st.container(key="ta_action_bar", border=True):
        btn_back, btn_spacer, btn_continue = st.columns([2, 5, 3])
        with btn_back:
            if st.button("← Back to Setup", key="di_back", use_container_width=True):
                st.switch_page("pages/1_Client_Setup.py")
        with btn_continue:
            if st.button(
                "Continue to Analyze →",
                key="di_continue",
                type="primary",
                use_container_width=True,
            ):
                st.switch_page("pages/_Analyze.py")

    # ── ai-exchange debug expander (inside .ta-content so it
    #    inherits the 1200px max-width and side padding) ──────────
    st.markdown("<div style='height:18px'></div>", unsafe_allow_html=True)
    with st.expander("Extracted text files (ai-exchange/)"):
        exchange_files = sorted(exchange_dir.glob("*-extracted.txt"))
        if exchange_files:
            for ef in exchange_files:
                st.markdown(f"&#128196; `{ef.name}` — {format_size(ef)}")
            st.caption(f"Path: `{exchange_dir}`")
        else:
            st.caption("No extracted text files yet.")
