"""v3e driver — chunked synthesis (6 chunks) with K + L additions
expanded to per-coverage always-emit lists for CA and WC.

The v3d 3-chunk run had Chunk 1 (220 KB) hang silently. The v3d-split
4-chunk run had 1A (170 KB) truncate mid-stream. v3e splits the
core-liability and ML/WC chunks more aggressively to keep all chunks
comfortably below the empirical 170,580-char truncation point.

Sub-chunk plan and measured prompt sizes (2026-04-30 with K+L expansion):
  core-1A1: Hanover Commercial Package alone   (~151 KB prompt)
  core-1A2: Hanover Auto alone                  (~117 KB prompt)
  core-1B:  Umbrella + Security Guards CGL      (~144 KB prompt)
  pro-cyber: Pro E&O + Convex + AmTrust Cyber   (~149 KB prompt)
  ml-3A:    Management Liability alone          (~131 KB prompt)
  wc-3B:    Workers' Comp alone                 (~132 KB prompt)

Reuses (loaded from disk, not regenerated):
  - contract_extractions_v3c-postpin.json      (Stage A, unchanged)
  - 9 per-policy analyses                      (unchanged)

Outputs to phase-2b-2/ (all carry v3e prefix; v3d artifacts untouched):
  _stage_b_v3e_chunk{1A1,1A2,1B,2,3A,3B}_prompt.txt + _response_raw.txt
  synthesis_v3e_chunk{1A1,1A2,1B,2,3A,3B}.json
  synthesis_v3e.json                merged synthesis (deduped Bad/Ugly)
  matrix_v3e_{entity,compliance,noc}.json
  matrix_v3e_findings.json          AI matrix pass output
  _stage_c_v3e_prompt.txt + _stage_c_v3e_response_raw.txt
  findings_v3e.json                 final
  chunk_metrics_v3e.json            per-chunk timing + size data
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

# Each policy must match exactly one chunk. Substring match against the
# lowercased _source_file. Verified against the 9 current PDF filenames.
CHUNKS = [
    {
        "name":      "core-1A1",
        "idx_label": "1A1",
        "label":     "Chunk 1A1 - Hanover Commercial Package alone",
        # 'hanover - commercial - ' (with trailing ' - ') matches the package
        # but NOT 'hanover - commercial umbrella - '
        "matches":   ["hanover - commercial - "],
    },
    {
        "name":      "core-1A2",
        "idx_label": "1A2",
        "label":     "Chunk 1A2 - Hanover Auto alone",
        "matches":   ["hanover - auto"],
    },
    {
        "name":      "core-1B",
        "idx_label": "1B",
        "label":     "Chunk 1B - Umbrella + Security Guards CGL",
        "matches":   ["hanover - commercial umbrella", "security guards"],
    },
    {
        "name":      "pro-cyber",
        "idx_label": "2",
        "label":     "Chunk 2 - Professional services / cyber (Pro E&O / Excess Tech E&O / Cyber)",
        "matches":   ["professional liability", "convex", "cyber"],
    },
    {
        "name":      "ml-3A",
        "idx_label": "3A",
        "label":     "Chunk 3A - Management Liability alone",
        "matches":   ["management liability"],
    },
    {
        "name":      "wc-3B",
        "idx_label": "3B",
        "label":     "Chunk 3B - Workers' Comp alone",
        "matches":   ["wc -"],
    },
]


def _log(msg: str):
    print(f"[v3e-chunked] {msg}", flush=True)


def _assign_to_chunks(policy_analyses: list) -> list:
    """Partition per-policy analyses into the 6 chunks. Asserts every policy
    matches exactly one chunk."""
    assignments = [(c, []) for c in CHUNKS]
    leftovers = []
    for pa in policy_analyses:
        src = (pa.get("_source_file") or pa.get("policy_file") or "").lower()
        matched = []
        for chunk_def, bucket in assignments:
            if any(kw.lower() in src for kw in chunk_def["matches"]):
                matched.append((chunk_def["name"], bucket))
        if len(matched) == 1:
            matched[0][1].append(pa)
        elif len(matched) == 0:
            leftovers.append(src)
        else:
            raise AssertionError(
                f"Policy {src!r} matched multiple chunks: {[m[0] for m in matched]}"
            )
    if leftovers:
        raise AssertionError(f"Unassigned policies: {leftovers}")
    for chunk_def, bucket in assignments:
        if not bucket:
            raise AssertionError(f"Chunk {chunk_def['name']!r} got 0 policies")
    return assignments


def run_chunk(chunk_def: dict, analyses: list, requirements_data: dict) -> tuple:
    """Synthesize one chunk. Returns (ok, findings, metrics_dict)."""
    idx_label = chunk_def["idx_label"]
    _log(f"=== {chunk_def['label']} ===")
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
    (OUT / f"_stage_b_v3e_chunk{idx_label}_prompt.txt").write_text(prompt, encoding='utf-8')

    t0 = time.time()
    ok, result = run_claude(prompt, timeout=ANALYSIS_TIMEOUT)
    elapsed = time.time() - t0
    _log(f"  ok={ok}, elapsed={elapsed:.1f}s, response_chars={len(result or ''):,}")
    (OUT / f"_stage_b_v3e_chunk{idx_label}_response_raw.txt").write_text(result or "", encoding='utf-8')

    metrics = {
        "chunk":          chunk_def["name"],
        "idx_label":      idx_label,
        "label":          chunk_def["label"],
        "policy_count":   len(analyses),
        "prompt_chars":   len(prompt),
        "response_chars": len(result or ""),
        "elapsed_s":      round(elapsed, 1),
        "ok":             ok,
        # Cache/token metrics not surfaced in --output-format text.
        # Compare elapsed_s across chunks as a prefix-cache proxy.
        "cache_read_input_tokens": None,
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
        f["_chunk"] = chunk_def["name"]
        like = f.get("likelihood")
        sev  = f.get("severity")
        if like and sev and "risk_score" not in f:
            f["risk_score"] = int(like) * int(sev)
        elif "risk_score" not in f:
            f["risk_score"] = None

    (OUT / f"synthesis_v3e_chunk{idx_label}.json").write_text(
        json.dumps({"client": SLUG, "chunk": chunk_def["name"], "findings": findings},
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
                merged.append(f)  # Good / Needs Review: keep all
    return merged, dup_log


def stage_c_matrix_pass(requirements_data: dict, findings: list, all_policy_analyses: list) -> list:
    """Cross-policy matrix pass against all 9 policies. Outputs all carry
    v3e prefix to avoid overwriting prior v3d artifacts."""
    _log("Stage C - Cross-policy matrix pass.")
    contracts_data = (requirements_data or {}).get("contracts", {}) or {}

    em = build_entity_matrix(all_policy_analyses)
    cm = build_contract_compliance_matrix(contracts_data, all_policy_analyses)
    nm = build_designated_entity_noc_matrix(contracts_data, all_policy_analyses)

    (OUT / "matrix_v3e_entity.json").write_text(
        json.dumps(em, indent=2, ensure_ascii=False), encoding='utf-8')
    (OUT / "matrix_v3e_compliance.json").write_text(
        json.dumps(cm, indent=2, ensure_ascii=False), encoding='utf-8')
    (OUT / "matrix_v3e_noc.json").write_text(
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
    (OUT / "_stage_c_v3e_prompt.txt").write_text(cp_prompt, encoding='utf-8')
    _log(f"  Matrix prompt size: {len(cp_prompt):,} chars")

    t0 = time.time()
    ok, result = run_claude(cp_prompt, timeout=ANALYSIS_TIMEOUT)
    elapsed = time.time() - t0
    _log(f"  ok={ok}, elapsed={elapsed:.1f}s, response_chars={len(result or ''):,}")
    (OUT / "_stage_c_v3e_response_raw.txt").write_text(result or "", encoding='utf-8')
    if not ok:
        _log(f"  Matrix pass FAILED: {(result or '')[:400]} - keeping synthesis findings only")
        return findings

    parsed = extract_json(result)
    if not parsed or "findings" not in parsed:
        _log("  Matrix JSON parse failed - keeping synthesis findings only")
        return findings

    new_findings = parsed["findings"]
    (OUT / "matrix_v3e_findings.json").write_text(
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

    contract_path = OUT / "contract_extractions_v3c-postpin.json"
    requirements_data = json.load(contract_path.open(encoding='utf-8'))
    _log(f"Loaded contract data from {contract_path.name}: "
         f"{len(requirements_data.get('contracts') or {})} contracts, "
         f"{len(requirements_data.get('requirements') or [])} flat reqs")

    all_policy_analyses: list = []
    for jf in sorted(EXCHANGE.glob(f"{SLUG}-policy-*-analysis.json")):
        pa = json.load(jf.open(encoding='utf-8'))
        pa.setdefault("_source_file", jf.name)
        all_policy_analyses.append(pa)
    _log(f"Loaded {len(all_policy_analyses)} per-policy analyses")

    assignments = _assign_to_chunks(all_policy_analyses)
    for chunk_def, analyses in assignments:
        _log(f"  {chunk_def['name']:<10} ({chunk_def['idx_label']}): {len(analyses)} policies")

    chunk_findings: list = []
    chunk_metrics: list  = []
    failures = 0
    for chunk_def, analyses in assignments:
        ok, findings, metrics = run_chunk(chunk_def, analyses, requirements_data)
        chunk_findings.append(findings)
        chunk_metrics.append(metrics)
        if not ok:
            failures += 1
            if failures >= 2:
                _log("STOP: 2+ chunks have failed. Saving partial state and exiting.")
                (OUT / "chunk_metrics_v3e.json").write_text(
                    json.dumps({"chunks": chunk_metrics, "stop_reason": "2+ chunks failed"},
                               indent=2, ensure_ascii=False),
                    encoding='utf-8',
                )
                sys.exit(2)

    merged, dup_log = merge_chunks(chunk_findings)
    _log(f"Merged synthesis: {len(merged)} findings "
         f"(across {sum(len(c) for c in chunk_findings)} pre-merge); "
         f"{len(dup_log)} duplicates collapsed")
    for d in dup_log:
        _log(f"  DUP: {d['requirement_type']!r} | {d['policy_file']!r} | "
             f"kept={d['kept_chunk']}({d['kept_risk_score']}) "
             f"dropped={d['dropped_chunk']}({d['dropped_risk_score']})")

    (OUT / "synthesis_v3e.json").write_text(
        json.dumps({"client": SLUG, "findings": merged, "duplicates_collapsed": dup_log},
                   indent=2, ensure_ascii=False),
        encoding='utf-8',
    )

    chunk_metrics_payload = {
        "chunks": chunk_metrics,
        "merge_stats": {
            "chunks_with_findings":  sum(1 for fs in chunk_findings if fs),
            "pre_merge_total":       sum(len(fs) for fs in chunk_findings),
            "post_merge_total":      len(merged),
            "duplicates_collapsed":  len(dup_log),
        },
        "elapsed_total_s": round(time.time() - overall_t0, 1),
        "metrics_capture_note": (
            "cache_read_input_tokens / input_tokens_total / output_tokens_total "
            "are None because the runner uses --output-format text. To capture "
            "these, switch run_claude to --output-format json (with envelope unwrap) "
            "or stream-json (with line-by-line parsing) and read the usage block."
        ),
    }
    (OUT / "chunk_metrics_v3e.json").write_text(
        json.dumps(chunk_metrics_payload, indent=2, ensure_ascii=False),
        encoding='utf-8',
    )

    findings_final = stage_c_matrix_pass(requirements_data, merged, all_policy_analyses)

    (OUT / "findings_v3e.json").write_text(
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
    print(f"v3e CHUNKED PIPELINE COMPLETE - {elapsed_total/60:.1f} min total")
    print(f"Per-chunk timings:")
    for m in chunk_metrics:
        print(f"  {m['chunk']:>10}  prompt={m['prompt_chars']:>7,}  "
              f"resp={m.get('response_chars',0):>7,}  "
              f"elapsed={m['elapsed_s']:>6.1f}s  "
              f"findings={m.get('findings_total','?')}")
    print(f"Merge: {sum(len(c) for c in chunk_findings)} pre-merge -> "
          f"{len(merged)} post-merge ({len(dup_log)} dupes)")
    print(f"Matrix pass added: {len(findings_final) - len(merged)}")
    print(f"Final: {len(findings_final)} findings = "
          f"{n_ugly}U + {n_bad}B + {n_review}R + {n_good}G "
          f"(of which {n_xpm} cross-policy-matrix)")
    print(f"Saved findings_v3e.json + synthesis_v3e.json + chunk_metrics_v3e.json")
