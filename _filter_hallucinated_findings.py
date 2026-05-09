"""
Re-apply the post-synthesis cleanup passes to a client's existing
findings.json:
  (1) filter_hallucinated_findings — drop chunk-induced "No <X> Policy"
      claims when X is in the program
  (2) dedupe_program_findings      — collapse duplicate program-level
      findings (synthesis + matrix passes both emit "No D&O" / "No Crime")
  (3) correct_carrier_mentions     — fix "Hanover BOP" → "Pekin BOP"
      style carrier-name hallucinations

The same passes run automatically inside the pipeline (_Analyze.py after
run_chunked_synthesis, before persist). Use this script to re-clean
findings produced before the cleanup passes shipped, or after rule changes.

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
from core.findings_filter import (
    filter_hallucinated_findings,
    dedupe_program_findings,
    correct_carrier_mentions,
    build_program_inventory,
    drop_record,
)


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
    if not backup.exists():
        shutil.copy2(findings_path, backup)
        print(f"Backed up pre-filter findings to {backup.name}")
    else:
        print(f"Pre-filter backup already exists at {backup.name} — preserving original baseline")

    # Pass 1: hallucination filter
    kept, dropped = filter_hallucinated_findings(findings, analyses)
    print(f"\nPass 1 — Hallucination filter: dropped {len(dropped)} findings")
    for f, reason in dropped:
        print(f"  - id={f.get('id', '?')}  pf={f.get('policy_file') or '<empty>'!r}")
        print(f"    rt: {(f.get('requirement_type') or '')[:80]}")
        print(f"    reason: {reason}")
    # Persistent audit-trail records (state['filter_drops'] in Pass 5)
    drop_records = [drop_record(f, reason) for f, reason in dropped]

    # Pass 2: program-level dedup
    kept, merged = dedupe_program_findings(kept)
    print(f"\nPass 2 — Program-level dedup: collapsed {len(merged)} duplicates")
    for winner, loser, key in merged:
        print(f"  - {key}: kept {winner.get('id','?')} ({winner.get('category')}), "
              f"dropped {loser.get('id','?')} ({loser.get('category')})")
        print(f"      kept rt:    {(winner.get('requirement_type') or '')[:80]}")
        print(f"      dropped rt: {(loser.get('requirement_type') or '')[:80]}")

    # Pass 3: carrier-name correction
    kept, corrections = correct_carrier_mentions(kept, analyses)
    print(f"\nPass 3 — Carrier correction: fixed {len(corrections)} mentions")
    for fid, pf, wrong, actual, n in corrections:
        print(f"  - {fid} on {pf}: \"{wrong}\" → \"{actual}\" ({n} replacement{'s' if n != 1 else ''})")

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

    # Update audit-state.json — findings + filter_drops audit trail
    state = ast.load(client)
    state["findings"] = kept
    if drop_records:
        state.setdefault("filter_drops", []).extend(drop_records)
    ast.save(client, state)
    print(f"Updated audit-state.json findings field "
          f"and appended {len(drop_records)} filter_drops record"
          f"{'s' if len(drop_records) != 1 else ''}.")


if __name__ == "__main__":
    slug = sys.argv[1] if len(sys.argv) > 1 else "precision-aero"
    main(slug)
