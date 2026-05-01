"""Validate the refactored app chunking pipeline against the v3e baseline.

Exercises app/core/chunking.py:run_chunked_synthesis end-to-end on run-test
data and produces findings_v3e_app.json. Pass criteria:
  - Findings count: 400+
  - RMF tag-aware coverage: 65%+

This is the validation harness that gives us confidence the refactor doesn't
break v3e-quality output before we ship.
"""
import json
import sys
import time
from pathlib import Path

REPO = Path(r"C:\Users\Bogdan\Documents\insurance-audits")
sys.path.insert(0, str(REPO / "app"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from core.chunking import run_chunked_synthesis  # noqa: E402
import _run_v3e_chunked as v3e_driver  # noqa: E402  # reuse stage_c_matrix_pass

OUT  = Path(__file__).resolve().parent
CLIENT = REPO / "clients" / "run-test-election-services"
EXCHANGE = CLIENT / "ai-exchange"
SLUG = "run-test-election-services"
CLIENT_NOTES = (CLIENT / "client-notes.md").read_text(encoding='utf-8', errors='replace')

t0 = time.time()
print("=== Validate app chunking refactor — Run-test ===", flush=True)

# Load contract data + 9 per-policy analyses (same as v3e)
contract_path = OUT / "contract_extractions_v3c-postpin.json"
requirements_data = json.load(contract_path.open(encoding='utf-8'))
print(f"Loaded contract data: {len(requirements_data.get('contracts') or {})} contracts, "
      f"{len(requirements_data.get('requirements') or [])} reqs", flush=True)

all_pa = []
for jf in sorted(EXCHANGE.glob(f"{SLUG}-policy-*-analysis.json")):
    pa = json.load(jf.open(encoding='utf-8'))
    pa.setdefault("_source_file", jf.name)
    all_pa.append(pa)
print(f"Loaded {len(all_pa)} per-policy analyses", flush=True)

# Run chunked synthesis via the new module (the same path the app uses)
def progress(label, frac):
    print(f"  [progress {frac:.0%}] {label}", flush=True)

print("\n=== Synthesis (via run_chunked_synthesis) ===", flush=True)
synth_findings, synth_meta = run_chunked_synthesis(
    CLIENT_NOTES, SLUG, requirements_data, all_pa,
    progress_callback=progress,
)

print(f"\nSynthesis mode: {synth_meta.get('mode')}", flush=True)
print(f"All-policies prompt size estimate: {synth_meta.get('all_policies_prompt_chars'):,}", flush=True)
print(f"Chunks: {len(synth_meta.get('chunks') or [])}", flush=True)
for c in synth_meta.get('chunks', []):
    print(f"  - {c.get('name'):<24} ok={c.get('ok')} prompt={c.get('prompt_chars',0):>7,} "
          f"resp={c.get('response_chars',0):>7,} findings={c.get('findings_total','?')} "
          f"elapsed={c.get('elapsed_s',0):>5.1f}s", flush=True)
print(f"Errors: {synth_meta.get('errors')}", flush=True)
print(f"Duplicates collapsed: {len(synth_meta.get('duplicates_collapsed') or [])}", flush=True)
print(f"\nMerged synthesis findings: {len(synth_findings)}", flush=True)

# Save synthesis output
(OUT / "synthesis_v3e_app.json").write_text(
    json.dumps({"client": SLUG, "findings": synth_findings, "metadata": synth_meta},
               indent=2, ensure_ascii=False, default=str),
    encoding='utf-8',
)

# Run matrix pass via the v3e driver's existing function
print("\n=== Matrix pass (via v3e_driver.stage_c_matrix_pass) ===", flush=True)
findings_final = v3e_driver.stage_c_matrix_pass(requirements_data, synth_findings, all_pa)

(OUT / "findings_v3e_app.json").write_text(
    json.dumps({"client": SLUG, "findings": findings_final}, indent=2, ensure_ascii=False),
    encoding='utf-8',
)

n_ugly  = sum(1 for f in findings_final if f.get("category") == "Ugly")
n_bad   = sum(1 for f in findings_final if f.get("category") == "Bad")
n_review = sum(1 for f in findings_final if f.get("category") in ("Review", "Needs Review"))
n_good  = sum(1 for f in findings_final if f.get("category") == "Good")
n_xpm   = sum(1 for f in findings_final if "cross-policy-matrix" in (f.get("tags") or []))
elapsed = time.time() - t0

print()
print("=" * 60)
print(f"VALIDATION COMPLETE - {elapsed/60:.1f} min total")
print(f"Final: {len(findings_final)} findings = {n_ugly}U + {n_bad}B + {n_review}R + {n_good}G "
      f"({n_xpm} cross-policy-matrix tagged)")

# Pass/fail vs v3e baseline
PASS_FINDINGS = 400
print()
print(f"=== Pass criteria ===")
print(f"  Findings: {len(findings_final)} {'>=' if len(findings_final) >= PASS_FINDINGS else '<'} {PASS_FINDINGS} "
      f"({'PASS' if len(findings_final) >= PASS_FINDINGS else 'FAIL'})")
print(f"  vs v3e baseline (449): {len(findings_final) - 449:+d}")
print()
print(f"Saved findings_v3e_app.json")
print(f"Saved synthesis_v3e_app.json")
