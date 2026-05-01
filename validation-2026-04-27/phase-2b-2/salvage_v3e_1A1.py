"""Salvage truncated v3e Chunk 1A1 response (Hanover Commercial Package).

Pattern: response was mid-stream truncated. JSON envelope opening + first
finding (and possibly partial leading prose of it) are lost. Surviving
content is a sequence of complete `{ "id": "..." ... }` finding objects
followed by a trailing `]\\n}\\n\\`\\`\\``.

Strategy: find first `{` followed by `"id":` pattern (boundary of first
complete finding), take from there to last `]`, wrap in synthetic envelope,
parse with json_repair.
"""
import json, re
import json_repair
from pathlib import Path

OUT = Path(r"C:\Users\Bogdan\Desktop\Run-Test Policies, Contracts\validation-2026-04-27\phase-2b-2")
SLUG = "run-test-election-services"

raw = (OUT / "_stage_b_v3e_chunk1A1_response_raw.txt").read_text(encoding='utf-8')
print(f"1A1 raw: {len(raw):,} chars")

# Find first { ... "id": pattern (boundary of first complete finding)
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
if len(findings) < 15:
    raise SystemExit(f"FAIL: only {len(findings)} findings recovered (<15 hard-stop threshold)")

for f in findings:
    f["_chunk"] = "core-1A1"
    like, sev = f.get("likelihood"), f.get("severity")
    if like and sev:
        f["risk_score"] = int(like) * int(sev)
    elif "risk_score" not in f:
        f["risk_score"] = None

print(f"  IDs: {[f.get('id','?') for f in findings[:3]]} ... {[f.get('id','?') for f in findings[-3:]]}")
print(f"  Categories: {set(f.get('category') for f in findings)}")

(OUT / "synthesis_v3e_chunk1A1.json").write_text(
    json.dumps({"client": SLUG, "chunk": "core-1A1", "findings": findings},
               indent=2, ensure_ascii=False),
    encoding='utf-8',
)
print(f"Wrote synthesis_v3e_chunk1A1.json")
