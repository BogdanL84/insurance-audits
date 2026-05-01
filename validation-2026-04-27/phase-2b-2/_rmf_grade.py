"""Re-grade v3c findings against the 86 RMF items."""
import json, sys, re
from pathlib import Path
sys.stdout.reconfigure(encoding='utf-8')

OUT = Path(r"C:\Users\Bogdan\Desktop\Run-Test Policies, Contracts\validation-2026-04-27\phase-2b-2")
findings = json.load((OUT / "findings_v3c.json").open(encoding='utf-8'))['findings']

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

def find_all(*keywords):
    kws = [k.lower() for k in keywords]
    return [f for f, b in blobs if all(k in b for k in kws)]

rmf_grade = []

# === General (5) ===
rmf_grade.append(("General-1", "90 day notice of cancellation",
    "PARTIAL" if find_any("designated entity notice of cancellation", "noc to designated", "cancellation notice") else "NOT CAUGHT"))
rmf_grade.append(("General-2", "Unintentional Errors and Omissions",
    "CAUGHT" if find_any("unintentional", "errors and omissions giveback") else "NOT CAUGHT"))
rmf_grade.append(("General-3", "Named insureds list per policy + flag missing",
    "CAUGHT" if find_any("cross-policy entity", "cross-policy named insured", "inc' vs 'llc") else "NOT CAUGHT"))
rmf_grade.append(("General-4", "Notice and Knowledge (all except umbrella)",
    "CAUGHT" if find_any("notice manager", "notice and knowledge", "imputation of knowledge") else "NOT CAUGHT"))
rmf_grade.append(("General-5", "Waiver of Subrogation",
    "CAUGHT" if find_any("blanket waiver of subrogation") else "NOT CAUGHT"))

# === CGL (33) ===
rmf_grade.append(("CGL-1",  "Additional Insured (blanket)", "CAUGHT" if find_any("additional insured ongoing", "blanket ai", "professional services carve-out", "ai includes professional") else "NOT CAUGHT"))
rmf_grade.append(("CGL-2",  "Care Custody Control (CGL)", "CAUGHT" if find_any("care, custody", "care custody") else "NOT CAUGHT"))
rmf_grade.append(("CGL-3",  "Compliance bank covenants/contracts/leases", "PARTIAL" if find_any("sacramento", "no additional exclusions") else "NOT CAUGHT"))
rmf_grade.append(("CGL-4",  "Composite Rating", "NOT CAUGHT"))
rmf_grade.append(("CGL-5",  "Contract Review procedure", "METHODOLOGY/NA"))
rmf_grade.append(("CGL-6",  "Contractual Liability + automatic AI/PNC/WoS", "CAUGHT" if find_any("contractual liability", "blanket ai", "p&nc") else "NOT CAUGHT"))
rmf_grade.append(("CGL-7",  "Contractual liability personal & advertising", "NOT CAUGHT"))
rmf_grade.append(("CGL-8",  "Coverage Territory", "NOT CAUGHT"))
rmf_grade.append(("CGL-9",  "Cyber Coverage on CGL", "CAUGHT" if find_any("cyber/data privacy", "cyber/privacy", "data privacy/bipa") else "NOT CAUGHT"))
rmf_grade.append(("CGL-10", "Damage to premises sublimit", "NOT CAUGHT"))
rmf_grade.append(("CGL-11", "Damages to Premises (Fire Legal)", "NOT CAUGHT"))
rmf_grade.append(("CGL-12", "Deductibles", "NOT CAUGHT"))
rmf_grade.append(("CGL-13", "Duty to Defend", "NOT CAUGHT"))
rmf_grade.append(("CGL-14", "EBL Coverage", "CAUGHT" if find_any("ebl", "employee benefit") else "NOT CAUGHT"))
rmf_grade.append(("CGL-15", "EPLI / Wage & Hour", "CAUGHT" if find_any("wage & hour", "wage and hour", "epli") else "NOT CAUGHT"))
rmf_grade.append(("CGL-16", "Endorsements list problematic", "METHODOLOGY/NA"))
rmf_grade.append(("CGL-17", "Environmental", "CAUGHT" if find_any("pollution") else "NOT CAUGHT"))
rmf_grade.append(("CGL-18", "Errors & Omissions / E&O", "CAUGHT" if find_any("e&o", "tech e&o", "professional liability", "delay-in-performance", "split limits") else "NOT CAUGHT"))
rmf_grade.append(("CGL-19", "Faulty Work / subcontractor giveback", "NOT CAUGHT"))
rmf_grade.append(("CGL-20", "Fellow Employee Coverage / exclusion deleted", "CAUGHT" if find_any("fellow employee") else "NOT CAUGHT"))
rmf_grade.append(("CGL-21", "Hired and Non-Owned on CGL", "CAUGHT" if find_any("hired", "non-owned") else "NOT CAUGHT"))
rmf_grade.append(("CGL-22", "Leased / temporary workers", "NOT CAUGHT"))
rmf_grade.append(("CGL-23", "Mental Anguish in BI definition", "CAUGHT" if find_any("mental anguish") else "NOT CAUGHT"))
rmf_grade.append(("CGL-24", "Named Insured (broad/subsidiaries/JVs)", "CAUGHT" if find_any("cross-policy entity", "cross-policy named insured") else "NOT CAUGHT"))
rmf_grade.append(("CGL-25", "Notice & Knowledge (officer-limited)", "NOT CAUGHT"))
rmf_grade.append(("CGL-26", "Per Location / Per Project Aggregate", "CAUGHT" if find_any("per-project", "per project") else "NOT CAUGHT"))
rmf_grade.append(("CGL-27", "Primary and Non-Contributory", "CAUGHT" if find_any("p&nc", "primary noncontributory", "primary and non-contributory") else "NOT CAUGHT"))
rmf_grade.append(("CGL-28", "Product Recall", "NOT CAUGHT"))
rmf_grade.append(("CGL-29", "Professional Coverage", "CAUGHT" if find_any("professional liability", "tech e&o", "professional services") else "NOT CAUGHT"))
rmf_grade.append(("CGL-30", "Stop Gap (CGL or WC)", "PARTIAL" if find_any("stop gap") else "NOT CAUGHT"))
rmf_grade.append(("CGL-31", "Total Pollution Exclusion", "CAUGHT" if find_any("total pollution", "pollution exclusion") else "NOT CAUGHT"))
rmf_grade.append(("CGL-32", "TRIA / terrorism", "NOT CAUGHT"))
rmf_grade.append(("CGL-33", "Waiver of Subrogation (blanket)", "CAUGHT" if find_any("blanket waiver of subrogation") else "NOT CAUGHT"))

# === CA / Auto (18) ===
rmf_grade.append(("CA-1",  "AI status — Automatic + WoS + P&NC", "CAUGHT" if find_any("auto — blanket ai", "auto — blanket", "auto blanket") else "NOT CAUGHT"))
rmf_grade.append(("CA-2",  "BI including Mental Anguish", "CAUGHT" if find_any("mental anguish") else "NOT CAUGHT"))
rmf_grade.append(("CA-3",  "Broad Named Insured + all NIs listed", "CAUGHT" if find_any("auto-only additional", "cross-policy entity") else "NOT CAUGHT"))
rmf_grade.append(("CA-4",  "Lease Gap coverage", "NOT CAUGHT"))
rmf_grade.append(("CA-5",  "Drive Other Car", "NOT CAUGHT"))
rmf_grade.append(("CA-6",  "Employee as Insured / CA 9933", "NOT CAUGHT"))
rmf_grade.append(("CA-7",  "Endorsements list", "METHODOLOGY/NA"))
rmf_grade.append(("CA-8",  "Environmental Exposures", "NOT CAUGHT"))
rmf_grade.append(("CA-9",  "Fellow Employee Exclusion", "CAUGHT" if find_any("fellow employee") else "NOT CAUGHT"))
rmf_grade.append(("CA-10", "Hired Non-Owned", "CAUGHT" if find_any("hired", "non-owned") else "NOT CAUGHT"))
rmf_grade.append(("CA-11", "No-fault states optional coverage", "NOT CAUGHT"))
rmf_grade.append(("CA-12", "Mobile Equipment vs auto", "NOT CAUGHT"))
rmf_grade.append(("CA-13", "Notice and Knowledge", "NOT CAUGHT"))
rmf_grade.append(("CA-14", "Ownership of Vehicles", "NOT CAUGHT"))
rmf_grade.append(("CA-15", "Parked Vehicles aggregate ded.", "NOT CAUGHT"))
rmf_grade.append(("CA-16", "Symbols 1/2 vs 7", "NOT CAUGHT"))
rmf_grade.append(("CA-17", "Temporary & Leased Workers", "NOT CAUGHT"))
rmf_grade.append(("CA-18", "Uninsured/Underinsured", "NOT CAUGHT"))

# Auto-line-specific extras (the v3c findings include strong Auto items that map to RMF items above)
# CA-1, CA-2, CA-3, CA-9, CA-10 caught above. Plus:
# - Maricopa Auto $2M shortfall is a separate finding (not strictly an RMF item)
# - Designated Entity NOC for Auto (not strictly RMF item, ties to General-1)

# === UMB (14) ===
rmf_grade.append(("UMB-1",  "Endorsements list", "METHODOLOGY/NA"))
rmf_grade.append(("UMB-2",  "Exclusions / non-follow-form", "CAUGHT" if find_any("umbrella — cyber", "umbrella excludes", "cyber/privacy exclusions strip") else "NOT CAUGHT"))
rmf_grade.append(("UMB-3",  "Horizontal exhaustion / P&NC + WoS follow form", "PARTIAL" if find_any("verify p&nc", "follow form") else "NOT CAUGHT"))
rmf_grade.append(("UMB-4",  "Insureds — AI follow form, NIs same as underlying", "CAUGHT" if find_any("multiple named insured", "schedule of underlying", "umbrella schedule") else "NOT CAUGHT"))
rmf_grade.append(("UMB-5",  "Defense inside vs outside limits", "NOT CAUGHT"))
rmf_grade.append(("UMB-6",  "Maintenance of underlying", "NOT CAUGHT"))
rmf_grade.append(("UMB-7",  "Notice and knowledge", "NOT CAUGHT"))
rmf_grade.append(("UMB-8",  "Per Project Aggregate / Per Location", "PARTIAL" if find_any("per-project", "per project") else "NOT CAUGHT"))
rmf_grade.append(("UMB-9",  "Professional Liability follow-form", "CAUGHT" if find_any("umbrella — cyber/privacy", "professional liability") else "NOT CAUGHT"))
rmf_grade.append(("UMB-10", "Punitive damages excluded", "NOT CAUGHT"))
rmf_grade.append(("UMB-11", "Right and Duty when underlying exhausted", "NOT CAUGHT"))
rmf_grade.append(("UMB-12", "Total Pollution Exclusion (umbrella)", "PARTIAL" if find_any("pollution") else "NOT CAUGHT"))
rmf_grade.append(("UMB-13", "Underlying Policies all listed", "CAUGHT" if find_any("schedule of underlying", "umbrella schedule") else "NOT CAUGHT"))
rmf_grade.append(("UMB-14", "Specific follow-form concerns", "PARTIAL" if find_any("verify p&nc", "follow form") else "NOT CAUGHT"))

# === WC (16) ===
rmf_grade.append(("WC-1",  "Small indemnity claims / back-to-work", "NOT CAUGHT"))
rmf_grade.append(("WC-2",  "Small med claims", "NOT CAUGHT"))
rmf_grade.append(("WC-3",  "All States Endorsement (3.A vs 3.C)", "CAUGHT" if find_any("multi-state", "stop gap", "all states") else "NOT CAUGHT"))
rmf_grade.append(("WC-4",  "(Intentionally Left Blank)", "METHODOLOGY/NA"))
rmf_grade.append(("WC-5",  "Alternate Employee Endorsement", "NOT CAUGHT"))
rmf_grade.append(("WC-6",  "EL Limits adequate to support Umbrella", "CAUGHT" if find_any("employer's liability", "employers liability", "el limits") else "NOT CAUGHT"))
rmf_grade.append(("WC-7",  "Endemic Disease / Foreign Voluntary", "NOT CAUGHT"))
rmf_grade.append(("WC-8",  "Experience Modification", "NOT CAUGHT"))
rmf_grade.append(("WC-9",  "Maritime coverage", "NOT CAUGHT"))
rmf_grade.append(("WC-10", "Large claims by name", "NOT CAUGHT"))
rmf_grade.append(("WC-11", "All possible credits", "NOT CAUGHT"))
rmf_grade.append(("WC-12", "Owners Excluded", "NOT CAUGHT"))
rmf_grade.append(("WC-13", "DBA included", "NOT CAUGHT"))
rmf_grade.append(("WC-14", "USL&H", "NOT CAUGHT"))
rmf_grade.append(("WC-15", "Classification codes correct", "PARTIAL" if find_any("classification", "indiana") else "NOT CAUGHT"))
rmf_grade.append(("WC-16", "Waiver of Subrogation", "CAUGHT" if find_any("workers' comp wos", "wc — wos", "wc wos", "blanket waiver") else "NOT CAUGHT"))

caught = sum(1 for _, _, v in rmf_grade if v == "CAUGHT")
partial = sum(1 for _, _, v in rmf_grade if v == "PARTIAL")
not_caught = sum(1 for _, _, v in rmf_grade if v == "NOT CAUGHT")
methodology = sum(1 for _, _, v in rmf_grade if v == "METHODOLOGY/NA")
total = len(rmf_grade)
finding_emittable = total - methodology

print(f"=== RMF SCORECARD v3c ===")
print(f"Total items: {total}")
print(f"  Methodology/NA:    {methodology}")
print(f"  Finding-emittable: {finding_emittable}")
print()
print(f"  CAUGHT:        {caught:3d} ({100*caught//finding_emittable}%)")
print(f"  PARTIAL:       {partial:3d} ({100*partial//finding_emittable}%)")
print(f"  NOT CAUGHT:    {not_caught:3d} ({100*not_caught//finding_emittable}%)")
print()
print(f"  Coverage (caught + partial): {caught + partial}/{finding_emittable} = "
      f"{100*(caught+partial)//finding_emittable}%")
print(f"  Strict CAUGHT:               {caught}/{finding_emittable} = {100*caught//finding_emittable}%")
print()

from collections import Counter, defaultdict
by_tab = defaultdict(lambda: Counter())
for tag, _, verdict in rmf_grade:
    tab = tag.split('-')[0]
    by_tab[tab][verdict] += 1

print("=== Per-tab breakdown ===")
print(f"{'Tab':<8} {'C':>3} {'P':>3} {'N':>3} {'NA':>3}  {'%C+P':>5}")
for tab in ['General', 'CGL', 'CA', 'UMB', 'WC']:
    c = by_tab[tab]['CAUGHT']
    p = by_tab[tab]['PARTIAL']
    n = by_tab[tab]['NOT CAUGHT']
    na = by_tab[tab]['METHODOLOGY/NA']
    fe = c + p + n
    pct = 100 * (c+p) // fe if fe else 0
    print(f"{tab:<8} {c:>3} {p:>3} {n:>3} {na:>3}  {pct:>4}%")

(OUT / "_rmf_grade_v3c.json").write_text(
    json.dumps([{"tag": t, "item": i, "verdict": v} for t, i, v in rmf_grade], indent=2),
    encoding='utf-8',
)
print(f"\nSaved per-item grade to _rmf_grade_v3c.json")

# Show the not-caught items so we know exactly what's missing
print()
print("=== Not-caught RMF items ===")
for tag, item, verdict in rmf_grade:
    if verdict == "NOT CAUGHT":
        print(f"  ❌ {tag:<10} — {item}")
