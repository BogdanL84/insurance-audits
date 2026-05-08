"""
Headless equivalent of the Streamlit Analyze page's "Review Full Program" mode,
scoped to Precision Aero. Runs synthesis → cross-policy intel → matrix passes,
persisting after each stage.
"""

import json
import sys
import time
import warnings
from datetime import datetime
from pathlib import Path

warnings.filterwarnings("ignore")
try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT / "app"))

from core import audit_state as ast
from core.claude_runner import (
    run_claude, extract_json,
    build_crosspolicy_prompt,
    ANALYSIS_TIMEOUT, RATE_LIMIT_DELAY,
)
from core.chunking import run_chunked_synthesis
from core.cross_policy import (
    build_entity_matrix,
    build_contract_compliance_matrix,
    build_designated_entity_noc_matrix,
    load_universal_kb_block,
    build_cross_policy_matrix_prompt,
)

CLIENT  = ROOT / "clients" / "precision-aero"
SLUG    = "precision-aero"
EXCHDIR = CLIENT / "ai-exchange"
OUTDIR  = CLIENT / "output"


def _persist_stage(state: dict, stage_name: str, findings: list) -> None:
    """Mirror of _Analyze.py:_persist_stage_findings (atomic per-stage save)."""
    OUTDIR.mkdir(parents=True, exist_ok=True)
    if stage_name == "final":
        target = OUTDIR / "findings.json"
        stage_label = "audited"
    else:
        target = OUTDIR / f"findings_{stage_name}.json"
        stage_label = {
            "synthesis":   "synthesized",
            "crosspolicy": "cross_policy_reviewed",
        }.get(stage_name, stage_name)
    payload = {
        "client":        SLUG,
        "stage":         stage_label,
        "saved_at":      datetime.now().isoformat(),
        "finding_count": len(findings),
        "findings":      findings,
    }
    tmp = target.with_suffix(target.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    tmp.replace(target)
    state["findings"] = findings
    state["stage"]    = stage_label
    ast.save(CLIENT, state)
    print(f"    -> Saved {len(findings)} findings to {target.name} (stage: {stage_label})")


def _client_notes() -> str:
    p = CLIENT / "client-notes.md"
    return p.read_text(encoding="utf-8") if p.exists() else ""


def _attach_risk(findings: list) -> None:
    for f in findings:
        like = f.get("likelihood")
        sev  = f.get("severity")
        if like and sev:
            try:
                f["risk_score"] = int(like) * int(sev)
            except (TypeError, ValueError):
                f.setdefault("risk_score", None)
        else:
            f.setdefault("risk_score", None)


def main():
    state = ast.load(CLIENT)
    notes = _client_notes()

    # ── Load all per-policy analyses ───────────────────────────────
    policy_analyses = []
    for jf in sorted(EXCHDIR.glob(f"{SLUG}-policy-*-analysis.json")):
        try:
            pa = json.loads(jf.read_text(encoding="utf-8"))
            pa.setdefault("_source_file", jf.name)
            policy_analyses.append(pa)
        except Exception as e:
            print(f"  ! Skipping {jf.name}: {e}")
    print(f"Loaded {len(policy_analyses)} policy analyses.")
    for pa in policy_analyses:
        sf = pa.get("_source_file") or pa.get("source_file") or "?"
        pt = pa.get("policy_type", "?")
        print(f"  - {sf}: type={pt}")

    if len(policy_analyses) < 2:
        print("FATAL: Need at least 2 analyses to run a multi-policy synthesis.")
        sys.exit(1)

    has_crossref = True
    requirements_data = {"requirements": [], "client": SLUG}
    contracts_data = {}

    # Archive prior findings
    prior_findings = state.get("findings", [])
    if prior_findings:
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
        print(f"Archived {len(prior_findings)} prior findings into prior_runs.")

    grand_t0 = time.time()

    # ── Stage 1: Synthesis (auto-chunked) ──────────────────────────
    print("\n=== STAGE 1: Synthesis ===")
    s_t0 = time.time()
    def _progress(label, frac):
        print(f"  [{int(time.time() - s_t0):>4}s]  {label}")
    findings, synth_meta = run_chunked_synthesis(
        notes,
        SLUG,
        requirements_data,
        policy_analyses,
        timeout=ANALYSIS_TIMEOUT,
        progress_callback=_progress,
    )
    s_elapsed = time.time() - s_t0
    print(f"\nSynthesis done in {s_elapsed:.0f}s")
    print(f"  mode={synth_meta.get('mode')}, "
          f"chunks={len(synth_meta.get('chunks') or [])}, "
          f"errors={len(synth_meta.get('errors') or [])}")
    print(f"  findings: {len(findings)}")

    if any("RATE_LIMIT" in (msg or "") for _, msg in (synth_meta.get("errors") or [])):
        print("RATE_LIMIT hit during synthesis — stopping.")
        sys.exit(2)

    if not findings:
        print("Synthesis produced no findings.")
        for err in synth_meta.get("errors") or []:
            print(f"  err: {err}")
        sys.exit(2)

    _persist_stage(state, "synthesis", findings)

    # ── Stage 2: Cross-policy intelligence pass ────────────────────
    print("\n=== STAGE 2: Cross-policy intelligence ===")
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
    cp_prompt = build_crosspolicy_prompt(compressed, policy_analyses)
    cp_t0 = time.time()
    print(f"  prompt={len(cp_prompt):,} chars; running...")
    ok, result = run_claude(cp_prompt, timeout=300)
    cp_elapsed = time.time() - cp_t0
    if not ok:
        print(f"  ! Cross-policy pass failed in {cp_elapsed:.0f}s: {str(result)[:200]}")
    else:
        parsed = extract_json(result)
        if parsed and "findings" in parsed:
            findings = parsed["findings"]
            _attach_risk(findings)
            n_covered = sum(1 for f in findings if f.get("covered_by_other_policy"))
            print(f"  ok in {cp_elapsed:.0f}s: {len(findings)} findings; {n_covered} covered_by_other_policy.")
            _persist_stage(state, "crosspolicy", findings)
        else:
            print(f"  ! Cross-policy pass JSON parse failed; keeping synthesis findings.")
            (EXCHDIR / f"{SLUG}-crosspolicy-RAW.txt").write_text(result or "", encoding="utf-8")

    # ── Stage 3: Cross-policy matrix construction ──────────────────
    print("\n=== STAGE 3: Cross-policy matrix ===")
    em = build_entity_matrix(policy_analyses)
    cm = build_contract_compliance_matrix(contracts_data, policy_analyses)
    nm = build_designated_entity_noc_matrix(contracts_data, policy_analyses)

    (EXCHDIR / f"{SLUG}-entity-matrix.json").write_text(
        json.dumps(em, indent=2, ensure_ascii=False), encoding="utf-8")
    (EXCHDIR / f"{SLUG}-compliance-matrix.json").write_text(
        json.dumps(cm, indent=2, ensure_ascii=False), encoding="utf-8")
    (EXCHDIR / f"{SLUG}-noc-matrix.json").write_text(
        json.dumps(nm, indent=2, ensure_ascii=False), encoding="utf-8")
    print("  wrote entity-matrix, compliance-matrix, noc-matrix JSONs.")

    n_inc   = len(em.get("inconsistencies", []))
    s_summ  = cm.get("summary", {}) or {}
    n_short = s_summ.get("shortfall", 0)
    n_viol  = s_summ.get("violation", 0)
    n_miss  = s_summ.get("missing_policy", 0)
    n_asym  = len(nm.get("asymmetries", []))
    print(f"  defects: {n_inc} entity inc, {n_short} shortfall, "
          f"{n_viol} violation, {n_miss} missing-policy, {n_asym} NOC asym.")

    if n_inc + n_short + n_viol + n_miss + n_asym > 0:
        print("  running cross-policy matrix AI pass...")
        time.sleep(RATE_LIMIT_DELAY)
        kb = load_universal_kb_block()
        m_prompt = build_cross_policy_matrix_prompt(
            notes, SLUG, em, cm, nm, kb, findings, policy_analyses, contracts_data,
        )
        m_t0 = time.time()
        print(f"  prompt={len(m_prompt):,} chars; running...")
        ok, result = run_claude(m_prompt, timeout=ANALYSIS_TIMEOUT)
        m_elapsed = time.time() - m_t0
        if ok:
            parsed = extract_json(result)
            if parsed and "findings" in parsed:
                new_findings = parsed["findings"]
                existing_keys = {
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
                    findings.append(nf)
                    added += 1
                _attach_risk(findings)
                print(f"  ok in {m_elapsed:.0f}s: {added} new finding(s) added.")
            else:
                print(f"  ! matrix pass JSON parse failed in {m_elapsed:.0f}s.")
                (EXCHDIR / f"{SLUG}-crosspolicy-matrix-RAW.txt").write_text(result or "", encoding="utf-8")
        else:
            print(f"  ! matrix pass failed in {m_elapsed:.0f}s: {str(result)[:200]}")
    else:
        print("  no cross-cutting defects → skipping matrix AI pass.")

    # ── Final persist ──────────────────────────────────────────────
    print("\n=== FINAL ===")
    policy_type_counts: dict = {}
    for pa in policy_analyses:
        pt = pa.get("policy_type") or "Unknown"
        policy_type_counts[pt] = policy_type_counts.get(pt, 0) + 1
    state["policy_type_counts"] = policy_type_counts
    state["last_analysis_date"] = datetime.now().isoformat()
    _persist_stage(state, "final", findings)

    (EXCHDIR / f"{SLUG}-findings.json").write_text(
        json.dumps({"client": SLUG, "findings": findings}, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    grand = time.time() - grand_t0

    n_ugly = sum(1 for f in findings if f.get("category") == "Ugly")
    n_bad  = sum(1 for f in findings if f.get("category") == "Bad")
    n_rev  = sum(1 for f in findings if f.get("category") in ("Review", "Needs Review"))
    n_good = sum(1 for f in findings if f.get("category") == "Good")
    n_info = sum(1 for f in findings if f.get("category") == "Informational")
    print(f"\nDONE in {grand:.0f}s ({grand/60:.1f} min)")
    print(f"  Total findings: {len(findings)}")
    print(f"   Ugly: {n_ugly}")
    print(f"   Bad: {n_bad}")
    print(f"   Review: {n_rev}")
    print(f"   Good: {n_good}")
    print(f"   Informational: {n_info}")


if __name__ == "__main__":
    main()
