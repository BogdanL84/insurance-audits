"""
Re-apply the hallucination filter to a client's existing findings.json.

This is a thin wrapper over app/core/findings_filter.py. The same filter
runs automatically inside the pipeline (_Analyze.py:run_chunked_synthesis
→ filter_hallucinated_findings → persist). Use this script when you need
to re-filter findings produced before the in-pipeline filter shipped, or
when you've changed the filter rules and want to re-apply them without
re-running synthesis.

Usage:
  python _filter_hallucinated_findings.py [client-slug]   # default: precision-aero
"""

import json
import shutil
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
from core.findings_filter import filter_hallucinated_findings, build_program_inventory


def main(slug: str = "precision-aero") -> None:
    client  = ROOT / "clients" / slug
    exchdir = client / "ai-exchange"
    outdir  = client / "output"
    findings_path = outdir / "findings.json"

    if not findings_path.exists():
        print(f"FATAL: {findings_path} does not exist."); sys.exit(1)

    raw = json.loads(findings_path.read_text(encoding="utf-8"))
    findings = raw.get("findings") if isinstance(raw, dict) else raw

    analyses = []
    for jf in sorted(exchdir.glob(f"{slug}-policy-*-analysis.json")):
        analyses.append(json.loads(jf.read_text(encoding="utf-8")))

    print(f"Client: {slug}")
    print(f"Pre-filter findings: {len(findings)}")
    print(f"Program covers: {sorted(build_program_inventory(analyses))}")

    backup = outdir / "findings.json.pre-filter"
    shutil.copy2(findings_path, backup)
    print(f"Backed up pre-filter findings to {backup.name}")

    kept, dropped = filter_hallucinated_findings(findings, analyses)
    print(f"\nDropped {len(dropped)} hallucinated findings:")
    for f, reason in dropped:
        rt = (f.get("requirement_type") or "")[:80]
        print(f"  - id={f.get('id', '?')}  pf={f.get('policy_file') or '<empty>'!r}")
        print(f"    rt: {rt}")
        print(f"    reason: {reason}")

    # Recompute counts
    from collections import Counter
    counts = Counter(f.get("category", "?") for f in kept)
    print(f"\nKept {len(kept)} findings — "
          f"Ugly={counts.get('Ugly', 0)} Bad={counts.get('Bad', 0)} "
          f"Review={counts.get('Needs Review', 0)} Good={counts.get('Good', 0)}")

    # Write filtered findings.json
    if isinstance(raw, dict):
        out_payload = dict(raw)
        out_payload["findings"]      = kept
        out_payload["finding_count"] = len(kept)
    else:
        out_payload = kept
    tmp = findings_path.with_suffix(findings_path.suffix + ".tmp")
    tmp.write_text(json.dumps(out_payload, indent=2, ensure_ascii=False), encoding="utf-8")
    tmp.replace(findings_path)
    print(f"\nWrote filtered findings.json ({len(kept)} findings).")

    # Update audit-state.json
    state = ast.load(client)
    state["findings"] = kept
    ast.save(client, state)
    print("Updated audit-state.json findings field.")


if __name__ == "__main__":
    slug = sys.argv[1] if len(sys.argv) > 1 else "precision-aero"
    main(slug)
