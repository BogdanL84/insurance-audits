"""Hunt for non-redacted master PDFs anywhere under C:\\Users\\Bogdan\\ matching
policy keywords; probe each for annotation type/count/author. Rank by likelihood
of being the marked-up master.

Skips system folders: AppData, node_modules, .git, .venv, __pycache__.
"""
import json
import re
from collections import Counter
from pathlib import Path
import fitz

ROOT = Path(r"C:\Users\Bogdan")
OUT  = Path(r"C:\Users\Bogdan\Desktop\Run-Test Policies, Contracts\validation-2026-04-27")

SKIP_DIRS = {"AppData", "node_modules", ".git", ".venv", "__pycache__",
             "Library Caches", "Caches", "Temp", "tmp", "venv"}

# Policy keyword groups (case-insensitive). Each group → policy slug.
KEYWORDS = {
    "ml":     [r"hartford", r"twin city", r"management liability"],
    "pl":     [r"berkley", r"gemini", r"professional liability", r"\be&o\b"],
    "sg":     [r"arch", r"security guard"],
    "convex": [r"convex"],
    "cyber":  [r"amtrust", r"cyber"],
    "auto":   [r"hanover.*auto"],
    "pkg":    [r"hanover.*commercial(?!.*umbrella)"],
    "umb":    [r"hanover.*(commercial )?umbrella", r"\bumbrella\b"],
    "wc":     [r"hanover.*wc", r"workers comp", r"\bwc\b"],
}
# Compile
KW_COMPILED = {slug: [re.compile(p, re.I) for p in pats] for slug, pats in KEYWORDS.items()}

NEG_TOKENS = ("redacted", "audited", "knowledge-base", "kb_check", ".trash")


def slug_for_filename(name: str) -> list:
    """Return list of slugs whose keywords match this filename."""
    matches = []
    for slug, pats in KW_COMPILED.items():
        if any(p.search(name) for p in pats):
            matches.append(slug)
    return matches


def walk_pdfs(root: Path):
    for p in root.rglob("*.pdf"):
        # Skip if any path part is in SKIP_DIRS
        if any(part in SKIP_DIRS or part.startswith(".") for part in p.parts):
            continue
        yield p


def probe(p: Path) -> dict:
    try:
        d = fitz.open(str(p))
    except Exception as e:
        return {"error": str(e)}
    types = Counter(); authors = Counter()
    n_pages = d.page_count
    for pg in d:
        for a in pg.annots() or []:
            types[a.type[1]] += 1
            authors[(a.info or {}).get("title", "") or "(none)"] += 1
    bm = len(d.get_toc())
    d.close()
    return {
        "pages": n_pages,
        "types": dict(types),
        "authors": dict(authors),
        "bookmarks": bm,
    }


# 1) Find candidate PDFs
print(f"Scanning {ROOT}…", flush=True)
candidates = []
for pdf in walk_pdfs(ROOT):
    name = pdf.name
    name_lower = name.lower()
    # Skip clearly-redacted-only files unless we have no other choice
    is_negative = any(t in name_lower for t in NEG_TOKENS)
    matched_slugs = slug_for_filename(name_lower)
    if not matched_slugs:
        continue
    candidates.append({"path": str(pdf), "slugs": matched_slugs, "is_redacted_or_audited": is_negative})

print(f"Found {len(candidates)} candidate PDFs matching policy keywords")

# 2) Probe each
NON_REDACT_MARKUP_TYPES = {"Highlight", "Square", "Circle", "Ink",
                           "FreeText", "Text", "Line", "Polygon",
                           "PolyLine", "Underline", "Squiggly", "StrikeOut"}

for c in candidates:
    info = probe(Path(c["path"]))
    c.update(info)

# 3) Rank
def rank(c: dict) -> int:
    """High=2 · Medium=1 · Low=0"""
    if c.get("error"):
        return 0
    types = c.get("types", {})
    authors = c.get("authors", {})
    has_markup = any(t in types for t in NON_REDACT_MARKUP_TYPES)
    is_bogdan = any("bogdan" in a.lower() for a in authors)
    if has_markup and is_bogdan:
        return 2  # High
    if has_markup or (is_bogdan and any(t == "Redact" for t in types)):
        return 1  # Medium (has user-redacted annots, so user touched it)
    return 0      # Low

for c in candidates:
    c["rank"] = rank(c)

candidates.sort(key=lambda c: (-c["rank"], c["is_redacted_or_audited"], c["path"].lower()))

(OUT / "hunt_results.json").write_text(json.dumps(candidates, indent=2), encoding="utf-8")

print(f"\n=== HIGH-likelihood matches (markup + Bogdan author) ===\n")
for c in candidates:
    if c["rank"] != 2:
        continue
    print(f"  {c['path']}")
    print(f"    slugs={c['slugs']}  pages={c.get('pages')}  bookmarks={c.get('bookmarks')}")
    print(f"    types={c.get('types')}")
    print(f"    authors={c.get('authors')}")

print(f"\n=== MEDIUM-likelihood matches (some markup or Bogdan-redacted) ===\n")
for c in candidates:
    if c["rank"] != 1:
        continue
    print(f"  {c['path']}")
    print(f"    slugs={c['slugs']}  pages={c.get('pages')}  redacted/audited_in_name={c['is_redacted_or_audited']}")
    print(f"    types={c.get('types')}")
    print(f"    authors={c.get('authors')}")

print(f"\n=== LOW-likelihood (filename loose match, no relevant annots) ===\n")
for c in candidates:
    if c["rank"] != 0:
        continue
    print(f"  {c['path']}  slugs={c['slugs']}  types={c.get('types')}")
print(f"\nTotal candidates: {len(candidates)} | High={sum(1 for c in candidates if c['rank']==2)} | Medium={sum(1 for c in candidates if c['rank']==1)} | Low={sum(1 for c in candidates if c['rank']==0)}")
