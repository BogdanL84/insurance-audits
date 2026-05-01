# Phase 4 — Contract-Match Overlay

Cross-reference each upstream contract's insurance requirements against the v2 audit findings. Specifically tests whether **GAP-17 (contract-specific coverage satisfaction)** and **GAP-21 (designated entity NOC)** are firing.

## Source contracts (4 files in `Upstream Contracts/`)

| File | Insurance provisions | Notes |
|---|---|---|
| `Redactedscrubbed - Maricopa Contract.pdf` | ✅ Full §8.1–8.2 (pp 5–7) | The most demanding contract |
| `RedactedAppendix G - Sacramento County Minimum Insurance Requirements.pdf` | ✅ Full Appendix G | 4-page standalone insurance schedule |
| `Redacted12.11.24_City and County of Los Angeles California Renewal_Fully Executed.pdf` | ❌ None | This is Amendment #4 only — base contract's insurance provisions not in this file |
| `Redacted12162026_Douglas County Colorado_2026 Renewal Print & Mail.pdf` | ❌ None | Print & mail order, no insurance schedule |

### App's contract-requirement extraction
The app's pre-extracted file `run-test-election-services-contract-requirements.json` shows:
```json
{ "source_file": "...LA County...pdf", "requirements": [], "notes": "no insurance provisions in this amendment" }
```

**Only the LA County contract was processed by the app's contract extraction step. Maricopa, Sacramento, and Douglas County were skipped.** This is a precondition failure for every GAP-17 / GAP-21 check that follows — the app cannot cross-reference what it never extracted.

---

## Maricopa County — full requirements

| § | Requirement | Limit/Term |
|---|---|---|
| 8.2.1 | Carrier rating | A.M. Best B++ minimum |
| 8.2.4 | Primary, non-contributory | All policies |
| 8.2.7 | Additional Insured (County, agents, reps, officers, directors, officials, employees) | All except WC and E&O |
| 8.2.8 | Waiver of Subrogation against County | All except WC and E&O |
| 8.2.9 | Umbrella may combine to meet limits | COI must indicate which lines umbrella covers |
| 8.2.10 | CGL + Umbrella if necessary | $2M each occurrence / $4M Products-CompOps Agg / $4M Gen Agg |
| 8.2.11 | Auto Liability — owned, hired, non-owned | **$2M CSL each occurrence** (no inline umbrella attachment language — distinct from CGL clause structure) |
| 8.2.12 | WC statutory + Employer's Liability | $1M / $1M / $1M |
| 8.2.13 | Cyber, Network Security, and Privacy Liability | **$5M per occurrence** with extensive scope (data breach, regulatory defense, cyber extortion, business interruption, funds transfer, third-party fidelity) |
| 8.2.14 | Certificates of Insurance | Identify Maricopa County as cert holder; renewal cert 15 days before expiration |
| 8.2.15 | Cancellation/Expiration Notice | **30 days prior written notice to Maricopa County**; Contractor must notify County within 2 business days of receipt |

## Sacramento County (Appendix G) — full requirements

| § | Requirement | Limit/Term |
|---|---|---|
| II.A | CGL form CG 0001 | Premises/Ops, Prods/CompOps, Contractual, Personal & Adv Injury |
| II.B | Auto form CA 0001 | Symbol 1 (any auto) for owned; Symbols 8+9 for non-owned + hired if no owned |
| II.C | WC statutory CA + EL | |
| II.D | PL/E&O | "appropriate to the contractor's profession" |
| II.E | Umbrella/Excess | At least follow-form over CGL, Auto, EL **(NOT over PL)** |
| III.A | CGL minimums | $2M Building Trades Gen Agg / $2M Prods-CompOps / $1M Pers&Adv / $1M Each Occ / $100K Fire; **CG-2503 per-project agg** for construction-style work |
| III.B | Auto minimums | **$1M CSL** for corp; for individually-owned $250K/$500K/$100K |
| III.C/D | WC + EL | Statutory + $1M EL per accident |
| III.E | PL minimum | $1M per claim and aggregate |
| VI.A.1 | Carrier rating | **A.M. Best A-VII minimum** (stricter than Maricopa's B++) |
| VI.A.2 | Maintenance | Renewal evidence 10 days before anniversary; **immediate notification of cancellation/non-renewal/material change** |
| VII.A | Additional Insured | County + officers/directors/officials/employees/volunteers (CGL + Auto) |
| VII.C | Primary insurance | Required |
| VIII | WC Waiver of Subrogation | Required |
| IX | Property/Inland Marine WOS | Required |

---

## Compliance check — policy-by-policy contract gaps

### 1. **Hanover Auto vs Maricopa $2M CSL** — GAP-17 critical test

| | |
|---|---|
| Contract requires | **$2M CSL each occurrence (Maricopa §8.2.11)** |
| Policy provides | **$1M CSL primary** (per master pg 24 highlight: `LIABILITY $1,000,000 COMBINED SINGLE LIMIT`) |
| Hanover Umbrella mitigation? | $10M umbrella above — but Maricopa §8.2.11 has no inline umbrella attachment language (unlike §8.2.10 for CGL). Master sticky note pg 24: *"contract DOES NOT state that auto limits can be met via use of an Umbrella. ((states so for GL but not Auto))"* |
| **App v2 catch?** | ❌ **MISSED** — no v2 finding addresses this |
| **GAP-17 verdict** | ❌ **MISSED**. The KB file `knowledge-base/universal/GAP-17-contract-specific-coverage-satisfaction.md` literally references this as its example case. Contract not extracted → cross-reference impossible → catch chain broken. |

### 2. **AmTrust Cyber vs Maricopa $5M** — GAP-22c critical test

| | |
|---|---|
| Contract requires | **$5M Cyber per occurrence (Maricopa §8.2.13)** |
| Policy provides | **$4M aggregate** (per presentation slide 32) |
| Mitigation? | None — Hanover Umbrella explicitly excludes Cyber (per umb v2 finding pg 31) |
| **App v2 catch?** | ❌ **MISSED** — no v2 finding mentions Maricopa $5M or aggregate shortfall |
| **GAP-17/GAP-22c verdict** | ❌ **MISSED**. Same root cause as Auto — no contract extraction. |

### 3. **Hanover Auto + Pkg cancellation notice vs Maricopa 30-day** — GAP-21 test

| Policy | Cancellation notice (per presentation slide 18) | Maricopa §8.2.15 requires | Contract pass/fail |
|---|---|---|---|
| Auto | 30 days | 30 days | ⚠ Just barely passes — no margin |
| Commercial Pkg | 45 days | 30 days | ✓ Passes |
| Umbrella | 60 days | 30 days | ✓ Passes |
| WC | 30 days | 30 days | ⚠ Just barely passes |
| ML | 10 days (non-pay) / 20 days (other per PP00H10700) | 30 days | ❌ **FAILS** |
| PL/E&O | 60 days | 30 days | ✓ Passes |
| SG | 60 days (AZ state endorsement) | 30 days | ✓ Passes |
| Cyber | (not specified in presentation) | 30 days | ⚠ Verify |

**GAP-21 (Designated Entity NOC):** Per prior context, Hanover Commercial Package has form 401-1235 (Designated Entity NOC) listing 8 customer counties with 30-day notice. Hanover Auto does NOT include any equivalent Designated Entity NOC endorsement. The 401-1235 asymmetry across Pkg vs Auto is exactly the cross-policy pattern GAP-21 KB file targets.

| App v2 catch | ❌ **MISSED** on every policy |
| **GAP-21 verdict** | ❌ **MISSED across the program.** No v2 finding addresses cancellation notice or Designated Entity NOC for any policy. |

### 4. **Sacramento Auto $1M CSL** — GAP-17 secondary test

| | |
|---|---|
| Contract requires | $1M CSL (Sacramento §III.B.1) |
| Policy provides | $1M CSL primary |
| **GAP-17 verdict** | ✓ **PASSES** — coverage matches; nothing for app to catch here |

### 5. **Sacramento Per-Project Aggregate (CG-2503)** — partial test

| | |
|---|---|
| Contract requires | CG-2503 per-project aggregate "for construction-style work" |
| Policy provides | Per-Project structure with $2M policy aggregate cap (per v2 pkg pg 205) |
| **App v2 catch?** | ⚠ **PARTIAL** — v2 pkg pg 205 catches the $2M cap as a structural defect (Bad/6) but doesn't tie it to Sacramento's CG-2503 requirement |
| **GAP-17 verdict** | PARTIAL — defect identified, contract linkage missing |

### 6. **Sacramento PL retro date / ERP** — partial test

| | |
|---|---|
| Contract requires | Retro before contract effective; 1-year ERP if not replaced |
| Policy provides | Base retro 03/27/2017; **mail processing split retro 04/01/2021** (per v2 pl pg 20) |
| **App v2 catch?** | ⚠ **PARTIAL** — v2 catches the split retro date (Ugly/15) but doesn't cross-reference whether 4/1/2021 predates each county contract effective date. If a Sacramento (or other) contract was effective before 4/1/2021, mail processing claims pre-contract are uninsured. |
| **GAP-17 verdict** | PARTIAL — defect identified, contract effective-date cross-check missing |

### 7. **Maricopa AI / WOS requirement** — comprehensive miss

| | |
|---|---|
| Contract requires | AI for Maricopa (CGL, Auto, Umbrella, ML, Cyber); WOS for same; Primary/Noncontributory |
| **App v2 findings on AI scope?** | ❌ **MISSED** on every policy. PL handoff notes AI is "defense only no indemnity" with "solely arising" qualifier — major gap. v2 silent. |
| **App v2 findings on WOS scope?** | ⚠ Partial — v2 wc pg 114 catches WOS gap in GA/NC/IL but doesn't cross-reference Maricopa contract specifically |
| **App v2 findings on Primary/NC?** | ❌ Not surfaced anywhere |
| **GAP-17 verdict** | ❌ **MISSED** for AI scope, ⚠ PARTIAL for WOS, ❌ MISSED for Primary/NC |

### 8. **Carrier rating** — silent

| | |
|---|---|
| Maricopa | A.M. Best B++ minimum |
| Sacramento | A.M. Best A-VII minimum |
| **App v2 catch?** | ❌ **MISSED** — no v2 finding addresses carrier rating against either contract. (Also: Gemini PL is surplus lines per handoff; AZ guaranty fund disclaimer — uncaught either.) |

---

## GAP-17 / GAP-21 Scorecard

| Test | Status | Note |
|---|---|---|
| GAP-17 — Maricopa Auto $2M CSL | ❌ **MISSED** | Master flagged it explicitly; v2 silent |
| GAP-17 — Maricopa Cyber $5M | ❌ **MISSED** | Presentation slide 32 flagged it; v2 silent |
| GAP-17 — Sacramento Auto $1M | ✓ N/A — passes | |
| GAP-17 — Sacramento Per-Project (CG-2503) | ⚠ PARTIAL | Defect found, not contract-linked |
| GAP-17 — Sacramento PL retro / ERP | ⚠ PARTIAL | Defect found, contract date not cross-referenced |
| GAP-17 — Maricopa AI/WOS/PNC | ❌ **MISSED** | No per-policy AI scope finding |
| GAP-17 — Carrier rating | ❌ **MISSED** | |
| GAP-21 — 401-1235 Designated Entity NOC asymmetry (Pkg has it, Auto doesn't) | ❌ **MISSED** | |
| GAP-21 — Maricopa 30-day notice across all policies | ❌ **MISSED** | ML fails outright (10/20 days); not surfaced |

**GAP-17 / GAP-21 net scorecard: 0 CAUGHT / 3 PARTIAL / 6 MISSED.**

## Root cause

**The app's contract extraction step processed only 1 of 4 contracts (LA County) and found 0 insurance requirements** because it received the amendment, not the base contract. Maricopa and Sacramento — the two contracts with substantive insurance requirements — were never extracted into the requirements JSON.

**This is a precondition failure for the entire GAP-17 / GAP-21 catch chain.** No matter how well the KB files are written, no contract-vs-policy comparison can fire if the contract requirements aren't extracted. This is the single most impactful fix for Phase 5's punch list.

## Recommended remediation

1. **Re-run contract extraction on the Maricopa and Sacramento PDFs** explicitly — the contract-extraction prompt likely needs to handle multi-page schedules and indemnification-then-insurance section structure.
2. **Add a contract-extraction-completeness check** — if `requirements: []` and the source file is >10 pages, flag for manual re-run rather than silently proceeding.
3. **GAP-17 KB file should require contract data as a precondition** — log a warning when GAP-17 cross-reference runs against an empty requirements set.
4. **Manually-curated contract requirements JSON** for Maricopa + Sacramento as a backstop until the extraction is reliable.
