"""Extract annotations + bookmarks from the 9 originals and 9 audited PDFs.

Writes:
  originals/<slug>.json
  audited/<slug>.json
  inventory.json   (list of all extractions w/ counts)
"""
import json
from pathlib import Path
import fitz

ROOT = Path(r"C:\Users\Bogdan\Desktop\Run-Test Policies, Contracts")
OUT  = ROOT / "validation-2026-04-27"
ORIG_DIR = ROOT / "Policies I bookmarked - and audited, including .pptx executive presentation"
AUD_DIR  = ROOT / "insurance-audit-tool-pdf output - including .txt summary output file"
(OUT / "originals").mkdir(parents=True, exist_ok=True)
(OUT / "audited").mkdir(parents=True, exist_ok=True)

# slug -> (original filename, audited filename)
PAIRS = [
    ("ml",     "Redacted2024-26 Management Liability Policy.pdf",
               "Redacted2024-26 Management Liability Policy-AUDITED (1).pdf"),
    ("pl",     "Redacted2025 - 2026 Professional Liability Policy.pdf",
               "Redacted2025 - 2026 Professional Liability Policy-AUDITED (1).pdf"),
    ("sg",     "Redacted2025-2026 Liability Policy - Security Guards.pdf",
               "Redacted2025-2026 Liability Policy - Security Guards-AUDITED (1).pdf"),
    ("convex", "RedactedConvex - 2025-2026 Excess Tech EO Policy.pdf",
               "RedactedConvex - 2025-2026 Excess Tech EO Policy-AUDITED (1).pdf"),
    ("cyber",  "RedactedCyber_Assoc Industries.AmTrust_04.25-04.26 #AES123191302.pdf",
               "RedactedCyber_Assoc Industries.AmTrust_04.25-04.26 #AES123191302-AUDITED (1).pdf"),
    ("auto",   "RedactedHanover - Auto - 4.1.25-4.1.26.pdf",
               "RedactedHanover - Auto - 4.1.25-4.1.26-AUDITED.pdf"),
    ("pkg",    "RedactedHanover - Commercial - 4.1.25-4.1.26.pdf",
               "RedactedHanover - Commercial - 4.1.25-4.1.26-AUDITED (1).pdf"),
    ("umb",    "RedactedHanover - Commercial Umbrella - 4.1.25-4.1.26.pdf",
               "RedactedHanover - Commercial Umbrella - 4.1.25-4.1.26-AUDITED (1).pdf"),
    # NOTE: Use the 1.5MB copy (345 annots) as ground truth — the lowercase 18MB
    # variant that was sent for audit has zero annotations.
    ("wc",     "RedactedHanover - WC - 4.1.25-4.1.26.pdf",
               "redacted - Hanover - WC - 4.1.25-4.1.26-AUDITED (1).pdf"),
]


def extract_annots(pdf_path: Path) -> dict:
    """Return dict with page count, annotations list, bookmarks list."""
    doc = fitz.open(str(pdf_path))
    annots = []
    for pg_idx in range(doc.page_count):
        page = doc[pg_idx]
        for a in page.annots() or []:
            info = a.info or {}
            colors = a.colors or {}
            stroke = colors.get("stroke")
            fill = colors.get("fill")
            # Pull underlying highlighted/markup text if it's a text-markup annotation
            highlighted_text = ""
            try:
                if a.type[0] in (8, 9, 10, 11):  # Highlight, Underline, Squiggly, StrikeOut
                    quads = a.vertices
                    if quads:
                        # Each quad = 4 points; iterate in groups of 4
                        rects = []
                        for i in range(0, len(quads), 4):
                            q = quads[i:i+4]
                            if len(q) == 4:
                                xs = [pt[0] for pt in q]
                                ys = [pt[1] for pt in q]
                                rects.append(fitz.Rect(min(xs), min(ys), max(xs), max(ys)))
                        highlighted_text = " ".join(page.get_text("text", clip=r).strip() for r in rects).strip()
            except Exception:
                pass

            annots.append({
                "page": pg_idx + 1,                       # 1-based
                "type_code": a.type[0],
                "type_name": a.type[1],
                "title":   info.get("title", "") or "",   # author
                "subject": info.get("subject", "") or "",
                "content": info.get("content", "") or "",
                "creation_date": info.get("creationDate", "") or "",
                "mod_date":      info.get("modDate", "") or "",
                "stroke_color":  list(stroke) if stroke else None,
                "fill_color":    list(fill) if fill else None,
                "rect": list(a.rect),
                "highlighted_text": highlighted_text,
            })
    bookmarks = [{"level": lvl, "title": ttl, "page": pg} for lvl, ttl, pg in doc.get_toc()]
    out = {
        "filename": pdf_path.name,
        "page_count": doc.page_count,
        "annot_count": len(annots),
        "bookmark_count": len(bookmarks),
        "annotations": annots,
        "bookmarks": bookmarks,
    }
    doc.close()
    return out


inventory = []
for slug, orig_name, aud_name in PAIRS:
    orig_path = ORIG_DIR / orig_name
    aud_path  = AUD_DIR / aud_name
    print(f"[{slug}] orig: {orig_path.name} ... ", end="", flush=True)
    od = extract_annots(orig_path)
    (OUT / "originals" / f"{slug}.json").write_text(json.dumps(od, indent=2, default=str), encoding="utf-8")
    print(f"{od['annot_count']} annots, {od['bookmark_count']} bookmarks")
    print(f"[{slug}] aud:  {aud_path.name} ... ", end="", flush=True)
    ad = extract_annots(aud_path)
    (OUT / "audited" / f"{slug}.json").write_text(json.dumps(ad, indent=2, default=str), encoding="utf-8")
    print(f"{ad['annot_count']} annots, {ad['bookmark_count']} bookmarks")
    inventory.append({
        "slug": slug,
        "original": {"file": orig_name, "annots": od["annot_count"], "bookmarks": od["bookmark_count"], "pages": od["page_count"]},
        "audited":  {"file": aud_name,  "annots": ad["annot_count"], "bookmarks": ad["bookmark_count"], "pages": ad["page_count"]},
    })

(OUT / "inventory.json").write_text(json.dumps(inventory, indent=2), encoding="utf-8")
print("\nInventory written to inventory.json")
