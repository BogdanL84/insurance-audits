"""Finish v3e-partial: salvaged 1A1 + clean 1A2 + salvaged 1B + v3d-vintage chunk2/3.

This is the partial-recovery path for v3e. The 6-chunk run had Chunk 1A1
and 1B truncate; 1A2 ran clean. Chunks 2/3A/3B were never run because the
driver bailed at the 2+ failure stop. We mix the salvaged v3e core-liability
synthesis with the still-good v3d Pro/Cyber + ML/WC synthesis from yesterday.

Output: findings_v3e-partial.json — does NOT overwrite findings_v3e.json
(reserved for the full re-run after stream-json runner migration).
"""
import json, sys, time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import _run_v3e_chunked as v3e  # reuse merge_chunks + matrix-pass helpers

OUT      = v3e.OUT
SLUG     = v3e.SLUG
EXCHANGE = v3e.EXCHANGE

t0 = time.time()

# Load 5 chunk synthesis files
chunk_files = [
    ("synthesis_v3e_chunk1A1.json", "core-1A1 (salvaged)"),
    ("synthesis_v3e_chunk1A2.json", "core-1A2 (clean)"),
    ("synthesis_v3e_chunk1B.json",  "core-1B (salvaged)"),
    ("synthesis_v3d_chunk2.json",   "pro-cyber (v3d-vintage)"),
    ("synthesis_v3d_chunk3.json",   "ml-wc (v3d-vintage)"),
]
all_chunk_lists = []
for fname, label in chunk_files:
    data = json.load((OUT / fname).open(encoding='utf-8'))
    findings = data.get("findings", [])
    all_chunk_lists.append(findings)
    print(f"Loaded {len(findings):>3} findings from {fname:<35} [{label}]")

merged, dup_log = v3e.merge_chunks(all_chunk_lists)
print(f"\nMerge: {sum(len(c) for c in all_chunk_lists)} pre-merge -> "
      f"{len(merged)} post-merge ({len(dup_log)} dups)")
for d in dup_log:
    print(f"  DUP: {d['requirement_type']!r} | {d['policy_file']!r} | "
          f"kept={d['kept_chunk']} dropped={d['dropped_chunk']}")

(OUT / "synthesis_v3e-partial.json").write_text(
    json.dumps({"client": SLUG, "findings": merged, "duplicates_collapsed": dup_log},
               indent=2, ensure_ascii=False),
    encoding='utf-8',
)

# Matrix pass against all 9 policies (writes matrix_v3e_*.json)
contract_path = OUT / "contract_extractions_v3c-postpin.json"
requirements_data = json.load(contract_path.open(encoding='utf-8'))
all_pa = []
for jf in sorted(EXCHANGE.glob(f"{SLUG}-policy-*-analysis.json")):
    pa = json.load(jf.open(encoding='utf-8'))
    pa.setdefault("_source_file", jf.name)
    all_pa.append(pa)

print(f"\n=== Matrix pass (1 API call) ===")
findings_final = v3e.stage_c_matrix_pass(requirements_data, merged, all_pa)

(OUT / "findings_v3e-partial.json").write_text(
    json.dumps({"client": SLUG, "findings": findings_final}, indent=2, ensure_ascii=False),
    encoding='utf-8',
)

n_ugly  = sum(1 for f in findings_final if f.get("category") == "Ugly")
n_bad   = sum(1 for f in findings_final if f.get("category") == "Bad")
n_review = sum(1 for f in findings_final if f.get("category") in ("Review", "Needs Review"))
n_good  = sum(1 for f in findings_final if f.get("category") == "Good")
n_xpm   = sum(1 for f in findings_final if "cross-policy-matrix" in (f.get("tags") or []))
elapsed_total = time.time() - t0

print()
print("=" * 60)
print(f"v3e-PARTIAL FINISHED - {elapsed_total/60:.1f} min total")
print(f"Pre-merge:    {sum(len(fs) for fs in all_chunk_lists)} synthesis findings across 5 chunks")
print(f"Post-merge:   {len(merged)} synthesis ({len(dup_log)} dups)")
print(f"Matrix added: {len(findings_final) - len(merged)}")
print(f"Final: {len(findings_final)} findings = "
      f"{n_ugly}U + {n_bad}B + {n_review}R + {n_good}G "
      f"({n_xpm} cross-policy-matrix)")
print(f"Saved findings_v3e-partial.json")
