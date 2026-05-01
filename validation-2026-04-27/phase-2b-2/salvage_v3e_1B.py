"""Salvage truncated v3e Chunk 1B response (Umbrella + Security Guards CGL).

Same pattern as 1A1: mid-stream truncation, lost envelope opening, surviving
finding objects in tail. Find first `{ "id": ` pattern, salvage forward.
"""
import json, re
import json_repair
from pathlib import Path

OUT = Path(r"C:\Users\Bogdan\Desktop\Run-Test Policies, Contracts\validation-2026-04-27\phase-2b-2")
SLUG = "run-test-election-services"

raw = (OUT / "_stage_b_v3e_chunk1B_response_raw.txt").read_text(encoding='utf-8')
print(f"1B raw: {len(raw):,} chars")

m = re.search(r'\{\s*"id"\s*:', raw)
if not m:
    raise SystemExit("FAIL: no '{ \"id\":' pattern found")
start = m.start()
print(f"First complete-finding boundary at offset {start}")

content = raw[start:]
last_array_close = content.rfind(']')
if last_array_close <= 0:
    raise SystemExit("FAIL: no closing array bracket")
content_trimmed = content[:last_array_close]

wrapped = '{"findings": [' + content_trimmed + ']}'
parsed = json_repair.loads(wrapped)
findings = parsed.get('findings', []) if isinstance(parsed, dict) else []

print(f"Recovered {len(findings)} findings")
if len(findings) < 25:
    raise SystemExit(f"FAIL: only {len(findings)} findings recovered (<25 hard-stop threshold)")

for f in findings:
    f["_chunk"] = "core-1B"
    like, sev = f.get("likelihood"), f.get("severity")
    if like and sev:
        f["risk_score"] = int(like) * int(sev)
    elif "risk_score" not in f:
        f["risk_score"] = None

print(f"  IDs: {[f.get('id','?') for f in findings[:3]]} ... {[f.get('id','?') for f in findings[-3:]]}")
print(f"  Categories: {set(f.get('category') for f in findings)}")

(OUT / "synthesis_v3e_chunk1B.json").write_text(
    json.dumps({"client": SLUG, "chunk": "core-1B", "findings": findings},
               indent=2, ensure_ascii=False),
    encoding='utf-8',
)
print(f"Wrote synthesis_v3e_chunk1B.json")
