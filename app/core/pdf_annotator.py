"""
pdf_annotator.py — Annotate insurance policy PDFs with audit findings.

Using PyMuPDF (fitz) to produce marked-up PDFs with:
  - Text highlights (yellow/orange/red by category)
  - Sticky-note popup annotations
  - Bookmark sidebar organized by category
  - Cover page with audit summary

The original PDF is never modified — always saves to output/.
"""

import re
import sys
from datetime import date
from pathlib import Path

try:
    import fitz  # PyMuPDF
except ImportError:
    raise ImportError("PyMuPDF not installed. Run: pip install pymupdf")


# ── Color constants  (RGB 0–1 tuples) ──────────────────────────────
_HL = {
    "Good": (1.00, 1.00, 0.00),   # pure yellow
    "Bad":  (1.00, 0.60, 0.00),   # orange
    "Ugly": (1.00, 0.30, 0.30),   # red
}
_NOTE_CLR = {
    "Good": (0.18, 0.49, 0.20),   # dark green
    "Bad":  (0.90, 0.40, 0.00),   # amber
    "Ugly": (0.72, 0.11, 0.11),   # deep red
}
_NAVY  = (0.10, 0.14, 0.49)
_WHITE = (1.00, 1.00, 1.00)
_DARK  = (0.15, 0.15, 0.15)
_GRAY  = (0.50, 0.50, 0.50)
_LGRAY = (0.80, 0.80, 0.80)

def _broker_line() -> str:
    from core.settings import load as _load_settings
    s = _load_settings()
    parts = [p for p in [s.get("broker_name", ""), s.get("broker_company", "")] if p]
    return "  |  ".join(parts)

def _broker_contact() -> str:
    from core.settings import load as _load_settings
    s = _load_settings()
    parts = [p for p in [s.get("broker_email", ""), s.get("broker_phone", "")] if p]
    return "  |  ".join(parts)


# ── Page-reference parser ───────────────────────────────────────────

def _parse_page(ref: str, total: int = 9999) -> int | None:
    """
    Parse a page reference string → first 1-indexed page number.

    Formats handled:
      "Page 42 of 89"          → 42
      "Pg. 4 of 31"            → 4
      "pages 1-16" / "1–16"    → 1
      "Section 12.3, Page 8"   → 8
      "42"                     → 42
    """
    if not ref:
        return None
    s = str(ref).strip()

    # "pages N-M" or "pages N–M"
    m = re.search(r'pages?\s+(\d+)\s*[-–]\s*\d+', s, re.IGNORECASE)
    if m:
        n = int(m.group(1))
        return n if 1 <= n <= total else None

    # "Page N" / "Pg. N"
    m = re.search(r'p(?:age|g\.?)\s+(\d+)', s, re.IGNORECASE)
    if m:
        n = int(m.group(1))
        return n if 1 <= n <= total else None

    # bare integer
    m = re.fullmatch(r'\s*(\d+)\s*', s)
    if m:
        n = int(m.group(1))
        return n if 1 <= n <= total else None

    # fallback: first number in string
    m = re.search(r'(\d+)', s)
    if m:
        n = int(m.group(1))
        return n if 1 <= n <= total else None

    return None


# ── Stopwords for keyword extraction ────────────────────────────────
_STOPWORDS = frozenset({
    'the', 'a', 'an', 'and', 'or', 'of', 'to', 'in', 'is', 'are', 'was', 'were',
    'be', 'been', 'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will',
    'would', 'could', 'should', 'may', 'might', 'shall', 'can', 'by', 'for',
    'with', 'at', 'from', 'as', 'on', 'this', 'that', 'it', 'its', 'such', 'any',
    'no', 'not', 'but', 'if', 'which', 'who', 'whom', 'whose', 'what', 'when',
    'where', 'how', 'all', 'each', 'every', 'both', 'either', 'neither', 'then',
    'than', 'into', 'upon', 'about', 'also', 'under', 'over', 'so', 'only',
    'said', 'herein', 'thereof', 'hereof', 'hereby', 'therein', 'shall', 'must',
})


def _clean_quote(text: str) -> str:
    """Normalize a policy quote for PDF search: collapse whitespace, normalize special chars."""
    t = re.sub(r'\s+', ' ', str(text).strip())
    return (t
            .replace('\u2019', "'").replace('\u2018', "'")   # smart single quotes
            .replace('\u201c', '"').replace('\u201d', '"')   # smart double quotes
            .replace('\u2013', '-').replace('\u2014', '-')   # en/em dashes
            .replace('\u00a0', ' ').replace('\u00ad', ''))   # NBSP, soft hyphen


def _search_with_method(page: "fitz.Page", text: str) -> "tuple[list, str]":
    """
    Search for text on a page using four progressively looser strategies.

    Returns (quads, method) where method is one of:
      'exact'    — full cleaned quote (up to 90 chars) found
      'prefix50' — first 50 chars found
      'prefix30' — first 30 chars found
      'keyword'  — cluster of 2+ distinctive keywords found on the page
      'fallback' — nothing found
    """
    if not text:
        return [], "fallback"

    t = _clean_quote(text)

    # 1. Exact / near-exact (cap at 90 chars to avoid PDF search length limits)
    hits = page.search_for(t[:90], quads=True)
    if hits:
        return hits, "exact"

    # 2. First 50 chars
    if len(t) > 50:
        hits = page.search_for(t[:50], quads=True)
        if hits:
            return hits, "prefix50"

    # 3. First 30 chars
    if len(t) > 30:
        hits = page.search_for(t[:30], quads=True)
        if hits:
            return hits, "prefix30"

    # 4. Keyword cluster — pick 3-4 distinctive words, check they appear near each other
    raw_words = re.findall(r'\b[A-Za-z]{4,}\b', t)
    # Deduplicate while preserving order, skip stopwords
    seen_kw: set = set()
    keywords: list = []
    for w in raw_words:
        wl = w.lower()
        if wl not in _STOPWORDS and wl not in seen_kw:
            seen_kw.add(wl)
            keywords.append(wl)
        if len(keywords) == 4:
            break

    if len(keywords) >= 2:
        kw_quads: list = []
        kw_found: list = []
        for kw in keywords:
            hits = page.search_for(kw, quads=True)
            if hits:
                kw_quads.extend(hits[:2])   # take up to 2 occurrences per word
                kw_found.append(kw)

        # Require at least 2 keywords found AND at least 2 quads within 120pt vertically
        if len(kw_found) >= 2 and len(kw_quads) >= 2:
            y_vals = sorted(q.rect.y0 for q in kw_quads)
            for i in range(len(y_vals) - 1):
                if y_vals[i + 1] - y_vals[i] <= 120:
                    return kw_quads, "keyword"

    return [], "fallback"


# ── Highlight + sticky note ─────────────────────────────────────────

def _highlight(page: "fitz.Page", quads: list, cat: str) -> None:
    if not quads:
        return
    color = _HL.get(cat, _HL["Good"])
    try:
        a = page.add_highlight_annot(quads)
        a.set_colors(stroke=color)
        a.set_opacity(0.4)   # semi-transparent so text stays readable
        a.update()
    except Exception:
        pass


def _sticky_note(page: "fitz.Page", pt: "fitz.Point", finding: dict) -> None:
    cat   = finding.get("category", "Good")
    title = str(finding.get("requirement_type", "Finding") or "Finding")[:60]
    plain = str(finding.get("plain_english",    "") or "")[:300].strip()
    rec   = str(finding.get("recommendation",   "") or "")[:200].strip()
    score = finding.get("risk_score")

    lines = [f"[{cat}] {title}"]
    if score is not None:
        lines.append(f"Risk Score: {score}/25")
    if plain:
        lines.append(f"\nWhat this means:\n{plain}")
    if rec:
        lines.append(f"\nRecommendation:\n{rec}")

    try:
        a = page.add_text_annot(pt, "\n".join(lines), icon="Note")
        a.set_colors(stroke=_NOTE_CLR.get(cat, _GRAY))
        a.set_info(title=title)
        a.update()
    except Exception:
        pass


def _header_band(page: "fitz.Page", finding: dict) -> None:
    """
    When text search fails — draw a colored tab in the right margin
    and place a sticky note there so the finding isn't lost.
    """
    cat   = finding.get("category", "Good")
    color = _HL.get(cat, _HL["Good"])
    pw    = page.rect.width
    ph    = page.rect.height
    # Right-margin colored tab — clearly visible without obscuring page content
    try:
        page.draw_rect(fitz.Rect(pw - 14, 8, pw - 2, 52), color=color, fill=color)
    except Exception:
        pass
    # Also draw a thin top band so the page is easy to spot when scrolling
    try:
        page.draw_rect(fitz.Rect(0, 0, pw, 4), color=color, fill=color)
    except Exception:
        pass
    label = str(finding.get("requirement_type", "Finding") or "Finding")
    note  = {**finding, "requirement_type": label + " [text not located — see page ref]"}
    _sticky_note(page, fitz.Point(pw - 30, 10), note)


# ── Cover page ──────────────────────────────────────────────────────

def _build_cover(
    pw: float,
    ph: float,
    client_name: str,
    policy_info: dict,
    findings: list,
    audit_date: str,
) -> "fitz.Document":
    """
    Build and return a single-page cover fitz.Document.
    Caller is responsible for closing it.
    """
    cover = fitz.open()
    pg    = cover.new_page(width=pw, height=ph)
    margin = 50

    # ── Navy header band ──────────────────────────────────────────
    pg.draw_rect(fitz.Rect(0, 0, pw, 125), color=_NAVY, fill=_NAVY)

    pg.insert_textbox(
        fitz.Rect(margin, 20, pw - margin, 72),
        "POLICY COMPLIANCE REVIEW",
        fontsize=24, fontname="helv", color=_WHITE, align=1,
    )
    pg.insert_textbox(
        fitz.Rect(margin, 72, pw - margin, 108),
        "Audit Findings & Coverage Analysis",
        fontsize=11, fontname="helv", color=(0.80, 0.85, 1.00), align=1,
    )

    # ── Policy info block ─────────────────────────────────────────
    y = 145

    def row(label: str, value: str) -> None:
        nonlocal y
        if not (value and str(value).strip()):
            return
        pg.insert_textbox(
            fitz.Rect(margin, y, margin + 130, y + 16),
            label.upper(),
            fontsize=7, fontname="helv", color=_GRAY,
        )
        pg.insert_textbox(
            fitz.Rect(margin + 135, y, pw - margin, y + 16),
            str(value).strip(),
            fontsize=10, fontname="helv", color=_DARK,
        )
        y += 19

    row("Client",        client_name)
    row("Policy Type",   policy_info.get("policy_type",   ""))
    row("Carrier",       policy_info.get("carrier",       ""))
    row("Policy No.",    policy_info.get("policy_number", ""))
    row("Named Insured", policy_info.get("named_insured", ""))

    eff = str(policy_info.get("effective_date", "") or "")
    exp = str(policy_info.get("expiry_date",    "") or "")
    if eff or exp:
        row("Policy Period", " → ".join(filter(None, [eff, exp])))

    row("Audit Date", audit_date)

    # ── Divider ───────────────────────────────────────────────────
    y += 6
    pg.draw_line(fitz.Point(margin, y), fitz.Point(pw - margin, y), color=_LGRAY, width=0.6)
    y += 12

    # ── Findings summary boxes ────────────────────────────────────
    ugly_n = sum(1 for f in findings if f.get("category") == "Ugly")
    bad_n  = sum(1 for f in findings if f.get("category") == "Bad")
    good_n = sum(1 for f in findings if f.get("category") == "Good")
    total  = len(findings)

    pg.insert_textbox(
        fitz.Rect(margin, y, pw - margin, y + 16),
        f"AUDIT SUMMARY — {total} findings",
        fontsize=9, fontname="helv", color=_NAVY,
    )
    y += 20

    box_w = (pw - 2 * margin - 16) / 3
    for i, (label, count, fill) in enumerate([
        ("CRITICAL",        ugly_n, _NOTE_CLR["Ugly"]),
        ("NEEDS ATTENTION", bad_n,  _NOTE_CLR["Bad"]),
        ("COMPLIANT",       good_n, _NOTE_CLR["Good"]),
    ]):
        bx   = margin + i * (box_w + 8)
        rect = fitz.Rect(bx, y, bx + box_w, y + 48)
        pg.draw_rect(rect, color=fill, fill=fill)
        pg.insert_textbox(
            fitz.Rect(bx + 4, y + 4, bx + box_w - 4, y + 28),
            str(count),
            fontsize=16, fontname="helv", color=_WHITE, align=1,
        )
        pg.insert_textbox(
            fitz.Rect(bx + 4, y + 28, bx + box_w - 4, y + 44),
            label,
            fontsize=6, fontname="helv", color=_WHITE, align=1,
        )
    y += 60

    # ── Divider ───────────────────────────────────────────────────
    pg.draw_line(fitz.Point(margin, y), fitz.Point(pw - margin, y), color=_LGRAY, width=0.6)
    y += 10

    # ── Findings index ────────────────────────────────────────────
    pg.insert_textbox(
        fitz.Rect(margin, y, pw - margin, y + 14),
        "FINDINGS INDEX",
        fontsize=7, fontname="helv", color=_GRAY,
    )
    y += 16

    sorted_findings = sorted(
        findings,
        key=lambda f: {"Ugly": 0, "Bad": 1, "Good": 2}.get(f.get("category", "Good"), 3),
    )
    for f in sorted_findings:
        if y > ph - 70:
            pg.insert_textbox(
                fitz.Rect(margin, y, pw - margin, y + 13),
                f"... and {len(sorted_findings) - sorted_findings.index(f)} more",
                fontsize=7, fontname="helv", color=_GRAY,
            )
            break
        cat    = f.get("category", "Good")
        title  = str(f.get("requirement_type", "Finding") or "Finding")[:72]
        pg_ref = str(f.get("policy_page", "") or "")
        pg_n   = _parse_page(pg_ref)
        pg_str = f"p.{pg_n}" if pg_n else ""

        bullet = {"Ugly": "●", "Bad": "◆", "Good": "✓"}.get(cat, "•")
        bullet_color = _NOTE_CLR.get(cat, _GRAY)

        pg.insert_textbox(
            fitz.Rect(margin, y, margin + 10, y + 12),
            bullet,
            fontsize=8, fontname="helv", color=bullet_color,
        )
        pg.insert_textbox(
            fitz.Rect(margin + 12, y, pw - margin - 35, y + 12),
            title,
            fontsize=7, fontname="helv", color=_DARK,
        )
        if pg_str:
            pg.insert_textbox(
                fitz.Rect(pw - margin - 32, y, pw - margin, y + 12),
                pg_str,
                fontsize=7, fontname="helv", color=_GRAY, align=2,
            )
        y += 13

    # ── Footer ────────────────────────────────────────────────────
    fy = ph - 50
    pg.draw_line(fitz.Point(margin, fy), fitz.Point(pw - margin, fy), color=_LGRAY, width=0.5)
    pg.insert_textbox(
        fitz.Rect(margin, fy + 5, pw - margin, fy + 20),
        _broker_line(),
        fontsize=8, fontname="helv", color=_NAVY, align=1,
    )
    pg.insert_textbox(
        fitz.Rect(margin, fy + 20, pw - margin, fy + 35),
        _broker_contact(),
        fontsize=7, fontname="helv", color=_GRAY, align=1,
    )

    return cover


# ── Bookmark tree ───────────────────────────────────────────────────

def _build_toc(findings: list, page_offset: int = 1) -> list:
    """
    Returns list of [level, title, page_num] for fitz.Document.set_toc().
    page_offset = 1 accounts for the inserted cover page.
    """
    toc = [[1, "Audit Findings", 1]]
    sections = [
        ("Ugly", "Critical (Ugly)"),
        ("Bad",  "Needs Attention (Bad)"),
        ("Good", "Compliant (Good)"),
    ]
    for cat, label in sections:
        cat_f = [f for f in findings if f.get("category") == cat]
        if not cat_f:
            continue
        # Level-2 bookmark at first finding's page
        first_pg = next(
            (_parse_page(str(f.get("policy_page", "") or "")) for f in cat_f
             if _parse_page(str(f.get("policy_page", "") or ""))),
            1,
        )
        toc.append([2, label, first_pg + page_offset])
        for f in cat_f:
            title  = str(f.get("requirement_type", "Finding") or "Finding")[:60]
            pg_num = _parse_page(str(f.get("policy_page", "") or ""))
            toc.append([3, title, (pg_num + page_offset) if pg_num else (1 + page_offset)])
    return toc


# ── Main annotator ──────────────────────────────────────────────────

def annotate_policy(
    pdf_path: Path,
    findings: list,
    policy_info: dict,
    client_name: str,
    output_dir: Path,
) -> Path:
    """
    Annotate a policy PDF with audit findings. Saves to output_dir.

    Args:
        pdf_path:    Original policy PDF (never modified).
        findings:    Findings that reference this PDF (policy_file matches).
        policy_info: Policy analysis dict (policy_type, carrier, etc.).
        client_name: Client display name.
        output_dir:  Destination directory.

    Returns:
        Path to the annotated PDF.
    """
    if not pdf_path.exists():
        raise FileNotFoundError(f"Policy PDF not found: {pdf_path}")

    output_dir.mkdir(parents=True, exist_ok=True)
    out_path    = output_dir / f"{pdf_path.stem}-AUDITED.pdf"
    doc         = fitz.open(str(pdf_path))
    total_pages = len(doc)

    # ── Step 1: Highlights + sticky notes ─────────────────────────
    # Group findings by page
    by_page: dict[int, list] = {}
    no_page_ref: list = []
    for f in findings:
        pg = _parse_page(str(f.get("policy_page", "") or ""), total_pages)
        if pg:
            by_page.setdefault(pg, []).append(f)
        else:
            no_page_ref.append(f)

    stats = {"exact": 0, "prefix50": 0, "prefix30": 0, "keyword": 0, "fallback": 0, "no_page": len(no_page_ref)}

    for pg_num, page_findings in by_page.items():
        if not (1 <= pg_num <= total_pages):
            continue
        page = doc[pg_num - 1]

        for finding in page_findings:
            cat   = finding.get("category", "Good")
            title = str(finding.get("requirement_type", "Finding") or "Finding")
            quote = str(finding.get("policy_quote", "") or "").strip()

            quads, method = _search_with_method(page, quote) if quote else ([], "fallback")
            stats[method] = stats.get(method, 0) + 1

            print(
                f"[pdf_annotator] HIGHLIGHT: {title[:55]!r} — "
                f"method: {method}, page {pg_num}",
                file=sys.stderr,
            )

            if method != "fallback":
                _highlight(page, quads, cat)
                q0      = quads[0]
                note_x  = min(q0.rect.x1 + 4, page.rect.width - 26)
                note_pt = fitz.Point(note_x, q0.rect.y0)
                _sticky_note(page, note_pt, finding)
            else:
                _header_band(page, finding)

    highlighted = stats["exact"] + stats["prefix50"] + stats["prefix30"] + stats["keyword"]
    print(
        f"[pdf_annotator] {pdf_path.name}: "
        f"{highlighted} highlighted "
        f"(exact={stats['exact']}, prefix50={stats['prefix50']}, "
        f"prefix30={stats['prefix30']}, keyword={stats['keyword']}), "
        f"fallback={stats['fallback']}, no_page_ref={stats['no_page']}",
        file=sys.stderr,
    )

    # ── Step 2: Insert cover page ──────────────────────────────────
    pw          = doc[0].rect.width  if total_pages else 595.0
    ph          = doc[0].rect.height if total_pages else 842.0
    audit_date  = date.today().strftime("%B %d, %Y")

    cover_doc = _build_cover(pw, ph, client_name, policy_info, findings, audit_date)
    doc.insert_pdf(cover_doc, from_page=0, to_page=0, start_at=0)
    cover_doc.close()

    # ── Step 3: Bookmarks ──────────────────────────────────────────
    try:
        doc.set_toc(_build_toc(findings, page_offset=1))
    except Exception:
        pass  # bookmarks are nice-to-have

    # ── Step 4: Save ───────────────────────────────────────────────
    doc.save(str(out_path), garbage=4, deflate=True)
    doc.close()

    return out_path


# ── Batch annotator ─────────────────────────────────────────────────

def annotate_all_policies(
    policies_dir: Path,
    findings: list,
    policy_analyses: list,
    client_name: str,
    output_dir: Path,
) -> list:
    """
    Annotate all policy PDFs that have findings referencing them.

    Returns list of (pdf_filename, output_path_or_None, n_findings, error_or_None).
    """
    # Build policy_info lookup: filename → analysis dict
    pinfo_map: dict[str, dict] = {}
    for pa in policy_analyses:
        src = str(pa.get("source_file") or pa.get("_source_file") or "")
        if src:
            pinfo_map[src]            = pa
            pinfo_map[Path(src).name] = pa

    # Group findings by policy_file. Supports three shapes:
    #   - "" or missing  → unattached, skipped
    #   - "PROGRAM"      → program-level finding, no specific PDF home (skipped here;
    #                      surfaces on the dashboard but not on any policy's PDF)
    #   - "file1.pdf"    → single-policy attachment
    #   - "file1.pdf; file2.pdf; ..." → multi-policy: attach to EACH listed PDF
    # Path(pf).name preserves the basename and strips any leading directory components.
    by_policy: dict[str, list] = {}
    for f in findings:
        pf = str(f.get("policy_file", "") or "").strip()
        if not pf or pf.upper() == "PROGRAM":
            continue
        pieces = [Path(p.strip()).name for p in pf.split(";") if p.strip()]
        for piece in pieces:
            by_policy.setdefault(piece, []).append(f)

    if not by_policy:
        # No findings have policy_file set — try to match all findings to all PDFs
        for pdf_file in policies_dir.glob("*.pdf"):
            by_policy[pdf_file.name] = findings
        if not by_policy:
            return []

    results = []
    processed: set[str] = set()

    for pdf_name, pdf_findings in by_policy.items():
        if pdf_name in processed:
            continue
        processed.add(pdf_name)

        # Resolve to disk path
        candidate = policies_dir / pdf_name
        if not candidate.exists():
            # Fuzzy match: look for any PDF whose stem matches
            stem    = Path(pdf_name).stem
            matches = list(policies_dir.glob(f"*{stem}*.pdf"))
            candidate = matches[0] if matches else None

        if not candidate or not candidate.exists():
            results.append((pdf_name, None, len(pdf_findings),
                            f"File not found: {pdf_name}"))
            continue

        pinfo = pinfo_map.get(candidate.name) or pinfo_map.get(pdf_name) or {}

        # Deduplicate findings by id
        seen, deduped = set(), []
        for f in pdf_findings:
            fid = f.get("id") or id(f)
            if fid not in seen:
                seen.add(fid)
                deduped.append(f)

        try:
            out = annotate_policy(
                pdf_path    = candidate,
                findings    = deduped,
                policy_info = pinfo,
                client_name = client_name,
                output_dir  = output_dir,
            )
            results.append((candidate.name, out, len(deduped), None))
        except Exception as exc:
            results.append((candidate.name, None, len(deduped), str(exc)))

    return results
