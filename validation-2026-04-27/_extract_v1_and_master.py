"""Extract v1 (older Downloads) audited findings + Auto master ground-truth markup.

Outputs:
  audited_v1/<slug>.json   (8 policies — no v1 for Auto)
  originals_real/auto.json (Bogdan Laza's actual marked-up Auto master)
"""
import json
from pathlib import Path
import fitz

OUT = Path(r"C:\Users\Bogdan\Desktop\Run-Test Policies, Contracts\validation-2026-04-27")
(OUT / "audited_v1").mkdir(parents=True, exist_ok=True)
(OUT / "originals_real").mkdir(parents=True, exist_ok=True)

DLD = Path(r"C:\Users\Bogdan\Downloads")

V1_FILES = {
    "ml":     DLD / "Redacted2024-26 Management Liability Policy-AUDITED.pdf",
    "pl":     DLD / "Redacted2025 - 2026 Professional Liability Policy-AUDITED.pdf",
    "sg":     DLD / "Redacted2025-2026 Liability Policy - Security Guards-AUDITED.pdf",
    "convex": DLD / "RedactedConvex - 2025-2026 Excess Tech EO Policy-AUDITED.pdf",
    "cyber":  DLD / "RedactedCyber_Assoc Industries.AmTrust_04.25-04.26 #AES123191302-AUDITED.pdf",
    "pkg":    DLD / "RedactedHanover - Commercial - 4.1.25-4.1.26-AUDITED.pdf",
    "umb":    DLD / "RedactedHanover - Commercial Umbrella - 4.1.25-4.1.26-AUDITED.pdf",
    "wc":     DLD / "redacted - Hanover - WC - 4.1.25-4.1.26-AUDITED.pdf",
    # No v1 for auto — confirmed via hunt
}

AUTO_MASTER = DLD / "Hanover - Auto - 4.1.25-4.1.26.pdf"


def extract(pdf_path: Path, keep_redacts: bool = False) -> dict:
    """Extract all annotations + bookmarks from a PDF.
    For audited PDFs, drop the BogdanLaza Redacts (visual noise — they're
    PII redactions, not findings). For originals, keep everything."""
    doc = fitz.open(str(pdf_path))
    annots = []
    for pg_idx in range(doc.page_count):
        page = doc[pg_idx]
        for a in page.annots() or []:
            info = a.info or {}
            colors = a.colors or {}
            t_num, t_name = a.type
            author = info.get("title", "") or ""
            # Skip BogdanLaza Redacts unless explicitly requested
            if not keep_redacts and t_name == "Redact" and author == "BogdanLaza":
                continue
            # Pull underlying/inside text where applicable
            rect = a.rect
            text_under = ""
            try:
                if t_name in ("Highlight", "Underline", "Squiggly", "StrikeOut"):
                    verts = a.vertices or []
                    if verts:
                        rects = []
                        for i in range(0, len(verts), 4):
                            q = verts[i:i+4]
                            if len(q) == 4:
                                xs = [pt[0] for pt in q]; ys = [pt[1] for pt in q]
                                rects.append(fitz.Rect(min(xs), min(ys), max(xs), max(ys)))
                        text_under = " ".join(page.get_text("text", clip=r).strip() for r in rects).strip()
                    else:
                        text_under = page.get_text("text", clip=rect).strip()
                elif t_name in ("Square", "Circle", "Polygon", "Ink", "Line", "PolyLine"):
                    clip = fitz.Rect(rect); clip.x0 -= 1; clip.y0 -= 1; clip.x1 += 1; clip.y1 += 1
                    text_under = page.get_text("text", clip=clip).strip()
            except Exception:
                pass
            annots.append({
                "page": pg_idx + 1,
                "type_num": t_num,
                "type_name": t_name,
                "author": author,
                "subject": info.get("subject", "") or "",
                "content": info.get("content", "") or "",
                "creation_date": info.get("creationDate", "") or "",
                "mod_date": info.get("modDate", "") or "",
                "stroke": list(colors.get("stroke")) if colors.get("stroke") else None,
                "fill":   list(colors.get("fill"))   if colors.get("fill")   else None,
                "rect": [round(x, 1) for x in rect],
                "text_under": text_under[:600],
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


# Extract v1 audited findings (drop BogdanLaza Redacts so only the app's findings remain)
print("=== Extracting v1 audited findings ===")
for slug, p in V1_FILES.items():
    if not p.exists():
        print(f"  [{slug}] MISSING: {p}")
        continue
    d = extract(p, keep_redacts=False)
    findings_only = [a for a in d["annotations"] if a["type_name"] in ("Text", "Highlight", "FreeText", "Square", "Line", "Ink")]
    print(f"  [{slug}] {p.name}: {len(findings_only)} non-redact annots, {d['bookmark_count']} bookmarks")
    d["annotations"] = findings_only
    d["annot_count"] = len(findings_only)
    (OUT / "audited_v1" / f"{slug}.json").write_text(json.dumps(d, indent=2, default=str), encoding="utf-8")

# Extract Auto master (keep ALL — these are user audit annotations, not redactions)
print("\n=== Extracting Auto Downloads master (Bogdan Laza markup) ===")
d = extract(AUTO_MASTER, keep_redacts=False)  # No BogdanLaza Redacts to drop here anyway
print(f"  auto-master: {AUTO_MASTER.name}: {d['annot_count']} annots, {d['bookmark_count']} bookmarks")
(OUT / "originals_real" / "auto.json").write_text(json.dumps(d, indent=2, default=str), encoding="utf-8")

print(f"\nDone.")
