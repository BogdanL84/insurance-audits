"""Full probe on the actual marked-up Hanover Auto in Downloads."""
from collections import Counter
from pathlib import Path
import fitz

SRC = Path(r"C:\Users\Bogdan\Downloads\Hanover - Auto - 4.1.25-4.1.26.pdf")
doc = fitz.open(str(SRC))

print(f"=== {SRC.name} — {doc.page_count} pages ===\n")

# Per-type and per-author counters
type_counter   = Counter()
author_counter = Counter()
type_by_author = {}
samples_by_type = {}   # type_name -> list of dicts

for pg_idx in range(doc.page_count):
    page = doc[pg_idx]
    for a in page.annots() or []:
        t_num, t_name = a.type
        info = a.info or {}
        author = info.get("title", "") or "(no author)"
        type_counter[(t_num, t_name)] += 1
        author_counter[author] += 1
        type_by_author.setdefault(author, Counter())[t_name] += 1

        # Pull text under or inside the annotation
        rect = a.rect
        text_under = ""
        if t_name in ("Highlight", "Underline", "Squiggly", "StrikeOut"):
            # Use vertices (quads) for precise highlighted text
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
        elif t_name in ("Square", "Circle", "Polygon", "PolyLine", "Ink", "Line"):
            # Pad rect a bit for ink/freehand
            clip = fitz.Rect(rect); clip.x0 -= 1; clip.y0 -= 1; clip.x1 += 1; clip.y1 += 1
            text_under = page.get_text("text", clip=clip).strip()
        elif t_name in ("FreeText", "Text", "Stamp"):
            text_under = info.get("content", "")  # inline note text

        samples_by_type.setdefault(t_name, []).append({
            "page": pg_idx + 1,
            "type_num": t_num,
            "type_name": t_name,
            "author": author,
            "subject": info.get("subject", ""),
            "content": info.get("content", ""),
            "creation_date": info.get("creationDate", ""),
            "mod_date": info.get("modDate", ""),
            "stroke": a.colors.get("stroke") if a.colors else None,
            "fill":   a.colors.get("fill")   if a.colors else None,
            "rect": [round(x, 1) for x in rect],
            "text_under": text_under[:300],
        })

print("By (type_num, type_name):")
for (n, name), c in type_counter.most_common():
    print(f"  {n:3d}  {name:12s}  {c}")
print(f"\nBy author:")
for k, v in author_counter.most_common():
    print(f"  {v:5d}  {k}")
print(f"\nBy author x type:")
for author, types in type_by_author.items():
    print(f"  {author}:")
    for tn, c in types.items():
        print(f"      {c:5d}  {tn}")

print(f"\nBookmarks (TOC): {len(doc.get_toc())}")
for lvl, ttl, pg in doc.get_toc()[:20]:
    print(f"  pg{pg:>3} | {ttl}")

# Print 3-5 examples per non-Redact type
SHOW_TYPES = ["Highlight", "Square", "Circle", "Ink", "FreeText", "Text", "StrikeOut", "Underline", "Stamp", "Line"]
print(f"\n=== Examples per type ===")
for tname in SHOW_TYPES:
    if tname not in samples_by_type:
        continue
    items = samples_by_type[tname][:5]
    print(f"\n--- {tname} ({len(samples_by_type[tname])} total, showing {len(items)}) ---")
    for s in items:
        print(f"\n  pg {s['page']:>3}  rect={s['rect']}  stroke={s['stroke']}  fill={s['fill']}")
        if s['content']:
            print(f"        content: {s['content'][:200]!r}")
        if s['subject']:
            print(f"        subject: {s['subject']!r}")
        print(f"        text_under: {s['text_under']!r}")

doc.close()
