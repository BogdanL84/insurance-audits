"""Finish the v3d-split pipeline.

Picks up where _run_v3d_chunk1_split.py bailed (both sub-chunks parse-failed
and the driver stopped). We've since recovered:
  - synthesis_v3d_chunk1A.json (14 findings, salvaged from truncated response)
  - synthesis_v3d_chunk1B.json (54 findings, salvaged via json_repair)
plus the still-good
  - synthesis_v3d_chunk2.json (64 findings, from earlier v3d_chunked run)
  - synthesis_v3d_chunk3.json (53 findings, from earlier v3d_chunked run)

This orchestrator merges all four, runs Stage C matrix pass against all 9
policies, writes findings_v3d-split.json. One API call only (matrix pass).

Output filenames carry '-split' suffix (inherited from
_run_v3d_chunk1_split.stage_c_matrix_pass) so the original v3d_chunked
artifacts are preserved alongside.
"""
import json
import sys
import time
from pathlib import Path

# Reuse merge + matrix-pass from the split driver. Module-level code in that
# file is just imports + constants + function defs; the __main__ block is
# skipped on import.
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import _run_v3d_chunk1_split as v3d  # noqa: E402

OUT      = v3d.OUT
SLUG     = v3d.SLUG
EXCHANGE = v3d.EXCHANGE

overall_t0 = time.time()

# === Step 1: load all 4 chunks ===
chunk_files = [
    ("synthesis_v3d_chunk1A.json", "core-1A"),
    ("synthesis_v3d_chunk1B.json", "core-1B"),
    ("synthesis_v3d_chunk2.json",  "pro-cyber"),
    ("synthesis_v3d_chunk3.json",  "ml-wc"),
]
all_chunk_lists = []
for fname, expected_chunk in chunk_files:
    data = json.load((OUT / fname).open(encoding='utf-8'))
    findings = data.get("findings", [])
    all_chunk_lists.append(findings)
    print(f"Loaded {len(findings):>3} findings from {fname} "
          f"(chunk={data.get('chunk','?')!r})")

# === Step 2: merge ===
merged, dup_log = v3d.merge_chunks(all_chunk_lists)
print(f"\nMerge: {sum(len(c) for c in all_chunk_lists)} pre-merge -> "
      f"{len(merged)} post-merge ({len(dup_log)} duplicates collapsed)")
for d in dup_log:
    print(f"  DUP: {d['requirement_type']!r} | {d['policy_file']!r} | "
          f"kept={d['kept_chunk']}({d['kept_risk_score']}) "
          f"dropped={d['dropped_chunk']}({d['dropped_risk_score']})")

(OUT / "synthesis_v3d-split.json").write_text(
    json.dumps({"client": SLUG, "findings": merged, "duplicates_collapsed": dup_log},
               indent=2, ensure_ascii=False),
    encoding='utf-8',
)
print(f"Wrote synthesis_v3d-split.json")

# === Step 3: refresh chunk_metrics_split.json to reflect the recovered data ===
chunk_metrics_payload = {
    "sub_chunks": [
        {"chunk": "core-1A", "recovered_findings": len(all_chunk_lists[0]),
         "source": "salvage_chunk1A.py",
         "note": "Truncated response, recovered from offset 1952"},
        {"chunk": "core-1B", "recovered_findings": len(all_chunk_lists[1]),
         "source": "salvage_chunk1B.py",
         "note": "Complete response with JSON escape bug; recovered via json_repair"},
    ],
    "existing_chunks_loaded": [
        {"chunk": "pro-cyber", "findings": len(all_chunk_lists[2])},
        {"chunk": "ml-wc",     "findings": len(all_chunk_lists[3])},
    ],
    "merge_stats": {
        "pre_merge_total":      sum(len(fs) for fs in all_chunk_lists),
        "post_merge_total":     len(merged),
        "duplicates_collapsed": len(dup_log),
    },
    "duplicates_log": dup_log,
}
(OUT / "chunk_metrics_split.json").write_text(
    json.dumps(chunk_metrics_payload, indent=2, ensure_ascii=False),
    encoding='utf-8',
)

# === Step 4: load contract data + 9 policy analyses for matrix pass ===
contract_path = OUT / "contract_extractions_v3c-postpin.json"
requirements_data = json.load(contract_path.open(encoding='utf-8'))
all_policy_analyses = []
for jf in sorted(EXCHANGE.glob(f"{SLUG}-policy-*-analysis.json")):
    pa = json.load(jf.open(encoding='utf-8'))
    pa.setdefault("_source_file", jf.name)
    all_policy_analyses.append(pa)
print(f"Loaded {len(all_policy_analyses)} per-policy analyses for matrix pass")

# === Step 5: matrix pass (writes matrix_v3d-split_*.json + AI pass) ===
print("\n=== Stage C - Matrix pass (one API call, ~6 min expected) ===")
findings_final = v3d.stage_c_matrix_pass(requirements_data, merged, all_policy_analyses)

# === Step 6: save final + summary ===
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
print(f"v3d-SPLIT FINISHED - {elapsed_total/60:.1f} min total")
print(f"Pre-merge:    {sum(len(fs) for fs in all_chunk_lists)} synthesis findings across 4 chunks")
print(f"Post-merge:   {len(merged)} synthesis findings ({len(dup_log)} dupes collapsed)")
print(f"Matrix added: {len(findings_final) - len(merged)}")
print(f"Final: {len(findings_final)} findings = "
      f"{n_ugly}U + {n_bad}B + {n_review}R + {n_good}G "
      f"(of which {n_xpm} cross-policy-matrix)")
print(f"Saved findings_v3d-split.json")
