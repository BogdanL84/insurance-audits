"""
cross_policy.py — Matrix-based cross-policy gap detection.

Builds three deterministic matrices from per-policy and per-contract analyses,
then composes a prompt for a final AI pass that emits cross-cutting findings.

Concerns separated:
  - Internal helpers + matrix builders: pure Python, fully unit-testable.
  - KB I/O: file reads only.
  - Prompt builder: text concatenation only.

The Claude call itself is in pages/_Analyze.py — this module never imports
or invokes claude_runner.run_claude.
"""

import json
import re
from pathlib import Path


# ── Constants ──────────────────────────────────────────────────────

# knowledge-base/universal/ — three levels up from app/core/cross_policy.py
_KB_UNIVERSAL_DIR = Path(__file__).parent.parent.parent / "knowledge-base" / "universal"

_KB_FILES_FOR_BLOCK = [
    "GAP-01-named-insured-verification.md",
    "GAP-17-contract-specific-coverage-satisfaction.md",
    "GAP-20-cross-policy-named-insured-inconsistency.md",
    "GAP-21-designated-entity-cancellation-notice.md",
]
_KB_PER_FILE_CAP = 10_000   # chars

# Coverage line → list of (policy_type, required_coverage_part_or_None) tuples.
# When required_coverage_part is set, the policy must contain it in coverage_parts[].
# Per Q1=b refinement: Package counts only when its coverage_parts contains the right line.
_COVERAGE_LINE_TO_POLICY_TYPES: dict = {
    "general_liability":      [("CGL", None), ("Package", "GL")],
    "auto_liability":         [("Auto", None)],
    "workers_comp":           [("Workers Comp", None)],
    "employers_liability":    [("Workers Comp", None)],   # EL rides on WC
    "professional_liability": [("Professional Liability", None), ("Tech E&O", None)],
    "cyber":                  [("Cyber", None)],
    "umbrella":               [("Umbrella", None)],
    "property":               [("Property", None), ("Package", "Property")],
    "crime":                  [("Crime", None), ("Management Liability", "Crime")],
    "inland_marine":          [("Inland Marine", None), ("Package", "Inland Marine")],
}

# Coverage line → (policy.limits field name, contract.by_coverage[line] minimum field name).
# (None, None) means no $-comparison applies (e.g., Workers Comp statutory).
_COVERAGE_LINE_TO_LIMIT_FIELD: dict = {
    "general_liability":      ("each_occurrence",       "minimum_per_occurrence"),
    "auto_liability":         ("combined_single_limit", "minimum_csl_each_occurrence"),
    "workers_comp":           (None,                    None),                       # statutory
    "employers_liability":    ("each_accident",         "minimum_per_accident"),
    "professional_liability": ("each_claim",            "minimum_per_claim"),
    "cyber":                  ("each_occurrence",       "minimum_per_occurrence"),
    "umbrella":               ("each_occurrence",       "minimum_aggregate"),
    "property":               (None,                    None),
    "crime":                  (None,                    None),
    "inland_marine":          (None,                    None),
}


# ── Internal helpers (deterministic) ───────────────────────────────

def _normalize_entity_name(name: str) -> str:
    """Return a normalized key for entity matching.

    Lowercases, strips, removes punctuation, normalizes 'L.L.C.' → 'llc', etc.
    The result is for dict-key matching ONLY — display strings preserve original
    spelling per refinement 3.
    """
    if not name:
        return ""
    s = name.lower().strip()
    # Normalize entity-suffix punctuation
    s = re.sub(r"\bl\.?\s*l\.?\s*c\.?\b", "llc", s)
    s = re.sub(r"\bi\.?\s*n\.?\s*c\.?\b", "inc", s)
    s = re.sub(r"\bcorp\.?\b", "corp", s)
    s = re.sub(r"\bp\.?\s*c\.?\b", "pc", s)
    s = re.sub(r"\bltd\.?\b", "ltd", s)
    s = re.sub(r"[,.\(\)]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def _coverage_line_to_applicable_policies(coverage_line: str, policy_analyses: list) -> list:
    """Return list of source_file values whose policy_type maps to this coverage line.

    For Package-style policies, requires the named coverage_part to be present in
    coverage_parts[] (case-insensitive).
    """
    spec = _COVERAGE_LINE_TO_POLICY_TYPES.get(coverage_line, [])
    if not spec:
        return []
    out = []
    for pa in policy_analyses or []:
        ptype  = (pa.get("policy_type") or "").strip()
        cparts = pa.get("coverage_parts") or []
        cparts_norm = [str(c).upper() for c in cparts]
        for required_type, required_part in spec:
            if ptype != required_type:
                continue
            if required_part is None:
                src = pa.get("_source_file") or pa.get("source_file") or "(unknown)"
                if src not in out:
                    out.append(src)
                break
            if required_part.upper() in cparts_norm:
                src = pa.get("_source_file") or pa.get("source_file") or "(unknown)"
                if src not in out:
                    out.append(src)
                break
    return out


def _extract_primary_limit(policy_analysis: dict, coverage_line: str):
    """Return (value, field_name) for the primary limit relevant to coverage_line.

    Returns (None, None) when no $-comparison applies (e.g., statutory WC).
    Returns (None, field_name) when the field is expected but absent in the policy.
    """
    field_name, _ = _COVERAGE_LINE_TO_LIMIT_FIELD.get(coverage_line, (None, None))
    if not field_name:
        return None, None
    limits = policy_analysis.get("limits") or {}
    val = limits.get(field_name)
    # Compatibility fallbacks for variant carrier field naming
    if val is None and field_name == "combined_single_limit":
        val = limits.get("each_occurrence")
    if val is None and field_name == "each_occurrence":
        val = limits.get("per_occurrence") or limits.get("aggregate")
    if isinstance(val, str):
        # Handle "$1,000,000" string variants — strip dollars/commas
        try:
            val = int(re.sub(r"[^\d]", "", val))
        except (ValueError, TypeError):
            val = None
    return val, field_name


def _verdict_for_compliance(
    contract_min,
    policy_limit,
    umbrella_may_satisfy,
    umbrella_total_limit,
):
    """Compute (verdict, delta).

    verdict: "missing_data" | "missing_policy" | "met" | "shortfall" | "violation"
    delta:   policy_limit - contract_min (None when not computable)
    """
    if contract_min is None:
        return "missing_data", None
    if not isinstance(contract_min, (int, float)):
        return "missing_data", None
    if policy_limit is None:
        return "missing_data", None
    if not isinstance(policy_limit, (int, float)):
        return "missing_data", None
    delta = policy_limit - contract_min
    if delta >= 0:
        return "met", delta
    # Primary is short. Check umbrella mitigation.
    if umbrella_may_satisfy and isinstance(umbrella_total_limit, (int, float)):
        combined = policy_limit + umbrella_total_limit
        if combined >= contract_min:
            return "met", delta   # met via umbrella attachment
    if umbrella_may_satisfy is False:
        # Contract structurally bars umbrella attachment for this line
        return "violation", delta
    return "shortfall", delta


def _severity_hint_for(
    verdict: str,
    ai_required:  bool, ai_present,
    pnc_required: bool, pnc_present,
    wos_required: bool, wos_present,
) -> str:
    """severity_hint per refinement 2:
       critical = missing_policy
       high     = violation (umbrella barred and shortfall)
       medium   = shortfall
       low      = met-or-missing-data but missing AI/PNC/WOS where required
       informational = otherwise
    """
    if verdict == "missing_policy":
        return "critical"
    if verdict == "violation":
        return "high"
    if verdict == "shortfall":
        return "medium"
    # met or missing_data — fall through to AI/PNC/WOS check
    missing_aux = (
        (ai_required  and ai_present  is False) or
        (pnc_required and pnc_present is False) or
        (wos_required and wos_present is False)
    )
    return "low" if missing_aux else "informational"


def _checklist_value(policy_analysis: dict, key: str):
    """Return True/False for a checklist key, or 'unknown' if absent."""
    checklist = policy_analysis.get("checklist") or {}
    if key not in checklist:
        return "unknown"
    return bool(checklist[key])


def _ai_present(policy_analysis: dict):
    """Combined AI presence: True if blanket OR scheduled OR completed_ops endorsed.
    'unknown' if all three are absent from the checklist.
    """
    b = _checklist_value(policy_analysis, "additional_insured_blanket")
    s = _checklist_value(policy_analysis, "additional_insured_scheduled")
    c = _checklist_value(policy_analysis, "additional_insured_completed_ops")
    if b == "unknown" and s == "unknown" and c == "unknown":
        return "unknown"
    return (b is True) or (s is True) or (c is True)


def _max_severity(*hints) -> str:
    """Return the highest-severity hint among inputs."""
    order = ["critical", "high", "medium", "low", "informational"]
    rank = {h: i for i, h in enumerate(order)}
    cur = "informational"
    for h in hints:
        if h in rank and rank[h] < rank[cur]:
            cur = h
    return cur


# ── Public matrix construction ──────────────────────────────────────

def build_entity_matrix(policy_analyses: list) -> dict:
    """Construct entity × policy matrix from policy analyses.

    Robust to missing fields: returns the most useful matrix it can build with
    available data. When `additional_named_insureds` is absent on an analysis
    (e.g., re-running an old analysis), treats it as an empty list.

    Entity names: per refinement 3, every entry includes both `display_name`
    (original spelling as extracted) and `normalized_name` (case-folded for
    matrix-internal lookups).
    """
    if not policy_analyses:
        return {
            "entities": [], "policies": [], "policy_types": {},
            "first_named_insured_entity_types": {},
            "matrix": {}, "inconsistencies": [],
        }

    policies_in_order: list = []
    policy_types: dict = {}
    fni_types:    dict = {}
    # entity_records: normalized_key → {"display_name": str, "per_policy": {source_file: cell}, "variants": set}
    entity_records: dict = {}

    for pa in policy_analyses:
        src = pa.get("_source_file") or pa.get("source_file") or "(unknown)"
        if src in policies_in_order:
            continue
        policies_in_order.append(src)
        policy_types[src] = (pa.get("policy_type") or "").strip() or "unknown"

        # First Named Insured
        ni      = (pa.get("named_insured") or "").strip()
        ni_type = (pa.get("named_insured_entity_type") or "").strip() or "unspecified"
        fni_types[src] = ni_type
        if ni:
            key = _normalize_entity_name(ni)
            rec = entity_records.setdefault(key, {
                "display_name": ni, "per_policy": {}, "variants": set(),
            })
            rec["variants"].add(ni)
            rec["per_policy"][src] = {
                "status": "first_named_insured",
                "entity_type": ni_type,
                "via_endorsement": None,
                "endorsement_type": None,
                "broad_form_llc_risk": False,
                "page": None,
            }

        # Additional Named Insureds
        for anr in (pa.get("additional_named_insureds") or []):
            ent = (anr.get("entity") or "").strip()
            if not ent:
                continue
            key = _normalize_entity_name(ent)
            rec = entity_records.setdefault(key, {
                "display_name": ent, "per_policy": {}, "variants": set(),
            })
            rec["variants"].add(ent)
            rec["per_policy"][src] = {
                "status": "additional_named_insured",
                "entity_type": (anr.get("entity_type") or "").strip() or "unspecified",
                "via_endorsement": anr.get("via_endorsement"),
                "endorsement_type": anr.get("endorsement_type"),
                "broad_form_llc_risk": bool(anr.get("broad_form_llc_risk")),
                "page": anr.get("page"),
            }

        # Additional Insureds (separate from NI)
        for ai in (pa.get("additional_insureds") or []):
            ent = (ai.get("entity") or "").strip()
            if not ent:
                continue
            key = _normalize_entity_name(ent)
            rec = entity_records.setdefault(key, {
                "display_name": ent, "per_policy": {}, "variants": set(),
            })
            rec["variants"].add(ent)
            # Don't overwrite an existing FNI / additional_named_insured cell with AI
            if src in rec["per_policy"]:
                continue
            rec["per_policy"][src] = {
                "status": "additional_insured",
                "entity_type": (ai.get("entity_type") or "").strip() or "unspecified",
                "via_endorsement": ai.get("via_endorsement"),
                "endorsement_type": ai.get("endorsement_type"),
                "broad_form_llc_risk": bool(ai.get("broad_form_llc_risk")),
                "page": ai.get("page"),
            }

    # Build the output matrix dict, keyed by display_name (per refinement 3)
    entities_display: list = []
    matrix: dict = {}
    for key, rec in sorted(entity_records.items(), key=lambda kv: kv[1]["display_name"].lower()):
        display = rec["display_name"]
        entities_display.append(display)
        matrix[display] = {}
        for src in policies_in_order:
            base_cell = {
                "display_name":    display,
                "normalized_name": key,
            }
            if src in rec["per_policy"]:
                cell = {**base_cell, **rec["per_policy"][src]}
            else:
                cell = {**base_cell, "status": "missing"}
            matrix[display][src] = cell

    # Inconsistencies — derived from the matrix for the AI to reason from
    inconsistencies: list = []

    # Kind 1: First Named Insured entity-type mismatch (Inc vs LLC across policies)
    if fni_types:
        types_seen = {t for t in fni_types.values() if t and t != "unspecified"}
        if len(types_seen) > 1:
            inconsistencies.append({
                "kind": "first_named_insured_entity_type_mismatch",
                "details": f"Policies disagree on First Named Insured entity type: {sorted(types_seen)}",
                "policy_breakdown": fni_types,
            })

    # Kind 2: Entity partial inclusion (present on some, missing from others)
    for display in entities_display:
        present_on   = [src for src in policies_in_order
                        if matrix[display][src]["status"] != "missing"]
        missing_from = [src for src in policies_in_order
                        if matrix[display][src]["status"] == "missing"]
        if present_on and missing_from:
            inconsistencies.append({
                "kind": "entity_partial_inclusion",
                "entity": display,
                "present_on": present_on,
                "missing_from": missing_from,
            })

    # Kind 3: Broad Form LLC risk
    for display in entities_display:
        risk_policies = [src for src in policies_in_order
                         if matrix[display][src].get("broad_form_llc_risk") is True]
        if risk_policies:
            inconsistencies.append({
                "kind": "broad_form_llc_risk",
                "entity": display,
                "policies_with_risk": risk_policies,
            })

    return {
        "entities":                          entities_display,
        "policies":                          policies_in_order,
        "policy_types":                      policy_types,
        "first_named_insured_entity_types":  fni_types,
        "matrix":                            matrix,
        "inconsistencies":                   inconsistencies,
    }


def build_contract_compliance_matrix(contracts_data: dict, policy_analyses: list) -> dict:
    """Construct contract × coverage-line × policy compliance matrix.

    Per Q3: generates `verdict: "missing_policy"` rows when no policy of the
    required type exists in the program.

    Per refinement 2: each row carries a `severity_hint` field.
    """
    rows: list = []
    # Singular keys match the verdict values returned by _verdict_for_compliance.
    summary = {
        "total_requirements": 0,
        "met":                0,
        "shortfall":          0,
        "violation":          0,
        "missing_data":       0,
        "missing_policy":     0,
    }

    if not contracts_data:
        return {"rows": rows, "summary": summary}

    # Compute total umbrella stack — used for umbrella mitigation comparisons
    umbrella_limits: list = []
    for pa in (policy_analyses or []):
        if (pa.get("policy_type") or "").strip() == "Umbrella":
            limits = pa.get("limits") or {}
            for fld in ("each_occurrence", "general_aggregate", "aggregate"):
                v = limits.get(fld)
                if isinstance(v, (int, float)):
                    umbrella_limits.append(v)
                    break
    umbrella_total = max(umbrella_limits) if umbrella_limits else None

    for c_filename, c_data in contracts_data.items():
        if not c_data:
            continue
        if c_data.get("has_insurance_provisions") is False:
            continue
        by_cov = c_data.get("by_coverage") or {}
        if not by_cov:
            continue

        for line, line_data in by_cov.items():
            if not line_data:
                continue

            # Pull contract minimums + scope flags
            limit_field, contract_min_field = _COVERAGE_LINE_TO_LIMIT_FIELD.get(line, (None, None))
            contract_min = line_data.get(contract_min_field) if contract_min_field else None
            umbrella_may = line_data.get("umbrella_may_satisfy_minimum")
            ai_required  = bool(line_data.get("additional_insured_required"))
            pnc_required = bool(line_data.get("primary_noncontributory_required"))
            wos_required = bool(line_data.get("waiver_of_subrogation_required"))

            # Build a requirement summary string
            req_parts: list = []
            if isinstance(contract_min, (int, float)):
                req_parts.append(f"${contract_min:,} {limit_field}")
            elif limit_field:
                req_parts.append(f"{limit_field} (no minimum specified)")
            if ai_required:
                req_parts.append("AI required")
            if pnc_required:
                req_parts.append("P/NC required")
            if wos_required:
                req_parts.append("WOS required")
            requirement_summary = "; ".join(req_parts) or "(no $ requirement)"

            applicable = _coverage_line_to_applicable_policies(line, policy_analyses)
            policy_check: dict = {}
            row_severity = "informational"

            if not applicable:
                # Per Q3: emit a missing_policy cell
                policy_check["(no policy of this type in program)"] = {
                    "policy_type":          "MISSING",
                    "primary_limit_value":  None,
                    "primary_limit_field":  limit_field,
                    "delta":                None,
                    "verdict":              "missing_policy",
                    "ai_present":           "unknown",
                    "pnc_present":          "unknown",
                    "wos_present":          "unknown",
                    "umbrella_mitigation":  None,
                    "severity_hint":        "critical",
                    "notes":                f"Contract requires {line} coverage but no policy of this type was found in the program.",
                }
                summary["missing_policy"] += 1
                summary["total_requirements"] += 1
                row_severity = "critical"

            for src in applicable:
                pa = next(
                    (p for p in (policy_analyses or [])
                     if (p.get("_source_file") or p.get("source_file")) == src),
                    None,
                )
                if pa is None:
                    continue
                policy_limit, policy_field = _extract_primary_limit(pa, line)

                ai_present  = _ai_present(pa)
                pnc_present = _checklist_value(pa, "primary_noncontributory")
                wos_present = _checklist_value(pa, "waiver_of_subrogation")

                verdict, delta = _verdict_for_compliance(
                    contract_min, policy_limit, umbrella_may, umbrella_total,
                )
                summary[verdict] = summary.get(verdict, 0) + 1
                summary["total_requirements"] += 1

                # Umbrella mitigation note
                if umbrella_may is False and verdict in ("shortfall", "violation"):
                    umb_note = f"rejected — contract bars umbrella attachment for {line}"
                elif (umbrella_may
                      and umbrella_total
                      and isinstance(contract_min, (int, float))
                      and isinstance(policy_limit, (int, float))
                      and policy_limit < contract_min):
                    umb_note = f"applies — umbrella ${umbrella_total:,} above primary ${policy_limit:,}"
                else:
                    umb_note = None

                hint = _severity_hint_for(
                    verdict,
                    ai_required,  ai_present,
                    pnc_required, pnc_present,
                    wos_required, wos_present,
                )
                row_severity = _max_severity(row_severity, hint)

                policy_check[src] = {
                    "policy_type":          (pa.get("policy_type") or "unknown"),
                    "primary_limit_value":  policy_limit,
                    "primary_limit_field":  policy_field,
                    "delta":                delta,
                    "verdict":              verdict,
                    "ai_present":           ai_present,
                    "pnc_present":          pnc_present,
                    "wos_present":          wos_present,
                    "umbrella_mitigation":  umb_note,
                    "severity_hint":        hint,
                    "notes":                "",
                }

            rows.append({
                "contract":                       c_filename,
                "coverage_line":                  line,
                "requirement_summary":            requirement_summary,
                "umbrella_may_satisfy_minimum":   umbrella_may,
                "umbrella_satisfaction_note":     line_data.get("umbrella_satisfaction_note"),
                "ai_required":                    ai_required,
                "pnc_required":                   pnc_required,
                "wos_required":                   wos_required,
                "section_ref":                    line_data.get("section_ref"),
                "exact_quote":                    line_data.get("exact_quote"),
                "severity_hint":                  row_severity,
                "policy_check":                   policy_check,
            })

    return {"rows": rows, "summary": summary}


def build_designated_entity_noc_matrix(contracts_data: dict, policy_analyses: list) -> dict:
    """Construct designated-entity-NOC × policy matrix to test GAP-21."""
    contract_reqs: list = []
    for c_filename, c_data in (contracts_data or {}).items():
        if not c_data or c_data.get("has_insurance_provisions") is False:
            continue
        noc = c_data.get("designated_entity_noc")
        if not noc or not noc.get("required"):
            continue
        contract_reqs.append({
            "contract":           c_filename,
            "designated_entity":  noc.get("designated_entity"),
            "notice_days":        noc.get("notice_period_days"),
            "applies_to_lines":   noc.get("applies_to_lines") or ["all"],
            "section_ref":        noc.get("section_ref"),
        })

    policy_eds: dict = {}
    for pa in (policy_analyses or []):
        src = pa.get("_source_file") or pa.get("source_file") or "(unknown)"
        eds = pa.get("designated_entity_noc_endorsements") or []
        policy_eds[src] = [
            {
                "form_number":          e.get("form_number"),
                "name":                 e.get("name"),
                "page":                 e.get("page"),
                "designated_entities":  e.get("designated_entities") or [],
                "notice_days":          e.get("notice_period_days"),
            }
            for e in eds
        ]

    asymmetries: list = []
    for req in contract_reqs:
        de_norm = _normalize_entity_name(req.get("designated_entity") or "")
        if not de_norm:
            continue
        present_on:        list = []
        missing_from:      list = []
        notice_mismatches: list = []
        for src, eds in policy_eds.items():
            matched = False
            for e in eds:
                names_norm = [_normalize_entity_name(n) for n in (e.get("designated_entities") or [])]
                if de_norm in names_norm:
                    matched = True
                    if (req.get("notice_days") and e.get("notice_days")
                            and e["notice_days"] != req["notice_days"]):
                        notice_mismatches.append({
                            "policy":               src,
                            "policy_notice_days":   e.get("notice_days"),
                            "required_notice_days": req.get("notice_days"),
                        })
                    break
            (present_on if matched else missing_from).append(src)
        if missing_from:
            asymmetries.append({
                "contract":                 req.get("contract"),
                "designated_entity":        req.get("designated_entity"),
                "contract_requires_on_lines": req.get("applies_to_lines"),
                "endorsement_present_on":   present_on,
                "endorsement_missing_from": missing_from,
                "notice_period_match":      (len(notice_mismatches) == 0),
                "notice_mismatches":        notice_mismatches,
            })

    return {
        "contract_requirements":  contract_reqs,
        "policy_endorsements":    policy_eds,
        "asymmetries":            asymmetries,
    }


# ── KB I/O ──────────────────────────────────────────────────────────

def load_universal_kb_block() -> str:
    """Read GAP-01/17/20/21 from knowledge-base/universal/ and return labeled block."""
    if not _KB_UNIVERSAL_DIR.exists():
        return ""
    parts: list = []
    for fname in _KB_FILES_FOR_BLOCK:
        p = _KB_UNIVERSAL_DIR / fname
        if not p.exists():
            continue
        try:
            text = p.read_text(encoding="utf-8", errors="replace").strip()
            text = text[:_KB_PER_FILE_CAP]
            parts.append(f"[UNIVERSAL] --- {fname} ---\n{text}")
        except OSError:
            pass
    if not parts:
        return ""
    return (
        "=== UNIVERSAL KB FILES (cross-policy reasoning) ===\n"
        + "\n\n".join(parts)
        + "\n=== END UNIVERSAL KB ===\n\n"
    )


# ── Prompt builder ──────────────────────────────────────────────────

def build_cross_policy_matrix_prompt(
    client_notes:       str,
    client_slug:        str,
    entity_matrix:      dict,
    compliance_matrix:  dict,
    noc_matrix:         dict,
    universal_kb:       str,
    existing_findings:  list,
    policy_analyses:    list,
    contracts_data:     dict,
) -> str:
    """Build the prompt for the cross-policy matrix pass.

    Composes methodology + universal_kb + critical-thinking block + the three
    matrices + compressed policy/contract context + de-dupe targets, and asks
    the AI to emit additional findings tagged `cross-policy-matrix`.
    """
    # Lazy import to keep this module independent of claude_runner's API surface
    from core.claude_runner import (
        _methodology_header, _CRITICAL_THINKING_BLOCK, _FINDINGS_SCHEMA,
    )

    # Compress policy summaries (so AI has policy_file context for citing)
    pol_summaries: list = []
    for pa in (policy_analyses or []):
        pol_summaries.append({
            "source_file":               pa.get("_source_file") or pa.get("source_file"),
            "policy_type":               pa.get("policy_type"),
            "named_insured":             pa.get("named_insured"),
            "named_insured_entity_type": pa.get("named_insured_entity_type"),
            "limits":                    pa.get("limits"),
            "coverage_parts":            pa.get("coverage_parts"),
        })

    # Compress existing findings for de-dupe (just the key fields)
    existing_keys = [
        {
            "requirement_type": f.get("requirement_type"),
            "policy_file":      f.get("policy_file"),
            "policy_page":      f.get("policy_page"),
        }
        for f in (existing_findings or [])
    ]

    # Compress contracts to filenames + section refs
    contract_summaries = {
        fname: {
            "contract_party": (data or {}).get("contract_party"),
            "section_ref":    (data or {}).get("contract_section_ref"),
        }
        for fname, data in (contracts_data or {}).items()
    }

    return (
        _methodology_header()
        + universal_kb
        + _CRITICAL_THINKING_BLOCK
        + f"""TASK: Identify cross-cutting defects from the entity matrix, contract-vs-policy compliance matrix, and designated-entity-NOC matrix below. Emit findings that the per-policy analyses could not surface in isolation.

CLIENT: {client_slug}

CLIENT CONTEXT:
{client_notes}

POLICY PROGRAM SUMMARY:
{json.dumps(pol_summaries, indent=2)}

CONTRACTS:
{json.dumps(contract_summaries, indent=2)}

ENTITY × POLICY MATRIX:
{json.dumps(entity_matrix, indent=2)}

CONTRACT-VS-POLICY COMPLIANCE MATRIX:
{json.dumps(compliance_matrix, indent=2)}

DESIGNATED-ENTITY-NOC MATRIX:
{json.dumps(noc_matrix, indent=2)}

EXISTING FINDINGS (DO NOT DUPLICATE — match by requirement_type + policy_file + policy_page):
{json.dumps(existing_keys, indent=2)}

INSTRUCTIONS:
- Each row in compliance_matrix.rows has a `severity_hint` field. Use it as a STRONG GUIDE for risk scoring:
    critical      → likelihood 4-5, severity 4-5  (Ugly)
    high          → likelihood 3-4, severity 3-4  (Ugly or Bad)
    medium        → likelihood 2-3, severity 2-3  (Bad)
    low           → likelihood 1-2, severity 1-2  (Bad or Review)
    informational → Good or Review

- For each policy_check cell with verdict in ("shortfall", "violation", "missing_policy"):
    Emit ONE finding tied to the cell's source_file (or "PROGRAM" with policy_page="—" for missing_policy).
    Include the contract's exact_quote from the row, and the policy's primary_limit_value if present.
    For violations (umbrella attachment barred but primary is short), explicitly state the structural
    distinction in the finding language — this is the GAP-17 flagship pattern (see Maricopa Auto example
    in the UNIVERSAL KB above).

- For each entity_matrix.inconsistencies entry:
    kind == "entity_partial_inclusion" → emit ONE finding per `missing_from` policy.
       policy_file = the missing-from policy. Use display_name (NOT normalized_name) when describing
       the entity. Reference GAP-20.
    kind == "first_named_insured_entity_type_mismatch" → emit one finding per affected policy
       describing the Inc-vs-LLC asymmetry across the program. Reference GAP-01 EXPANDED.
    kind == "broad_form_llc_risk" → emit one finding per policy in `policies_with_risk` noting
       the Broad Form NI excludes LLCs, so the entity won't be auto-covered. Reference GAP-01 EXPANDED.

- For each noc_matrix.asymmetries entry:
    Emit one finding per policy in `endorsement_missing_from`. policy_file = that policy.
    Reference GAP-21. Notice-period mismatches in `notice_mismatches` also produce findings.

- For findings tied to a specific policy_file:
    Use the policy_page from entity matrix `page` field when available, or the compliance row's
    `section_ref` formatted as "Contract §X.Y" when no policy page is known.
- For program-level findings (no specific policy), set policy_file = "PROGRAM" and policy_page = "—".

- ALWAYS use the entity matrix's `display_name` field when describing an entity in finding text —
  never the `normalized_name` (which is for internal lookups only).
- Tag every finding from this pass with: tags = [..., "cross-policy-matrix"].
- DO NOT duplicate findings already in EXISTING FINDINGS (match by requirement_type + policy_file + policy_page).
- Quote contract / policy language verbatim from the matrices' `exact_quote` fields. Do not paraphrase.
- For each Bad/Ugly finding, generate 2-4 discoveryQuestions per the standard rubric (open-ended,
  Socratic, specific to this client's operations).
- Use client slug: "{client_slug}"

Return ONLY valid JSON matching the schema below. No prose before or after the JSON.

REQUIRED JSON SCHEMA:
{_FINDINGS_SCHEMA}"""
    )
