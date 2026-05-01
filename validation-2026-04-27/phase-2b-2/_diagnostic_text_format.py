"""Task 2 diagnostic — replay the 354K synthesis prompt with --output-format text
instead of --output-format json. If the JSON envelope wrapping is the upstream
truncation point, text mode should capture cleanly.

Saves three artifacts for inspection:
  _diagnostic_text_format.txt        — what the script captured (post-run_claude)
  _diagnostic_text_tempfile.txt      — raw tempfile preserved (pre-run_claude processing)
  _diagnostic_text_meta.json         — metadata (sizes, timing, JSON structure check)
"""
import os, sys, time, subprocess, tempfile, shutil, json
from pathlib import Path

OUT = Path(r"C:\Users\Bogdan\Desktop\Run-Test Policies, Contracts\validation-2026-04-27\phase-2b-2")
PROMPT_PATH = OUT / "_stage_b_prompt.txt"

prompt = PROMPT_PATH.read_text(encoding='utf-8')
print(f"Prompt size: {len(prompt):,} chars")

# Use --output-format text instead of json. No JSON envelope.
CMD = "claude --dangerously-skip-permissions -p --output-format text"

# Capture via tempfile (same approach as run_claude) but preserve the tempfile no matter what
tmp_dir = Path(tempfile.mkdtemp(prefix="diag_text_"))
tmp_out = tmp_dir / "stdout.txt"
print(f"Tempfile: {tmp_out}")
print(f"Calling claude with --output-format text (expect ~22 min)...")

t0 = time.time()
with open(tmp_out, "w", encoding='utf-8', errors='replace') as f_out:
    proc = subprocess.run(
        CMD,
        shell=True,
        input=prompt,
        stdout=f_out,
        stderr=subprocess.PIPE,
        text=True,
        timeout=1800,
        encoding='utf-8',
        errors='replace',
    )
elapsed = time.time() - t0

# Always preserve the tempfile to OUT folder
preserved = OUT / "_diagnostic_text_tempfile.txt"
shutil.copyfile(tmp_out, preserved)
captured = tmp_out.read_text(encoding='utf-8', errors='replace')

print(f"Returned in {elapsed:.0f}s ({elapsed/60:.1f} min)")
print(f"  rc:                  {proc.returncode}")
print(f"  stderr (first 200):  {(proc.stderr or '')[:200]!r}")
print(f"  Tempfile bytes:      {tmp_out.stat().st_size:,}")
print(f"  read_text chars:     {len(captured):,}")
print()

# Quick structural checks
print(f"First 300 chars: {captured[:300]!r}")
print()
print(f"Last 300 chars:  {captured[-300:]!r}")
print()

import re
fids = re.findall(r'finding-(\d+)', captured)
unique_fids = sorted(set(fids), key=int)
print(f"Total finding-NNN occurrences: {len(fids)}")
print(f"Unique IDs: {len(unique_fids)}, range: {unique_fids[0] if unique_fids else None} → {unique_fids[-1] if unique_fids else None}")

# Save what the script saw
(OUT / "_diagnostic_text_format.txt").write_text(captured, encoding='utf-8')

# Try to parse — text mode should still emit JSON inside markdown fence (or raw)
import sys as _sys
_sys.path.insert(0, r"C:\Users\Bogdan\Documents\insurance-audits\app")
from core.claude_runner import extract_json
parsed = extract_json(captured)
findings_count = len((parsed or {}).get("findings", []))

meta = {
    "elapsed_s": round(elapsed, 1),
    "rc": proc.returncode,
    "tempfile_bytes": tmp_out.stat().st_size,
    "captured_chars": len(captured),
    "stderr_first_200": (proc.stderr or '')[:200],
    "first_300_chars": captured[:300],
    "last_300_chars": captured[-300:],
    "finding_id_count": len(unique_fids),
    "finding_id_range": [unique_fids[0] if unique_fids else None,
                         unique_fids[-1] if unique_fids else None],
    "extract_json_findings_count": findings_count,
}
(OUT / "_diagnostic_text_meta.json").write_text(json.dumps(meta, indent=2), encoding='utf-8')

# Check expectations
print()
print("=" * 70)
clean_start = captured.lstrip().startswith('{') or captured.lstrip().startswith('```')
mid_word_start = re.match(r'^[a-z]', captured.strip())
print(f"Starts with '{{' or '```' : {clean_start}")
print(f"Starts mid-word         : {bool(mid_word_start)}")
print(f"Finding count           : {len(unique_fids)} (expect 60-90)")
print(f"extract_json findings   : {findings_count}")
print("=" * 70)
print(f"Saved diagnostics to {OUT}")
