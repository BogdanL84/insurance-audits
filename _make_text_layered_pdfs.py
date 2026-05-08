"""
Generate text-layered versions of the 3 scanned Precision Aero PDFs so the
annotator can anchor highlights via PyMuPDF's text search.

Strategy: for each scanned PDF, render each page to PNG at 300 DPI, run
pytesseract in 'pdf' output mode (yields a single-page PDF with a hidden
OCR text layer over the rasterized image), then merge all pages into one
PDF via fitz.Document.insert_pdf. Save as <stem>-text-layered.pdf, then
replace the original (backing up to <stem>.pdf.bak first).

Idempotent: if <stem>.pdf.bak already exists, we restore from it before
re-running so the layered version is rebuilt from the true original.
"""

import io
import shutil
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

import fitz
import pytesseract
from PIL import Image

pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

ROOT      = Path(__file__).parent
POLDIR    = ROOT / "clients" / "precision-aero" / "policies"
TARGETS   = ["BOP.pdf", "UMBRELLA.pdf", "WC PEKIN 24.pdf"]
DPI       = 300


def make_text_layered(src_pdf: Path, dst_pdf: Path) -> tuple[int, int, int]:
    """Build a text-layered copy of src_pdf at dst_pdf.
    Returns (pages, words_total, elapsed_sec)."""
    t0 = time.time()
    src = fitz.open(str(src_pdf))
    out = fitz.open()  # blank target
    words_total = 0
    try:
        for i in range(len(src)):
            page = src[i]
            pix = page.get_pixmap(dpi=DPI)
            img = Image.open(io.BytesIO(pix.tobytes("png")))
            try:
                pdf_bytes = pytesseract.image_to_pdf_or_hocr(
                    img, extension="pdf", lang="eng"
                )
            except Exception as e:
                print(f"    ! OCR PDF gen failed on page {i+1}: {e}", flush=True)
                # Fallback: insert the rasterized image as-is (no text layer)
                tmp_doc = fitz.open()
                page2   = tmp_doc.new_page(width=pix.width, height=pix.height)
                page2.insert_image(page2.rect, pixmap=pix)
                pdf_bytes = tmp_doc.write()
                tmp_doc.close()

            page_doc = fitz.open(stream=pdf_bytes, filetype="pdf")
            out.insert_pdf(page_doc)
            page_doc.close()

            # Count OCR words from the resulting text layer for diagnostics
            try:
                words_total += len(out[i].get_text().split())
            except Exception:
                pass
    finally:
        src.close()
    out.save(str(dst_pdf), garbage=4, deflate=True)
    out.close()
    return len(fitz.open(str(dst_pdf))), words_total, int(time.time() - t0)


def main():
    print(f"Building text-layered PDFs for {len(TARGETS)} scanned policies.\n")
    grand_t0 = time.time()
    for filename in TARGETS:
        src = POLDIR / filename
        bak = POLDIR / (filename + ".bak")
        dst = POLDIR / (Path(filename).stem + "-text-layered.pdf")

        if not src.exists():
            print(f"  ! {filename}: missing, skipping")
            continue

        # Restore from backup if it exists, so we always start from the true original
        if bak.exists():
            print(f"  - {filename}: restoring from existing .bak before rebuild")
            shutil.copy2(bak, src)

        print(f"  - {filename}: building text-layered version...")
        try:
            pages, words, elapsed = make_text_layered(src, dst)
        except Exception as e:
            print(f"    ! FAIL: {e}")
            continue
        size_kb = dst.stat().st_size / 1024
        print(f"    OK pages={pages} words_in_layer={words:,} {size_kb:.0f} KB in {elapsed}s")

        # Back up original then replace
        if not bak.exists():
            shutil.copy2(src, bak)
            print(f"    backed up original -> {bak.name}")
        shutil.move(str(dst), str(src))
        print(f"    replaced {src.name} with text-layered version.")

    print(f"\nTotal: {time.time() - grand_t0:.0f}s")


if __name__ == "__main__":
    main()
