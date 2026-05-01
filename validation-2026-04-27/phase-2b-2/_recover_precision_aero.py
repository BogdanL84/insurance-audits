"""Recover Precision Aero findings from the surviving runner tempfile.

The user ran the Streamlit audit on Precision Aero (5 policies, no contracts)
on 2026-05-01 ~15:30. Synthesis (chunked) ran cleanly, producing 55 findings.
The cross-policy intelligence pass (build_crosspolicy_prompt, 300s timeout)
also completed cleanly — 4 min 26 sec, 43.5 KB response, parsed as 55
findings. THEN Streamlit hung: the page never updated past 'Running
cross-policy intelligence pass...' and `audit-state.json` was never written
with the findings.

Tempfile path: C:\\Users\\Bogdan\\AppData\\Local\\Temp\\claude_runner_kx59zxk2\\

This script extracts the 55 findings from that tempfile's stream-json output,
saves them to disk in two places (the client output dir AND the validation
backup), and updates audit-state.json so the Findings Dashboard renders.

No API spend.
"""
import json
import shutil
import sys
import time
from pathlib import Path

REPO = Path(r"C:\Users\Bogdan\Documents\insurance-audits")
sys.path.insert(0, str(REPO / "app"))
from core.claude_runner import extract_json  # noqa: E402

TMP_PATH = Path(r"C:\Users\Bogdan\AppData\Local\Temp\claude_runner_kx59zxk2\claude_stdout.txt")
CLIENT   = REPO / "clients" / "precision-aero"
VALIDATION = REPO / "validation-2026-04-27" / "phase-2b-2"

assert TMP_PATH.exists(), f"Tempfile missing: {TMP_PATH}"
assert CLIENT.exists(),   f"Client dir missing: {CLIENT}"

# 1. Reconstruct the response text from the stream-json events
text_chunks: list[str] = []
result_obj = None
with TMP_PATH.open(encoding='utf-8') as f:
    for line in f:
        line = line.strip()
        if not line:
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        etype = event.get("type")
        if etype == "stream_event":
            sub = event.get("event", {}) or {}
            if sub.get("type") == "content_block_delta":
                delta = sub.get("delta", {}) or {}
                if delta.get("type") == "text_delta":
                    text_chunks.append(delta.get("text", ""))
        elif etype == "result":
            result_obj = event

reconstructed = "".join(text_chunks)
print(f"Reconstructed response: {len(reconstructed):,} chars")
print(f"Result event present: {result_obj is not None}")
if result_obj:
    print(f"  duration_ms: {result_obj.get('duration_ms')}")
    print(f"  is_error:    {result_obj.get('is_error')}")

# 2. Parse JSON
parsed = extract_json(reconstructed)
if not parsed or "findings" not in parsed:
    raise SystemExit("FAIL: extract_json could not recover findings from tempfile")

findings = parsed["findings"]
print(f"Recovered {len(findings)} findings")

# Compute risk_score where missing
for f in findings:
    like = f.get("likelihood")
    sev  = f.get("severity")
    if like and sev and "risk_score" not in f:
        f["risk_score"] = int(like) * int(sev)
    elif "risk_score" not in f:
        f["risk_score"] = None

# Category breakdown
from collections import Counter
cats = Counter(f.get("category") for f in findings)
print(f"Categories: {dict(cats)}")

# 3. Save to client output dir + validation backup dir
client_out  = CLIENT / "output" / "findings.json"
backup_out  = VALIDATION / "findings_precision_aero_v3e.json"

payload = {
    "client":       "precision-aero",
    "display_name": "Precision Aero",
    "recovered_from": str(TMP_PATH),
    "recovery_date": time.strftime("%Y-%m-%dT%H:%M:%S"),
    "findings":     findings,
}
client_out.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding='utf-8')
backup_out.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding='utf-8')
print(f"Saved {client_out}")
print(f"Saved {backup_out}")

# 4. Update audit-state.json to embed findings + bump stage
audit_state_path = CLIENT / "output" / "audit-state.json"
state = json.load(audit_state_path.open(encoding='utf-8'))

# Backup the original first
shutil.copy(audit_state_path, audit_state_path.with_suffix(".json.pre-recovery"))

state["findings"] = findings
state["stage"] = "audited"
state["last_modified"] = time.strftime("%Y-%m-%dT%H:%M:%S")
state["recovery_note"] = (
    "Findings recovered 2026-05-01 from preserved runner tempfile after the "
    "Streamlit audit hung post-synthesis. Source: " + str(TMP_PATH) + ". "
    "55 findings parsed from the cross-policy intelligence pass response. "
    "Stage C matrix pass did not run (no contracts uploaded would have made it "
    "low-value anyway)."
)

audit_state_path.write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding='utf-8')
print(f"Updated {audit_state_path} (backed up to .pre-recovery)")

# 5. Top findings preview
print()
print("=== Top 5 by risk_score ===")
sorted_findings = sorted(findings, key=lambda x: x.get("risk_score") or 0, reverse=True)
for f in sorted_findings[:5]:
    rs = f.get("risk_score")
    cat = f.get("category", "?")
    rt = (f.get("requirement_type", "") or "")[:90]
    pf = (f.get("policy_file", "") or "")[:50]
    print(f"  [{cat:<14}] risk={rs}  {rt}  ({pf})")

print()
print("RECOVERY COMPLETE")
