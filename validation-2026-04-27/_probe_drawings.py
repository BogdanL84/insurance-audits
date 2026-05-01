"""Probe whether the user's audit markup was flattened into page drawings.

If the markup was flattened, page.get_drawings() will show:
  - Stroked rectangles (red boxes around clauses) → 're' op + 'S' op with non-default stroke color
  - Filled translucent rectangles (highlights) → 're' op + 'f' op with low opacity / yellow fill
  - Free-form ink → curve paths
"""
from collections import Counter
from pathlib import Path
import fitz

SRC = Path(r"C:\Users\Bogdan\Desktop\Run-Test Policies, Contracts\Policies I bookmarked - and audited, including .pptx executive presentation\RedactedHanover - Auto - 4.1.25-4.1.26.pdf")

doc = fitz.open(str(SRC))

# Aggregate stats
total_drawings   = 0
by_type          = Counter()
by_color         = Counter()       # (stroke_rgb, fill_rgb) → count
fill_color_count = Counter()
stroke_color_count = Counter()
samples          = []   # for non-black/white drawings

EPS = 0.02

def rgb_round(c):
    if c is None:
        return None
    if isinstance(c, (tuple, list)):
        return tuple(round(x, 2) for x in c)
    return c

def is_chromatic(rgb):
    """Skip pure black, pure white, near-grayscale text strokes."""
    if rgb is None:
        return False
    if len(rgb) == 1:
        return False
    r, g, b = rgb[:3]
    # near-black or near-white
    if max(r, g, b) < 0.10:
        return False
    if min(r, g, b) > 0.95:
        return False
    # near-gray (R==G==B)
    if abs(r - g) < EPS and abs(g - b) < EPS:
        return False
    return True

for pg_idx in range(doc.page_count):
    page = doc[pg_idx]
    drawings = page.get_drawings()
    for d in drawings:
        total_drawings += 1
        op_type = d.get("type")     # 's' (stroke), 'f' (fill), 'fs' (fill+stroke), or 'clip'
        by_type[op_type] += 1
        s_color = rgb_round(d.get("color"))
        f_color = rgb_round(d.get("fill"))
        fill_color_count[f_color] += 1
        stroke_color_count[s_color] += 1
        # Capture chromatic samples (non-text-rendering drawings)
        if (is_chromatic(s_color) or is_chromatic(f_color)) and len(samples) < 30:
            rect = d.get("rect")
            if rect:
                clip = fitz.Rect(rect)
                # Slightly enlarge to catch boundary text
                clip.x0 -= 1; clip.y0 -= 1; clip.x1 += 1; clip.y1 += 1
                under = page.get_text("text", clip=clip).strip()
                if len(under) > 200:
                    under = under[:200] + "..."
            else:
                under = ""
            samples.append({
                "page": pg_idx + 1,
                "type": op_type,
                "stroke": s_color,
                "fill": f_color,
                "rect": [round(x,1) for x in (rect or [])],
                "width": d.get("width"),
                "stroke_opacity": d.get("stroke_opacity"),
                "fill_opacity": d.get("fill_opacity"),
                "under": under,
            })

print(f"Total page drawings: {total_drawings}")
print(f"\nBy op type:")
for k, v in by_type.most_common():
    print(f"  {k!s:8s}  {v}")

print(f"\nTop 15 stroke colors:")
for k, v in stroke_color_count.most_common(15):
    print(f"  {k!s:25s}  {v}")

print(f"\nTop 15 fill colors:")
for k, v in fill_color_count.most_common(15):
    print(f"  {k!s:25s}  {v}")

print(f"\n=== Chromatic (non-black/white/grayscale) drawing samples ({len(samples)} of capped 30) ===")
for s in samples:
    print(f"\n  pg {s['page']:>3} | type={s['type']} | stroke={s['stroke']} fill={s['fill']} "
          f"width={s['width']} s_op={s['stroke_opacity']} f_op={s['fill_opacity']}")
    print(f"          rect={s['rect']}")
    print(f"          under={s['under']!r}")

doc.close()
