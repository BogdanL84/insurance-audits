"""v3d chunk-1 split driver — sub-chunks 1A and 1B (replacing the hung
220 KB Chunk 1 from the original 3-chunk v3d run on 2026-04-30).

Sub-chunk 1A: Hanover Commercial Package + Hanover Auto    (~176 KB prompt)
Sub-chunk 1B: Hanover Commercial Umbrella + Security Guards CGL (~146 KB prompt)

Reuses (loaded from disk, not regenerated):
  - contract_extractions_v3c-postpin.json
  - 9 per-policy analyses
  - synthesis_v3d_chunk2.json (Pro/Cyber findings; _chunk='pro-cyber')
  - synthesis_v3d_chunk3.json (ML/WC findings; _chunk='ml-wc')

Outputs to phase-2b-2/ - all carry '-split' or '1A/1B' suffix to avoid
overwriting the original v3d artifacts:
  _stage_b_v3d_chunk1A_prompt.txt + _stage_b_v3d_chunk1A_response_raw.txt
  _stage_b_v3d_chunk1B_prompt.txt + _stage_b_v3d_chunk1B_response_raw.txt
  synthesis_v3d_chunk1A.json + synthesis_v3d_chunk1B.json
  synthesis_v3d-split.json    (merged 1A + 1B + existing chunk2 + existing chunk3)
  matrix_v3d-split_entity.json + matrix_v3d-split_compliance.json + matrix_v3d-split_noc.json
  matrix_v3d-split_findings.json
  _stage_c_v3d-split_prompt.txt + _stage_c_v3d-split_response_raw.txt
  findings_v3d-split.json     (final)
  chunk_metrics_split.json    (per-sub-chunk timings)
"""
import json, sys, time
from pathlib import Path

APP = Path(r"C:\Users\Bogdan\Documents\insurance-audits\app")
sys.path.insert(0, str(APP))

from core.claude_runner import (
    run_claude, extract_json, build_crossref_prompt, ANALYSIS_TIMEOUT,
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

CLIENT_NOTES = (CLIENT / "client-notes.md").read_text(encoding='utf-8', errors='replace')

# Keywords identifying the 4 core-liability policies (the ones that lived in
# the hung Chunk 1 of the original v3d_chunked run). Used to filter the 9
# policies down to the ones we're re-running. Verified 2026-04-30 preflight.
CORE_LIB_KEYWORDS = [
    "hanover - commercial - ",      # trailing ' - ' so it does NOT match umbrella
    "hanover - auto",
    "hanover - commercial umbrella",
    "security guards",
]

SUBCHUNKS = [
    {
        "name":    "core-1A",
        "label":   "Sub-chunk 1A - Commercial Package + Auto",
        "matches": ["hanover - commercial - ", "hanover - auto"],
    },
    {
        "name":    "core-1B",
        "label":   "Sub-chunk 1B - Umbrella + Security Guards CGL",
        "matches": ["hanover - commercial umbrella", "security guards"],
    },
]


def _log(msg: str):
    print(f"[v3d-split] {msg}", flush=True)


def _is_core_liability(pa: dict) -> bool:
    src = (pa.get("_source_file") or pa.get("policy_file") or "").lower()
    return any(kw in src for kw in CORE_LIB_KEYWORDS)


def _assign_to_subchunks(core_analyses: list) -> list:
    """Partition the 4 core-liability analyses into 1A / 1B. Asserts each
    matches exactly one sub-chunk."""
    assignments = [(c, []) for c in SUBCHUNKS]
    leftovers = []
    for pa in core_analyses:
        src = (pa.get("_source_file") or pa.get("policy_file") or "").lower()
        matched = []
        for sub_def, bucket in assignments:
            if any(kw.lower() in src for kw in sub_def["matches"]):
                matched.append((sub_def["name"], bucket))
        if len(matched) == 1:
            matched[0][1].append(pa)
        elif len(matched) == 0:
            leftovers.append(src)
        else:
            raise AssertionError(
                f"Policy {src!r} matched multiple sub-chunks: {[m[0] for m in matched]}"
            )
    if leftovers:
        raise AssertionError(f"Unassigned core-liability policies: {leftovers}")
    for sub_def, bucket in assignments:
        if not bucket:
            raise AssertionError(f"Sub-chunk {sub_def['name']!r} got 0 policies")
    return assignments


def run_subchunk(sub_def: dict, analyses: list, requirements_data: dict, idx_label: str) -> tuple:
    """Synthesize one sub-chunk. Returns (ok, findings, metrics_dict).
    Behaviorally identical to run_chunk in _run_v3d_chunked.py; the only
    differences are the output-filename suffix (idx_label like '1A')
    and the _chunk tag value."""
    _log(f"=== {sub_def['label']} ===")
    _log(f"  policies: {len(analyses)}")
    for pa in analyses:
        src = pa.get("_source_file") or pa.get("policy_file") or "?"
        _log(f"    - {src}")

    synthesis_reqs = {
        "client":        requirements_data.get("client"),
        "analysis_date": requirements_data.get("analysis_date"),
        "requirements":  requirements_data.get("requirements") or [],
    }

    prompt = build_crossref_prompt(CLIENT_NOTES, SLUG, synthesis_reqs, analyses)
    _log(f"  prompt size: {len(prompt):,} chars")
    (OUT / f"_stage_b_v3d_chunk{idx_label}_prompt.txt").write_text(prompt, encoding='utf-8')

    t0 = time.time()
    ok, result = run_claude(prompt, timeout=ANALYSIS_TIMEOUT)
    elapsed = time.time() - t0
    _log(f"  ok={ok}, elapsed={elapsed:.1f}s, response_chars={len(result or ''):,}")
    (OUT / f"_stage_b_v3d_chunk{idx_label}_response_raw.txt").write_text(result or "", encoding='utf-8')

    metrics = {
        "chunk":          sub_def["name"],
        "label":          sub_def["label"],
        "policy_count":   len(analyses),
        "prompt_chars":   len(prompt),
        "response_chars": len(result or ""),
        "elapsed_s":      round(elapsed, 1),
        "ok":             ok,
        "cache_read_input_tokens": None,  # text mode doesn't surface
        "input_tokens_total":      None,
        "output_tokens_total":     None,
    }

    if not ok:
        _log(f"  FAILED: {(result or '')[:300]}")
        return False, [], metrics

    parsed = extract_json(result)
    if not parsed or "findings" not in parsed:
        _log(f"  PARSE FAILED - saved raw response")
        metrics["parse_failed"] = True
        return False, [], metrics

    findings = parsed["findings"]
    for f in findings:
        f["_chunk"] = sub_def["name"]   # 'core-1A' or 'core-1B'
        like = f.get("likelihood")
        sev  = f.get("severity")
        if like and sev and "risk_score" not in f:
            f["risk_score"] = int(like) * int(sev)
        elif "risk_score" not in f:
            f["risk_score"] = None

    (OUT / f"synthesis_v3d_chunk{idx_label}.json").write_text(
        json.dumps({"client": SLUG, "chunk": sub_def["name"], "findings": findings},
                   indent=2, ensure_ascii=False),
        encoding='utf-8',
    )

    n_ugly = sum(1 for f in findings if f.get("category") == "Ugly")
    n_bad  = sum(1 for f in findings if f.get("category") == "Bad")
    n_review = sum(1 for f in findings if f.get("category") in ("Review", "Needs Review"))
    n_good = sum(1 for f in findings if f.get("category") == "Good")
    _log(f"  findings: {len(findings)} = {n_ugly}U + {n_bad}B + {n_review}R + {n_good}G")
    metrics.update({
        "findings_total":  len(findings),
        "findings_ugly":   n_ugly,
        "findings_bad":    n_bad,
        "findings_review": n_review,
        "findings_good":   n_good,
    })
    return True, findings, metrics


def merge_chunks(chunk_findings_lists: list) -> tuple:
    """Merge synthesis findings across N chunks.
    Bad/Ugly: dedupe by (requirement_type, policy_file or 'MULTI');
              keep highest risk_score on collision.
    Good / Needs Review: keep all (per-policy by nature).
    Returns (merged_findings_list, dup_log_list)."""
    seen_keys: dict = {}
    merged: list = []
    dup_log: list = []
    for findings in chunk_findings_lists:
        for f in findings:
            cat = f.get("category")
            if cat in ("Bad", "Ugly"):
                key = (
                    (f.get("requirement_type") or "").strip(),
                    (f.get("policy_file") or "MULTI").strip(),
                )
                if key in seen_keys:
                    prev = seen_keys[key]
                    prev_score = prev.get("risk_score") or 0
                    cur_score  = f.get("risk_score") or 0
                    keep = f if cur_score > prev_score else prev
                    drop = prev if keep is f else f
                    dup_log.append({
                        "requirement_type":   key[0],
                        "policy_file":        key[1],
                        "kept_chunk":         keep.get("_chunk"),
                        "dropped_chunk":      drop.get("_chunk"),
                        "kept_risk_score":    keep.get("risk_score"),
                        "dropped_risk_score": drop.get("risk_score"),
                    })
                    if keep is f:
                        merged[merged.index(prev)] = f
                        seen_keys[key] = f
                else:
                    seen_keys[key] = f
                    merged.append(f)
            else:
                merged.append(f)
    return merged, dup_log


def stage_c_matrix_pass(requirements_data: dict, findings: list, all_policy_analyses: list) -> list:
    """Cross-policy matrix pass against all 9 policies. Outputs all carry
    '-split' suffix to avoid overwriting the prior v3d run's matrix files."""
    _log("Stage C - Cross-policy matrix pass (split run).")
    contracts_data = (requirements_data or {}).get("contracts", {}) or {}

    em = build_entity_matrix(all_policy_analyses)
    cm = build_contract_compliance_matrix(contracts_data, all_policy_analyses)
    nm = build_designated_entity_noc_matrix(contracts_data, all_policy_analyses)

    (OUT / "matrix_v3d-split_entity.json").write_text(
        json.dumps(em, indent=2, ensure_ascii=False), encoding='utf-8')
    (OUT / "matrix_v3d-split_compliance.json").write_text(
        json.dumps(cm, indent=2, ensure_ascii=False), encoding='utf-8')
    (OUT / "matrix_v3d-split_noc.json").write_text(
        json.dumps(nm, indent=2, ensure_ascii=False), encoding='utf-8')

    n_inc   = len(em.get("inconsistencies", []))
    s_summ  = cm.get("summary", {}) or {}
    n_short = s_summ.get("shortfall", 0)
    n_viol  = s_summ.get("violation", 0)
    n_miss  = s_summ.get("missing_policy", 0)
    n_asym  = len(nm.get("asymmetries", []))
    _log(f"  Matrix construction: {n_inc} entity, "
         f"{n_short}+{n_viol}+{n_miss} short+viol+missing, {n_asym} NOC asym")

    if n_inc + n_short + n_viol + n_miss + n_asym == 0:
        _log("  No cross-cutting defects - skipping AI pass.")
        return findings

    kb = load_universal_kb_block()
    cp_prompt = build_cross_policy_matrix_prompt(
        CLIENT_NOTES, SLUG, em, cm, nm, kb, findings, all_policy_analyses, contracts_data,
    )
    (OUT / "_stage_c_v3d-split_prompt.txt").write_text(cp_prompt, encoding='utf-8')
    _log(f"  Matrix prompt size: {len(cp_prompt):,} chars")

    t0 = time.time()
    ok, result = run_claude(cp_prompt, timeout=ANALYSIS_TIMEOUT)
    elapsed = time.time() - t0
    _log(f"  ok={ok}, elapsed={elapsed:.1f}s, response_chars={len(result or ''):,}")
    (OUT / "_stage_c_v3d-split_response_raw.txt").write_text(result or "", encoding='utf-8')
    if not ok:
        _log(f"  Matrix pass FAILED: {(result or '')[:400]} - keeping synthesis findings only")
        return findings

    parsed = extract_json(result)
    if not parsed or "findings" not in parsed:
        _log("  Matrix JSON parse failed - keeping synthesis findings only")
        return findings

    new_findings = parsed["findings"]
    (OUT / "matrix_v3d-split_findings.json").write_text(
        json.dumps({"client": SLUG, "findings": new_findings}, indent=2, ensure_ascii=False),
        encoding='utf-8',
    )
    _log(f"  Matrix pass produced {len(new_findings)} findings")

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
    _log(f"  Merged: {added} new findings (after de-dup)")
    return findings


# Main
if __name__ == "__main__":
    overall_t0 = time.time()

    # Reuse contract data from earlier today
    contract_path = OUT / "contract_extractions_v3c-postpin.json"
    requirements_data = json.load(contract_path.open(encoding='utf-8'))
    _log(f"Loaded contract data from {contract_path.name}: "
         f"{len(requirements_data.get('contracts') or {})} contracts, "
         f"{len(requirements_data.get('requirements') or [])} flat reqs")

    # Load all 9 per-policy analyses (full list - needed for matrix pass)
    all_policy_analyses: list = []
    for jf in sorted(EXCHANGE.glob(f"{SLUG}-policy-*-analysis.json")):
        pa = json.load(jf.open(encoding='utf-8'))
        pa.setdefault("_source_file", jf.name)
        all_policy_analyses.append(pa)
    _log(f"Loaded {len(all_policy_analyses)} per-policy analyses")

    # Filter to the 4 core-liability ones for sub-chunk synthesis
    core_lib_analyses = [pa for pa in all_policy_analyses if _is_core_liability(pa)]
    _log(f"Core-liability subset: {len(core_lib_analyses)} policies")
    assert len(core_lib_analyses) == 4, (
        f"Expected 4 core-liability policies, got {len(core_lib_analyses)}"
    )

    # Assign into 1A / 1B
    sub_assignments = _assign_to_subchunks(core_lib_analyses)
    for sub_def, analyses in sub_assignments:
        _log(f"  {sub_def['name']}: {len(analyses)} policies")

    # Run each sub-chunk
    sub_findings: list = []
    sub_metrics: list  = []
    failures = 0
    for (sub_def, analyses), label in zip(sub_assignments, ["1A", "1B"]):
        ok, findings, metrics = run_subchunk(sub_def, analyses, requirements_data, label)
        sub_findings.append(findings)
        sub_metrics.append(metrics)
        if not ok:
            failures += 1
            if failures >= 2:
                _log("STOP: both sub-chunks failed. ~146 KB is hitting the same threshold "
                     "as 220 KB. Saving partial state and exiting.")
                (OUT / "chunk_metrics_split.json").write_text(
                    json.dumps({"sub_chunks": sub_metrics, "stop_reason": "both sub-chunks failed"},
                               indent=2, ensure_ascii=False),
                    encoding='utf-8',
                )
                sys.exit(2)

    # Load existing chunk2 / chunk3 synthesis findings (already validated good
    # in the 2026-04-30 v3d_chunked run; their _chunk tags ride along).
    existing_chunks: list = []
    for label in ("chunk2", "chunk3"):
        p = OUT / f"synthesis_v3d_{label}.json"
        data = json.load(p.open(encoding='utf-8'))
        existing_chunks.append(data["findings"])
        _log(f"Loaded {len(data['findings'])} findings from {p.name} "
             f"(chunk={data.get('chunk','?')!r})")

    # Merge order: 1A, 1B, existing chunk2, existing chunk3
    all_chunk_lists = sub_findings + existing_chunks
    merged, dup_log = merge_chunks(all_chunk_lists)
    _log(f"Merged synthesis: {len(merged)} findings "
         f"(across {sum(len(c) for c in all_chunk_lists)} pre-merge); "
         f"{len(dup_log)} duplicates collapsed")
    for d in dup_log:
        _log(f"  DUP: {d['requirement_type']!r} | {d['policy_file']!r} | "
             f"kept={d['kept_chunk']}({d['kept_risk_score']}) "
             f"dropped={d['dropped_chunk']}({d['dropped_risk_score']})")

    (OUT / "synthesis_v3d-split.json").write_text(
        json.dumps({"client": SLUG, "findings": merged, "duplicates_collapsed": dup_log},
                   indent=2, ensure_ascii=False),
        encoding='utf-8',
    )

    chunk_metrics_payload = {
        "sub_chunks": sub_metrics,
        "merge_stats": {
            "sub_chunk_findings_total":  sum(len(fs) for fs in sub_findings),
            "existing_chunks_loaded":    [len(c) for c in existing_chunks],
            "pre_merge_total":           sum(len(fs) for fs in all_chunk_lists),
            "post_merge_total":          len(merged),
            "duplicates_collapsed":      len(dup_log),
        },
        "elapsed_total_s": round(time.time() - overall_t0, 1),
        "metrics_capture_note": (
            "cache_read_input_tokens / input_tokens_total / output_tokens_total "
            "are None because the runner uses --output-format text. To capture "
            "these, switch run_claude to --output-format json (with envelope unwrap) "
            "or stream-json (with line-by-line parsing) and read the usage block."
        ),
    }
    (OUT / "chunk_metrics_split.json").write_text(
        json.dumps(chunk_metrics_payload, indent=2, ensure_ascii=False),
        encoding='utf-8',
    )

    findings_final = stage_c_matrix_pass(requirements_data, merged, all_policy_analyses)

    (OUT / "findings_v3d-split.json").write_text(
        json.dumps({"client": SLUG, "findings": findings_final}, indent=2, ensure_ascii=False),
        encoding='utf-8',
    )

    n_ugly  = sum(1 for f in findings_final if f.get("category") == "Ugly")
    n_bad   = sum(1 for f in findings_final if f.get("category") == "Bad")
    n_review = sum(1 for f in findings_final if f.get("category") in ("Review", "Needs Review"))
    n_good  = sum(1 for f in findings_final if f.get("category") == "Good")
    n_xpm   = sum(1 for f in findings_final if "cross-policy-matrix" in (f.get("tags") or []))
    elapsed_total = time.time() - overall_t0

    print()
    print("=" * 60)
    print(f"v3d SPLIT PIPELINE COMPLETE - {elapsed_total/60:.1f} min total")
    print(f"Sub-chunk timings:")
    for m in sub_metrics:
        print(f"  {m['chunk']:>16}  prompt={m['prompt_chars']:>7,}  "
              f"resp={m.get('response_chars',0):>7,}  "
              f"elapsed={m['elapsed_s']:>6.1f}s  "
              f"findings={m.get('findings_total','?')}")
    print(f"Merge: {sum(len(c) for c in all_chunk_lists)} pre-merge -> "
          f"{len(merged)} post-merge ({len(dup_log)} dupes)")
    print(f"Matrix pass added: {len(findings_final) - len(merged)}")
    print(f"Final: {len(findings_final)} findings = "
          f"{n_ugly}U + {n_bad}B + {n_review}R + {n_good}G "
          f"(of which {n_xpm} cross-policy-matrix)")
    print(f"Saved findings_v3d-split.json + synthesis_v3d-split.json + chunk_metrics_split.json")
