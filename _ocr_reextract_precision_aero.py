"""
One-shot: re-extract the 3 scanned Precision Aero PDFs with the new OCR-aware
pdf_extractor, save extracted text files, update audit-state.json.
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

from core.pdf_extractor import extract_with_info, save_extracted_text, get_word_count
from core import audit_state as ast

CLIENT  = ROOT / "clients" / "precision-aero"
POLDIR  = CLIENT / "policies"
EXCHDIR = CLIENT / "ai-exchange"

TARGETS = ["BOP.pdf", "UMBRELLA.pdf", "WC PEKIN 24.pdf"]

def main():
    state = ast.load(CLIENT)
    print(f"Re-extracting {len(TARGETS)} scanned PDFs via OCR.\n")

    grand_total = 0
    for filename in TARGETS:
        src = POLDIR / filename
        if not src.exists():
            print(f"  ✗ {filename}: file not found, skipping")
            continue

        print(f"  • {filename}")
        t0 = time.time()
        try:
            extracted, info = extract_with_info(src)
        except Exception as e:
            print(f"    ✗ extraction error: {e}")
            continue
        elapsed = time.time() - t0

        words = get_word_count(extracted)
        out   = EXCHDIR / f"{src.stem}-extracted.txt"
        save_extracted_text(extracted, out)
        ast.mark_extracted(state, filename, "policy", words, info.get("method", "pdf_text"))

        grand_total += words
        print(f"    method={info['method']}, pages={len(extracted)}, words={words:,}, "
              f"elapsed={elapsed:.0f}s")
        if info.get("method") == "ocr":
            print(f"    OCR pages: {info.get('ocr_pages_succeeded')} ok / "
                  f"{info.get('ocr_pages_failed')} failed")

    ast.refresh_stage(state)
    ast.save(CLIENT, state)
    print(f"\nTotal new words extracted: {grand_total:,}")
    print(f"audit-state.json updated.")

if __name__ == "__main__":
    main()
