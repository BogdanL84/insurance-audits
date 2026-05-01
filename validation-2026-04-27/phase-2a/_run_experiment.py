"""Phase 2A diagnostic — v2 vs v3 prompt schema-crowding experiment.

Runs the Hanover Auto extracted text through TWO prompts:
  - v2-style (no structured-fields block, no new schema fields)
  - v3-style (current production build_policy_prompt)

Both use the same policy text, same client notes, no contract context (standalone),
same KB injection, same model. Captures prompt size, response size, time, and the
parsed JSON for diff.

NOTE: For "fair" comparison both runs use the standalone prompt builder so contracts
do not affect the comparison. The user's regression hypothesis is about per-policy
SCHEMA crowding — that's what this isolates.
"""
import json, sys, time
from pathlib import Path

# Allow imports from app/
APP = Path(r"C:\Users\Bogdan\Documents\insurance-audits\app")
sys.path.insert(0, str(APP))

from core.claude_runner import (
    run_claude,
    extract_json,
    _methodology_header,
    _CRITICAL_THINKING_BLOCK,
    _load_kb_for_policy_type,
    build_standalone_policy_prompt as v3_standalone,
    ANALYSIS_TIMEOUT,
)

OUT = Path(r"C:\Users\Bogdan\Desktop\Run-Test Policies, Contracts\validation-2026-04-27\phase-2a")
OUT.mkdir(parents=True, exist_ok=True)

AUTO_EXTRACT = Path(r"C:\Users\Bogdan\Documents\insurance-audits\clients\run-test-election-services\ai-exchange\RedactedHanover - Auto - 4.1.25-4.1.26-extracted.txt")
CLIENT_NOTES = Path(r"C:\Users\Bogdan\Documents\insurance-audits\clients\run-test-election-services\client-notes.md")

POLICY_TEXT  = AUTO_EXTRACT.read_text(encoding='utf-8', errors='replace')
CLIENT_BLOCK = CLIENT_NOTES.read_text(encoding='utf-8', errors='replace')

# ── v2-style schema + prompt (reconstructed from pre-v3 conversation history) ──
V2_SCHEMA = """{
  "source_file": "filename.pdf",
  "analysis_date": "YYYY-MM-DD",
  "policy_type": "General Liability",
  "is_package": false,
  "coverage_parts": ["GL"],
  "is_primary": true,
  "named_insured": "Company Name",
  "carrier": "Hartford",
  "policy_number": "GL-XXXXXXXX",
  "effective_date": "YYYY-MM-DD",
  "expiry_date": "YYYY-MM-DD",
  "limits": {"each_occurrence": 1000000, "general_aggregate": 2000000},
  "endorsements": [
    {"form_number": "CG 20 10 04 13", "name": "Additional Insured — Scheduled", "page": 42, "notes": "Scheduled only, not blanket. Ongoing ops only."}
  ],
  "exclusions_of_note": [
    {"name": "Total Pollution Exclusion", "form_number": "CG 21 49", "page": 38, "impact": "Absolute pollution exclusion — no coverage of any kind."}
  ],
  "checklist": {
    "additional_insured_blanket": false,
    "additional_insured_scheduled": false,
    "additional_insured_completed_ops": false,
    "waiver_of_subrogation": false,
    "waiver_of_subrogation_page": null,
    "primary_noncontributory": false,
    "contractual_liability": false,
    "per_project_aggregate": false
  }
}"""


def v2_standalone(filename: str, text_content: str, client_notes: str) -> str:
    """Reconstruction of the pre-v3 build_standalone_policy_prompt.

    No _POLICY_STRUCTURED_FIELDS_BLOCK injection. No new schema fields. No
    instruction to populate canonical policy_type enum. KB injection identical.
    """
    pt_hint    = "commercial auto"
    kb_section = _load_kb_for_policy_type(pt_hint)
    return (
        _methodology_header()
        + kb_section
        + _CRITICAL_THINKING_BLOCK
        + f"""TASK: Analyze this insurance policy on its own merits. No upstream contracts were provided.

CLIENT CONTEXT:
{client_notes}

INSTRUCTIONS:
- You have the full extracted text of this policy below. Read every page.
- Identify the policy type from the declarations page. Do not assume — read the dec page and figure it out.
- Identify if monoline or package. List all coverage parts if package.
- For Management Liability packages: check for manufacturing/professional services exclusions on entity coverage.
- Use the coverage-specific checklist from the methodology above. Find real issues:
    * Problematic exclusions (absolute, total, or unusually broad)
    * Missing standard endorsements (AI blanket, waiver of subrogation, primary & noncontributory)
    * Poorly constructed terms (narrow definitions of "professional services", "employee", "occurrence")
    * Coverage limitations, sublimits, and sunset clauses
    * Prior acts gaps on claims-made policies
    * Defense cost treatment (inside vs. outside limits)
    * Hammer clauses and consent-to-settle restrictions
- Note every endorsement, especially AI forms (CG 20 10, CG 20 33, CG 20 37).
- Note every exclusion of significance and its potential business impact.
- Populate all checklist fields accurately.
- When you find significant exclusions or gaps, note whether a DIFFERENT policy type would typically cover that exposure. Add this to the exclusion's "impact" field.
- Do NOT generate meta-findings about missing contracts or audit completeness.
- Only report findings that come from actually reading this policy text.
- Return ONLY valid JSON matching the schema below. No prose before or after the JSON.

SOURCE FILE: {filename}

REQUIRED JSON SCHEMA:
{V2_SCHEMA}

POLICY TEXT (PAGE N OF M notation preserved):
{text_content}"""
    )


def run_one(label: str, prompt_text: str) -> dict:
    print(f"\n=== {label} ===")
    print(f"  prompt chars: {len(prompt_text):,}")
    t0 = time.time()
    ok, result = run_claude(prompt_text, timeout=ANALYSIS_TIMEOUT)
    elapsed = time.time() - t0
    response_chars = len(result or "")
    parsed = extract_json(result) if ok else None

    n_endos = len((parsed or {}).get("endorsements") or [])
    n_excl  = len((parsed or {}).get("exclusions_of_note") or [])
    print(f"  ok: {ok}")
    print(f"  elapsed: {elapsed:.1f}s")
    print(f"  response chars: {response_chars:,}")
    print(f"  endorsements: {n_endos}")
    print(f"  exclusions_of_note: {n_excl}")

    # Save raw response for inspection
    (OUT / f"{label}_response_raw.txt").write_text(result or "", encoding='utf-8')
    if parsed:
        (OUT / f"{label}_parsed.json").write_text(
            json.dumps(parsed, indent=2, ensure_ascii=False), encoding='utf-8'
        )
    (OUT / f"{label}_prompt.txt").write_text(prompt_text, encoding='utf-8')

    return {
        "label":           label,
        "ok":              ok,
        "elapsed_s":       round(elapsed, 1),
        "prompt_chars":    len(prompt_text),
        "response_chars":  response_chars,
        "n_endorsements":  n_endos,
        "n_exclusions":    n_excl,
        "parsed":          parsed,
    }


if __name__ == "__main__":
    filename = "RedactedHanover - Auto - 4.1.25-4.1.26.pdf"

    v2_prompt = v2_standalone(filename, POLICY_TEXT, CLIENT_BLOCK)
    v3_prompt = v3_standalone(filename, POLICY_TEXT, CLIENT_BLOCK)

    v2_run = run_one("v2", v2_prompt)
    print("\n[Sleeping 5s rate-limit]"); time.sleep(5)
    v3_run = run_one("v3", v3_prompt)

    summary = {
        "v2": {k: v2_run.get(k) for k in ("ok","elapsed_s","prompt_chars","response_chars","n_endorsements","n_exclusions")},
        "v3": {k: v3_run.get(k) for k in ("ok","elapsed_s","prompt_chars","response_chars","n_endorsements","n_exclusions")},
    }
    summary["delta"] = {
        "prompt_chars":   summary["v3"]["prompt_chars"]   - summary["v2"]["prompt_chars"],
        "response_chars": (summary["v3"]["response_chars"] or 0) - (summary["v2"]["response_chars"] or 0),
        "elapsed_s":      (summary["v3"]["elapsed_s"]      or 0) - (summary["v2"]["elapsed_s"]      or 0),
        "n_endorsements": (summary["v3"]["n_endorsements"] or 0) - (summary["v2"]["n_endorsements"] or 0),
        "n_exclusions":   (summary["v3"]["n_exclusions"]   or 0) - (summary["v2"]["n_exclusions"]   or 0),
    }
    (OUT / "summary.json").write_text(json.dumps(summary, indent=2), encoding='utf-8')
    print("\n=== SUMMARY ===")
    print(json.dumps(summary, indent=2))
