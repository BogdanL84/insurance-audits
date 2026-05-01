"""Recover all 54 findings from 1B (response complete but has 1+ JSON escape
bugs in policy_quote fields where the model emitted unescaped `"` inside
string values). json_repair handles it cleanly — verified in smoke test."""
import json
import re
import json_repair
from pathlib import Path

OUT = Path(r"C:\Users\Bogdan\Desktop\Run-Test Policies, Contracts\validation-2026-04-27\phase-2b-2")
SLUG = "run-test-election-services"

raw = (OUT / "_stage_b_v3d_chunk1B_response_raw.txt").read_text(encoding='utf-8')
print(f"1B raw: {len(raw):,} chars")

# Greedy fence-strip (the standard regex in extract_json was non-greedy and
# would stop at the first inner '}', missing the outer envelope close)
m = re.search(r'```(?:json)?\s*(\{[\s\S]*\})\s*```', raw)
if not m:
    raise SystemExit("FAIL: no code-fenced JSON block found")
inner = m.group(1)
print(f"Fence-stripped: {len(inner):,} chars")

parsed = json_repair.loads(inner)
if not isinstance(parsed, dict) or "findings" not in parsed:
    raise SystemExit(f"FAIL: json_repair returned {type(parsed).__name__}, no findings key")

findings = parsed["findings"]
print(f"Recovered {len(findings)} findings")
if len(findings) < 30:
    raise SystemExit(f"FAIL: only {len(findings)} findings recovered (expected ~54)")

for f in findings:
    f["_chunk"] = "core-1B"
    like, sev = f.get("likelihood"), f.get("severity")
    if like and sev:
        f["risk_score"] = int(like) * int(sev)
    elif "risk_score" not in f:
        f["risk_score"] = None

print(f"  First 3 IDs: {[f.get('id') for f in findings[:3]]}")
print(f"  Last 3 IDs:  {[f.get('id') for f in findings[-3:]]}")
print(f"  Categories: {set(f.get('category') for f in findings)}")

(OUT / "synthesis_v3d_chunk1B.json").write_text(
    json.dumps({"client": SLUG, "chunk": "core-1B", "findings": findings},
               indent=2, ensure_ascii=False),
    encoding='utf-8',
)
print(f"Wrote synthesis_v3d_chunk1B.json")
