"""Deep probe on Hanover Auto original to figure out where the user's audit markup lives.

Tries multiple extraction paths:
  1. page.annots() with no filter — print every annot type seen
  2. page.widgets() — form fields
  3. Raw /Annots from page xref
  4. Sample 5 highlights + 5 rectangles, extract the text under/inside
"""
import json
from collections import Counter
from pathlib import Path
import fitz

SRC = Path(r"C:\Users\Bogdan\Desktop\Run-Test Policies, Contracts\Policies I bookmarked - and audited, including .pptx executive presentation\RedactedHanover - Auto - 4.1.25-4.1.26.pdf")
OUT = Path(r"C:\Users\Bogdan\Desktop\Run-Test Policies, Contracts\validation-2026-04-27")

doc = fitz.open(str(SRC))
print(f"Doc: {SRC.name}")
print(f"Pages: {doc.page_count}")
print(f"PyMuPDF version: {fitz.__doc__ if hasattr(fitz,'__doc__') else fitz.version}")
print(f"Doc.is_pdf: {doc.is_pdf}, encrypted: {doc.is_encrypted}, needs_pass: {doc.needs_pass}")
print()

# --- Pass 1: page.annots() with NO type filter, count everything ---
type_counter   = Counter()
author_counter = Counter()
type_by_author = {}
sample_per_type = {}        # type_name -> first 5 annotations

for pg_idx in range(doc.page_count):
    page = doc[pg_idx]
    for a in page.annots() or []:
        t_num, t_name = a.type
        info = a.info or {}
        author = info.get("title", "") or "(no author)"
        type_counter[(t_num, t_name)] += 1
        author_counter[author] += 1
        type_by_author.setdefault(author, Counter())[t_name] += 1
        if t_name not in sample_per_type:
            sample_per_type[t_name] = []
        if len(sample_per_type[t_name]) < 5:
            sample_per_type[t_name].append({
                "page": pg_idx + 1,
                "rect": list(a.rect),
                "info": info,
                "colors": a.colors,
                "vertices": a.vertices,
            })

print("=== Pass 1: page.annots() (no filter) ===")
print(f"Total annotations seen: {sum(type_counter.values())}")
print("\nBy (type_num, type_name):")
for (n, name), c in type_counter.most_common():
    print(f"  {n:3d}  {name:20s}  {c}")

print("\nBy author:")
for author, c in author_counter.most_common():
    print(f"  {c:5d}  {author}")

print("\nBy author x type:")
for author, types in type_by_author.items():
    print(f"  {author}:")
    for tn, c in types.items():
        print(f"      {c:5d}  {tn}")

# --- Pass 2: page.widgets() ---
widget_count = 0
for pg_idx in range(doc.page_count):
    for w in doc[pg_idx].widgets() or []:
        widget_count += 1
print(f"\n=== Pass 2: form widgets (page.widgets()) ===")
print(f"Total widgets across all pages: {widget_count}")

# --- Pass 3: raw /Annots from page xref (catch anything page.annots() filters out) ---
print(f"\n=== Pass 3: raw /Annots subtype counter from page object dict ===")
raw_subtypes = Counter()
for pg_idx in range(doc.page_count):
    page = doc[pg_idx]
    page_xref = page.xref
    annots_str = doc.xref_get_key(page_xref, "Annots")
    # annots_str is e.g. ('array', '[1234 0 R 1235 0 R ...]') if the page has annots
    if annots_str and annots_str[0] == "array":
        # Parse the xrefs out
        import re
        xrefs = re.findall(r"(\d+)\s+\d+\s+R", annots_str[1])
        for x in xrefs:
            try:
                subtype = doc.xref_get_key(int(x), "Subtype")
                if subtype and subtype[0] == "name":
                    raw_subtypes[subtype[1]] += 1
            except Exception:
                pass

for st, c in raw_subtypes.most_common():
    print(f"  {st:25s}  {c}")
print(f"Total raw annotation objects in xref: {sum(raw_subtypes.values())}")

# --- Pass 4: sample with extracted text per type ---
print(f"\n=== Pass 4: sample 3 annotations per non-Redact type with extracted underlying/inside text ===")
for type_name in sorted(sample_per_type.keys()):
    if type_name == "Redact":
        continue
    samples = sample_per_type[type_name][:3]
    print(f"\n--- {type_name} (showing {len(samples)} of {sum(1 for k,v in type_counter.items() if k[1]==type_name)}) ---")
    for s in samples:
        page = doc[s["page"] - 1]
        rect = fitz.Rect(s["rect"])
        text_inside = page.get_text("text", clip=rect).strip()
        if len(text_inside) > 240:
            text_inside = text_inside[:240] + "..."
        print(f"  pg {s['page']:>3} | rect={[round(c,1) for c in s['rect']]}")
        print(f"          author={s['info'].get('title','')!r}")
        print(f"          subject={s['info'].get('subject','')!r}")
        print(f"          contents={s['info'].get('content','')!r}")
        print(f"          colors={s['colors']}")
        print(f"          text_inside_clip={text_inside!r}")

doc.close()
