"""v3d driver — synthesis ONLY re-run, with the new K + L prompt instructions
applied. Per-policy analyses, contract data (v3c), and matrix-pass findings
are unchanged and reused.

Outputs:
  synthesis_v3d.json   — synthesis findings only
  findings_v3d.json    — synthesis_v3d + matrix_v3c_findings, deduped
  _stage_b_v3d_*.txt   — prompt and raw response artifacts
"""
import json, sys, time
from pathlib import Path

APP = Path(r"C:\Users\Bogdan\Documents\insurance-audits\app")
sys.path.insert(0, str(APP))

from core.claude_runner import (
    run_claude, extract_json, build_crossref_prompt, ANALYSIS_TIMEOUT,
)

CLIENT      = Path(r"C:\Users\Bogdan\Documents\insurance-audits\clients\run-test-election-services")
EXCHANGE    = CLIENT / "ai-exchange"
SLUG        = "run-test-election-services"
OUT         = Path(r"C:\Users\Bogdan\Desktop\Run-Test Policies, Contracts\validation-2026-04-27\phase-2b-2")

CLIENT_NOTES = (CLIENT / "client-notes.md").read_text(encoding='utf-8', errors='replace')

# Reuse v3c contract data (Stage A unchanged)
contract_path = OUT / "contract_extractions_v3c.json"
requirements_data = json.load(contract_path.open(encoding='utf-8'))
print(f"Loaded contract data from v3c: {len(requirements_data.get('contracts') or {})} contracts, "
      f"{len(requirements_data.get('requirements') or [])} flat reqs")

# Load existing per-policy analyses (unchanged from v3c)
policy_analyses = []
for jf in sorted(EXCHANGE.glob(f"{SLUG}-policy-*-analysis.json")):
    pa = json.load(jf.open(encoding='utf-8'))
    pa.setdefault("_source_file", jf.name)
    policy_analyses.append(pa)
print(f"Loaded {len(policy_analyses)} per-policy analyses")

# Compressed synthesis input (Phase 2B-1 fix preserved)
synthesis_reqs = {
    "client":        requirements_data.get("client"),
    "analysis_date": time.strftime("%Y-%m-%d"),
    "requirements":  requirements_data.get("requirements") or [],
}

prompt = build_crossref_prompt(CLIENT_NOTES, SLUG, synthesis_reqs, policy_analyses)
print(f"Synthesis prompt size: {len(prompt):,} chars")
(OUT / "_stage_b_v3d_prompt.txt").write_text(prompt, encoding='utf-8')

# Verify the new K+L instructions made it into the prompt
checks = [
    "Default to emitting a finding for every RMF item",
    "ALWAYS-EMIT ITEMS",
    "Care, Custody, and Control exclusion review",
    "Mental Anguish in BI definition",
    "substantive and reference-worthy",
]
for c in checks:
    assert c in prompt, f"missing in prompt: {c!r}"
print(f"All 5 new-instruction checks present in prompt")
print()

print(f"Calling claude (text-mode capture, expect ~12-14 min)...")
t0 = time.time()
ok, result = run_claude(prompt, timeout=ANALYSIS_TIMEOUT)
elapsed = time.time() - t0
print(f"  ok={ok}, elapsed={elapsed:.0f}s ({elapsed/60:.1f} min), response_chars={len(result or ''):,}")
(OUT / "_stage_b_v3d_response_raw.txt").write_text(result or "", encoding='utf-8')

if not ok:
    print(f"FAILED: {result[:500]}")
    sys.exit(1)

parsed = extract_json(result)
if not parsed or "findings" not in parsed:
    print("PARSE FAILED. Saved raw response to _stage_b_v3d_response_raw.txt")
    sys.exit(1)

findings = parsed["findings"]
for f in findings:
    like = f.get("likelihood")
    sev  = f.get("severity")
    if like and sev and "risk_score" not in f:
        f["risk_score"] = int(like) * int(sev)
    elif "risk_score" not in f:
        f["risk_score"] = None

# Save synthesis-only output
(OUT / "synthesis_v3d.json").write_text(
    json.dumps({"client": SLUG, "findings": findings}, indent=2, ensure_ascii=False),
    encoding='utf-8',
)

n_ugly   = sum(1 for f in findings if f.get("category") == "Ugly")
n_bad    = sum(1 for f in findings if f.get("category") == "Bad")
n_review = sum(1 for f in findings if f.get("category") in ("Review", "Needs Review"))
n_good   = sum(1 for f in findings if f.get("category") == "Good")
print()
print(f"Synthesis: {len(findings)} findings — {n_ugly}U, {n_bad}B, {n_review}R, {n_good}G")

# Merge with existing matrix findings (v3c) — dedupe by (requirement_type, policy_file, policy_page)
matrix_path = OUT / "matrix_v3c_findings.json"
matrix_findings = json.load(matrix_path.open(encoding='utf-8')).get("findings", [])
print(f"Loaded {len(matrix_findings)} matrix findings from v3c (unchanged for v3d)")

existing_keys = {
    (f.get("requirement_type"), f.get("policy_file"), f.get("policy_page"))
    for f in findings
}
added = 0
for nf in matrix_findings:
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
print(f"Merged: {added} new matrix findings (after de-dup)")

# Save final v3d
(OUT / "findings_v3d.json").write_text(
    json.dumps({"client": SLUG, "findings": findings}, indent=2, ensure_ascii=False),
    encoding='utf-8',
)
n_ugly   = sum(1 for f in findings if f.get("category") == "Ugly")
n_bad    = sum(1 for f in findings if f.get("category") == "Bad")
n_review = sum(1 for f in findings if f.get("category") in ("Review", "Needs Review"))
n_good   = sum(1 for f in findings if f.get("category") == "Good")
n_xpm    = sum(1 for f in findings if "cross-policy-matrix" in (f.get("tags") or []))
print()
print("=" * 60)
print(f"v3d FINAL: {len(findings)} findings = {n_ugly}U + {n_bad}B + {n_review}R + {n_good}G "
      f"(of which {n_xpm} cross-policy-matrix)")
print(f"Saved findings_v3d.json")
