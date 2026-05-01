"""Tag-aware RMF grader. Runs alongside _rmf_grade.py.

Background: _rmf_grade.py uses substring keyword matching against finding
text. The K+L always-emit prompt instructions cause findings to carry
explicit `rmf-XX-N` tags (e.g., `rmf-ca-1`, `rmf-cgl-23`), but the keyword
grader doesn't recognize tags directly. Result: K+L-emitted findings can be
undercounted because their tag-tagged content doesn't always include the
specific keywords the grader looks for.

This grader credits an item as CAUGHT if EITHER:
  (a) the keyword grader finds it, OR
  (b) ANY finding has a tag matching `rmf-{tag-lower}` (e.g., `rmf-ca-1`)

Usage:
  python -c "
  src = open('_rmf_grade_tag_aware.py').read().replace('FINDINGS_FILE', 'findings_v3e.json')
  exec(src)
  "
"""
import json, sys
from pathlib import Path
from collections import Counter, defaultdict

sys.stdout.reconfigure(encoding='utf-8')

OUT = Path(r"C:\Users\Bogdan\Desktop\Run-Test Policies, Contracts\validation-2026-04-27\phase-2b-2")

# Default to findings_v3e.json; can be overridden via env var
FINDINGS_FILE = "FINDINGS_FILE"  # placeholder — exec() will replace
import os
findings_path = OUT / os.environ.get("RMF_FINDINGS", FINDINGS_FILE)
findings = json.load(findings_path.open(encoding='utf-8'))['findings']

# Step 1: keyword grade (replicate _rmf_grade.py logic inline)
def blob_of(f):
    return ' '.join([
        (f.get('requirement_type','') or '').lower(),
        (f.get('plain_english','')   or '').lower(),
        (f.get('gap_description','') or '').lower(),
        (f.get('contract_quote','')  or '').lower(),
        (f.get('policy_quote','')    or '').lower(),
        ' '.join(f.get('tags', []) or []).lower(),
    ])

blobs = [(f, blob_of(f)) for f in findings]

def find_any(*keywords):
    kws = [k.lower() for k in keywords]
    return [f for f, b in blobs if any(k in b for k in kws)]

# Step 2: tag-based credit — find any finding with rmf-XX-N tag
tag_index = defaultdict(list)
for f in findings:
    for tag in (f.get('tags') or []):
        tlow = tag.lower()
        if tlow.startswith('rmf-'):
            tag_index[tlow].append(f)

def has_tag(*tag_options):
    for t in tag_options:
        if tag_index.get(t.lower()):
            return tag_index[t.lower()]
    return []

# Replicate the _rmf_grade.py items but add tag-based check to each
rmf = []
def add(tag, desc, kw_caught, kw_partial=None):
    """Add an RMF entry with both keyword and tag-based credit."""
    rmf_tag_keys = [f"rmf-{tag.lower()}", f"rmf-{tag.lower().replace('-','')}"]
    tag_hits = has_tag(*rmf_tag_keys)
    kw_verdict = kw_caught
    final = kw_verdict
    if final == "NOT CAUGHT" and tag_hits:
        final = "CAUGHT (tag)"
    rmf.append((tag, desc, kw_verdict, len(tag_hits), final))

# General (5)
add("General-1", "90 day notice of cancellation",
    "PARTIAL" if find_any("designated entity notice of cancellation", "noc to designated", "cancellation notice") else "NOT CAUGHT")
add("General-2", "Unintentional Errors and Omissions",
    "CAUGHT" if find_any("unintentional", "errors and omissions giveback") else "NOT CAUGHT")
add("General-3", "Named insureds list per policy + flag missing",
    "CAUGHT" if find_any("cross-policy entity", "cross-policy named insured", "inc' vs 'llc") else "NOT CAUGHT")
add("General-4", "Notice and Knowledge (all except umbrella)",
    "CAUGHT" if find_any("notice manager", "notice and knowledge", "imputation of knowledge") else "NOT CAUGHT")
add("General-5", "Waiver of Subrogation",
    "CAUGHT" if find_any("blanket waiver of subrogation") else "NOT CAUGHT")

# CGL (33)
add("CGL-1",  "Additional Insured (blanket)", "CAUGHT" if find_any("additional insured ongoing", "blanket ai", "professional services carve-out", "ai includes professional") else "NOT CAUGHT")
add("CGL-2",  "Care Custody Control (CGL)", "CAUGHT" if find_any("care, custody", "care custody") else "NOT CAUGHT")
add("CGL-3",  "Compliance bank covenants/contracts/leases", "PARTIAL" if find_any("sacramento", "no additional exclusions") else "NOT CAUGHT")
add("CGL-4",  "Composite Rating", "NOT CAUGHT")
add("CGL-5",  "Contract Review procedure", "METHODOLOGY/NA")
add("CGL-6",  "Contractual Liability + automatic AI/PNC/WoS", "CAUGHT" if find_any("contractual liability", "blanket ai", "p&nc") else "NOT CAUGHT")
add("CGL-7",  "Contractual liability personal & advertising", "NOT CAUGHT")
add("CGL-8",  "Coverage Territory", "NOT CAUGHT")
add("CGL-9",  "Cyber Coverage on CGL", "CAUGHT" if find_any("cyber/data privacy", "cyber/privacy", "data privacy/bipa") else "NOT CAUGHT")
add("CGL-10", "Damage to premises sublimit", "NOT CAUGHT")
add("CGL-11", "Damages to Premises (Fire Legal)", "NOT CAUGHT")
add("CGL-12", "Deductibles", "NOT CAUGHT")
add("CGL-13", "Duty to Defend", "NOT CAUGHT")
add("CGL-14", "EBL Coverage", "CAUGHT" if find_any("ebl", "employee benefit") else "NOT CAUGHT")
add("CGL-15", "EPLI / Wage & Hour", "CAUGHT" if find_any("wage & hour", "wage and hour", "epli") else "NOT CAUGHT")
add("CGL-16", "Endorsements list problematic", "METHODOLOGY/NA")
add("CGL-17", "Environmental", "CAUGHT" if find_any("pollution") else "NOT CAUGHT")
add("CGL-18", "Errors & Omissions / E&O", "CAUGHT" if find_any("e&o", "tech e&o", "professional liability", "delay-in-performance", "split limits") else "NOT CAUGHT")
add("CGL-19", "Faulty Work / subcontractor giveback", "NOT CAUGHT")
add("CGL-20", "Fellow Employee Coverage / exclusion deleted", "CAUGHT" if find_any("fellow employee") else "NOT CAUGHT")
add("CGL-21", "Hired and Non-Owned on CGL", "CAUGHT" if find_any("hired", "non-owned") else "NOT CAUGHT")
add("CGL-22", "Leased / temporary workers", "NOT CAUGHT")
add("CGL-23", "Mental Anguish in BI definition", "CAUGHT" if find_any("mental anguish") else "NOT CAUGHT")
add("CGL-24", "Named Insured (broad/subsidiaries/JVs)", "CAUGHT" if find_any("cross-policy entity", "cross-policy named insured") else "NOT CAUGHT")
add("CGL-25", "Notice & Knowledge (officer-limited)", "NOT CAUGHT")
add("CGL-26", "Per Location / Per Project Aggregate", "CAUGHT" if find_any("per-project", "per project") else "NOT CAUGHT")
add("CGL-27", "Primary and Non-Contributory", "CAUGHT" if find_any("p&nc", "primary noncontributory", "primary and non-contributory") else "NOT CAUGHT")
add("CGL-28", "Product Recall", "NOT CAUGHT")
add("CGL-29", "Professional Coverage", "CAUGHT" if find_any("professional liability", "tech e&o", "professional services") else "NOT CAUGHT")
add("CGL-30", "Stop Gap (CGL or WC)", "PARTIAL" if find_any("stop gap") else "NOT CAUGHT")
add("CGL-31", "Total Pollution Exclusion", "CAUGHT" if find_any("total pollution", "pollution exclusion") else "NOT CAUGHT")
add("CGL-32", "TRIA / terrorism", "NOT CAUGHT")
add("CGL-33", "Waiver of Subrogation (blanket)", "CAUGHT" if find_any("blanket waiver of subrogation") else "NOT CAUGHT")

# CA (18)
add("CA-1",  "AI status — Automatic + WoS + P&NC", "CAUGHT" if find_any("auto — blanket ai", "auto — blanket", "auto blanket") else "NOT CAUGHT")
add("CA-2",  "BI including Mental Anguish", "CAUGHT" if find_any("mental anguish") else "NOT CAUGHT")
add("CA-3",  "Broad NI / NIs listed (Auto)", "CAUGHT" if find_any("auto cross-policy entity", "auto named insured") else "NOT CAUGHT")
add("CA-4",  "Lease Gap coverage", "NOT CAUGHT")
add("CA-5",  "Drive Other Car", "NOT CAUGHT")
add("CA-6",  "Employee as Insured / CA 9933", "NOT CAUGHT")
add("CA-7",  "Endorsements list (Auto)", "METHODOLOGY/NA")
add("CA-8",  "Environmental Exposures", "NOT CAUGHT")
add("CA-9",  "Fellow Employee (Auto)", "CAUGHT" if find_any("fellow employee") else "NOT CAUGHT")
add("CA-10", "HNOA on Auto", "CAUGHT" if find_any("hired", "non-owned") else "NOT CAUGHT")
add("CA-11", "No-fault states optional coverage", "NOT CAUGHT")
add("CA-12", "Mobile Equipment vs auto", "NOT CAUGHT")
add("CA-13", "Notice and Knowledge (Auto)", "NOT CAUGHT")
add("CA-14", "Ownership of Vehicles", "NOT CAUGHT")
add("CA-15", "Parked Vehicles aggregate ded.", "NOT CAUGHT")
add("CA-16", "Symbols 1/2 vs 7", "NOT CAUGHT")
add("CA-17", "Temporary & Leased Workers (Auto)", "NOT CAUGHT")
add("CA-18", "Uninsured/Underinsured", "NOT CAUGHT")

# UMB (13)
add("UMB-1",  "Acceptable carrier rating", "PARTIAL" if find_any("ratings of underlying", "carrier ratings") else "NOT CAUGHT")
add("UMB-2",  "Exclusions / non-follow-form", "CAUGHT" if find_any("non follow-form", "follow-form", "umbrella does not follow") else "NOT CAUGHT")
add("UMB-3",  "Aggregates and Per Project", "CAUGHT" if find_any("aggregate non-reinstat", "aggregate erosion", "no reinstatement") else "NOT CAUGHT")
add("UMB-4",  "Coordinate w/ all upstream contracts", "METHODOLOGY/NA")
add("UMB-5",  "Defense inside vs outside limits", "NOT CAUGHT")
add("UMB-6",  "Maintenance of underlying", "NOT CAUGHT")
add("UMB-7",  "Notice and knowledge", "NOT CAUGHT")
add("UMB-8",  "Pollution Exclusion (Umbrella)", "PARTIAL" if find_any("pollution exclusion") else "NOT CAUGHT")
add("UMB-9",  "Primary and Non-Contributory (Umbrella)", "CAUGHT" if find_any("p&nc", "primary noncontributory") else "NOT CAUGHT")
add("UMB-10", "Punitive damages excluded", "NOT CAUGHT")
add("UMB-11", "Right and Duty when underlying exhausted", "NOT CAUGHT")
add("UMB-12", "Schedule of Underlying", "PARTIAL" if find_any("schedule of underlying", "underlying limit") else "NOT CAUGHT")
add("UMB-13", "Self-Insured Retention (SIR)", "CAUGHT" if find_any("sir", "self-insured retention", "self insured retention") else "NOT CAUGHT")

# WC (16)
add("WC-1",  "Small indemnity claims / back-to-work", "NOT CAUGHT")
add("WC-2",  "Small med claims", "NOT CAUGHT")
add("WC-3",  "All States Endorsement / 3.A vs 3.C", "CAUGHT" if find_any("all states", "item 3.a", "3.a vs 3.c", "missing state") else "NOT CAUGHT")
add("WC-4",  "Intentionally Left Blank", "METHODOLOGY/NA")
add("WC-5",  "Alternate Employee Endorsement", "NOT CAUGHT")
add("WC-6",  "EL Limits", "CAUGHT" if find_any("employer's liability", "employer's liability limits", "el limit") else "NOT CAUGHT")
add("WC-7",  "Endemic Disease / Foreign Voluntary", "NOT CAUGHT")
add("WC-8",  "Experience Modification", "NOT CAUGHT")
add("WC-9",  "Maritime coverage", "NOT CAUGHT")
add("WC-10", "Large claims by name", "NOT CAUGHT")
add("WC-11", "All possible credits", "NOT CAUGHT")
add("WC-12", "Owners Excluded", "NOT CAUGHT")
add("WC-13", "DBA included", "NOT CAUGHT")
add("WC-14", "USL&H", "NOT CAUGHT")
add("WC-15", "Classification codes correct", "PARTIAL" if find_any("classification code", "class code") else "NOT CAUGHT")
add("WC-16", "Waiver of Subrogation (WC)", "CAUGHT" if find_any("blanket waiver of subrogation") else "NOT CAUGHT")

# Summary
print(f"=== TAG-AWARE RMF GRADE: {findings_path.name} ===")
print(f"Total items: {len(rmf)}")
print()

# By verdict (using FINAL — combined keyword + tag)
caught_kw      = sum(1 for _,_,kw,_,_ in rmf if kw == "CAUGHT")
partial_kw     = sum(1 for _,_,kw,_,_ in rmf if kw == "PARTIAL")
caught_final   = sum(1 for _,_,_,_,fn in rmf if fn in ("CAUGHT", "CAUGHT (tag)"))
partial_final  = sum(1 for _,_,_,_,fn in rmf if fn == "PARTIAL")
methodology    = sum(1 for _,_,_,_,fn in rmf if fn == "METHODOLOGY/NA")
total          = len(rmf)
fe             = total - methodology

print(f"  Finding-emittable: {fe}")
print()
print(f"  Keyword-only: CAUGHT {caught_kw} + PARTIAL {partial_kw} = {caught_kw + partial_kw}/{fe} = {100*(caught_kw+partial_kw)//fe}%")
print(f"  Tag-aware:    CAUGHT {caught_final} + PARTIAL {partial_final} = {caught_final + partial_final}/{fe} = {100*(caught_final+partial_final)//fe}%")
print()

# Per-tab breakdown (using FINAL verdict)
by_tab = defaultdict(lambda: Counter())
for tag, _, _, _, fn in rmf:
    tab = tag.split('-')[0]
    by_tab[tab][fn] += 1

print("=== Per-tab breakdown (tag-aware) ===")
print(f"{'Tab':<8} {'C':>3} {'C-tag':>6} {'P':>3} {'N':>3} {'NA':>3}  {'%C+P':>5}")
for tab in ['General', 'CGL', 'CA', 'UMB', 'WC']:
    c    = by_tab[tab]['CAUGHT']
    ctag = by_tab[tab]['CAUGHT (tag)']
    p    = by_tab[tab]['PARTIAL']
    n    = by_tab[tab]['NOT CAUGHT']
    na   = by_tab[tab]['METHODOLOGY/NA']
    fe_t = c + ctag + p + n
    pct  = 100 * (c + ctag + p) // fe_t if fe_t else 0
    print(f"{tab:<8} {c:>3} {ctag:>6} {p:>3} {n:>3} {na:>3}  {pct:>4}%")

# Save per-item grade
out_path = OUT / f"_rmf_grade_tag_aware_{findings_path.stem}.json"
out_path.write_text(
    json.dumps([{"tag": t, "item": i, "kw_verdict": kw, "tag_hits": th, "final": fn}
                for t, i, kw, th, fn in rmf], indent=2),
    encoding='utf-8',
)
print(f"\nSaved: {out_path.name}")

# Always-emit completeness for K+L
print()
print("=== K+L always-emit completeness check ===")
kl_items = [
    "General-2", "General-4",
    "CGL-2", "CGL-10", "CGL-13", "CGL-20", "CGL-23", "CGL-25", "CGL-32",
    "CA-1", "CA-2", "CA-3", "CA-6", "CA-8", "CA-9", "CA-10", "CA-12", "CA-13", "CA-14", "CA-16", "CA-17", "CA-18",
    "UMB-5", "UMB-6", "UMB-10", "UMB-11",
    "WC-1", "WC-2", "WC-3", "WC-5", "WC-6", "WC-8", "WC-10", "WC-11", "WC-12", "WC-15", "WC-16",
]
rmf_by_tag = {t: (i, kw, th, fn) for t, i, kw, th, fn in rmf}
hits, misses = 0, 0
for kl in kl_items:
    if kl in rmf_by_tag:
        i, kw, th, fn = rmf_by_tag[kl]
        marker = "OK" if fn in ("CAUGHT", "CAUGHT (tag)", "PARTIAL") else "MISS"
        if marker == "OK":
            hits += 1
        else:
            misses += 1
        print(f"  [{marker:<4}] {kl:<10} {fn:<14} (tag_hits={th}) - {i[:50]}")
    else:
        print(f"  [???] {kl:<10} not in grader")
print(f"K+L always-emit: {hits}/{len(kl_items)} hit, {misses} miss")

# Conditional N/A check
print()
print("=== Conditional N/A items (should appear with category=Good and 'N/A' in content) ===")
conditional = ["CA-4", "CA-5", "CA-11", "CA-15", "WC-7", "WC-9", "WC-13", "WC-14"]
na_hits = 0
for c_tag in conditional:
    rmf_tag_lc = f"rmf-{c_tag.lower()}"
    matched = tag_index.get(rmf_tag_lc, [])
    if matched:
        # Check if any are N/A Goods
        na_findings = [f for f in matched if f.get("category") == "Good" and any(
            kw in (f.get("plain_english","") + f.get("gap_description","") + f.get("requirement_type","")).lower()
            for kw in ["n/a", "not applicable", "no exposure", "no leased", "no exec", "no operations", "no fleet", "no foreign", "no maritime", "no dba", "no longshore", "no harbor"]
        )]
        if na_findings:
            print(f"  [N/A-Good] {c_tag:<8}  ({len(na_findings)} N/A-Good finding(s))")
            na_hits += 1
        else:
            print(f"  [emitted but not N/A] {c_tag:<8}  ({len(matched)} finding(s); category(s): {[f.get('category') for f in matched]})")
    else:
        print(f"  [MISS] {c_tag:<8}  no rmf-{c_tag.lower()} tagged finding")
print(f"Conditional N/A: {na_hits}/{len(conditional)} emitted as N/A-Good")
