"""
Re-run per-policy analysis on the 3 newly-OCR'd Precision Aero PDFs.
Standalone mode (no contracts uploaded). Single-chunk for all 3 (sizes verified).
"""

import json
import sys
import time
import warnings
from pathlib import Path

warnings.filterwarnings("ignore")
try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT / "app"))

from core.claude_runner import (
    run_claude, extract_json,
    build_standalone_policy_prompt,
    ANALYSIS_TIMEOUT,
)

CLIENT  = ROOT / "clients" / "precision-aero"
SLUG    = "precision-aero"
EXCHDIR = CLIENT / "ai-exchange"
# BOP succeeded on the first run; UMBRELLA + WC PEKIN 24 still need analysis.
TARGETS = ["UMBRELLA.pdf", "WC PEKIN 24.pdf"]


def client_notes() -> str:
    p = CLIENT / "client-notes.md"
    return p.read_text(encoding="utf-8") if p.exists() else ""


def main():
    notes = client_notes()
    print(f"Re-analyzing {len(TARGETS)} OCR'd policies for Precision Aero (standalone mode).\n")
    grand_t0 = time.time()
    results = {}

    for filename in TARGETS:
        stem = Path(filename).stem
        text_path = EXCHDIR / f"{stem}-extracted.txt"
        if not text_path.exists():
            print(f"  - {filename}: extracted text missing, skipping")
            continue
        text = text_path.read_text(encoding="utf-8")
        prompt = build_standalone_policy_prompt(filename, text, notes)

        print(f"  - {filename}: prompt {len(prompt):,} chars; running...")
        t0 = time.time()
        ok, output = run_claude(prompt, timeout=ANALYSIS_TIMEOUT)
        elapsed = time.time() - t0

        if not ok:
            print(f"    FAIL run_claude in {elapsed:.0f}s: {output[:300]}")
            results[filename] = {"ok": False, "elapsed": elapsed, "error": output[:300]}
            continue

        parsed = extract_json(output)
        if not parsed:
            print(f"    FAIL JSON parse after {elapsed:.0f}s; output {len(output):,} chars")
            (EXCHDIR / f"{SLUG}-policy-{stem}-RAW.txt").write_text(output, encoding="utf-8")
            results[filename] = {"ok": False, "elapsed": elapsed, "error": "JSON parse failed"}
            continue

        parsed["_source_file"] = filename
        out = EXCHDIR / f"{SLUG}-policy-{stem}-analysis.json"
        out.write_text(json.dumps(parsed, indent=2, ensure_ascii=False), encoding="utf-8")
        size_kb = out.stat().st_size / 1024
        ptype   = parsed.get("policy_type", "?")
        print(f"    OK {ptype}, {size_kb:.1f} KB written in {elapsed:.0f}s")
        results[filename] = {"ok": True, "elapsed": elapsed, "policy_type": ptype, "kb": size_kb}

    grand = time.time() - grand_t0
    print(f"\nTotal elapsed: {grand:.0f}s ({grand/60:.1f} min)")
    print("\nSummary:")
    for f, r in results.items():
        if r["ok"]:
            print(f"  OK   {f}: {r['policy_type']}, {r['kb']:.1f} KB ({r['elapsed']:.0f}s)")
        else:
            print(f"  FAIL {f}: {r['error']}")


if __name__ == "__main__":
    main()
