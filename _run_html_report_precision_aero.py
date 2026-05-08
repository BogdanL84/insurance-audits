"""
Generate the dark-mode HTML audit report for Precision Aero.
Reads audit-state.json + per-policy analyses, writes audit-report.html.
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

from core import audit_state as ast
from core.html_report import render_audit_report

CLIENT  = ROOT / "clients" / "precision-aero"
SLUG    = "precision-aero"
EXCHDIR = CLIENT / "ai-exchange"
OUTDIR  = CLIENT / "output"


def main() -> None:
    state = ast.load(CLIENT)
    if not state.get("findings"):
        print("FATAL: no findings in audit-state.json"); sys.exit(1)

    policy_analyses = []
    for jf in sorted(EXCHDIR.glob(f"{SLUG}-policy-*-analysis.json")):
        try:
            pa = json.loads(jf.read_text(encoding="utf-8"))
            pa.setdefault("_source_file", pa.get("source_file") or jf.stem)
            policy_analyses.append(pa)
        except Exception as e:
            print(f"  ! Skipping {jf.name}: {e}")
    print(f"Loaded {len(state['findings'])} findings, "
          f"{len(policy_analyses)} policy analyses.")

    html_doc = render_audit_report(state, policy_analyses, SLUG)
    out = OUTDIR / "audit-report.html"
    out.write_text(html_doc, encoding="utf-8")
    print(f"\nWrote {out}: {len(html_doc):,} chars, "
          f"{out.stat().st_size:,} bytes")


if __name__ == "__main__":
    main()
