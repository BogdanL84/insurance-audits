"""
One-shot data fixes for the 2026-05-08 Precision Aero quality audit:

  Fix 2: Reclassify finding-023 WC "Pending Rate Change — Mid-Term Premium
         Risk" from Needs Review to Bad with severity=3, likelihood=3
         (model-emitted misclassification; concrete policy provision with
         material premium-impact downside, not a confirm-with-carrier item).

  Fix 3: Drop finding-001 WC "Audit Scope Limitation — Contract Requirements
         Not Loaded" — meta-finding about the audit process, belongs in
         audit-state metadata or report cover-page, not the findings list.

  Fix 4: Collapse three Needs Review "Unintentional Errors and Omissions
         Giveback" findings (one per policy: USLI EPLI, WC PEKIN, AUTO)
         into a single PROGRAM-level rollup. The 4th E&O Giveback finding
         on BOP+UMBRELLA (category=Bad, "neither policy carries this
         endorsement") is intentionally NOT folded in — it asserts a
         concrete fact while the three NR findings say "we cannot
         determine," and the cross-reference in the rollup body handles
         the linkage.

Auditable: each drop is recorded in audit-state.json:state["filter_drops"]
with reason + ts. Each addition is tracked via source_findings[] on the
new finding.

Idempotent guard: rerunning will not double-apply (looks for the
specific ids; if any are missing, skips that pass). Use the .pre-filter
backup in output/ to roll back to the pre-2026-05-08-quality-fix state.
"""

import json
import shutil
import sys
import warnings
from datetime import datetime
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

CLIENT  = ROOT / "clients" / "precision-aero"
OUTDIR  = CLIENT / "output"
FIN     = OUTDIR / "findings.json"


def _drop_record(finding: dict, reason: str) -> dict:
    return {
        "id":               finding.get("id"),
        "policy_file":      finding.get("policy_file"),
        "requirement_type": finding.get("requirement_type"),
        "category":         finding.get("category"),
        "reason":           reason,
        "ts":               datetime.now().isoformat(timespec="seconds"),
    }


# ── Fix 4: collapsed-rollup finding ────────────────────────────────
COLLAPSED_EAO_GIVEBACK = {
    "id": "finding-eao-giveback-program",
    "category": "Needs Review",
    "policy_file": "PROGRAM",
    "requirement_type": "Program — Unintentional Errors & Omissions Giveback (per-policy status)",
    "policy_quote": "N/A",
    "policy_page": "N/A",
    "contract_quote": "N/A",
    "contract_page": "N/A",
    "contract_file": "N/A",
    "gap_description": (
        "Three policies in the program have not been confirmed as carrying "
        "the Unintentional Errors and Omissions giveback endorsement (which "
        "protects coverage if an inadvertent application or audit reporting "
        "error is later discovered). Status by policy:\n\n"
        "- Auto (Pekin): Cannot determine from extracted text. CA 31 34 is "
        "the carrier's broadening endorsement and may include this provision; "
        "standard ISO forms do not.\n"
        "- Workers' Comp (Pekin): WC policies traditionally don't carry a "
        "separate Unintentional E&O endorsement (the form is statutory), but "
        "the broader principle — that an inadvertent omission of a class "
        "code, payroll figure, or location should not void coverage — should "
        "be confirmed with Pekin.\n"
        "- EPLI (USLI): The analogous concern is whether innocent failure to "
        "disclose material facts at application or renewal voids coverage. "
        "Without the EPL-J coverage form text we cannot confirm whether USLI's "
        "EPLI form provides an innocent-insureds / innocent-misrepresentation "
        "severability provision.\n\n"
        "Note: the BOP and Umbrella are addressed in a separate Bad-category "
        "finding (finding-002 BOP+UMB) confirming neither policy carries the "
        "giveback — that is a concrete observation, not a confirm-with-carrier "
        "item."
    ),
    "plain_english": (
        "Insurance policies sometimes contain a \"giveback\" that protects "
        "you if you make an honest mistake on your application — for example, "
        "forgetting to mention a piece of equipment, or a class code is "
        "slightly wrong. If the giveback isn't there, the carrier could deny "
        "a claim because of that mistake. We need to confirm with the carrier "
        "whether this protection is on the Auto, WC, and EPLI policies. "
        "(We've separately confirmed it's NOT on the BOP and Umbrella — "
        "that's a separate finding.)"
    ),
    "recommendation": (
        "Ask each carrier in writing whether their respective policy carries "
        "an Unintentional E&O / inadvertent-omission giveback. For Auto "
        "(Pekin), confirm whether CA 31 34 includes it. For WC (Pekin), "
        "confirm whether the Pekin WC form has an analogous protection "
        "embedded. For EPLI (USLI), confirm the EPL-J base form has an "
        "innocent-insureds severability provision. If any are absent, request "
        "endorsement at next renewal."
    ),
    "covered_by_other_policy": False,
    "covered_by_which_policy": None,
    "tags": ["unintentional-eo", "general-rmf", "program-rollup", "needs-verification"],
    "discoveryQuestions": [],
    "source_findings": ["finding-007.USLI EPLI", "finding-003.WC PEKIN 24", "finding-002.AUTO"],
    "_chunk": "merge",
}


def main() -> None:
    if not FIN.exists():
        print(f"FATAL: {FIN} missing"); sys.exit(1)

    raw = json.loads(FIN.read_text(encoding="utf-8"))
    findings = raw.get("findings") if isinstance(raw, dict) else raw
    pre_count = len(findings)
    print(f"Pre: {pre_count} findings")

    state = ast.load(CLIENT)
    state.setdefault("filter_drops", [])

    # ── Fix 2: reclassify finding-023 WC ────────────────────────────
    fix2_done = False
    for f in findings:
        if (f.get("id") == "finding-023"
            and "WC PEKIN" in (f.get("policy_file") or "")
            and "Pending Rate Change" in (f.get("requirement_type") or "")):
            if f.get("category") == "Bad":
                print("Fix 2: already applied (finding-023 already Bad), skipping")
            else:
                print(f"Fix 2: reclassifying finding-023 WC: "
                      f"{f.get('category')!r} -> 'Bad', severity=3, likelihood=3")
                f["category"]    = "Bad"
                f["likelihood"]  = 3
                f["severity"]    = 3
                f["risk_score"]  = 9
                fix2_done = True
            break
    else:
        print("Fix 2: finding-023 WC not found — skipping")

    # ── Fix 3: drop finding-001 WC meta-finding ─────────────────────
    fix3_dropped = None
    for f in findings:
        if (f.get("id") == "finding-001"
            and "WC PEKIN" in (f.get("policy_file") or "")
            and "Audit Scope Limitation" in (f.get("requirement_type") or "")):
            fix3_dropped = f
            break
    if fix3_dropped:
        findings.remove(fix3_dropped)
        state["filter_drops"].append(_drop_record(
            fix3_dropped,
            "manual-drop-meta-audit-scope-belongs-in-state-metadata-not-findings",
        ))
        print(f"Fix 3: dropped finding-001 WC meta-finding")
    else:
        print("Fix 3: finding-001 WC meta-finding not found — skipping")

    # ── Fix 4: collapse three Needs Review E&O Giveback findings ────
    targets = []
    for f in list(findings):
        rt = (f.get("requirement_type") or "").lower()
        cat = f.get("category")
        pf = (f.get("policy_file") or "")
        if "unintentional" not in rt or ("errors" not in rt and "e&o" not in rt):
            continue
        if cat != "Needs Review":
            continue
        # Should match exactly: finding-007 EPLI / finding-003 WC / finding-002 AUTO
        if (f.get("id") == "finding-007" and "USLI EPLI" in pf) or \
           (f.get("id") == "finding-003" and "WC PEKIN" in pf) or \
           (f.get("id") == "finding-002" and "AUTO" in pf):
            targets.append(f)
    if len(targets) == 3:
        for f in targets:
            findings.remove(f)
            state["filter_drops"].append(_drop_record(
                f,
                "manual-collapse-into-finding-eao-giveback-program",
            ))
        # Insert the rollup near where the originals were (end-of-list is fine)
        findings.append(COLLAPSED_EAO_GIVEBACK)
        print(f"Fix 4: collapsed 3 NR E&O Giveback findings into "
              f"'{COLLAPSED_EAO_GIVEBACK['id']}'")
    elif len(targets) == 0:
        print("Fix 4: no NR E&O Giveback findings found — skipping (already collapsed?)")
    else:
        print(f"Fix 4: found {len(targets)} matches (expected 3) — aborting collapse "
              f"to avoid partial state. Inspect manually.")

    post_count = len(findings)
    print(f"\nPost: {post_count} findings (delta {post_count - pre_count:+d})")

    # Severity breakdown
    from collections import Counter
    cnt = Counter(f.get("category", "?") for f in findings)
    print(f"  Ugly={cnt.get('Ugly', 0)}  Bad={cnt.get('Bad', 0)}  "
          f"Needs Review={cnt.get('Needs Review', 0)}  Good={cnt.get('Good', 0)}")

    # Write findings.json
    if isinstance(raw, dict):
        out_payload = dict(raw)
        out_payload["findings"]      = findings
        out_payload["finding_count"] = post_count
    else:
        out_payload = findings
    tmp = FIN.with_suffix(FIN.suffix + ".tmp")
    tmp.write_text(json.dumps(out_payload, indent=2, ensure_ascii=False), encoding="utf-8")
    tmp.replace(FIN)
    print(f"Wrote {FIN.name}")

    # Update audit-state
    state["findings"] = findings
    ast.save(CLIENT, state)
    print(f"Updated audit-state.json (filter_drops total: {len(state['filter_drops'])})")


if __name__ == "__main__":
    main()
