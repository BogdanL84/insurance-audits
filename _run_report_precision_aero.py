"""
Headless: generate the markdown audit report for Precision Aero.
Loads audit-state, calls report_writer, saves to output/audit-report.md.
"""

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
from core.report_writer import generate_markdown_report

CLIENT = ROOT / "clients" / "precision-aero"
OUTDIR = CLIENT / "output"


def main():
    state = ast.load(CLIENT)
    if not state.get("findings"):
        print("FATAL: no findings in audit-state.json")
        sys.exit(1)
    report_md = generate_markdown_report(state)
    if not report_md:
        print("FATAL: report_writer returned empty")
        sys.exit(2)
    out = OUTDIR / "audit-report.md"
    out.write_text(report_md, encoding="utf-8")
    print(f"Wrote {out}: {len(report_md):,} chars, {out.stat().st_size:,} bytes")
    print(f"Findings: {len(state['findings'])}")


if __name__ == "__main__":
    main()
