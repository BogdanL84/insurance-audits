"""Phase 2B-2 Task 5 driver — v3c full re-run (3 stages, no per-policy re-analysis).

Stage A: Contract re-extraction (4 contracts, 4 calls) — applies new strict-reading
         umbrella_may_satisfy_minimum rule.
Stage B: Synthesis (1 call) — RMF-walk + compressed input + Needs Review category.
Stage C: Cross-policy matrix pass (1 call) — entity + compliance + NOC matrices.

Per-policy analyses are NOT re-run (already healthy per Phase 2A diagnostic).

Outputs to phase-2b-2/:
  contract_extractions_v3c.json    (per-contract aggregate)
  synthesis_v3c.json                (synthesis-only findings)
  matrix_v3c_entity.json            (entity matrix)
  matrix_v3c_compliance.json        (compliance matrix)
  matrix_v3c_noc.json               (NOC matrix)
  matrix_v3c_findings.json          (matrix-pass findings before merge)
  findings_v3c.json                 (merged synthesis + matrix, deduped)
  _stage_a.log / _stage_b.log / _stage_c.log
"""
import json, sys, time
from pathlib import Path

APP = Path(r"C:\Users\Bogdan\Documents\insurance-audits\app")
sys.path.insert(0, str(APP))

from core.claude_runner import (
    run_claude, extract_json,
    build_contract_prompt, build_crossref_prompt,
    ANALYSIS_TIMEOUT, RATE_LIMIT_DELAY,
)
from core.cross_policy import (
    build_entity_matrix, build_contract_compliance_matrix,
    build_designated_entity_noc_matrix, load_universal_kb_block,
    build_cross_policy_matrix_prompt,
)

CLIENT      = Path(r"C:\Users\Bogdan\Documents\insurance-audits\clients\run-test-election-services")
EXCHANGE    = CLIENT / "ai-exchange"
SLUG        = "run-test-election-services"
OUT         = Path(r"C:\Users\Bogdan\Desktop\Run-Test Policies, Contracts\validation-2026-04-27\phase-2b-2")
OUT.mkdir(parents=True, exist_ok=True)

CLIENT_NOTES = (CLIENT / "client-notes.md").read_text(encoding='utf-8', errors='replace')


def _log(stage: str, msg: str):
    print(f"[{stage}] {msg}", flush=True)


# ── STAGE A: contract re-extraction ────────────────────────────────────
def stage_a():
    _log("A", "Contract re-extraction begins. Strict-reading rule applies.")
    contract_files = sorted(EXCHANGE.glob("*-extracted.txt"))
    # Filter to contracts only (skip policy extracted texts)
    contract_files = [
        f for f in contract_files
        if any(kw in f.name.lower() for kw in
               ("maricopa", "sacramento", "los angeles", "douglas county"))
    ]
    _log("A", f"Found {len(contract_files)} contract extracts")

    per_contract: dict = {}
    flat_requirements: list = []
    log_entries = []

    for i, ext_path in enumerate(contract_files, 1):
        # Recover original PDF filename from the extracted-text filename
        orig_pdf = ext_path.name.replace("-extracted.txt", ".pdf")
        text = ext_path.read_text(encoding='utf-8', errors='replace')
        _log("A", f"  ({i}/{len(contract_files)}) {orig_pdf} ({len(text):,} chars)")
        prompt = build_contract_prompt(orig_pdf, text, CLIENT_NOTES)
        t0 = time.time()
        ok, result = run_claude(prompt, timeout=ANALYSIS_TIMEOUT)
        elapsed = time.time() - t0
        log_entries.append({
            "filename": orig_pdf,
            "elapsed_s": round(elapsed, 1),
            "ok": ok,
            "response_chars": len(result or ""),
        })
        if not ok:
            _log("A", f"     FAILED: {result[:200]}")
            continue
        parsed = extract_json(result)
        if not parsed:
            _log("A", f"     PARSE FAILED, saving raw")
            (OUT / f"_stage_a_{orig_pdf}-raw.txt").write_text(result or "", encoding='utf-8')
            continue
        parsed.setdefault("source_file", orig_pdf)
        per_contract[orig_pdf] = parsed
        flat_requirements.extend(parsed.get("requirements", []) or [])

        # Surface the GAP-17 flagship cell from this contract's extraction
        if "maricopa" in orig_pdf.lower():
            auto = (parsed.get("by_coverage") or {}).get("auto_liability") or {}
            if auto:
                _log("A", f"  FLAGSHIP CHECK — Maricopa Auto: "
                          f"min_csl={auto.get('minimum_csl_each_occurrence')}, "
                          f"umbrella_may_satisfy={auto.get('umbrella_may_satisfy_minimum')}")
        time.sleep(RATE_LIMIT_DELAY)

    requirements_data = {
        "client":        SLUG,
        "analysis_date": time.strftime("%Y-%m-%d"),
        "contracts":     per_contract,
        "requirements":  flat_requirements,
    }
    (OUT / "contract_extractions_v3c.json").write_text(
        json.dumps(requirements_data, indent=2, ensure_ascii=False),
        encoding='utf-8',
    )
    (OUT / "_stage_a.log").write_text(
        json.dumps(log_entries, indent=2), encoding='utf-8',
    )
    _log("A", f"Saved contract_extractions_v3c.json — "
              f"{len(per_contract)} contracts, {len(flat_requirements)} flat reqs")
    return requirements_data


# ── STAGE B: synthesis ──────────────────────────────────────────────────
def stage_b(requirements_data: dict):
    _log("B", "Synthesis begins (RMF-walk + compressed input).")

    # Load existing per-policy analyses (NOT re-running them)
    policy_analyses: list = []
    for jf in sorted(EXCHANGE.glob(f"{SLUG}-policy-*-analysis.json")):
        pa = json.load(jf.open(encoding='utf-8'))
        pa.setdefault("_source_file", jf.name)
        policy_analyses.append(pa)
    _log("B", f"Loaded {len(policy_analyses)} per-policy analyses")

    # Compressed synthesis input (Phase 2B-1 fix preserved)
    synthesis_reqs = {
        "client":        requirements_data.get("client"),
        "analysis_date": requirements_data.get("analysis_date"),
        "requirements":  requirements_data.get("requirements") or [],
    }
    _log("B", f"synthesis_reqs JSON size: "
              f"{len(json.dumps(synthesis_reqs)):,} chars (vs full reqs "
              f"{len(json.dumps(requirements_data)):,})")

    prompt = build_crossref_prompt(CLIENT_NOTES, SLUG, synthesis_reqs, policy_analyses)
    _log("B", f"Synthesis prompt size: {len(prompt):,} chars")
    (OUT / "_stage_b_prompt.txt").write_text(prompt, encoding='utf-8')

    t0 = time.time()
    ok, result = run_claude(prompt, timeout=ANALYSIS_TIMEOUT)
    elapsed = time.time() - t0
    _log("B", f"  ok={ok}, elapsed={elapsed:.1f}s, response_chars={len(result or ''):,}")
    (OUT / "_stage_b_response_raw.txt").write_text(result or "", encoding='utf-8')
    if not ok:
        raise RuntimeError(f"Synthesis failed: {result[:500]}")

    parsed = extract_json(result)
    if not parsed or "findings" not in parsed:
        raise RuntimeError("Synthesis JSON parse failed")

    findings = parsed["findings"]
    for f in findings:
        like = f.get("likelihood")
        sev  = f.get("severity")
        if like and sev and "risk_score" not in f:
            f["risk_score"] = int(like) * int(sev)
        elif "risk_score" not in f:
            f["risk_score"] = None

    out = {"client": SLUG, "findings": findings}
    (OUT / "synthesis_v3c.json").write_text(
        json.dumps(out, indent=2, ensure_ascii=False), encoding='utf-8',
    )
    n_ugly   = sum(1 for f in findings if f.get("category") == "Ugly")
    n_bad    = sum(1 for f in findings if f.get("category") == "Bad")
    n_review = sum(1 for f in findings if f.get("category") in ("Review", "Needs Review"))
    n_good   = sum(1 for f in findings if f.get("category") == "Good")
    _log("B", f"Synthesis: {len(findings)} findings — "
              f"{n_ugly}U, {n_bad}B, {n_review}R, {n_good}G")
    return findings, policy_analyses


# ── STAGE C: cross-policy matrix pass ───────────────────────────────────
def stage_c(requirements_data: dict, findings: list, policy_analyses: list):
    _log("C", "Cross-policy matrix pass begins.")
    contracts_data = (requirements_data or {}).get("contracts", {}) or {}

    em = build_entity_matrix(policy_analyses)
    cm = build_contract_compliance_matrix(contracts_data, policy_analyses)
    nm = build_designated_entity_noc_matrix(contracts_data, policy_analyses)

    (OUT / "matrix_v3c_entity.json").write_text(
        json.dumps(em, indent=2, ensure_ascii=False), encoding='utf-8')
    (OUT / "matrix_v3c_compliance.json").write_text(
        json.dumps(cm, indent=2, ensure_ascii=False), encoding='utf-8')
    (OUT / "matrix_v3c_noc.json").write_text(
        json.dumps(nm, indent=2, ensure_ascii=False), encoding='utf-8')

    # Flagship Maricopa Auto cell — verify the strict-reading flip
    for row in cm.get("rows", []):
        if "maricopa" in (row.get("contract") or "").lower() and row.get("coverage_line") == "auto_liability":
            for src, cell in (row.get("policy_check") or {}).items():
                _log("C", f"  FLAGSHIP — Maricopa Auto: "
                          f"req={row.get('requirement_summary')}, "
                          f"actual=${cell.get('primary_limit_value')}, "
                          f"umbrella={'permitted' if row.get('umbrella_may_satisfy_minimum') else 'BARRED'}, "
                          f"verdict={cell.get('verdict')}, "
                          f"hint={cell.get('severity_hint')}")
            break

    n_inc   = len(em.get("inconsistencies", []))
    s_summ  = cm.get("summary", {}) or {}
    n_short = s_summ.get("shortfall", 0)
    n_viol  = s_summ.get("violation", 0)
    n_miss  = s_summ.get("missing_policy", 0)
    n_asym  = len(nm.get("asymmetries", []))
    _log("C", f"Matrix construction: {n_inc} entity inconsistencies, "
              f"{n_short} shortfalls + {n_viol} violations + {n_miss} missing-policy, "
              f"{n_asym} NOC asymmetries.")

    if n_inc + n_short + n_viol + n_miss + n_asym == 0:
        _log("C", "No cross-cutting defects in matrices — skipping AI pass.")
        return findings  # unchanged

    time.sleep(RATE_LIMIT_DELAY)
    kb = load_universal_kb_block()
    cp_prompt = build_cross_policy_matrix_prompt(
        CLIENT_NOTES, SLUG, em, cm, nm, kb, findings, policy_analyses, contracts_data,
    )
    (OUT / "_stage_c_prompt.txt").write_text(cp_prompt, encoding='utf-8')
    _log("C", f"Matrix prompt size: {len(cp_prompt):,} chars")

    t0 = time.time()
    ok, result = run_claude(cp_prompt, timeout=ANALYSIS_TIMEOUT)
    elapsed = time.time() - t0
    _log("C", f"  ok={ok}, elapsed={elapsed:.1f}s, response_chars={len(result or ''):,}")
    (OUT / "_stage_c_response_raw.txt").write_text(result or "", encoding='utf-8')
    if not ok:
        _log("C", f"Matrix pass FAILED: {result[:400]} — keeping synthesis findings only")
        return findings

    parsed = extract_json(result)
    if not parsed or "findings" not in parsed:
        _log("C", "Matrix JSON parse failed — keeping synthesis findings only")
        return findings

    new_findings = parsed["findings"]
    (OUT / "matrix_v3c_findings.json").write_text(
        json.dumps({"client": SLUG, "findings": new_findings}, indent=2, ensure_ascii=False),
        encoding='utf-8',
    )
    _log("C", f"Matrix pass produced {len(new_findings)} findings")

    # Dedupe and merge into the synthesis findings list
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
        like, sev = nf.get("likelihood"), nf.get("severity")
        if like and sev:
            nf["risk_score"] = int(like) * int(sev)
        elif "risk_score" not in nf:
            nf["risk_score"] = None
        findings.append(nf)
        added += 1
    _log("C", f"Merged: {added} new findings (after de-dup)")
    return findings


# ── Run pipeline ────────────────────────────────────────────────────────
if __name__ == "__main__":
    overall_start = time.time()

    requirements_data = stage_a()
    print()
    findings, policy_analyses = stage_b(requirements_data)
    print()
    findings = stage_c(requirements_data, findings, policy_analyses)

    # Save final merged findings
    final_obj = {"client": SLUG, "findings": findings}
    (OUT / "findings_v3c.json").write_text(
        json.dumps(final_obj, indent=2, ensure_ascii=False),
        encoding='utf-8',
    )

    n_ugly   = sum(1 for f in findings if f.get("category") == "Ugly")
    n_bad    = sum(1 for f in findings if f.get("category") == "Bad")
    n_review = sum(1 for f in findings if f.get("category") in ("Review", "Needs Review"))
    n_good   = sum(1 for f in findings if f.get("category") == "Good")
    n_xpm    = sum(1 for f in findings if "cross-policy-matrix" in (f.get("tags") or []))

    elapsed_total = time.time() - overall_start
    print()
    print("=" * 60)
    print(f"v3c PIPELINE COMPLETE — {elapsed_total/60:.1f} min total")
    print(f"Findings: {len(findings)} = {n_ugly}U + {n_bad}B + {n_review}R + {n_good}G")
    print(f"Of which {n_xpm} cross-policy-matrix tagged")
    print(f"Saved to: {OUT}")
