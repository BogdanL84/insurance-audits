"""
prompt_generator.py — Build structured prompts for Claude Code analysis.

Reads client-notes.md and all *-extracted.txt files from ai-exchange/,
combines them into a single prompt that Claude Code can analyze to produce
findings JSON.
"""

from pathlib import Path
from datetime import date


# ── Hardcoded methodology fallback ─────────────────────────────────
_METHODOLOGY_FALLBACK = """
GENERAL LIABILITY — KEY CHECKS
- Additional Insured endorsements: blanket vs. scheduled, ongoing vs. completed operations
- Waiver of Subrogation: is it on the policy? For all applicable coverages?
- Primary & Noncontributory language: does the contract require it? Does the policy provide it?
- Contractual Liability coverage: is it excluded or limited?
- Products/Completed Operations aggregate: separate from general aggregate?
- Per-project aggregate: required for construction?
- Classification accuracy: do the class codes match actual operations?

WORKERS' COMPENSATION — KEY CHECKS
- Experience Modification Rate (EMR) and trend
- Alternate Employer endorsement if using staffing agencies
- Voluntary Compensation for exempt workers
- USL&H / Maritime coverage if applicable
- Waiver of Subrogation: required by contract? Endorsed on policy?
- Classification codes: do they match actual operations?
- Monopolistic state compliance (OH, ND, WA, WY)

COMMERCIAL AUTO — KEY CHECKS
- Hired & Non-Owned Auto (HNOA): is it included or must be added?
- MCS-90 endorsement if client is a motor carrier
- Uninsured/Underinsured Motorist coverage
- Loading/Unloading liability — whose policy responds?

PROFESSIONAL LIABILITY / E&O — KEY CHECKS
- Claims-made vs. occurrence: what is the retroactive date? Is there a prior acts gap?
- Definition of "professional services": does it match what the client actually does?
- Exclusions for specific work types or industries
- Duty to defend vs. right to defend
- Hammer clause / consent to settle
- Coverage for work performed by subcontractors

DIRECTORS & OFFICERS (D&O) — KEY CHECKS
- Entity coverage (Side C): not just individual directors
- Insured vs. Insured exclusion: carved back for derivative suits?
- Prior/Pending litigation date
- Bump-up exclusion in M&A context
- Regulatory investigation coverage and sublimits
- Broad definition of "Claim" including regulatory proceedings

CYBER LIABILITY — KEY CHECKS
- First-party vs. third-party coverage: both present?
- Business interruption / dependent business interruption: sublimits?
- Ransomware / extortion sublimits
- Social engineering / funds transfer fraud coverage
- Regulatory defense and penalty coverage
- PCI-DSS assessment coverage
- Retroactive date for prior incidents

EMPLOYMENT PRACTICES LIABILITY (EPLI) — KEY CHECKS
- Third-party coverage for harassment by non-employees
- Wage & Hour: defense costs only, or indemnity too?
- Definition of "Employee": does it include temps, contractors, interns?
- Prior/Pending litigation date

UMBRELLA / EXCESS — KEY CHECKS
- Follow-form vs. stand-alone: what gaps exist vs. primary?
- Schedule of underlying: are ALL required policies listed?
- Drop-down coverage for exhausted aggregates
- Self-insured retention for claims not covered by underlying
- Defense costs: inside or outside limits?
- Additional Insured and Waiver of Subrogation follow underlying?

CRIME / FIDELITY — KEY CHECKS
- Employee theft: per-occurrence limit adequate?
- Forgery or alteration coverage
- Computer fraud / funds transfer fraud
- Social engineering: included or sublimited?
- Client property coverage
- Third-party coverage (covers losses to clients caused by employee dishonesty)

CONTRACTUAL RISK TRANSFER — WHAT TO WATCH
- "Arising out of" vs. "caused by" — "arising out of" is much broader
- "Sole negligence" vs. "any negligence" — who bears risk of shared fault?
- Hold Harmless scope: limited to work performed, or broad form?
- Defense obligation: immediate or only after liability determination?
- Waiver of Subrogation: required by contract? Endorsed on all applicable policies?
- Additional Insured status: which policies? Ongoing AND completed operations?
- Primary & Noncontributory: required by contract? Confirmed in policy language?
- Certificate requirements: specific holders, language, or endorsement copies required?
"""


# ── JSON schema for findings output ────────────────────────────────
_FINDINGS_SCHEMA = """{
  "client": "[slug]",
  "analysis_date": "[YYYY-MM-DD]",
  "findings": [
    {
      "id": "finding-001",
      "requirement_type": "Additional Insured — Completed Operations",
      "category": "Ugly",
      "likelihood": 4,
      "severity": 4,
      "risk_score": 16,
      "contract_quote": "exact language from contract",
      "contract_page": "Section 12.3, Page 8 of 47",
      "contract_file": "filename.pdf",
      "policy_quote": "exact language from policy",
      "policy_page": "Page 42 of 89",
      "policy_file": "filename.pdf",
      "gap_description": "Technical description of the gap",
      "plain_english": "CFO-friendly explanation of business impact",
      "recommendation": "Specific endorsement or action needed",
      "covered_by_other_policy": false,
      "covered_by_which_policy": null,
      "covered_by_page": null,
      "tags": ["additional-insured", "completed-operations"]
    }
  ]
}"""


def get_methodology_excerpt(base_dir: Path = None) -> str:
    """
    Return audit methodology text.
    Tries to read CLAUDE.md from base_dir first; falls back to hardcoded excerpt.
    """
    if base_dir is not None:
        claude_md = base_dir / "CLAUDE.md"
        if claude_md.exists():
            try:
                raw = claude_md.read_text(encoding="utf-8", errors="replace")
                # Extract the "What I Always Check" section
                start_marker = "### What I Always Check"
                end_marker   = "### Contractual Risk Transfer"
                end_marker2  = "---"

                start = raw.find(start_marker)
                if start != -1:
                    # Find the end — look for the next H3 heading after our section
                    # or the horizontal rule that separates sections
                    end = raw.find("\n## ", start + 1)
                    if end == -1:
                        end = len(raw)
                    section = raw[start:end].strip()
                    # Also grab Contractual Risk Transfer section
                    crt_start = raw.find("### Contractual Risk Transfer")
                    if crt_start != -1:
                        crt_end = raw.find("\n## ", crt_start + 1)
                        if crt_end == -1:
                            crt_end = len(raw)
                        crt_section = raw[crt_start:crt_end].strip()
                        return section + "\n\n" + crt_section
                    return section
            except OSError:
                pass

    return _METHODOLOGY_FALLBACK.strip()


def get_findings_schema() -> str:
    """Return the JSON schema as a formatted string block."""
    return _FINDINGS_SCHEMA


def build_combined_prompt(
    client_path: Path,
    state: dict,
    base_dir: Path = None,
    selected_files: list = None,
) -> str:
    """
    Build a complete analysis prompt for Claude Code.

    Args:
        client_path:    Path to the client folder (e.g. clients/acme-corp/)
        state:          Loaded audit-state dict
        base_dir:       Root of the insurance-audits/ directory (for CLAUDE.md)
        selected_files: List of extracted filenames to include; None = include all

    Returns:
        Complete prompt string ready to paste into Claude Code.
    """
    today        = date.today().isoformat()
    client_slug  = state.get("client", client_path.name)
    display_name = state.get("display_name", client_slug)
    exchange_dir = client_path / "ai-exchange"

    # ── Client notes ───────────────────────────────────────────────
    notes_file = client_path / "client-notes.md"
    if notes_file.exists():
        try:
            client_notes = notes_file.read_text(encoding="utf-8", errors="replace").strip()
        except OSError:
            client_notes = f"Client: {display_name}\n(client-notes.md could not be read)"
    else:
        # Build minimal context from state
        info = state.get("client_info", {})
        lines = [
            f"# {display_name}",
            "",
            f"Industry: {info.get('industry', 'Unknown')}",
            f"Revenue: {info.get('revenue', 'Unknown')}",
            f"Employees: {info.get('employees', 'Unknown')}",
            f"States: {', '.join(info.get('states', [])) or 'Unknown'}",
        ]
        risks = info.get("special_risks", [])
        if risks:
            lines.append(f"Special Risks: {', '.join(risks)}")
        parties = info.get("contract_parties", [])
        if parties:
            lines.append("")
            lines.append("Upstream Contract Parties:")
            for p in parties:
                lines.append(f"  - {p}")
        notes = info.get("notes", "").strip()
        if notes:
            lines.append("")
            lines.append("Notes:")
            lines.append(notes)
        client_notes = "\n".join(lines)

    # ── Gather extracted files ─────────────────────────────────────
    if exchange_dir.exists():
        all_extracted = sorted(exchange_dir.glob("*-extracted.txt"))
    else:
        all_extracted = []

    if selected_files is not None:
        # Filter to only selected filenames
        selected_set  = set(selected_files)
        all_extracted = [f for f in all_extracted if f.name in selected_set]

    # ── Methodology ────────────────────────────────────────────────
    methodology = get_methodology_excerpt(base_dir)

    # ── Build prompt sections ──────────────────────────────────────
    divider = "=" * 68

    sections = []

    # Header
    sections.append(
        f"{divider}\n"
        f"INSURANCE AUDIT — {display_name.upper()}\n"
        f"Generated: {today}\n"
        f"{divider}"
    )

    # Task
    sections.append(
        "TASK\n"
        "----\n"
        "You are analyzing an insurance program against contractual obligations.\n"
        "Cross-reference every contract requirement against every policy.\n"
        "Return ALL findings as JSON — Good (compliant), Bad (gap/limitation),\n"
        "and Ugly (critical exposure). Do not skip Good findings; credit matters.\n"
        "\n"
        "Read the contracts first to extract every insurance requirement.\n"
        "Then read every policy and find where (or whether) each requirement\n"
        "is addressed. Quote exact language. Cite exact page numbers.\n"
        "Check ALL policies before calling something Ugly — a gap on GL might\n"
        "be covered by umbrella or another policy in the program."
    )

    # Client context
    sections.append(
        "CLIENT CONTEXT\n"
        "--------------\n"
        + client_notes
    )

    # Methodology
    sections.append(
        "AUDIT METHODOLOGY — WHAT TO CHECK\n"
        "-----------------------------------\n"
        + methodology
    )

    # Scoring guidelines
    sections.append(
        "SCORING GUIDELINES\n"
        "------------------\n"
        "Likelihood (1–5): How likely is this gap to result in a claim or coverage denial?\n"
        "  1 = Very unlikely — theoretical risk, rarely triggers\n"
        "  2 = Unlikely — possible but uncommon\n"
        "  3 = Possible — has happened to similar businesses\n"
        "  4 = Likely — common scenario in this industry\n"
        "  5 = Very likely — near-certain to be an issue\n"
        "\n"
        "Severity (1–5): What is the potential financial impact?\n"
        "  1 = Minimal    — under $10,000\n"
        "  2 = Moderate   — $10,000 – $50,000\n"
        "  3 = Significant — $50,000 – $250,000\n"
        "  4 = Severe     — $250,000 – $1,000,000\n"
        "  5 = Catastrophic — over $1,000,000 or business-threatening\n"
        "\n"
        "risk_score = likelihood × severity  (range: 1–25)\n"
        "  ≤ 5   = Low    — monitor\n"
        "  6–14  = Medium — address at next renewal\n"
        "  15–19 = High   — address urgently\n"
        "  ≥ 20  = Critical — immediate action required\n"
        "\n"
        "For Good findings: set likelihood and severity to null, risk_score to null."
    )

    # Output format
    sections.append(
        "REQUIRED OUTPUT FORMAT\n"
        "-----------------------\n"
        "Return ONLY valid JSON. No prose before or after the JSON block.\n"
        "No markdown code fences. No explanation. Just the raw JSON.\n"
        "Match this schema exactly:\n"
        "\n"
        + _FINDINGS_SCHEMA
        + "\n\n"
        "RULES:\n"
        '- category must be exactly: "Good", "Bad", "Ugly", or "Needs Review"\n'
        '- Good          = policy meets or exceeds the contract requirement\n'
        '- Bad           = gap or limitation that needs attention but is not catastrophic\n'
        '- Ugly          = critical exposure: expressly excluded, or serious uninsured gap\n'
        '- Needs Review  = cannot confirm coverage or gap without carrier/broker verification\n'
        '                  or human judgment; use when the policy language is ambiguous, a\n'
        '                  key endorsement is missing from the provided documents, contract\n'
        '                  interpretation is debatable, or the class code / provision needs\n'
        '                  underwriter confirmation before calling it a gap\n'
        "- For Good findings: likelihood, severity, and risk_score can be null\n"
        "- For Needs Review findings: likelihood, severity, and risk_score can be null\n"
        "- Check ALL policies before calling something Ugly\n"
        "- Quote EXACT language from the documents. Cite EXACT page numbers.\n"
        "- plain_english: no jargon, explain what this means for the business\n"
        "- Never guess. If you cannot find something in a policy, say so — use Needs Review.\n"
        "- EVERY finding MUST include:\n"
        '    policy_file: exact filename of the policy being cited (e.g. "gl-policy.pdf")\n'
        '    policy_page: exact page reference (e.g. "Page 42 of 89")\n'
        "- If a gap is covered by another policy:\n"
        "    covered_by_other_policy: true\n"
        '    covered_by_which_policy: exact filename of the policy providing coverage (e.g. "umbrella.pdf")\n'
        '    covered_by_page: exact page in that policy where coverage appears (e.g. "Page 12 of 89")\n'
        "- If not covered by another policy: covered_by_other_policy: false, covered_by_which_policy: null, covered_by_page: null\n"
        f'- Use client slug: "{client_slug}"'
    )

    # Extracted documents
    doc_sections = []
    if all_extracted:
        for ef in all_extracted:
            try:
                text = ef.read_text(encoding="utf-8", errors="replace")
            except OSError:
                text = f"(could not read {ef.name})"
            doc_sections.append(
                f"{'─' * 60}\n"
                f"FILE: {ef.name}\n"
                f"{'─' * 60}\n"
                + text.strip()
            )
    else:
        doc_sections.append(
            "(No extracted text files found in ai-exchange/.\n"
            "Please extract documents in the Document Intake step first.)"
        )

    sections.append(
        "EXTRACTED DOCUMENTS\n"
        "-------------------\n"
        + "\n\n".join(doc_sections)
    )

    # Combine all sections
    return "\n\n".join(sections)
