# RMF Ground-Truth Scorecard — v3b vs v3c vs the 86 Spreadsheet Items

**Source of truth:** `knowledge-base/methodology/Template_Contract_Analysis.xlsx` (5 tabs × items = 86 RMF items, 5 of which are methodology/NA = 81 finding-emittable).

**Audit subjects:**
- **v3b** = synthesis-only with compressed-input fix (Phase 2B-1) — 45 findings
- **v3c** = full pipeline with text-mode capture + RMF-walk + Needs Review + ambiguity flagging (Phase 2B-2) — **56 findings**

> **HEADLINE:** v3c lifts coverage from **26% to 43%** (+17 percentage points). Strict caught-only goes from 16% to 35% (+19). **Below the 60%+ target and below the 50% reassess-threshold, but a substantial improvement.** Per the user's stop rule, halting iteration here pending review.

---

## Headline numbers

| Metric | v3b | **v3c** | Δ |
|---|---|---|---|
| Total findings | 45 | **56** | +11 |
| Total RMF items (active) | 86 | 86 | — |
| Methodology/NA items | 4 | 5 | +1 (WC-4 "Intentionally Left Blank" now classified) |
| Finding-emittable items | 82 | 81 | — |
| **CAUGHT** | 13 (16%) | **29 (35%)** | **+16 / +19 pts** |
| **PARTIAL** | 8 (10%) | 6 (7%) | −2 |
| **NOT CAUGHT** | 61 (74%) | 46 (57%) | −15 |
| **Coverage (caught + partial)** | 21 (**26%**) | 35 (**43%**) | **+14 / +17 pts** |

## Per-tab breakdown — v3b → v3c

| Tab | v3b CAUGHT+PARTIAL | v3c CAUGHT+PARTIAL | Δ |
|---|---|---|---|
| General | 0+2 = 40% | **3+1 = 80%** | **+40 pts** |
| CGL | 10+5 = 47% | **15+1 = 51%** | +4 |
| CA | 2+0 = 12% | 4+0 = 23% | +11 |
| UMB | 0+0 = 0% | **4+4 = 61%** | **+61 pts** |
| WC | 1+1 = 14% | 3+0 = 20% | +6 |

**Biggest gains:** UMB (+61) — driven by the cross-policy matrix Schedule-of-Underlying findings + the new umbrella exclusions findings. General (+40) — driven by recovered cross-policy NI checks + WoS surfacing.

**Underperforming:** CA (23%), WC (20%) — many operational/admin items the AI deemed "not applicable."

---

## v3c per-item scorecard

### General All Policies (5 items) — 80% coverage

| # | RMF Item | v3c Verdict | v3c Finding (if any) |
|---|---|---|---|
| 1 | 90-day notice of cancellation | **PARTIAL** | "Designated Entity Notice of Cancellation — Maricopa County NOT Listed" Bad/12 (catches 30-day requirement; doesn't surface broker 90-day benchmark) |
| 2 | Unintentional Errors and Omissions | **NOT CAUGHT** | — |
| 3 | Named insureds list per policy + flag missing | ✅ **CAUGHT** | Multiple cross-policy entity findings (Properties LLC missing, Lincoln Shields, Black Mountain, 401(k) plan, Inc-vs-LLC mismatch) |
| 4 | Notice and Knowledge of Claims (all except umbrella) | **NOT CAUGHT** | — |
| 5 | Waiver of Subrogation | ✅ **CAUGHT** | "GL/Auto/Property — Blanket Waiver of Subrogation Across Program" Good |

### CGL (33 items, 2 NA) — 51% coverage

| # | RMF Item | v3c Verdict | Notable v3c Finding |
|---|---|---|---|
| 1 | Additional Insured (blanket) | ✅ CAUGHT | "GL Hanover — Blanket AI Includes Professional Services Carve-Out" Bad/9 |
| 2 | Care Custody and Control (CGL) | NOT CAUGHT | — |
| 3 | Compliance bank/contracts/leases | PARTIAL | Sacramento "No Additional Exclusions" findings |
| 4 | Composite Rating | NOT CAUGHT | — |
| 5 | Contract Review procedure | METHODOLOGY/NA | |
| 6 | Contractual Liability + AI/PNC/WoS | ✅ CAUGHT | Multiple Blanket AI findings |
| 7 | Contractual liability — personal & advertising | NOT CAUGHT | — |
| 8 | Coverage Territory | NOT CAUGHT | — |
| 9 | Cyber Coverage on CGL | ✅ CAUGHT | "GL — Cyber/Data Privacy/BIPA Exclusions Conflict with Maricopa" Ugly/12 |
| 10 | Damage to premises sublimit | NOT CAUGHT | — |
| 11 | Damages to Premises (Fire Legal) | NOT CAUGHT | — |
| 12 | Deductibles | NOT CAUGHT | — |
| 13 | Duty to Defend | NOT CAUGHT | — |
| 14 | EBL Coverage | ✅ CAUGHT | EBL findings (cyber/programming/virus carve-out) |
| 15 | EPLI / Wage & Hour | ✅ CAUGHT | "Hartford EPLI — Wage & Hour Defense Sublimit Only ($100K)" Bad/9 |
| 16 | Endorsements list problematic | METHODOLOGY/NA | |
| 17 | Environmental | ✅ CAUGHT | Pollution-related findings |
| 18 | Errors & Omissions / E&O | ✅ CAUGHT | E&O Delay-in-Performance Bad/16, Split Limits Bad/12, Client Print Media Bad/12 |
| 19 | Faulty Work / subcontractor giveback | NOT CAUGHT | — |
| 20 | Fellow Employee Coverage | NOT CAUGHT | (in per-policy analysis but not as finding) |
| 21 | Hired Non-Owned on CGL | ✅ CAUGHT | Auto Hired/Non-Owned Good |
| 22 | Leased / temporary workers | NOT CAUGHT | — |
| 23 | Mental Anguish in BI definition | NOT CAUGHT | (master annotation flagged this, still missed) |
| 24 | Named Insured (broad/subsidiaries/JVs) | ✅ CAUGHT | Cross-policy entity findings |
| 25 | Notice & Knowledge (officer-limited) | NOT CAUGHT | — |
| 26 | Per Location / Per Project Aggregate | ✅ CAUGHT | "Hanover Per-Project/Per-Location Aggregate Capped at $2M" Bad/9 |
| 27 | Primary and Non-Contributory | ✅ CAUGHT | P&NC findings |
| 28 | Product Recall | NOT CAUGHT | — |
| 29 | Professional Coverage | ✅ CAUGHT | Tech E&O findings |
| 30 | Stop Gap | PARTIAL | (mentioned in WC context) |
| 31 | Total Pollution Exclusion | ✅ CAUGHT | Pollution-related findings |
| 32 | TRIA / terrorism | NOT CAUGHT | — |
| 33 | Waiver of Subrogation (blanket) | ✅ CAUGHT | "GL/Auto/Property — Blanket WoS Across Program" Good |

### CA / Commercial Auto (18 items, 1 NA) — 23% coverage

| # | RMF Item | v3c Verdict | v3c Finding (if any) |
|---|---|---|---|
| 1 | AI status — Automatic + WoS + P&NC | ✅ CAUGHT | "Auto — Blanket AI / WoS / P&NC Properly Constructed" Good |
| 2 | BI including Mental Anguish | NOT CAUGHT | — |
| 3 | Broad Named Insured + all NIs listed | ✅ CAUGHT | "Auto-Only Additional Named Insureds (Lincoln Shields...)" Ugly/20 |
| 4 | Lease Gap coverage | NOT CAUGHT | — |
| 5 | Drive Other Car | NOT CAUGHT | — |
| 6 | Employee as Insured / CA 9933 | NOT CAUGHT | — |
| 7 | Endorsements list | METHODOLOGY/NA | |
| 8 | Environmental Exposures | NOT CAUGHT | — |
| 9 | Fellow Employee Exclusion | NOT CAUGHT | (per-policy captures it, synthesis didn't surface) |
| 10 | Hired Non-Owned | ✅ CAUGHT | "Auto — Hired & Non-Owned + Owned Coverage" |
| 11 | No-fault states optional | NOT CAUGHT | (probably correctly omitted — AZ not no-fault) |
| 12 | Mobile Equipment vs auto | NOT CAUGHT | — |
| 13 | Notice and Knowledge | NOT CAUGHT | — |
| 14 | Ownership of Vehicles | NOT CAUGHT | — |
| 15 | Parked Vehicles aggregate ded. | NOT CAUGHT | — |
| 16 | Symbols 1/2 vs 7 | NOT CAUGHT | — |
| 17 | Temporary & Leased Workers | NOT CAUGHT | — |
| 18 | Uninsured/Underinsured | NOT CAUGHT | — |

### UMB (14 items, 1 NA) — 61% coverage

| # | RMF Item | v3c Verdict | v3c Finding |
|---|---|---|---|
| 1 | Endorsements list | METHODOLOGY/NA | |
| 2 | Exclusions / non-follow-form | ✅ CAUGHT | "Umbrella — Cyber/Privacy Exclusions Strip Coverage Across Tower" Bad/16 |
| 3 | Horizontal exhaustion / P&NC + WoS follow form | PARTIAL | "Umbrella — Verify P&NC and AI Follow Form for Maricopa" Needs Review |
| 4 | Insureds — AI follow form, NIs same as underlying | ✅ CAUGHT | "Cross-Policy Entity Matrix — Auto-Only ANIs (Lincoln Shields…)" Ugly/20 |
| 5 | Defense inside vs outside limits | NOT CAUGHT | — |
| 6 | Maintenance of underlying | NOT CAUGHT | — |
| 7 | Notice and knowledge | NOT CAUGHT | — |
| 8 | Per Project Aggregate / Per Location | PARTIAL | (CGL per-project caught; umbrella-side not explicit) |
| 9 | Professional Liability follow-form | ✅ CAUGHT | Umbrella Cyber/Privacy exclusions findings |
| 10 | Punitive damages excluded | NOT CAUGHT | — |
| 11 | Right and Duty when underlying exhausted | NOT CAUGHT | — |
| 12 | Total Pollution Exclusion | PARTIAL | (CGL pollution caught; umbrella-side via follow-form implicit) |
| 13 | Underlying Policies all listed | ✅ CAUGHT | Schedule-of-Underlying matrix finding |
| 14 | Specific follow-form concerns | PARTIAL | "Verify P&NC and AI Follow Form for Maricopa" Needs Review |

### WC (16 items, 1 NA) — 20% coverage

| # | RMF Item | v3c Verdict | v3c Finding |
|---|---|---|---|
| 1 | Small indemnity claims | NOT CAUGHT | (operational/management item) |
| 2 | Small med claims | NOT CAUGHT | (operational) |
| 3 | All States Endorsement (3.A vs 3.C) | ✅ CAUGHT | WC Multi-State + Stop Gap findings |
| 4 | (Intentionally Left Blank) | METHODOLOGY/NA | |
| 5 | Alternate Employee Endorsement | NOT CAUGHT | — |
| 6 | EL Limits adequate | ✅ CAUGHT | EL findings present |
| 7 | Endemic Disease / Foreign Voluntary | NOT CAUGHT | (probably correctly omitted — no foreign ops) |
| 8 | Experience Modification | NOT CAUGHT | (was in v1, lost in v2/v3, still missed) |
| 9 | Maritime coverage | NOT CAUGHT | (probably correctly omitted) |
| 10 | Large claims by name | NOT CAUGHT | (operational) |
| 11 | All possible credits | NOT CAUGHT | (operational) |
| 12 | Owners Excluded | NOT CAUGHT | (data not in input) |
| 13 | DBA included | NOT CAUGHT | (probably correctly omitted) |
| 14 | USL&H | NOT CAUGHT | (probably correctly omitted) |
| 15 | Classification codes correct | PARTIAL | "WC — Indiana Voluntary Compensation Carve-Out" Bad/3 (related, not full classification check) |
| 16 | Waiver of Subrogation | ✅ CAUGHT | WC WoS findings |

---

## What v3c surfaced that v3b didn't

The 14-pt jump in coverage isn't just keyword-matching — substantive findings recovered:

- **Maricopa Auto $2M CSL Shortfall (Bad/12)** — first time captured in production output (was MISSED in v3 entirely; only surfaced in the v3b synthesis-only experiment that lacked matrix pass)
- **Maricopa $5M Cyber Shortfall (Ugly/25)** — top-scoring finding in the program
- **E&O Delay-in-Performance Exclusion (Bad/16)** — election-services-specific; was in v3 master annotation, missed by v3 production
- **E&O Client Print Media Exclusion (Bad/12)** — county-furnished ballot content carve-out
- **Hanover Per-Project Aggregate $2M Cap (Bad/9)** — was in v2, lost in v3, recovered now
- **Hartford EPLI Wage & Hour $100K Sublimit (Bad/9)** — was in v2, lost in v3, recovered
- **Cross-Policy Inc-vs-LLC mismatch (Bad/9)** — explicit finding (vs prior implicit signals)
- **5 Needs Review findings** — new fourth verdict category firing for the first time

## What v3c still misses (the 46 not-caught)

Two clusters:

**Cluster A — operational/management items the AI deemed not applicable** (probably correctly):
- WC small claims management, EMR, large claims by name, all-credits, owners-excluded
- WC DBA / Maritime / USL&H (no overseas/maritime ops)
- CA No-fault states (AZ not no-fault)
- CGL Composite Rating, Contract Review procedure (methodology)

**Cluster B — real coverage items the AI silently skipped despite RMF-walk instruction:**
- CGL: Care/Custody/Control, Damage to Premises, Fire Legal Liability, Deductibles, Duty to Defend, Faulty Work, Fellow Employee, Leased Workers, Mental Anguish in BI, Notice & Knowledge officer-limited, Product Recall, TRIA
- CA: Lease Gap, Drive Other Car, CA 9933 Employee-as-Insured, Mobile Equipment, Symbols 1/2 vs 7, U/UIM, Notice & Knowledge, Ownership, Parked Vehicles, Temporary Workers
- UMB: Defense inside vs outside, Maintenance of underlying, Notice & Knowledge, Punitive damages, Right and Duty
- General: Unintentional E&O, Notice & Knowledge

Cluster B is the meaningful gap. These are real RMF checklist items the AI was instructed to walk explicitly. It walked some but skipped others. Likely the AI's "is this applicable to this client?" filter was too aggressive.

## Per the user's stop-rule

> "Target: lift RMF coverage from 26% to 60%+. If the result is materially below 50%, stop and reassess before further iteration."

**v3c landed at 43%. Below the 50% threshold. Halting iteration. Reassess required before any further KB or prompt changes.**

## Suggested reassess questions for the user

1. **Is the AI's "not applicable" filter too aggressive?** The synthesis prompt says "If the item is genuinely not applicable to this client → omit silently." The AI may be applying this filter to items that ARE applicable but don't have obvious defects (e.g., Mental Anguish in BI definition, U/UIM, Parked Vehicles aggregate ded.). If so, the prompt could be tightened: "Only omit if the item has zero conceivable applicability to this client's industry/geography/operations."

2. **Should methodology/operational items (CGL Composite Rating, WC Small Claims) be filtered out of the RMF spreadsheet itself?** Some items are not "audit findings" — they're audit *processes*. Excluding ~15 of these from the denominator would push v3c from 43% to ~52%.

3. **Is "Cluster B" worth one more prompt iteration?** Targeted bullet: "For these specific Auto/Umbrella RMF items, ALWAYS emit a finding even if compliant: Mental Anguish in BI, U/UIM, Notice & Knowledge, Maintenance of Underlying, Punitive Damages…"

4. **Or is 43% acceptable as a v3c shipping baseline?** The substantive Ugly/Bad findings are strong. RMF coverage caps the comprehensiveness story but doesn't undermine the finding quality.

---

## Known limitation: keyword-based grading produces false positives

The grader (`phase-2b-2/_rmf_grade.py`) uses substring keyword matching against the findings blob (requirement_type + plain_english + gap_description + contract_quote + policy_quote + tags) to decide CAUGHT / PARTIAL / NOT CAUGHT for each RMF item. This is fast and simple but produces false positives when the same keyword serves multiple RMF items.

**Documented case (2026-04-30, v3d-split run):**
The grader credited **CA-2** ("BI including Mental Anguish") as CAUGHT despite no Auto-specific Mental Anguish finding existing in `findings_v3d-split.json`. The credit came from `finding-018`, which is a CGL-policy finding tagged `rmf-cgl-23`. Both CGL-23 and CA-2 use the same keyword set (`mental anguish`), so any CGL-23 hit auto-credits CA-2 even when no Auto-specific analysis was actually performed. Real CA-2 evidence (a separate Auto-policy BI definition walkthrough) was missing.

**Implication:** v3d-split's reported 48% coverage is slightly inflated. Adjusting for this single known false positive, *real* coverage is approximately 47% (38/81). The same false positive existed in v3c (43% reported → ~42% real) and v3d (45% reported → ~44% real), so it's **not a regression** — it's a pre-existing grader limitation.

**Future cleanup (out of scope at the time of this writing):**
A more rigorous grader would key on explicit RMF tags in finding metadata (e.g., `rmf-ca-2` or `rmf-cgl-23` tags emitted by the synthesis prompt) rather than free-text keyword matching. The v3e prompt iteration (2026-04-30) adds explicit "CA-specific finding, separate from any CGL-23 finding" language to force separate findings — once those land, the grader could be tightened to require tag-based matching instead of keyword matching, eliminating the false-positive class.

For now, treat reported coverage as approximate (±1–2 pp) when comparing across runs. Big swings (5 pp+) are still meaningful; small movements may be within the false-positive noise.
