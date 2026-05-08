"""
Headless invocation of annotate_all_policies for Precision Aero.
Reads findings.json + per-policy analyses, writes <stem>-AUDITED.pdf
files into clients/precision-aero/output/.
"""

import json
import sys
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

from core.pdf_annotator import annotate_all_policies

CLIENT  = ROOT / "clients" / "precision-aero"
SLUG    = "precision-aero"
DISPLAY = "Precision Aero"
POLDIR  = CLIENT / "policies"
EXCHDIR = CLIENT / "ai-exchange"
OUTDIR  = CLIENT / "output"


def main():
    findings_path = OUTDIR / "findings.json"
    if not findings_path.exists():
        print(f"FATAL: findings.json not found at {findings_path}")
        sys.exit(1)
    payload = json.loads(findings_path.read_text(encoding="utf-8"))
    findings = payload.get("findings") if isinstance(payload, dict) else payload
    if not findings:
        print("FATAL: findings list empty.")
        sys.exit(1)

    policy_analyses = []
    for jf in sorted(EXCHDIR.glob(f"{SLUG}-policy-*-analysis.json")):
        try:
            pa = json.loads(jf.read_text(encoding="utf-8"))
            pa.setdefault("_source_file", pa.get("source_file") or jf.stem)
            policy_analyses.append(pa)
        except Exception as e:
            print(f"  ! skipping {jf.name}: {e}")
    print(f"Loaded {len(findings)} findings, {len(policy_analyses)} policy analyses.")

    OUTDIR.mkdir(parents=True, exist_ok=True)
    results = annotate_all_policies(
        policies_dir    = POLDIR,
        findings        = findings,
        policy_analyses = policy_analyses,
        client_name     = DISPLAY,
        output_dir      = OUTDIR,
    )

    print("\nAnnotation results:")
    for r in results:
        pdf, out, n_findings, err = r
        if err:
            print(f"  FAIL  {pdf} ({n_findings} findings) — {err}")
        elif out:
            try:
                size_mb = Path(out).stat().st_size / (1024 * 1024)
            except Exception:
                size_mb = -1
            print(f"  OK    {pdf} -> {Path(out).name} ({n_findings} findings, {size_mb:.1f} MB)")
        else:
            print(f"  ?     {pdf} ({n_findings} findings) — no output, no error")


if __name__ == "__main__":
    main()
