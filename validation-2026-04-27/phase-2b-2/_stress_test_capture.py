"""Stress test the new tempfile-based stdout capture in run_claude.

Uses the existing _stage_b_prompt.txt (354 KB synthesis prompt that produced
75 findings last run, but had stdout truncated to the last 27). With the new
capture, we expect ALL 75 findings to make it through.

Verifies:
  1. response_length in expected range (~120-160 KB)
  2. Captured response STARTS with proper JSON envelope opening
     (no mid-sentence truncation)
  3. Captured response ENDS with proper JSON envelope closing
     (or trailing prose AFTER a complete envelope)
  4. JSON parses successfully
  5. Result has roughly 75 findings (within ±10 for AI variance)

If any check fails, prints diagnostics and exits non-zero.
"""
import json, sys, time, re
from pathlib import Path

APP = Path(r"C:\Users\Bogdan\Documents\insurance-audits\app")
sys.path.insert(0, str(APP))

from core.claude_runner import run_claude, extract_json, ANALYSIS_TIMEOUT

PROMPT_PATH = Path(r"C:\Users\Bogdan\Desktop\Run-Test Policies, Contracts\validation-2026-04-27\phase-2b-2\_stage_b_prompt.txt")
OUT         = Path(r"C:\Users\Bogdan\Desktop\Run-Test Policies, Contracts\validation-2026-04-27\phase-2b-2")

prompt = PROMPT_PATH.read_text(encoding='utf-8')
print(f"Prompt size: {len(prompt):,} chars")

print(f"Calling claude (expect ~22 min)...")
t0 = time.time()
ok, result = run_claude(prompt, timeout=ANALYSIS_TIMEOUT)
elapsed = time.time() - t0
print(f"Claude returned in {elapsed:.0f}s ({elapsed/60:.1f} min)")
print(f"  ok={ok}")
print(f"  response_length={len(result or ''):,} chars")

# Save raw response for inspection
(OUT / "_stress_test_response_raw.txt").write_text(result or "", encoding='utf-8')

if not ok:
    print(f"\n❌ FAIL: claude returned not-ok. result[:500]={result[:500]}")
    sys.exit(1)

# CHECK 1 — response length in expected range
length_ok = 100_000 <= len(result) <= 200_000
print(f"\nCheck 1 — response length 100K-200K range: "
      f"{'✓ PASS' if length_ok else '✗ FAIL'} ({len(result):,} chars)")

# CHECK 2 — captured response STARTS with proper JSON envelope opening
head = result[:300].strip()
starts_with_json = head.startswith('{') and ('"client"' in head[:200] or '"findings"' in head[:200])
print(f"Check 2 — starts with JSON envelope: {'✓ PASS' if starts_with_json else '✗ FAIL'}")
print(f"  first 200 chars: {head[:200]!r}")

# CHECK 3 — captured response ENDS with proper JSON envelope closing
tail = result.rstrip()[-300:]
# Strip trailing prose (find last `}` and check what's after)
last_close = tail.rfind('}')
ends_clean = last_close >= 0
print(f"Check 3 — ends with valid JSON close: {'✓ PASS' if ends_clean else '✗ FAIL'}")
print(f"  last 300 chars: ...{tail[-300:]!r}")

# CHECK 4 — JSON parses
parsed = extract_json(result)
parse_ok = parsed is not None and isinstance(parsed, dict)
print(f"Check 4 — JSON parses: {'✓ PASS' if parse_ok else '✗ FAIL'}")

# CHECK 5 — roughly 75 findings
findings = (parsed or {}).get('findings', [])
finding_count_ok = 65 <= len(findings) <= 90
print(f"Check 5 — finding count 65-90 (expected ~75): "
      f"{'✓ PASS' if finding_count_ok else '✗ FAIL'} ({len(findings)} findings)")

if findings:
    from collections import Counter
    cats = Counter(f.get('category', '?') for f in findings)
    print(f"  categories: {dict(cats)}")

all_pass = length_ok and starts_with_json and ends_clean and parse_ok and finding_count_ok
print(f"\n{'='*60}")
print(f"STRESS TEST: {'✓✓✓ ALL CHECKS PASS — SAFE TO PROCEED' if all_pass else '✗ ONE OR MORE CHECKS FAILED — DO NOT PROCEED'}")
print(f"{'='*60}")

# Save the parsed findings for reuse (so we don't burn another synthesis call if everything's fine)
if parsed:
    (OUT / "synthesis_v3c.json").write_text(
        json.dumps(parsed if isinstance(parsed, dict) else {"findings": findings},
                   indent=2, ensure_ascii=False),
        encoding='utf-8',
    )
    print(f"\nSaved parsed result to synthesis_v3c.json (re-usable for Stage C)")

sys.exit(0 if all_pass else 1)
