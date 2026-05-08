"""
findings_filter.py — Defensive post-synthesis filter that drops chunk-induced
"No <X> Policy" hallucinations.

Background: chunked synthesis splits policies into coverage clusters, so each
chunk only sees a subset of the program. A chunk that doesn't see the WC
policy can confidently emit "Program Gap — No Workers' Compensation Policy"
even when WC is in another chunk. The merge step doesn't cross-check these
claims against the full program inventory, so they survive into findings.json.

This filter is a defensive net. It runs after merge_chunks() returns. For each
finding whose title matches a canonical "missing-coverage" phrasing (Program
Gap — No X / X Policy — Not Provided / Missing Policy — X), we check whether
X is actually present in the program (via the per-policy analyses' policy_type
+ coverage_parts). If yes, we drop the finding. If no, we keep it — a real
gap.

Match scope is requirement_type ONLY. The body is too prone to incidental
phrasings ("the umbrella does not extend EPLI" → false-positive on
"no umbrella") and gets skipped.

Coverage flags are FINE-GRAINED: a "Management Liability" policy that only
carries an EPLI coverage_part contributes EPLI to PROGRAM_HAS but NOT D&O,
so a "Missing Policy — D&O" finding remains legitimate.
"""

import re


# ── Program inventory ───────────────────────────────────────────────
def build_program_inventory(policy_analyses: list) -> set:
    """Map per-policy analyses → set of fine-grained coverage flags actually
    provided by the program. Drives the hallucination filter."""
    has = set()
    for d in policy_analyses or []:
        pt = (d.get("policy_type") or "").lower()
        cp = [str(c).lower() for c in (d.get("coverage_parts") or [])]
        sf = (d.get("source_file") or d.get("_source_file") or "").lower()

        if "auto" in pt or "auto" in sf:
            has.add("AUTO")
        if "workers" in pt or "wc" in sf or "comp" in pt:
            has.add("WC")
        if "umbrella" in pt or "excess" in pt:
            has.add("UMBRELLA")
        # Coverage-part inspection drives fine-grained flags.
        # Do NOT inflate from policy_type alone (e.g. a "Management Liability"
        # package may only carry EPLI — D&O is then absent).
        for c in cp:
            if "general liability" in c or c.strip() == "gl":
                has.add("GL")
            if "property" in c:
                has.add("PROPERTY")
            if "inland marine" in c or c.startswith("im "):
                has.add("IM")
            # EBL has the substring "e&o" in some carrier phrasings — match
            # EBL first and treat that branch as exclusive of standalone E&O.
            if "employee benefits" in c or "ebl" in c:
                has.add("EBL")
            elif "professional liability" in c or "errors and omissions" in c or " e&o" in f" {c}":
                has.add("E&O")
            if "epli" in c or "employment practices" in c:
                has.add("EPLI")
            if "d&o" in c or "directors and officers" in c:
                has.add("DO")
            if "fiduciary" in c:
                has.add("FIDUCIARY")
            if "crime" in c or "fidelity" in c:
                has.add("CRIME")
            if "cyber" in c:
                has.add("CYBER")
            if "pollution" in c:
                has.add("POLLUTION")
    return has


# ── Hallucination patterns (match against requirement_type ONLY) ────
HALLUCINATION_PATTERNS = [
    # "Program Gap — No <X>" / "Program Gap — No <X> Policy"
    (re.compile(r"^Program Gap.*\bNo General Liability\b", re.I),               "GL"),
    (re.compile(r"^Program Gap.*\bNo CGL\b", re.I),                             "GL"),
    (re.compile(r"^Program Gap.*\bNo Workers'?\s*Comp", re.I),                  "WC"),
    (re.compile(r"^Program Gap.*\bNo Commercial Auto\b", re.I),                 "AUTO"),
    (re.compile(r"^Program Gap.*\bNo Auto Policy\b", re.I),                     "AUTO"),
    (re.compile(r"^Program Gap.*\bNo Umbrella\b", re.I),                        "UMBRELLA"),
    (re.compile(r"^Program Gap.*\bNo Excess Liability\b", re.I),                "UMBRELLA"),
    (re.compile(r"^Program Gap.*\bNo Property\s*(?:[/—\-]|$)", re.I),           "PROPERTY"),
    (re.compile(r"^Program Gap.*\bNo Inland Marine\b", re.I),                   "IM"),
    (re.compile(r"^Program Gap.*\bNo EPLI\b", re.I),                            "EPLI"),
    (re.compile(r"^Program Gap.*\bNo Employment Practices\b", re.I),            "EPLI"),

    # "<X> Policy — Not Provided in Audit Batch"
    (re.compile(r"^Auto Policy\s*[—\-:]\s*Not Provided", re.I),                 "AUTO"),
    (re.compile(r"^Commercial Auto Policy\s*[—\-:]\s*Not Provided", re.I),      "AUTO"),
    (re.compile(r"^Workers'?\s*Comp(?:ensation)?\s*Policy\s*[—\-:]\s*Not Provided",
                re.I),                                                          "WC"),
    (re.compile(r"^Umbrella(?:\s*Policy)?\s*[—\-:]\s*Not Provided", re.I),      "UMBRELLA"),
    (re.compile(r"^General Liability(?:\s*Policy)?\s*[—\-:]\s*Not Provided",
                re.I),                                                          "GL"),

    # Canonical "Missing Policy — <X>" — only canonical names. Generic
    # "Missing Policy — Property" intentionally excluded so Bailee /
    # Property-of-Others-Liability findings (specific gaps) survive.
    (re.compile(r"^Missing Policy\s*[—\-:]\s*EPLI\b", re.I),                    "EPLI"),
    (re.compile(r"^Missing Policy\s*[—\-:]\s*Workers", re.I),                   "WC"),
    (re.compile(r"^Missing Policy\s*[—\-:]\s*Commercial Auto\b", re.I),         "AUTO"),
    (re.compile(r"^Missing Policy\s*[—\-:]\s*Umbrella\b", re.I),                "UMBRELLA"),
    (re.compile(r"^Missing Policy\s*[—\-:]\s*General Liability\b", re.I),       "GL"),
    # Intentionally NOT including "Missing Policy — D&O" or
    # "— Management Liability" — those remain legitimate when only an
    # EPLI-only ML policy is in the program.
]

SINGLE_POLICY_PROGRAM_RE = re.compile(r"single-?policy program", re.I)


def _is_hallucination(finding: dict, program_has: set, n_policies: int):
    """Return (drop, reason). Match against requirement_type ONLY."""
    rt = (finding.get("requirement_type") or "")

    if SINGLE_POLICY_PROGRAM_RE.search(rt) and n_policies > 1:
        return True, f"single-policy-program-but-{n_policies}-policies-exist"

    for pat, flag in HALLUCINATION_PATTERNS:
        if pat.search(rt):
            if flag in program_has:
                return True, f"claims-{flag}-missing-but-program-has-{flag}"
            return False, None
    return False, None


# ── Public entry point ──────────────────────────────────────────────
def filter_hallucinated_findings(
    findings: list,
    policy_analyses: list,
) -> tuple[list, list]:
    """Filter chunk-induced 'No X Policy' hallucinations.

    Args:
      findings:        merged synthesis findings list
      policy_analyses: list of per-policy analysis dicts (each with
                       policy_type / coverage_parts / source_file)

    Returns (kept, dropped):
      kept    — findings list with hallucinations removed
      dropped — list of (finding, reason_str) tuples for visibility
    """
    program_has = build_program_inventory(policy_analyses)
    n_policies  = len(policy_analyses or [])
    kept    = []
    dropped = []
    for f in findings or []:
        drop, reason = _is_hallucination(f, program_has, n_policies)
        if drop:
            dropped.append((f, reason))
        else:
            kept.append(f)
    return kept, dropped
