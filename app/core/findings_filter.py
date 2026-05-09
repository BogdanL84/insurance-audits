"""
findings_filter.py — Post-synthesis cleanup. Three orthogonal passes:

  1. filter_hallucinated_findings  — drop chunk-induced "No <X> Policy"
     claims when X is actually in the program.
  2. dedupe_program_findings       — collapse duplicate program-level
     findings (synthesis + matrix passes both emit "No D&O" / "No Crime"
     etc.; keep the higher-severity one).
  3. correct_carrier_mentions      — fix carrier-name hallucinations in
     finding text (e.g. "Hanover BOP" replaced with the actual carrier
     when the policy_file's carrier is something else).

Match scope for #1 is requirement_type ONLY. The body is too prone to
incidental phrasings ("the umbrella does not extend EPLI" → false-positive
on "no umbrella") and gets skipped.

Coverage flags are FINE-GRAINED: a "Management Liability" policy that only
carries an EPLI coverage_part contributes EPLI to PROGRAM_HAS but NOT D&O,
so a "Missing Policy — D&O" finding remains legitimate.
"""

import re
from pathlib import Path


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

# ── Multi-policy "not provided in audit" check ─────────────────────
# The HALLUCINATION_PATTERNS above match against requirement_type only —
# they catch single-source hallucinations whose title carries the canonical
# "Not Provided" / "Missing Policy" phrasing. Some chunks emit the same
# "X policy was not provided" claim in the BODY of a finding whose title
# is a generic coverage-confirmation question (e.g. "Hired & Non-Owned
# Auto — Coverage Confirmation" with body "A Pekin Commercial Auto policy
# at $1M CSL ... was not provided in this audit batch"). This per-sentence
# scan catches those: a sentence in gap_description must contain BOTH a
# "<policy noun> ... not provided/supplied/included in (this) audit/batch"
# phrase AND the referenced policy must actually be in the program
# inventory. Per-sentence (vs whole-text) matching avoids false positives
# where unrelated mentions of "not provided" and a policy name happen to
# land in the same long description.

_NOT_PROVIDED_PHRASE = re.compile(
    r"\b(?:was|were|is|are)?\s*"
    r"not\s+(?:provided|supplied|included)"
    r"(?:\s+(?:in|to|for))?\s*"
    r"(?:this\s+)?(?:audit|batch|review|engagement)",
    re.I,
)

# Policy-reference patterns → coverage flag. Names that the model uses
# when referencing a missing policy in body text. Distinct from the
# policy_file flag set so we can distinguish e.g. "Auto policy" (claim)
# from "policy_file = AUTO.pdf" (where the finding is anchored).
_POLICY_REF_PATTERNS = [
    (re.compile(r"\b(?:Commercial\s+)?Auto\s+policy\b", re.I),               "AUTO"),
    (re.compile(r"\b(?:Pekin|Hanover|Travelers|Hartford|Chubb|CNA|"
                r"Cincinnati|Liberty|Zurich|Nationwide|AmTrust|Berkley|"
                r"Markel|Cincinnati|FCCI|Selective|Westfield|Auto-Owners)"
                r"\s+Commercial\s+Auto\b", re.I),                            "AUTO"),
    (re.compile(r"\bWorkers'?\s*Comp(?:ensation)?\s+policy\b", re.I),        "WC"),
    (re.compile(r"\bWC\s+policy\b", re.I),                                   "WC"),
    (re.compile(r"\bUmbrella\s+policy\b", re.I),                             "UMBRELLA"),
    (re.compile(r"\bExcess\s+(?:Liability\s+)?policy\b", re.I),              "UMBRELLA"),
    (re.compile(r"\bBOP\s+policy\b", re.I),                                  "BOP"),
    (re.compile(r"\bProperty\s+policy\b", re.I),                             "PROPERTY"),
    (re.compile(r"\b(?:General\s+Liability|CGL)\s+policy\b", re.I),          "GL"),
    (re.compile(r"\bGL\s+policy\b", re.I),                                   "GL"),
    (re.compile(r"\bEPLI\s+policy\b", re.I),                                 "EPLI"),
    (re.compile(r"\bCyber\s+policy\b", re.I),                                "CYBER"),
]


def _multi_policy_not_provided(finding: dict, program_has: set):
    """Return (flag, sentence) when gap_description claims a policy is
    missing AND that policy is in the program. Per-sentence scan."""
    gd = finding.get("gap_description") or ""
    if not gd:
        return None, None
    # BOP coverage_part check: BOP isn't normally in program_has by name
    # because we flag GL/PROPERTY/IM/EBL separately. If the claim names
    # "BOP policy" specifically and we have GL or PROPERTY, treat that
    # as the BOP being present.
    program_has_with_bop = set(program_has)
    if "GL" in program_has or "PROPERTY" in program_has:
        program_has_with_bop.add("BOP")
    for sentence in re.split(r"(?<=[.!?])\s+", gd):
        if not _NOT_PROVIDED_PHRASE.search(sentence):
            continue
        for pat, flag in _POLICY_REF_PATTERNS:
            if pat.search(sentence) and flag in program_has_with_bop:
                return flag, sentence
    return None, None


def _is_hallucination(finding: dict, program_has: set, n_policies: int):
    """Return (drop, reason). Match against requirement_type first; if no
    title-based pattern fires, fall through to the multi-policy
    gap_description scan."""
    rt = (finding.get("requirement_type") or "")

    if SINGLE_POLICY_PROGRAM_RE.search(rt) and n_policies > 1:
        return True, f"single-policy-program-but-{n_policies}-policies-exist"

    for pat, flag in HALLUCINATION_PATTERNS:
        if pat.search(rt):
            if flag in program_has:
                return True, f"claims-{flag}-missing-but-program-has-{flag}"
            return False, None

    # Title didn't match a hallucination pattern — check the body for
    # the multi-policy "X policy not provided" variant.
    flag, _sentence = _multi_policy_not_provided(finding, program_has)
    if flag:
        return True, f"gap-description-claims-{flag}-not-provided-but-in-program"

    return False, None


# ── Drop-record helper (audit trail) ───────────────────────────────
def drop_record(finding: dict, reason: str) -> dict:
    """Convert a (finding, reason) drop tuple into a serializable record
    for persistence in audit-state.json:state['filter_drops']."""
    from datetime import datetime
    return {
        "id":               finding.get("id"),
        "policy_file":      finding.get("policy_file"),
        "requirement_type": finding.get("requirement_type"),
        "category":         finding.get("category"),
        "reason":           reason,
        "ts":               datetime.now().isoformat(timespec="seconds"),
    }


# ── Public entry point: hallucination filter ───────────────────────
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


# ── Program-level dedup ────────────────────────────────────────────
# Severity rank: lower = drop first (Good < Review < Bad < Ugly).
_SEVERITY_RANK = {"Good": 0, "Needs Review": 1, "Review": 1, "Bad": 2, "Ugly": 3}

# Map a program-level finding to a coverage-key bucket. Two findings
# claiming the same missing coverage are duplicates of each other.
_PROGRAM_COVERAGE_PATTERNS = [
    # (regex, key)
    (re.compile(r"\bcyber\b", re.I),                                      "CYBER"),
    (re.compile(r"\b(directors?\s*&?\s*officers?|d\s*&\s*o|management liability)\b",
                re.I),                                                    "DO_ML"),
    (re.compile(r"\b(crime|fidelity|fid(?:elity)?\s*bond|social engineering)\b",
                re.I),                                                    "CRIME"),
    (re.compile(r"\b(products|aerospace products|product liability)\b",
                re.I),                                                    "PRODUCTS"),
    (re.compile(r"\b(pollution|environmental)\b", re.I),                  "POLLUTION"),
    (re.compile(r"\b(professional liability|errors\s*&?\s*omissions|e\s*&\s*o|miscellaneous professional)\b",
                re.I),                                                    "E_AND_O"),
    (re.compile(r"\bstop\s*gap\b", re.I),                                 "STOP_GAP"),
    (re.compile(r"\b(fiduciary)\b", re.I),                                "FIDUCIARY"),
]


def _program_coverage_key(f: dict) -> str | None:
    """Return a coverage-key bucket for grouping program-level duplicates,
    or None when no canonical bucket matches (don't dedup)."""
    pf = (f.get("policy_file") or "").strip().upper()
    if pf not in ("", "PROGRAM", "N/A"):
        return None  # only dedup program-level findings
    title = f.get("requirement_type") or ""
    tags  = " ".join(f.get("tags") or [])
    blob  = f"{title}\n{tags}"
    # Only buckets that look like missing-policy claims; the cross-program
    # entity-type matrix finding ("First Named Insured Entity Type
    # Inconsistency") shouldn't get bucketed.
    if not re.search(r"\b(no|missing|program gap|not provided)\b", title, re.I):
        return None
    for pat, key in _PROGRAM_COVERAGE_PATTERNS:
        if pat.search(blob):
            return key
    return None


def dedupe_program_findings(findings: list) -> tuple[list, list]:
    """Collapse duplicate program-level findings about the same missing
    coverage. Keep the highest-severity one in each bucket.

    Returns (kept, merged) where merged = list of (kept_finding,
    dropped_finding, key) tuples for visibility."""
    findings = list(findings or [])
    buckets: dict[str, list[int]] = {}  # key -> list of indices
    for i, f in enumerate(findings):
        key = _program_coverage_key(f)
        if key:
            buckets.setdefault(key, []).append(i)

    merged: list = []
    drop_idxs: set[int] = set()
    for key, idxs in buckets.items():
        if len(idxs) < 2:
            continue
        # Pick the one with highest severity rank; tiebreak on risk_score
        def _rank(i):
            f = findings[i]
            cat  = (f.get("category") or "").strip()
            sev  = _SEVERITY_RANK.get(cat, 0)
            risk = f.get("risk_score") or 0
            try:
                risk = int(risk)
            except (TypeError, ValueError):
                risk = 0
            return (sev, risk)
        ranked = sorted(idxs, key=_rank, reverse=True)
        winner = ranked[0]
        for loser in ranked[1:]:
            merged.append((findings[winner], findings[loser], key))
            drop_idxs.add(loser)

    kept = [f for i, f in enumerate(findings) if i not in drop_idxs]
    return kept, merged


# ── Carrier-name correction ────────────────────────────────────────
# Carriers worth name-correcting. The replacement only fires when the
# wrong-carrier name sits in a "<Carrier> <coverage-noun>" or "Have
# <Carrier> add" construction — i.e. where the text is naming the carrier
# of THIS policy rather than mentioning an alternative carrier in a
# recommendation.
_CARRIER_BRANDS = [
    "Hanover", "Travelers", "Hartford", "Chubb", "CNA", "Liberty Mutual",
    "Cincinnati", "Zurich", "AIG", "Nationwide", "Allstate", "Progressive",
    "AmTrust", "Berkley", "Markel", "Arch", "QBE", "FCCI", "Selective",
    "Westfield", "Auto-Owners",
]
_COVERAGE_NOUNS = (
    r"BOP|CGL|Commercial Auto|Commercial General Liability|Commercial Umbrella|"
    r"Auto|Umbrella|Property|GL|WC|Workers'?\s*Comp(?:ensation)?|"
    r"Excess|Package|Inland Marine"
)


def _build_carrier_lookup(policy_analyses: list) -> dict:
    """Return {filename: actual_carrier_str}. Empty when no analyses."""
    out = {}
    for pa in policy_analyses or []:
        sf = pa.get("source_file") or pa.get("_source_file") or ""
        sf = Path(sf).name
        c  = (pa.get("carrier") or "").strip()
        if sf and c:
            out[sf] = c
    return out


def _carrier_brand_token(carrier_str: str) -> str:
    """Extract the brand token from a long carrier name. e.g.
    'Pekin Insurance Company' → 'Pekin'."""
    if not carrier_str:
        return ""
    # Strip common suffixes
    s = re.sub(r"\b(Insurance|Ins\.?|Company|Co\.?|Group|Mutual|Corp(?:oration)?)\b",
               "", carrier_str, flags=re.I)
    # Take the first non-trivial token
    tokens = [t for t in re.split(r"[\s,/]+", s) if t and len(t) > 1]
    return tokens[0] if tokens else ""


def correct_carrier_mentions(
    findings: list,
    policy_analyses: list,
) -> tuple[list, list]:
    """Replace carrier-name hallucinations in finding text.

    Targets only constructions that imply "the carrier of this policy"
    (e.g. "Hanover BOP", "Have Hanover add"). Other carrier mentions
    (recommendations to consider alternative markets) are preserved.

    Returns (findings_in_place, corrections) where corrections is a list
    of (finding_id, policy_file, wrong_brand, actual_brand, n_replacements)
    tuples for visibility. Mutates findings in place.
    """
    carriers = _build_carrier_lookup(policy_analyses)
    if not carriers:
        return findings, []

    corrections = []
    coverage_re = _COVERAGE_NOUNS

    for f in findings or []:
        pf = (f.get("policy_file") or "").strip()
        # Only apply when the finding is anchored to a single policy
        pieces = [p.strip() for p in pf.replace(";", ",").split(",") if p.strip()]
        pdf_pieces = [p for p in pieces if p.lower().endswith(".pdf")]
        if len(pdf_pieces) != 1:
            continue

        actual_carrier = carriers.get(pdf_pieces[0])
        if not actual_carrier:
            continue
        actual_brand = _carrier_brand_token(actual_carrier)
        if not actual_brand:
            continue

        for field in ("gap_description", "recommendation"):
            text = f.get(field) or ""
            if not text:
                continue

            for wrong in _CARRIER_BRANDS:
                # Skip if this brand IS the actual carrier
                if wrong.lower() == actual_brand.lower():
                    continue
                # Pattern A: "<Wrong> <coverage-noun>" — implies "the X policy"
                pat_a = re.compile(rf"\b{re.escape(wrong)}\s+(?={coverage_re}\b)", re.I)
                # Pattern B: "Have <Wrong> add" / "with <Wrong>" / "the <Wrong> ___"
                # Restrict B to "Have <Wrong> add" construction to avoid sweeping
                # alternative-market recommendations.
                pat_b = re.compile(rf"\bHave\s+{re.escape(wrong)}\s+add\b", re.I)

                new_text, n_a = pat_a.subn(f"{actual_brand} ", text)
                new_text, n_b = pat_b.subn(f"Have {actual_brand} add", new_text)
                n_total = n_a + n_b
                if n_total > 0:
                    text = new_text
                    corrections.append((
                        f.get("id", "?"),
                        pdf_pieces[0],
                        wrong,
                        actual_brand,
                        n_total,
                    ))
            f[field] = text

    return findings, corrections
