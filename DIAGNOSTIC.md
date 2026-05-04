# OCR Pre-processing — Diagnostic & Next Steps

**Date:** 2026-05-04
**Context:** Attempt to add OCR pre-processing to Stage A document intake so scanned image-only PDFs (Precision Aero's BOP, UMBRELLA, WC PEKIN 24) get text-extracted instead of producing zero-word per-policy analyses.
**Outcome:** Stopped — every install path attempted hit the same Windows DLL initialization failure. No OCR is available without admin-rights intervention or a cloud-API approach.

## What was tried

### 1. `pip install rapidocr-onnxruntime` (pure-python OCR via ONNX Runtime)

**Install:** succeeded — `rapidocr-onnxruntime-1.4.4`, `onnxruntime-1.25.1`, `opencv-python-4.13.0.92`, `Shapely-2.1.2`, `pyclipper-1.4.0`, `flatbuffers-25.12.19` all installed cleanly into `C:\Users\Bogdan\anaconda3\Lib\site-packages\`.

**Import:** failed.

```
ImportError: DLL load failed while importing onnxruntime_pybind11_state:
  A dynamic link library (DLL) initialization routine failed.
  File: C:\Users\Bogdan\anaconda3\Lib\site-packages\onnxruntime\capi\_pybind_state.py
```

**Diagnosis:** `onnxruntime_pybind11_state.pyd` requires the Microsoft Visual C++ 2015–2022 Redistributable (x64). It's a system-wide DLL set, not bundled with pip wheels. Pip cannot install it.

### 2. `pip install easyocr` (PyTorch-based OCR)

**Install:** succeeded.

**Import:** failed at `import torch`.

```
OSError: [WinError 1114] A dynamic link library (DLL) initialization routine failed.
  Error loading "C:\Users\Bogdan\anaconda3\Lib\site-packages\torch\lib\c10.dll" or
  one of its dependencies.
```

**Diagnosis:** PyTorch's `c10.dll` has the same VC++ Redistributable dependency. Same root cause as #1.

### 3. `conda install -c conda-forge tesseract pytesseract` (system-binary OCR)

**Run:** the install was attempted twice (once 2026-05-01, once 2026-05-03) and both runs left no observable artifacts: no `tesseract.exe` in `C:\Users\Bogdan\anaconda3\Library\bin\`, no `pytesseract` Python module installed, no obvious error in captured output. By 2026-05-04 multiple `conda.exe` and Python conda-script processes were still running for the original invocations and were killed manually.

**Diagnosis (presumptive):** conda's solver was either still running for ~2 days (plausible — conda-forge channel has a notoriously expensive solve on Windows) or the underlying tesseract conda-forge package itself depends on the same VC++ runtime that's missing. The conda-forge `tesseract` package on Windows links against `vcruntime140.dll`/`msvcp140.dll`, which is part of the VC++ Redistributable.

### Common root cause — Microsoft Visual C++ Redistributable

All three failure paths trace to the same missing system component:

> Microsoft Visual C++ 2015–2022 Redistributable (x64) — `vcruntime140.dll`, `vcruntime140_1.dll`, `msvcp140.dll`, `concrt140.dll`

This is a system-wide install that **requires admin rights** on Windows. Modern Windows 10/11 ship with it pre-installed via Windows Update for most consumer setups, but the absence here suggests it was either never installed or was uninstalled. Without it, no compiled C/C++ Python extensions targeting modern MSVC will load — including ONNX Runtime, PyTorch, OpenCV's compiled bits, and the conda-forge tesseract binary.

**Other dependent packages that would fail under the same condition:** numpy (some builds), pandas (some builds), scipy, scikit-learn, lxml, pyzmq. The fact that the existing audit pipeline runs (Streamlit, pymupdf, pillow, openpyxl, json-repair) implies those particular packages either bundle their own runtime or use older MSVC versions still satisfied by what's on disk.

## Three options for next session

The user must pick one before any further OCR work proceeds.

### (a) Install Visual C++ Redistributable — admin rights required

**Source:** Microsoft, official: <https://aka.ms/vs/17/release/vc_redist.x64.exe>

**Steps:**
1. Download `vc_redist.x64.exe` from the link above (or via `winget install Microsoft.VCRedist.2015+.x64`).
2. Right-click → Run as administrator → Install.
3. Reboot if prompted.
4. After install: re-run the `pip install easyocr` smoke test
   (`python -c "import easyocr; r = easyocr.Reader(['en'], gpu=False); print('ok')"`).
   The first import downloads English models (~64 MB) — takes ~30 sec.
5. Once that works, integrate OCR into `app/core/pdf_extractor.py:_extract_pdf` per the original plan.

**Pros:** unblocks the broader Python ecosystem too (this DLL is needed for many libraries). Solves the underlying problem rather than working around it.

**Cons:** requires admin rights one-time. Most permissive but most invasive option.

### (b) Install Tesseract via official Windows installer — admin rights required

**Source:** UB-Mannheim build, official: <https://github.com/UB-Mannheim/tesseract/wiki>

**Steps:**
1. Download `tesseract-ocr-w64-setup-5.x.x.exe`.
2. Right-click → Run as administrator → Install (defaults are fine).
3. Note the install path (typically `C:\Program Files\Tesseract-OCR\tesseract.exe`).
4. Add to PATH or set `pytesseract.pytesseract.tesseract_cmd` in code.
5. `pip install pytesseract` (the Python wrapper — already installed during conda attempt or trivial to install).
6. Integrate into `app/core/pdf_extractor.py`.

**Pros:** lighter weight than option (a). Tesseract is a single-purpose tool, no system-wide DLL impact. Well-tested for OCR specifically.

**Cons:** still requires admin one-time. Doesn't unblock other Python libraries that need VC++ Redistributable.

### (c) Cloud OCR via Claude API or OpenAI Vision — no admin, costs API quota

**Approach:** for each page of an image-only PDF, render it to PNG (PyMuPDF can do this), base64-encode, send to Claude or OpenAI vision API with prompt "extract all text from this page verbatim." Concatenate per-page output as the OCR'd text.

**Steps:**
1. Add `_ocr_pdf_via_api(path)` helper to `app/core/pdf_extractor.py`.
2. Use the existing `claude_runner` infrastructure with a vision-capable prompt — Claude Code's `claude -p` should support image input via stream-json prompt or we'd switch to direct Anthropic SDK calls.
3. Cache results to disk so re-runs don't re-pay (`<stem>-extracted.txt` already serves this purpose).

**Pros:** no admin, no system install. Works today.

**Cons:** burns API quota. Bogdan flagged this as needing explicit approval (the original task spec said "Don't burn API quota on this. PDF annotator and report generation should both be entirely local operations" — same principle applies). Estimate: a 35-page BOP at typical Anthropic vision pricing is ~$0.50-$1.00 per document; 3 PDFs ~$2-$3 per Precision Aero re-run. Not huge but real, and requires multi-call latency (each page is a separate API call, ~5s each, so 35-page BOP = ~3 min, all 3 PDFs ~10 min).

**Recommendation:** for a one-off backfill of Precision Aero's 3 PDFs, (c) is cheapest in elapsed time. For a permanent feature in the pipeline, (a) or (b) is better — once admin is granted, OCR is local, fast, and free.

## What's preserved on disk regardless

The work to date is unaffected by this OCR blocker:

- 55 Precision Aero findings recovered to `clients/precision-aero/output/findings.json`
- 2 marked-up PDFs (AUTO, USLI EPLI) successfully generated; 3 scanned PDFs gracefully skipped
- Markdown report generation works
- All Friday-evening hardening commits intact: `91e6a50` (persist per stage), `7f982d1` (annotator skip), `14a384f` (live progress UX), `8ab633e` (comma split), `2bfdfbe` (recovery), `c741f33` (PDF annotator hang doc), `e46cead` (RESUME-STATE update)

The OCR addition would expand the deliverable from 2 marked-up PDFs to 5 and lift the 3 scanned policies' per-policy analyses from ~1.6 KB metadata-only to ~10–16 KB substantive — but the audit on the 2 text-extractable policies is already shipping-quality.

## State at stop

- All running OCR-install processes killed (4 PIDs: 9932, 10016, 12008, 15136 — two `conda.exe` and two `conda-script.py` instances from the long-running solves).
- No partial OCR install remains: pip-installed `easyocr`, `rapidocr-onnxruntime`, `onnxruntime`, `opencv-python`, `Shapely`, `pyclipper`, `flatbuffers` are still in the conda env from the earlier successful pip-install steps. They're harmless (just don't work) but bloat the env. Can be removed later via `pip uninstall easyocr rapidocr-onnxruntime onnxruntime opencv-python` if desired.
- No code changes to `pdf_extractor.py` were applied — Stage A is exactly as it was before this attempt.
- `RESUME-STATE.md` open issue #1 (OCR pre-processing) remains open.
