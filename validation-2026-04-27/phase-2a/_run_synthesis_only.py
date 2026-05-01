"""Phase 2B-1 — synthesis-only re-run with the compressed requirements shape.

Loads existing per-policy analyses from ai-exchange/ (NOT re-running them)
and the existing contract-requirements file. Builds the compressed
synthesis_reqs (mirroring the new _Analyze.py logic), calls
build_crossref_prompt + run_claude, and saves the resulting findings to
phase-2a/v3b_findings.json for diff against v2 and v3.
"""
import json, sys, time
from pathlib import Path

APP = Path(r"C:\Users\Bogdan\Documents\insurance-audits\app")
sys.path.insert(0, str(APP))

from core.claude_runner import (
    run_claude, extract_json,
    build_crossref_prompt,
    ANALYSIS_TIMEOUT,
)

CLIENT     = Path(r"C:\Users\Bogdan\Documents\insurance-audits\clients\run-test-election-services")
EXCHANGE   = CLIENT / "ai-exchange"
SLUG       = "run-test-election-services"
OUT        = Path(r"C:\Users\Bogdan\Desktop\Run-Test Policies, Contracts\validation-2026-04-27\phase-2a")

client_notes = (CLIENT / "client-notes.md").read_text(encoding='utf-8', errors='replace')

# Load existing contract-requirements file
req_path = EXCHANGE / f"{SLUG}-contract-requirements.json"
requirements_data = json.load(req_path.open(encoding='utf-8'))

# Load all per-policy analyses
policy_analyses = []
for jf in sorted(EXCHANGE.glob(f"{SLUG}-policy-*-analysis.json")):
    pa = json.load(jf.open(encoding='utf-8'))
    pa.setdefault("_source_file", jf.name)
    policy_analyses.append(pa)

print(f"Loaded {len(policy_analyses)} per-policy analyses")
print(f"Loaded contract-requirements with "
      f"{len(requirements_data.get('contracts') or {})} contracts and "
      f"{len(requirements_data.get('requirements') or [])} flat requirements")

# Apply the Phase 2B-1 compression
synthesis_reqs = {
    "client":        requirements_data.get("client"),
    "analysis_date": requirements_data.get("analysis_date"),
    "requirements":  requirements_data.get("requirements") or [],
}
print(f"Compressed synthesis_reqs JSON size: "
      f"{len(json.dumps(synthesis_reqs)):,} chars (vs current "
      f"{len(json.dumps(requirements_data)):,} = "
      f"{100*len(json.dumps(synthesis_reqs))//len(json.dumps(requirements_data))}%)")

prompt = build_crossref_prompt(client_notes, SLUG, synthesis_reqs, policy_analyses)
print(f"Synthesis prompt size: {len(prompt):,} chars")

# Save the prompt for inspection
(OUT / "v3b_synthesis_prompt.txt").write_text(prompt, encoding='utf-8')

print("\nCalling claude (synthesis-only)...")
t0 = time.time()
ok, result = run_claude(prompt, timeout=ANALYSIS_TIMEOUT)
elapsed = time.time() - t0
print(f"  ok={ok}, elapsed={elapsed:.1f}s, response_chars={len(result or ''):,}")

(OUT / "v3b_synthesis_response_raw.txt").write_text(result or "", encoding='utf-8')

if not ok:
    print(f"FAILED: {result[:500]}")
    sys.exit(1)

parsed = extract_json(result)
if not parsed or "findings" not in parsed:
    print(f"PARSE FAILED. raw saved to v3b_synthesis_response_raw.txt")
    sys.exit(1)

findings = parsed["findings"]
# Apply the same risk_score backfill as the production path
for f in findings:
    like = f.get("likelihood")
    sev  = f.get("severity")
    if like and sev and "risk_score" not in f:
        f["risk_score"] = int(like) * int(sev)
    elif "risk_score" not in f:
        f["risk_score"] = None

# Save
out_obj = {"client": SLUG, "findings": findings}
(OUT / "v3b_findings.json").write_text(
    json.dumps(out_obj, indent=2, ensure_ascii=False), encoding='utf-8'
)

n_ugly = sum(1 for f in findings if f.get("category") == "Ugly")
n_bad  = sum(1 for f in findings if f.get("category") == "Bad")
n_good = sum(1 for f in findings if f.get("category") == "Good")
n_rev  = sum(1 for f in findings if f.get("category") == "Review")
print(f"\nSynthesis-only result: {len(findings)} findings — "
      f"{n_ugly} Ugly, {n_bad} Bad, {n_good} Good, {n_rev} Review")

print(f"\nSaved: {OUT / 'v3b_findings.json'}")
