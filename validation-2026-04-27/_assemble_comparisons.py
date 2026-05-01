"""Assemble per-policy data dumps for Phase 3 comparison files.

For each slug, computes:
  - v1 vs v2 finding match (NEW / REMOVED / UNCHANGED-OR-REWORDED)
  - Presentation slide claims relevant to that policy
  - Prior report verification (where available)
  - Auto: master annotations + bookmarks (where available)
  - GAP-XX keyword search across v2 audited annot content

Outputs: per_slug_data/<slug>.json  (consumed by the per-policy MD writer)
"""
import json, re
from pathlib import Path
from difflib import SequenceMatcher

OUT = Path(r"C:\Users\Bogdan\Desktop\Run-Test Policies, Contracts\validation-2026-04-27")
(OUT / "per_slug_data").mkdir(exist_ok=True)

SLUGS = ["ml", "pl", "sg", "convex", "cyber", "auto", "pkg", "umb", "wc"]

POLICY_NAMES = {
    "ml": "Management Liability (Hartford / Twin City Fire)",
    "pl": "Professional Liability / E&O (Gemini / WR Berkley)",
    "sg": "Security Guards Liability (Arch Insurance)",
    "convex": "Convex Excess Tech E&O",
    "cyber": "Cyber (AmTrust)",
    "auto": "Hanover Commercial Auto",
    "pkg": "Hanover Commercial Package",
    "umb": "Hanover Commercial Umbrella",
    "wc": "Hanover Workers' Compensation",
}

PRIOR_REPORT_AVAILABLE = {"ml", "pl", "sg", "wc"}
MASTER_AVAILABLE       = {"auto"}

# ----- helpers ---------------------------------------------------------
def normalize(s: str) -> str:
    if not s:
        return ""
    s = s.lower()
    s = (s.replace(chr(0x2014), "-")
           .replace(chr(0x2013), "-")
           .replace(chr(0xfffd), "-"))   # PyMuPDF replacement char for em-dash
    s = re.sub(r"\s+", " ", s).strip()
    return s


def title_of(annot):
    """v1 stored finding name in 'author', v2 stored in 'title'."""
    return annot.get("title") or annot.get("author") or ""


def similar(a: str, b: str) -> float:
    return SequenceMatcher(None, normalize(a), normalize(b)).ratio()


def load_findings(path: Path):
    if not path.exists():
        return []
    d = json.loads(path.read_text(encoding="utf-8"))
    out = []
    for a in d["annotations"]:
        if a["type_name"] not in ("Text", "FreeText"):
            continue
        out.append({
            "page": a["page"],
            "title": title_of(a),
            "content": a.get("content", ""),
            "type_name": a["type_name"],
        })
    return out


# ----- presentation slides → policy slug ------------------------------
PRES_BY_SLUG = {
    "ml": [10, 24],
    "auto": [11, 12, 21],
    "sg": [13, 15, 22],
    "pl": [16, 23, 26, 33, 34],
    "cyber": [17, 22, 32],
    # "Multiple Policies" cancellation slide 18 applies to multiple slugs
    "pkg": [24, 28, 29, 30, 31],
    "umb": [25, 27],
    "wc": [23],
    "convex": [],   # not specifically in presentation
}
# Slide 18 — cancellation notice — applies to all
CANCEL_SLIDE = 18


def load_presentation():
    return json.loads((OUT / "presentation.json").read_text(encoding="utf-8"))


def pres_claims_for_slug(slug, slides):
    """Return relevant slide entries for this slug."""
    target_pages = set(PRES_BY_SLUG.get(slug, []))
    target_pages.add(CANCEL_SLIDE)  # cancellation slide is relevant to all
    out = []
    for s in slides:
        if s["slide"] in target_pages:
            out.append(s)
    return out


# ----- v1 → v2 matching -----------------------------------------------
SIMILARITY_MATCH_THRESHOLD = 0.55  # title similarity required to call it "same"


def match_v1_v2(v1_findings, v2_findings):
    """Greedy bipartite match by title similarity."""
    used_v2 = set()
    pairs = []  # (v1, v2|None, similarity)
    for f1 in v1_findings:
        best_idx, best_score = None, 0.0
        for j, f2 in enumerate(v2_findings):
            if j in used_v2:
                continue
            sc = similar(f1["title"], f2["title"])
            if sc > best_score:
                best_score = sc
                best_idx = j
        if best_idx is not None and best_score >= SIMILARITY_MATCH_THRESHOLD:
            pairs.append((f1, v2_findings[best_idx], best_score))
            used_v2.add(best_idx)
        else:
            pairs.append((f1, None, best_score))
    # Any v2 not consumed = NEW IN V2
    new_v2 = [f for j, f in enumerate(v2_findings) if j not in used_v2]
    return pairs, new_v2


# ----- GAP-XX keyword detection ---------------------------------------
GAP_TESTS = {
    "auto": [
        ("GAP-17",  "Maricopa $2M CSL fails (umbrella attachment barred for Auto)",
                   ["maricopa", "2,000,000", "csl", "combined single limit", "umbrella"]),
        ("GAP-18",  "$500 electronic equipment sublimit",
                   ["$500", "electronic equipment", "audio, visual", "461-0155"]),
        ("GAP-19",  "Malina Trujillo named driver exclusion",
                   ["malina", "trujillo", "named driver"]),
        ("GAP-20",  "Lincoln Shields LLC + Black Mountain on Auto, missing from Umbrella",
                   ["lincoln shields", "black mountain", "475-0174"]),
        ("GAP-21",  "Auto missing 401-1235 Designated Entity NOC",
                   ["401-1235", "designated entity", "noc to designated"]),
        ("GAP-01",  "Inc-vs-LLC entity-type mismatch",
                   ["inc", "llc", "form of business", "entity type"]),
    ],
    "cyber": [
        ("GAP-22a", "Cyber Deception $250K=$250K phantom coverage",
                   ["$250,000", "250k", "cyber deception", "social engineering", "retention"]),
        ("GAP-22b", "Defense Within Limits + Shared Aggregate erosion",
                   ["defense within", "dwl", "erosion", "shared aggregate"]),
        ("GAP-22c", "$4M aggregate vs Maricopa $5M",
                   ["$5,000,000", "$5m", "$4m", "$4,000,000", "maricopa"]),
        ("GAP-22d", "NY choice-of-law on AZ insured",
                   ["new york", "choice of law", "governed by"]),
        ("GAP-22e", "Proof of Loss $250K secondary sublimit",
                   ["proof of loss", "$250"]),
        ("GAP-22f", "Cyber is the ONLY policy with correct LLC entity",
                   ["llc", "policy change", "endorsement #1", "name change"]),
    ],
    "umb": [
        ("GAP-08a", "Schedule of Underlying blank for Tech E&O / D&O",
                   ["schedule of underlying", "blank", "tech e&o", "d&o", "professional liability"]),
        ("GAP-08b", "Hanover Umbrella does NOT sit over Convex Tech E&O",
                   ["convex", "tech e&o", "follow-form"]),
        ("GAP-08c", "Coverage B direct exclusions strip professional services",
                   ["coverage b", "professional services", "exclusion"]),
    ],
    "pkg": [
        ("GAP-20a", "Properties LLC missing from CGL but on Auto/Umbrella/Cyber",
                   ["properties llc", "cgl"]),
        ("GAP-20b", "Cross-policy entity inconsistency pattern",
                   ["lincoln shields", "black mountain"]),
        ("GAP-21",  "Designated Entity NOC 401-1235 details",
                   ["401-1235", "designated entity"]),
    ],
}
# All-policy GAP-01 (Inc vs LLC)
ALL_GAP_01 = ("GAP-01-EXPANDED", "Inc-vs-LLC entity-type mismatch caught here?",
              ["inc", "llc", "form of business", "named insured"])


def search_v2(v2_findings, keywords):
    """Return list of (page, title, content_snippet) where keywords appear."""
    hits = []
    kws_norm = [k.lower() for k in keywords]
    for f in v2_findings:
        haystack = (normalize(f["title"]) + " " + (f["content"] or "").lower())
        if any(k in haystack for k in kws_norm):
            hits.append({
                "page": f["page"],
                "title": f["title"],
                "snippet": (f["content"] or "")[:280],
            })
    return hits


# ----- Prior report claim summaries (for ML/PL/SG/WC) -----------------
# These are hand-extracted from the handoff doc + 2 interim reports.
PRIOR_CLAIMS = {
    "ml": [
        ("Wage & Hour no carrier defense duty, defense costs sub", "Bad Risk 9", "p15"),
        ("Crime coverage $2M included", "Good", "p60"),
        ("Entity regulatory proceedings not covered unless individual", "Bad Risk 12", "p73"),
        ("PE Co-Defendant Extension + Shadow Director", "Good", "p74"),
        ("D&O Manufacturing/Professional Services Exclusion bars Entity coverage", "Ugly Risk 12", "p86"),
        ("Split Prior/Pending Date — $1M gap on excess layer", "Bad Risk 12", "p107"),
        ("PRESENTATION CLAIM G1 (slide 10): Notice of Knowledge CEO/CFO only — pg 74", "PARTIAL — cite wrong, claim lives at pp 20/25/42/58", "p20-58"),
        ("PRESENTATION CLAIM B4 (slide 18): ML cancellation 10 days", "PARTIAL — 10 days non-pay only; 20 days other (PP00H10700 pg 70)", "p70"),
    ],
    "pl": [
        ("Tech services carve-back excluding hardware malfunction / electrical / delay / ISP outages", "Verified", "p26-27"),
        ("Mail Processing Services restricted retro date 4/1/2021 (vs base 3/27/2017)", "Verified", "p20"),
        ("Network Security/Privacy Breach + Biometric Identifiers exclusion (BIPA)", "Verified", "p45-46"),
        ("Blanket AI endorsement: Claim Expenses only, no Loss; 'solely' from insured's wrongful acts", "Verified U6", "p21"),
        ("PRESENTATION U13 (slide 33) Recall/Reprinting — cite WRONG (pg 23 = Split Limits, recall is at pg 24 Media Extension)", "REVISE", "p24+15"),
        ("Split Limits $1M/$1M / +$1M xs $1M / +$3M xs $2M trigger-date buckets — hidden $1M effective limit", "MISSED BY V1", "p23"),
        ("M&A auto-termination clause (PE-critical)", "MISSED BY V1", "p17-18"),
        ("AZ guaranty fund disclaimer (Gemini surplus lines)", "MISSED BY V1", "p3"),
        ("Mandatory binding arbitration in Chicago", "MISSED BY V1", "p18"),
        ("ERP pricing 75/125/175% of annual ≈ $188k for 36-mo on $107k premium", "MISSED BY V1", "(ERP)"),
    ],
    "sg": [
        ("Security Guard policy covers security ops only; not core election services", "Bad Risk 4", "p40"),
        ("Wrongful acts paid only under Coverage D sublimit (NOT BI/PD on Coverage A)", "Verified B1", "p24-27"),
        ("PRESENTATION G4 (slide 13) AI+P/NC at pp 59-60 — CITES OFF BY ONE; correct: pp 60 (P/NC) + 61 (AI ongoing) + sep CG 20 37 (AI completed ops)", "REVISE", "p60-61"),
        ("PRESENTATION B1 wrongful acts cite pp 23-26 — pp 23 is Canine, pp 27 has the narrow definition", "REVISE", "p27"),
        ("Cancellation 60 days (AZ state endorsement)", "Verified", "p15-16"),
    ],
    "wc": [
        ("Favorable EMR 0.690", "Good", "p61"),
        ("Multi-state with Stop Gap", "Good", "p61"),
        ("Waiver of Subrogation gap GA, NC, IL", "Bad Risk 9", "p114"),
        ("Ownership Change Reporting Obligation (PE-critical)", "Bad Risk 6", "p137"),
        ("Cancellation 30 days", "Verified", "p149"),
        ("Named Insured: 'ELECTION SERVICES INC' on 18 state schedules; Dec p57 redacted; 'RUNBECK' once", "UNDERSTATED IN PRES", "(multi-page)"),
    ],
}


# ----- assemble per slug ----------------------------------------------
def build_per_slug():
    pres = load_presentation()
    v2_text = OUT / "audited"
    v1_text = OUT / "audited_v1"
    findings_table = json.loads((OUT / "findings_table.json").read_text(encoding="utf-8"))

    for slug in SLUGS:
        v1 = load_findings(v1_text / f"{slug}.json")
        v2 = load_findings(v2_text / f"{slug}.json")
        pairs, new_v2 = match_v1_v2(v1, v2)

        # Categorize
        unchanged = [(f1, f2, sc) for f1, f2, sc in pairs if f2 is not None]
        removed   = [f1 for f1, f2, sc in pairs if f2 is None]

        # Pull v2 findings_table entries (they have category/score)
        v2_table = [f for f in findings_table if f["policy_slug"] == slug]

        # Master annots (auto only)
        master = None
        if slug in MASTER_AVAILABLE:
            mp = OUT / "originals_real" / f"{slug}.json"
            if mp.exists():
                master = json.loads(mp.read_text(encoding="utf-8"))

        # GAP-XX hits
        gap_results = []
        for gap_id, desc, kws in GAP_TESTS.get(slug, []):
            hits = search_v2(v2, kws)
            # Also search v2 highlight annots in case the keyword is on a highlighted text
            v2_full = json.loads((v2_text / f"{slug}.json").read_text(encoding="utf-8"))
            for a in v2_full["annotations"]:
                if a["type_name"] != "Highlight":
                    continue
                txt = (a.get("text_under") or "").lower()
                title = title_of(a).lower()
                if any(k.lower() in (txt + " " + title) for k in kws):
                    hits.append({
                        "page": a["page"],
                        "title": "(highlight)",
                        "snippet": (a.get("text_under") or "")[:200],
                    })
            gap_results.append({
                "gap_id": gap_id,
                "description": desc,
                "keywords": kws,
                "caught": len(hits) > 0,
                "hits": hits[:4],   # cap
            })
        # ALL-policy GAP-01
        gap_id, desc, kws = ALL_GAP_01
        all_hits = search_v2(v2, kws)
        gap_results.append({
            "gap_id": gap_id,
            "description": desc,
            "keywords": kws,
            "caught": len(all_hits) > 0,
            "hits": all_hits[:4],
        })

        out = {
            "slug": slug,
            "policy_name": POLICY_NAMES[slug],
            "sources": {
                "presentation": True,
                "prior_report": slug in PRIOR_REPORT_AVAILABLE,
                "annotation_master": slug in MASTER_AVAILABLE,
                "v1": len(v1) > 0,
                "v2": len(v2) > 0,
            },
            "v1_findings": v1,
            "v2_findings": v2,
            "v2_table_entries": v2_table,
            "v1_v2_unchanged": [{"v1": f1, "v2": f2, "similarity": round(sc, 2)} for f1, f2, sc in unchanged],
            "v1_v2_removed":   removed,
            "v1_v2_new_in_v2": new_v2,
            "presentation_slides": pres_claims_for_slug(slug, pres),
            "prior_report_claims": PRIOR_CLAIMS.get(slug, []),
            "master_annotations": master,
            "gap_xx_results": gap_results,
        }
        (OUT / "per_slug_data" / f"{slug}.json").write_text(json.dumps(out, indent=2, default=str), encoding="utf-8")
        print(f"[{slug:6s}] v1={len(v1)} v2={len(v2)} | unchanged={len(unchanged)} removed={len(removed)} new={len(new_v2)} | gap_tests={sum(1 for g in gap_results if g['caught'])}/{len(gap_results)} caught")


if __name__ == "__main__":
    build_per_slug()
    print("\nPer-slug data assembled in per_slug_data/")
