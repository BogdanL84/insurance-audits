"""Recover findings from the truncated 1A response.

The response was mid-stream truncated: JSON envelope opening + the first
~2 findings were lost. 14 finding objects (IDs 055-068) survived, starting
at offset 1952 (the `{` of finding-055, verified by inspection).

Note: the model continuation-numbered findings from 055 (it had context that
chunk 1B had findings 001-054 — this isn't 1A finding-001, this is the model's
own continuation). Treating it as 14 independent findings is fine; the
numbering doesn't carry semantic weight.
"""
import json
import json_repair
from pathlib import Path

OUT = Path(r"C:\Users\Bogdan\Desktop\Run-Test Policies, Contracts\validation-2026-04-27\phase-2b-2")
SLUG = "run-test-election-services"

raw = (OUT / "_stage_b_v3d_chunk1A_response_raw.txt").read_text(encoding='utf-8')
print(f"1A raw: {len(raw):,} chars")

# Boundary verified: offset 1952 is `{` of finding-055
start = raw.find('{')
assert start == 1952, f"Expected first {{ at 1952, got {start}"

# Original response ended with `}\n  ]\n}\n```. Trim at last `]` (array close):
content = raw[start:]
last_array_close = content.rfind(']')
assert last_array_close > 0, "No closing array bracket found"
content_trimmed = content[:last_array_close]

wrapped = '{"findings": [' + content_trimmed + ']}'
parsed = json_repair.loads(wrapped)
findings = parsed.get('findings', []) if isinstance(parsed, dict) else []

print(f"Recovered {len(findings)} findings")
if len(findings) < 8:
    raise SystemExit(f"FAIL: only {len(findings)} findings recovered (<8 threshold)")

for f in findings:
    f["_chunk"] = "core-1A"
    like, sev = f.get("likelihood"), f.get("severity")
    if like and sev:
        f["risk_score"] = int(like) * int(sev)
    elif "risk_score" not in f:
        f["risk_score"] = None

ids = [f.get('id', '?') for f in findings]
cats = {f.get('category') for f in findings}
print(f"  IDs: {ids}")
print(f"  Categories: {cats}")
print(f"  All _chunk='core-1A': {all(f.get('_chunk')=='core-1A' for f in findings)}")

(OUT / "synthesis_v3d_chunk1A.json").write_text(
    json.dumps({"client": SLUG, "chunk": "core-1A", "findings": findings},
               indent=2, ensure_ascii=False),
    encoding='utf-8',
)
print(f"Wrote synthesis_v3d_chunk1A.json")
