"""
report_writer.py — Generate email drafts, markdown reports, and slide outlines
from imported findings data.
"""

from datetime import date
from pathlib import Path
from core.settings import load as _load_settings


def _get_broker_info():
    s = _load_settings()
    return (
        s["broker_name"],
        s["broker_title"],
        s["broker_company"],
        s["broker_email"],
        s["broker_phone"],
    )


# Dynamic properties — re-read settings each call so changes take effect without restart
@property
def _sig():
    n, t, c, e, p = _get_broker_info()
    return f"---\n{n}\n{t}\n{c}\n{e} | {p}"


def _signature():
    n, t, c, e, p = _get_broker_info()
    return f"---\n{n}\n{t}\n{c}\n{e} | {p}"


# These are used at function call time (not module load time) so settings changes are picked up
def _bname():   return _load_settings()["broker_name"]
def _btitle():  return _load_settings()["broker_title"]
def _bcompany():return _load_settings()["broker_company"]
def _bemail():  return _load_settings()["broker_email"]
def _bphone():  return _load_settings()["broker_phone"]


# Back-compat: module-level names used by the legacy _SIGNATURE string
BROKER_NAME    = _bname()
BROKER_TITLE   = _btitle()
BROKER_COMPANY = _bcompany()
BROKER_EMAIL   = _bemail()
BROKER_PHONE   = _bphone()

_SIGNATURE = _signature()


# ── Internal helpers ────────────────────────────────────────────────
def _severity_label(score: int) -> str:
    """Convert numeric risk score to text label."""
    if score is None:
        return "N/A"
    if score <= 5:
        return "Low"
    elif score <= 14:
        return "Medium"
    elif score <= 19:
        return "High"
    else:
        return "Critical"


def _sort_findings_by_risk(findings: list) -> list:
    """Sort Ugly first (by risk score desc), then Bad, then Good."""
    if not findings:
        return []

    def _sort_key(f):
        cat = f.get("category", "Good")
        order = {"Ugly": 0, "Bad": 1, "Good": 2}.get(cat, 3)
        score = f.get("risk_score") or 0
        return (order, -score)

    return sorted(findings, key=_sort_key)


def _get_top_recommendations(findings: list, n: int = 3) -> list:
    """Return the top N recommendations from Ugly/Bad findings."""
    priority = [
        f for f in findings
        if f.get("category") in ("Ugly", "Bad")
        and str(f.get("recommendation", "") or "").strip()
    ]
    sorted_priority = _sort_findings_by_risk(priority)
    return [str(f.get("recommendation", "") or "").strip() for f in sorted_priority[:n]]


# ── Email draft ─────────────────────────────────────────────────────
def generate_email_draft(state: dict, recipient_type: str = "am") -> str:
    """
    Generate an email draft from findings.

    Args:
        state:          Loaded audit-state dict with findings
        recipient_type: "am" (account manager internal) or "client" (CFO/owner)

    Returns:
        Formatted email string (Subject line + body + signature)
    """
    findings     = state.get("findings", [])
    display_name = state.get("display_name", "Client")
    today        = date.today().strftime("%B %d, %Y")
    today_short  = date.today().strftime("%Y-%m-%d")

    sorted_findings = _sort_findings_by_risk(findings)
    ugly   = [f for f in sorted_findings if f.get("category") == "Ugly"]
    bad    = [f for f in sorted_findings if f.get("category") == "Bad"]
    review = [f for f in sorted_findings if f.get("category") in ("Review", "Needs Review")]
    good   = [f for f in sorted_findings if f.get("category") == "Good"]

    top_recs = _get_top_recommendations(findings, n=3)

    if recipient_type == "client":
        return _email_client(
            display_name, today, today_short, ugly, bad, good, top_recs,
            review=review,
        )
    else:
        return _email_am(
            display_name, today, today_short, ugly, bad, good, top_recs,
            review=review,
        )


def _email_am(
    display_name: str,
    today: str,
    today_short: str,
    ugly: list,
    bad: list,
    good: list,
    top_recs: list,
    review: list = None,
) -> str:
    """Internal account manager email — full technical detail."""
    review = review or []
    subject = f"Subject: {display_name} — Program Review — {today_short}"

    summary_parts = [
        f"{len(ugly)} critical issues",
        f"{len(bad)} items to address",
    ]
    if review:
        summary_parts.append(f"{len(review)} needing human judgment")
    summary_parts.append(f"{len(good)} areas in good shape")

    lines = [
        subject,
        "",
        f"Team,",
        "",
        f"Completed the insurance program audit for {display_name}. "
        f"Here's the summary — " + ", ".join(summary_parts) + ".",
        "",
    ]

    # Critical findings
    if ugly:
        lines.append("CRITICAL (Ugly) — Address Immediately:")
        for i, f in enumerate(ugly, 1):
            req  = f.get("requirement_type", "Unknown")
            desc = str(f.get("gap_description", "") or "").strip()
            score = f.get("risk_score")
            label = _severity_label(score) if score else ""
            score_str = f" [Score: {score} — {label}]" if score else ""
            lines.append(f"  {i}. {req}{score_str}")
            if desc:
                # First sentence only for the summary
                first_sentence = desc.split(".")[0].strip()
                if first_sentence:
                    lines.append(f"     {first_sentence}.")
        lines.append("")

    # Bad findings
    if bad:
        lines.append("NEEDS ATTENTION (Bad):")
        for i, f in enumerate(bad, 1):
            req   = f.get("requirement_type", "Unknown")
            score = f.get("risk_score")
            label = _severity_label(score) if score else ""
            score_str = f" [Score: {score} — {label}]" if score else ""
            lines.append(f"  {i}. {req}{score_str}")
        lines.append("")

    # Needs Review findings — items requiring human judgment
    if review:
        lines.append("")
        lines.append("NEEDS REVIEW — Human Judgment Required:")
        lines.append("(These findings turn on contract interpretation, "
                     "ambiguous policy language, or information not in "
                     "the policy. Each requires manual review before "
                     "finalizing the audit.)")
        lines.append("")
        for i, f in enumerate(review, 1):
            title = f.get("requirement_type", "(untitled)")
            gap = (f.get("plain_english") or "")[:200]
            lines.append(f"  {i}. {title}")
            if gap:
                lines.append(f"     {gap}")
        lines.append("")

    # Good count
    if good:
        lines.append(f"IN GOOD SHAPE: {len(good)} requirement(s) confirmed compliant.")
        lines.append("")

    # Top recommendations
    if top_recs:
        lines.append("TOP 3 RECOMMENDED ACTIONS:")
        for i, rec in enumerate(top_recs, 1):
            lines.append(f"  {i}. {rec}")
        lines.append("")

    lines.append("Full findings are in the audit system. Let me know if you have questions.")
    lines.append("")
    lines.append(_signature())

    return "\n".join(lines)


def _email_client(
    display_name: str,
    today: str,
    today_short: str,
    ugly: list,
    bad: list,
    good: list,
    top_recs: list,
    review: list = None,
) -> str:
    """Client-facing CFO/owner email — plain English, no jargon."""
    review = review or []
    subject = f"Subject: {display_name} — Insurance Program Review — {today_short}"

    total = len(ugly) + len(bad) + len(review) + len(good)

    lines = [
        subject,
        "",
        f"Hi,",
        "",
        f"I've completed a detailed review of {display_name}'s insurance program "
        f"against your contractual obligations. Of the {total} items I reviewed, "
        f"here is what you need to know:",
        "",
    ]

    # Critical findings in plain English
    if ugly:
        lines.append(f"CRITICAL GAPS — {len(ugly)} issue{'s' if len(ugly) != 1 else ''} "
                     f"that need immediate attention:")
        for i, f in enumerate(ugly, 1):
            req          = f.get("requirement_type", "Unknown requirement")
            plain        = str(f.get("plain_english", "") or "").strip()
            rec          = str(f.get("recommendation", "") or "").strip()
            lines.append(f"")
            lines.append(f"  {i}. {req}")
            if plain:
                lines.append(f"     What this means for you: {plain}")
            if rec:
                lines.append(f"     What to do: {rec}")
        lines.append("")

    # Bad findings
    if bad:
        lines.append(f"WORTH ADDRESSING — {len(bad)} item{'s' if len(bad) != 1 else ''} "
                     f"that should be reviewed at your next renewal:")
        for i, f in enumerate(bad, 1):
            req   = f.get("requirement_type", "Unknown requirement")
            plain = str(f.get("plain_english", "") or "").strip()
            lines.append(f"  {i}. {req}")
            if plain:
                # First sentence only for the email summary
                first = plain.split(".")[0].strip()
                if first:
                    lines.append(f"     {first}.")
        lines.append("")

    # Needs Review findings
    if review:
        lines.append(f"NEEDS REVIEW — {len(review)} item{'s' if len(review) != 1 else ''} "
                     f"requiring human judgment:")
        lines.append("(These findings turn on contract interpretation, "
                     "ambiguous policy language, or information not in "
                     "the policy. Each requires manual review before "
                     "finalizing the audit.)")
        for i, f in enumerate(review, 1):
            req   = f.get("requirement_type", "Unknown requirement")
            plain = str(f.get("plain_english", "") or "").strip()
            lines.append(f"  {i}. {req}")
            if plain:
                first = plain.split(".")[0].strip()
                if first:
                    lines.append(f"     {first}.")
        lines.append("")

    # Good news
    if good:
        lines.append(f"GOOD NEWS — {len(good)} area{'s' if len(good) != 1 else ''} "
                     f"where your coverage is solid:")
        for f in good[:5]:  # Show up to 5 good findings
            req = f.get("requirement_type", "Unknown")
            lines.append(f"  ✓ {req}")
        if len(good) > 5:
            lines.append(f"  ... and {len(good) - 5} more.")
        lines.append("")

    # Next steps
    if top_recs:
        lines.append("THE MOST IMPORTANT NEXT STEPS:")
        for i, rec in enumerate(top_recs, 1):
            lines.append(f"  {i}. {rec}")
        lines.append("")

    lines.append(
        "I'm happy to walk you through these findings in detail and discuss "
        "your options. Would you have 30 minutes this week for a call?"
    )
    lines.append("")
    lines.append(_signature())

    return "\n".join(lines)


# ── Markdown report ─────────────────────────────────────────────────
def generate_markdown_report(state: dict) -> str:
    """
    Generate a full detailed markdown report from findings.

    Returns:
        Markdown string suitable for saving as .md or displaying in st.text_area.
    """
    bn, bt, bc, be, bp = _get_broker_info()
    findings     = state.get("findings", [])
    display_name = state.get("display_name", "Client")
    client_slug  = state.get("client", "client")
    today        = date.today().strftime("%B %d, %Y")
    today_iso    = date.today().isoformat()
    info         = state.get("client_info", {})

    sorted_findings = _sort_findings_by_risk(findings)
    ugly   = [f for f in sorted_findings if f.get("category") == "Ugly"]
    bad    = [f for f in sorted_findings if f.get("category") == "Bad"]
    review = [f for f in sorted_findings if f.get("category") in ("Review", "Needs Review")]
    good   = [f for f in sorted_findings if f.get("category") == "Good"]

    lines = []

    # Title block
    lines += [
        f"# Insurance Program Audit",
        f"## {display_name}",
        "",
        f"**Prepared by:** {bn}, {bc}",
        f"**Date:** {today}",
        f"**Contact:** {be} | {bp}",
        "",
        "---",
        "",
    ]

    # Client overview
    lines += [
        "## Client Overview",
        "",
        f"| Field | Value |",
        f"|---|---|",
        f"| Industry | {info.get('industry', '—')} |",
        f"| Annual Revenue | {info.get('revenue', '—')} |",
        f"| Employees | {info.get('employees', '—')} |",
        f"| States of Operation | {', '.join(info.get('states', [])) or '—'} |",
    ]
    risks = info.get("special_risks", [])
    if risks:
        lines.append(f"| Special Risk Flags | {', '.join(risks)} |")
    lines += ["", "---", ""]

    # Executive summary
    total = len(findings)
    lines += [
        "## Executive Summary",
        "",
    ]

    if not findings:
        lines += ["*No findings have been imported yet.*", "", "---", ""]
    else:
        # Risk overview table
        lines += [
            f"| Category | Count | Description |",
            f"|---|---|---|",
            f"| 🔴 Ugly (Critical) | {len(ugly)} | "
            f"Critical exposures requiring immediate action |",
            f"| 🟠 Bad | {len(bad)} | "
            f"Gaps and limitations needing attention |",
            f"| ⚠ Needs Review | {len(review)} | "
            f"Items requiring human judgment before finalizing |",
            f"| 🟢 Good | {len(good)} | "
            f"Requirements confirmed covered |",
            f"| **Total** | **{total}** | |",
            "",
        ]

        # Top risks narrative
        if ugly:
            lines.append(
                f"**This program has {len(ugly)} critical exposure"
                f"{'s' if len(ugly) != 1 else ''} that require immediate attention.** "
                "These are not theoretical risks — they are gaps that could result in "
                "uncovered claims, contract breaches, or significant uninsured losses."
            )
            lines.append("")

        top_recs = _get_top_recommendations(findings, n=3)
        if top_recs:
            lines += [
                "**Top Recommended Actions:**",
                "",
            ]
            for i, rec in enumerate(top_recs, 1):
                lines.append(f"{i}. {rec}")
            lines.append("")

        lines += ["---", ""]

    # Findings sections
    for section_title, section_findings, icon in [
        ("Critical Findings (Ugly)", ugly, "🔴"),
        ("Findings Needing Attention (Bad)", bad, "🟠"),
        ("Items Requiring Human Judgment (Needs Review)", review, "⚠"),
        ("Compliant Areas (Good)", good, "🟢"),
    ]:
        if not section_findings:
            continue

        lines += [
            f"## {icon} {section_title}",
            "",
        ]

        for f in section_findings:
            fid      = f.get("id", "—")
            req_type = f.get("requirement_type", "Unknown")
            cat      = f.get("category", "")
            score    = f.get("risk_score")
            like     = f.get("likelihood")
            sev      = f.get("severity")

            # Finding header
            score_str = f" — Risk Score: **{score}** ({_severity_label(score)})" if score else ""
            lines += [
                f"### {req_type}",
                "",
                f"**Finding ID:** `{fid}`  ",
                f"**Category:** {cat}{score_str}  ",
            ]
            if like is not None and sev is not None:
                lines.append(
                    f"**Likelihood:** {like}/5  "
                    f"**Severity:** {sev}/5  "
                )
            lines.append("")

            # Contract quote
            contract_quote = str(f.get("contract_quote", "") or "").strip()
            contract_page  = str(f.get("contract_page", "") or "").strip()
            contract_file  = str(f.get("contract_file", "") or "").strip()
            if contract_quote:
                cite = ""
                if contract_file:
                    cite += f" — {contract_file}"
                if contract_page:
                    cite += f", {contract_page}"
                lines += [
                    "**Contract Requires:**",
                    f"> {contract_quote}",
                    f"*{cite.strip(' —')}*" if cite.strip(" —") else "",
                    "",
                ]

            # Policy quote
            policy_quote = str(f.get("policy_quote", "") or "").strip()
            policy_page  = str(f.get("policy_page", "") or "").strip()
            policy_file  = str(f.get("policy_file", "") or "").strip()
            if policy_quote:
                cite = ""
                if policy_file:
                    cite += f" — {policy_file}"
                if policy_page:
                    cite += f", {policy_page}"
                lines += [
                    "**Policy Provides:**",
                    f"> {policy_quote}",
                    f"*{cite.strip(' —')}*" if cite.strip(" —") else "",
                    "",
                ]

            # Gap description
            gap = str(f.get("gap_description", "") or "").strip()
            if gap:
                lines += [
                    "**Technical Analysis:**",
                    gap,
                    "",
                ]

            # Plain English
            plain = str(f.get("plain_english", "") or "").strip()
            if plain:
                lines += [
                    "**What This Means for the Business:**",
                    f"_{plain}_",
                    "",
                ]

            # Covered by other policy
            if f.get("covered_by_other_policy"):
                other = f.get("covered_by_which_policy", "another policy")
                lines += [
                    f"**Note:** This requirement is covered by {other}.",
                    "",
                ]

            # Recommendation
            rec = str(f.get("recommendation", "") or "").strip()
            if rec:
                lines += [
                    "**Recommendation:**",
                    f"✅ {rec}",
                    "",
                ]

            # Tags
            tags = f.get("tags", [])
            if tags:
                tag_str = " ".join(f"`{t}`" for t in tags)
                lines += [f"**Tags:** {tag_str}", ""]

            lines += ["---", ""]

    # Footer
    lines += [
        "",
        f"*Report generated {today} by {bn}, {bc}.*",
        f"*{be} | {bp}*",
    ]

    return "\n".join(lines)


# ── Slide outline ───────────────────────────────────────────────────
def generate_slide_outline(state: dict) -> list:
    """
    Generate a slide-by-slide outline for a presentation deck.

    Returns:
        List of slide dicts: {number, title, content, notes, section}
    """
    bn, bt, bc, be, bp = _get_broker_info()
    findings     = state.get("findings", [])
    display_name = state.get("display_name", "Client")
    today        = date.today().strftime("%B %d, %Y")
    info         = state.get("client_info", {})

    sorted_findings = _sort_findings_by_risk(findings)
    ugly   = [f for f in sorted_findings if f.get("category") == "Ugly"]
    bad    = [f for f in sorted_findings if f.get("category") == "Bad"]
    review = [f for f in sorted_findings if f.get("category") in ("Review", "Needs Review")]
    good   = [f for f in sorted_findings if f.get("category") == "Good"]

    slides = []
    slide_num = 1

    def add_slide(title: str, content: str, notes: str = "", section: str = ""):
        nonlocal slide_num
        slides.append({
            "number":  slide_num,
            "title":   title,
            "content": content,
            "notes":   notes,
            "section": section,
        })
        slide_num += 1

    # ── Title slide ────────────────────────────────────────────────
    add_slide(
        title   = f"Insurance Program Review",
        content = (
            f"{display_name}\n"
            f"{today}\n"
            f"Prepared by {bn}\n"
            f"{bc}"
        ),
        notes   = (
            "Welcome. Today I'm going to walk you through a detailed review of your "
            "insurance program against your contractual obligations. We found some "
            "things that are working well, some things that need attention, and "
            "a few things that kept me up at night."
        ),
        section = "intro",
    )

    # ── Agenda ─────────────────────────────────────────────────────
    add_slide(
        title   = "What We're Covering Today",
        content = (
            "1. How we analyzed your program\n"
            "2. The Good — what's working\n"
            "3. The Bad — gaps to address\n"
            "4. The Ugly — critical exposures\n"
            "5. Recommended actions and next steps"
        ),
        notes   = (
            "Quick roadmap. We use a three-tier system: Good, Bad, and Ugly. "
            "Good means your coverage meets the requirement. Bad means there's a gap "
            "that needs attention but won't sink the ship. Ugly means we need to "
            "talk — these are exposures that could result in uncovered claims."
        ),
        section = "intro",
    )

    # ── Methodology ────────────────────────────────────────────────
    add_slide(
        title   = "Our Analysis Methodology",
        content = (
            "Step 1: Read your contracts → extract every insurance requirement\n"
            "Step 2: Read every policy → identify what's covered and what isn't\n"
            "Step 3: Cross-reference → find gaps and confirm compliance\n"
            "Step 4: Check across policies → a GL gap may be covered by umbrella\n"
            "Step 5: Rate every finding → Likelihood × Severity = Risk Score"
        ),
        notes   = (
            "We don't guess. Every finding is tied to exact contract language and "
            "exact policy language — page numbers included. If we couldn't find "
            "something in writing, we said so."
        ),
        section = "intro",
    )

    # ── Executive summary ──────────────────────────────────────────
    total = len(findings)
    add_slide(
        title   = "Program Summary",
        content = (
            f"Total Requirements Reviewed: {total}\n"
            f"🔴 Critical (Ugly):  {len(ugly)}\n"
            f"🟠 Needs Attention (Bad): {len(bad)}\n"
            f"🟢 Compliant (Good): {len(good)}"
        ),
        notes   = (
            f"Here's the scoreboard. Of the {total} requirements we reviewed, "
            f"{len(ugly)} are critical and need immediate action, "
            f"{len(bad)} need to be addressed, "
            f"and {len(good)} are in good shape."
        ),
        section = "summary",
    )

    # ── Good section divider ────────────────────────────────────────
    if good:
        add_slide(
            title   = "THE GOOD",
            content = "Your program gets these right.",
            notes   = (
                "[SECTION DIVIDER — use happy dog meme image]\n"
                "Let's start with the good news. Here's what your program does well."
            ),
            section = "good",
        )

        for f in good[:6]:  # Cap Good slides at 6
            req   = f.get("requirement_type", "Unknown")
            plain = str(f.get("plain_english", "") or "").strip()
            cquote = str(f.get("contract_quote", "") or "").strip()
            pquote = str(f.get("policy_quote", "") or "").strip()
            cpage  = f.get("contract_page", "")
            ppage  = f.get("policy_page", "")

            content_parts = []
            if cquote:
                content_parts.append(f"Contract requires:\n\"{cquote[:200]}\"")
                if cpage:
                    content_parts.append(f"({cpage})")
            if pquote:
                content_parts.append(f"\nPolicy provides:\n\"{pquote[:200]}\"")
                if ppage:
                    content_parts.append(f"({ppage})")
            if not content_parts:
                content_parts.append("Requirement confirmed covered.")

            add_slide(
                title   = f"✓ {req}",
                content = "\n".join(content_parts),
                notes   = plain or f"This requirement is met. {req} is properly addressed in the policy.",
                section = "good",
            )

        if len(good) > 6:
            add_slide(
                title   = f"✓ {len(good) - 6} More Compliant Areas",
                content = "\n".join(
                    f"✓ {f.get('requirement_type', 'Unknown')}"
                    for f in good[6:]
                ),
                notes   = "These items are all confirmed compliant. Full details in the written report.",
                section = "good",
            )

    # ── Bad section divider ─────────────────────────────────────────
    if bad:
        add_slide(
            title   = "THE BAD",
            content = "Gaps that need attention — not catastrophic, but not fine either.",
            notes   = (
                "[SECTION DIVIDER — use suspicious dog meme image]\n"
                "Now for the stuff that needs work. These aren't emergencies, "
                "but left unaddressed they become problems."
            ),
            section = "bad",
        )

        for f in bad:
            req   = f.get("requirement_type", "Unknown")
            plain = str(f.get("plain_english", "") or "").strip()
            rec   = str(f.get("recommendation", "") or "").strip()
            score = f.get("risk_score")
            like  = f.get("likelihood")
            sev   = f.get("severity")
            cquote = str(f.get("contract_quote", "") or "")[:200]
            pquote = str(f.get("policy_quote",  "") or "")[:200]

            score_str = f"Risk Score: {score}/25 ({_severity_label(score)})" if score else ""

            content_parts = []
            if cquote:
                content_parts.append(f"Contract: \"{cquote}\"")
            if pquote:
                content_parts.append(f"Policy: \"{pquote}\"")
            if score_str:
                content_parts.append(score_str)
            if rec:
                content_parts.append(f"Fix: {rec}")

            add_slide(
                title   = f"⚠ {req}",
                content = "\n\n".join(content_parts) if content_parts else "See written report for details.",
                notes   = (
                    (plain + "\n\n" if plain else "") +
                    (f"Recommendation: {rec}" if rec else "")
                ).strip(),
                section = "bad",
            )

    # ── Ugly section divider ────────────────────────────────────────
    if ugly:
        add_slide(
            title   = "THE UGLY",
            content = "Critical exposures. These need immediate action.",
            notes   = (
                "[SECTION DIVIDER — use ugly dog meme image]\n"
                "Okay. Deep breath. Here's the stuff that kept me up at night. "
                "These are not theoretical — these are gaps that, if triggered, "
                "could result in a major uncovered loss."
            ),
            section = "ugly",
        )

        for f in ugly:
            req   = f.get("requirement_type", "Unknown")
            plain = str(f.get("plain_english", "") or "").strip()
            rec   = str(f.get("recommendation", "") or "").strip()
            gap   = str(f.get("gap_description", "") or "").strip()
            score = f.get("risk_score")
            like  = f.get("likelihood")
            sev   = f.get("severity")
            cquote = str(f.get("contract_quote", "") or "")[:200]
            pquote = str(f.get("policy_quote",  "") or "")[:200]

            score_str = ""
            if score:
                score_str = f"Risk Score: {score}/25 ({_severity_label(score)})"
                if like and sev:
                    score_str += f" | Likelihood: {like}/5 | Severity: {sev}/5"

            content_parts = []
            if cquote:
                content_parts.append(f"Contract requires:\n\"{cquote}\"")
            if pquote:
                content_parts.append(f"Policy provides:\n\"{pquote}\"")
            if score_str:
                content_parts.append(f"🚨 {score_str}")
            if rec:
                content_parts.append(f"Action required: {rec}")

            add_slide(
                title   = f"🚨 {req}",
                content = "\n\n".join(content_parts) if content_parts else gap or "See written report.",
                notes   = (
                    (plain + "\n\n" if plain else "") +
                    (gap + "\n\n" if gap else "") +
                    (f"Recommendation: {rec}" if rec else "")
                ).strip(),
                section = "ugly",
            )

    # ── Recommendations summary ─────────────────────────────────────
    top_recs = _get_top_recommendations(findings, n=5)
    if top_recs:
        rec_content = "\n".join(f"{i}. {r}" for i, r in enumerate(top_recs, 1))
        add_slide(
            title   = "Recommended Actions",
            content = rec_content,
            notes   = (
                "Here are the priority actions. I'd suggest we tackle these in order. "
                "Some of these can be resolved with a simple endorsement — a quick call "
                "to the carrier. Others may require shopping the market at renewal."
            ),
            section = "next_steps",
        )

    # ── Next steps ─────────────────────────────────────────────────
    add_slide(
        title   = "Next Steps",
        content = (
            "1. Review this report with your team\n"
            "2. Schedule a 30-minute call to prioritize action items\n"
            "3. We'll reach out to carriers for endorsements and quotes\n"
            "4. Review at next renewal cycle"
        ),
        notes   = (
            "This is where we go from analysis to action. Some of these items "
            "can be fixed today with a phone call. Others need to wait for renewal. "
            "I'll send you a written report to go along with this presentation."
        ),
        section = "next_steps",
    )

    # ── Contact slide ──────────────────────────────────────────────
    add_slide(
        title   = "Questions?",
        content = (
            f"{bn}\n"
            f"{bt}\n"
            f"{bc}\n"
            f"{be}\n"
            f"{bp}"
        ),
        notes   = "Open the floor for questions. Remind them the written report has all the page references.",
        section = "next_steps",
    )

    return slides
