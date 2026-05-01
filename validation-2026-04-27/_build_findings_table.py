"""Parse the .txt summary's 25 findings and link each to the audited-PDF
sticky-note location (page + content) where it appears.

Output: findings_table.json + findings_table.md
"""
import json
import re
from pathlib import Path

OUT = Path(r"C:\Users\Bogdan\Desktop\Run-Test Policies, Contracts\validation-2026-04-27")
TXT = Path(r"C:\Users\Bogdan\Desktop\Run-Test Policies, Contracts\insurance-audit-tool-pdf output - including .txt summary output file\run-test-election-services-email-am-20260427.txt")

# Map summary headings to policy slug — based on the keywords in the title
TITLE_TO_SLUG = [
    # Order matters — first match wins. More specific routes go first.
    (re.compile(r"convex|excess tech|excess tower", re.I),             "convex"),
    (re.compile(r"^umbrella\b", re.I),                                 "umb"),
    (re.compile(r"^cyber\b", re.I),                                    "cyber"),
    (re.compile(r"^d&o\b|management liability|management |^epli\b",
                re.I),                                                 "ml"),
    (re.compile(r"workers' compensation|workers comp|^wc\b|california employers", re.I), "wc"),
    (re.compile(r"^auto\b|auto.*custody", re.I),                       "auto"),
    (re.compile(r"property|per-project|equipment breakdown", re.I),    "pkg"),
    (re.compile(r"general liability|^gl |classification|arch policy|security guard", re.I), "sg"),
    # Catch-all for Professional Liability / E&O
    (re.compile(r"professional liability|^pl |^e&o", re.I),            "pl"),
]

def slug_for_title(title: str) -> str:
    for pat, slug in TITLE_TO_SLUG:
        if pat.search(title):
            return slug
    return "?"


# Parse the email .txt — three sections: CRITICAL (Ugly), NEEDS ATTENTION (Bad), IN GOOD SHAPE
text = TXT.read_text(encoding="utf-8")

findings = []
def parse_block(block_text: str, category: str):
    """Each finding = a numbered line + a description on the next line(s) until the next number or blank."""
    # Pattern: "  N. Title [Score: X — Severity]"
    item_re = re.compile(r"^\s*\d+\.\s+(.+?)\s*\[Score:\s*(\d+)\s*[—–-]\s*(\w+)\s*\]\s*$", re.M)
    items = list(item_re.finditer(block_text))
    for i, m in enumerate(items):
        title = m.group(1).strip()
        score = int(m.group(2))
        sev   = m.group(3).strip()
        # Description is the text from end of this match line to start of next match line (or end of block)
        desc_start = m.end()
        desc_end = items[i + 1].start() if i + 1 < len(items) else len(block_text)
        desc = block_text[desc_start:desc_end].strip()
        # Trim trailing newlines and "TOP 3 RECOMMENDED" / "IN GOOD SHAPE" markers
        desc = re.sub(r"\n\s*$", "", desc)
        findings.append({
            "category": category,
            "title": title,
            "score": score,
            "severity_word": sev,
            "description": desc,
            "policy_slug": slug_for_title(title),
        })


crit_match = re.search(r"CRITICAL \(Ugly\)[^\n]*:(.+?)NEEDS ATTENTION", text, re.S)
bad_match  = re.search(r"NEEDS ATTENTION \(Bad\):(.+?)IN GOOD SHAPE", text, re.S)
if crit_match:
    parse_block(crit_match.group(1), "Ugly")
if bad_match:
    parse_block(bad_match.group(1), "Bad")


# Now link each finding to an audited-PDF location.
# The audited PDFs use Text/Highlight annots; the title field contains a (truncated) version of the finding name.
def normalize(s):
    s = s.lower()
    # Replace various dashes / em-dashes / unicode replacement chars
    s = s.replace("—", "-").replace("–", "-").replace("�", "-")
    s = re.sub(r"\s+", " ", s).strip()
    return s


for f in findings:
    slug = f["policy_slug"]
    f["matched_in_audited"] = False
    if slug == "?":
        continue
    aud_path = OUT / "audited" / f"{slug}.json"
    if not aud_path.exists():
        continue
    aud = json.loads(aud_path.read_text(encoding="utf-8"))
    f_norm = normalize(f["title"])
    # First try matching against annotation title (which is the finding name, often truncated)
    # Then content (which has the full finding body)
    best = None
    for a in aud["annotations"]:
        if a["type_name"] not in ("Text", "Highlight"):
            continue
        atitle_norm = normalize(a.get("title", ""))
        acontent_norm = normalize(a.get("content", ""))
        # Match logic: substring match on title, or title-prefix appears in content
        # The annotation title is truncated at ~70 chars — use a prefix match
        if atitle_norm and atitle_norm[:30] and atitle_norm[:30] in f_norm:
            best = a
            break
        # If first significant words of finding-title appear in content
        head = f_norm[:50]
        if head and head in acontent_norm:
            best = a
            break
    if best:
        f["matched_in_audited"] = True
        f["audited_page"] = best["page"]
        f["audited_annot_type"] = best["type_name"]
        f["audited_content_preview"] = (best.get("content") or "")[:300]


# Stats
matched = sum(1 for f in findings if f["matched_in_audited"])
print(f"Parsed {len(findings)} findings from .txt; matched {matched} to audited-PDF pages")
unmatched = [f["title"] for f in findings if not f["matched_in_audited"]]
if unmatched:
    print("Unmatched:")
    for t in unmatched:
        print(f"  - {t}")

# Now append the 5 Good findings that exist as audited Text annotations but
# weren't enumerated in the .txt summary.
matched_titles_norm = {normalize(f["title"]) for f in findings if f["matched_in_audited"]}
for slug in sorted({s for _, s in [(p, p) for p in ['ml','pl','sg','convex','cyber','auto','pkg','umb','wc']]}):
    aud_path = OUT / "audited" / f"{slug}.json"
    if not aud_path.exists():
        continue
    d = json.loads(aud_path.read_text(encoding="utf-8"))
    for a in d["annotations"]:
        if a["type_name"] != "Text":
            continue
        title = a.get("title", "") or ""
        content = a.get("content", "") or ""
        title_norm = normalize(title)
        # Skip if already matched
        if any(title_norm and title_norm[:30] and title_norm[:30] in mt for mt in matched_titles_norm):
            continue
        # Detect category from content prefix [Good]/[Bad]/[Ugly]
        cat = "Unknown"
        score = None
        m = re.search(r"\[(Good|Bad|Ugly)\]", content)
        if m:
            cat = m.group(1)
        m2 = re.search(r"Risk Score:\s*(\d+)", content)
        if m2:
            score = int(m2.group(1))
        findings.append({
            "category": cat,
            "title": title,
            "score": score if score is not None else 0,
            "severity_word": "",
            "description": content[:500],
            "policy_slug": slug,
            "matched_in_audited": True,
            "audited_page": a["page"],
            "audited_annot_type": "Text",
            "audited_content_preview": content[:300],
            "from_pdf_only": True,
        })

good_added = sum(1 for f in findings if f.get("from_pdf_only"))
print(f"Added {good_added} additional findings from audited PDFs (not in .txt)")

(OUT / "findings_table.json").write_text(json.dumps(findings, indent=2), encoding="utf-8")

# Markdown report
md = ["# App's 25 Findings — Linked to Audited-PDF Pages\n"]
md.append("| # | Cat | Score | Policy | Title | Audited Page |")
md.append("|---|---|---|---|---|---|")
for i, f in enumerate(findings, 1):
    pg = f.get("audited_page", "—")
    md.append(f"| {i} | {f['category']} | {f['score']} | {f['policy_slug']} | {f['title']} | {pg} |")
md.append("\n## Per-finding detail\n")
for i, f in enumerate(findings, 1):
    md.append(f"\n### {i}. [{f['category']}, score {f['score']}] {f['title']}")
    md.append(f"- **Policy slug:** `{f['policy_slug']}`")
    md.append(f"- **Audited PDF page:** {f.get('audited_page', 'NOT MATCHED')}")
    md.append(f"- **Annotation type:** {f.get('audited_annot_type', '—')}")
    md.append(f"- **Summary description (from .txt):** {f['description']}")
    if f.get("audited_content_preview"):
        md.append(f"- **Audited annot content preview:** {f['audited_content_preview']}")

(OUT / "findings_table.md").write_text("\n".join(md), encoding="utf-8")
print(f"\nfindings_table.json + findings_table.md written")
