# Validation Rollup — Stage 1 (KB-cleanup v2 → Pipeline-fix v3)

**Run dates:** v2 = 2026-04-27 · v3 = 2026-04-29 · **Policies:** 9 · **Contracts:** 4 · **Stage 1 changes:** per-contract extraction (Issue A), cross-policy matrix pass with universal-KB injection (Issue B), schema additions (`additional_named_insureds`, `policy_type` enum, `designated_entity_noc_endorsements`, `cancellation_notice_days`, etc.), plus 5 production-stability fixes (orphan logic, multi-policy attachment, session-state persistence, timestamps, Download All ZIP).

> **Number framing note.** The v2 .txt summary listed 25 findings (10 Ugly + 10 Bad + 5 Good). The canonical `findings.json` had **30** (10/13/7) — the .txt was top-N filtered. v3's .txt and `findings.json` agree at **38** (13/14/11). The headline below uses both framings; per-policy tables use the canonical 30→38.

---

# Section 1 — Headline answer

**Stage 1 partly worked, but the picture is more nuanced than the headline numbers suggest.** Against the v2 .txt baseline the deliverable went from 25 to 38 findings (+13, +52%); against the canonical findings.json baseline it went from 30 to 38 (+8, +27%). The cross-policy matrix pass added **11 cross-cutting findings worth a combined ~Ugly-180 risk score** (Lincoln Shields, Black Mountain, Properties LLC, Inc-vs-LLC mismatch, Schedule of Underlying misalignment, 401(k) on the wrong policy, Designated Entity NOC asymmetries) — every one of which v2 was structurally incapable of producing because no matrix-construction step existed. **That is a clean validation of the Stage 1 architecture.** But against this win, **v3 lost ~17 v2 per-policy substantive findings** — the entire PL Ugly-tier (Network Security, Ransomware, BIPA, Mail Processing retro), Property sublimits, Auto Care/Custody/Control, Auto Malina Trujillo, WC WOS gap, CA Labor Code §2810.3, ML EPLI Wage & Hour, GL Arch classification, Convex policy-number defect, plus several Goods. The flagship GAP-17 test (Maricopa $2M Auto CSL breach) **fired through the pipeline but reached the wrong verdict** because the v3 contract extraction read Maricopa §8.2.9's general umbrella-attachment clause as overriding the §8.2.10/§8.2.11 structural distinction the master annotator used; the matrix correctly computed `met-via-umbrella` from that input, and v3 emitted a Good "Umbrella stacks over Maricopa $2M Auto" finding that contradicts the master's stricter reading. Net: Stage 1 closed the cross-policy validation gap but introduced per-policy depth regressions that need Stage 2 attention.

---

# Section 2 — v2 → v3 net change scorecard

Per-policy counts, canonical (`findings.json` v2 vs `audit-state.json` v3 after fix-recovery):

| Slug | v2 total | v3 total | Net Δ | NEW (v3 only) | REMOVED (regressions) | Notes |
|---|---|---|---|---|---|---|
| ml | 4 (1U/2B/1G) | 6 (2U/4B/0G) | **+2** | Fiduciary 401(k) wrong-policy (Ugly/20 XPM); Cross-policy NI Investments+Graphics missing (Bad/16 XPM); Crime Social Engineering $15K (Bad/12); Cyber-related items | EPLI Wage & Hour (Bad/9); PE Co-Defendant Good ack | Mfg/Prof Services Exclusion (Ugly/20) kept; Split P/P reframed Bad/8→Bad/12 |
| pl | 6 (5U/1B/0G) | 4 (0U/2B/2G) | **−2** | Tech E&O Sacramento $1M Min met (Good); Retro Date Good ack | **All 4 v2 Ugly findings lost**: Mail Processing Retro Restricted (Ugly/15), Network Security/Privacy (Ugly/20), Ransomware (Ugly/16), BIPA (Ugly/15); Hammer Clause (Bad/9) | **Major regression — entire PL Ugly tier gone**. Split Limits downgraded Ugly/12 → Bad/8 |
| sg | 1 (1U/0/0) | 1 (0/0/1G) | flat count, **regression** | CA Civil Code §2782(b) Anti-Indemnity Compliance (Good) | GL Classification Limitation on Arch (Ugly/12) | Substantive Ugly replaced with informational Good — net regression |
| convex | 1 (1U/0/0) | 0 | **−1** | — | Excess Tower Convex Policy Number Doc Defect (Ugly/10) | Convex now only appears via multi-policy semicolon-strings; no standalone finding |
| cyber | 1 (1U/0/0) | 8 (5U/3B/0) | **+7** | DWL + Shared Aggregate Erosion (Ugly/20); $5M Per-Occurrence Maricopa (Ugly/20); AI Status Maricopa (Ugly/12); WOS Maricopa (Ugly/12); Cyber Phantom Coverage upgraded Ugly/16→Ugly/20; Continuity/Retro Gap (Bad/12); P&NC Maricopa (Bad/6); Proof of Loss Sublimit $250K (Bad/6) | — | **Largest single-slug improvement.** GAP-22 multi-pattern catch + contract-driven Maricopa AI/WOS/PNC findings |
| auto | 3 (0/2B/1G) | 2 (0/0/2G) | **−1** (count) / **regression** | AI+P&NC+WOS Blanket (Good); HNOA + Owned (Good) | Care, Custody, Control Exclusion (Bad/9); Malina Trujillo named-driver (Bad/6) | Both Bad findings lost. The flagship Maricopa $2M CSL breach surfaced incorrectly as a Good "umbrella stacks" finding (see §3) |
| pkg | 4 (0/3B/1G) | 7 (1U/4B/2G) | **+3** | GL AI Ongoing+Completed Ops blanket (Good); GL P&NC+WOS blanket (Good); Inland Marine WOS Sacramento (Bad/6); GL Sacramento No-Add'l-Exclusions vs Cyber stack (Bad/4) + 1 cross-policy NOC asymmetry tied here as primary | Property Electronic Data Sublimit (Bad/9); Property Interruption of Computer Operations (Bad/9); Per-Project Aggregate Cap (Bad/6); Equipment Breakdown Adequacy (Good) | All 3 first-party-property substantive findings lost; replaced with contract-compliance acks |
| umb | 1 (1U/0/0) | 5 (3U/1B/1G) | **+4** | Schedule of Underlying NI Misalignment (Ugly/20 XPM); Cross-policy NI primaries (XPM); Landlord AI ARC Airport (Bad/9 XPM); $10M Stacks Over Maricopa $2M Auto (Good) | Umbrella excludes PL/Cyber/D&O (Ugly/15) | **Caveat: lost the v2 Ugly "PL/Cyber/D&O excluded" finding**, which is genuinely material; the new Good "stacks over Auto" finding is built on a contract-interpretation that contradicts the master |
| wc | 4 (0/2B/2G) | 4 (1U/0/3G) | flat (composition shift) | Multi-State Statutory CA (Good); Blanket WOS incl. CA (Good); EL Limits Meet Both Contracts (Good); Designated Entity NOC Maricopa (Ugly/9) | WC WOS Gap GA/NC/IL (Bad/9); CA Labor Code §2810.3 (Bad/8); Stop Gap for Monopolistic States (Good); EMR 0.690 (Good) | **Both substantive Bads lost.** Goods reframed to be contract-compliance-oriented |
| **PROGRAM** | n/a | 1 (1U/0/0) | **+1** | Inc-vs-LLC Entity-Type Mismatch Across Program (Ugly/20 XPM) | — | The marquee Stage 1 cross-policy finding |
| ?(v2 "Multiple") | 5 (0/3B/2G) | 0 | **−5** | n/a | Defense Costs Inside Limits (Bad/12); Crime Computer/Funds Transfer (Bad/9); Carrier Concentration E&S (Bad/4); GL+Auto Blanket AI+P&NC (Good); Cancellation Notice to Designated Govt Entities (Good) | v2 used `policy_file: "Multiple"` for cross-policy findings; v3 replaced with structured semicolon-list `policy_file` values |
| **TOTAL** | **30** | **38** | **+8** | **+19** new | **−11** removed | |

**Category breakdown:**

| | v2 | v3 | Δ |
|---|---|---|---|
| Ugly (critical) | 10 | 13 | **+3** |
| Bad (needs attn) | 13 | 14 | +1 |
| Good (compliant) | 7 | 11 | +4 |
| **Total** | **30** | **38** | **+8** |
| of which `cross-policy-matrix` tagged | 0 | **11** | +11 |

**Critical observation:** the +3 Ugly is misleading — 5 v2 Uglies were lost (PL ×4 + Convex) and 8 new v3 Uglies were gained (5 Cyber + 3 cross-policy entity). The headline "+3 Ugly" hides a complete restructuring of the Ugly catalog.

---

# Section 3 — GAP-XX scorecard v3

Three-tier rubric: CAUGHT (defect + consequence articulated) · PARTIAL (headline only or wrong consequence) · MISSED (no hit / wrong direction).

| KB File | v2 status | v3 status | Notes |
|---|---|---|---|
| **GAP-01 EXPANDED** named-insured-verification | 0/9 MISSED | **CAUGHT** (1 PROGRAM-level finding + 4 entity-specific findings; Cyber asymmetry recognized as the only LLC-correct policy in the Top-3 actions) | "First Named Insured — Inc vs LLC Entity-Type Mismatch Across Program (Systemic)" Ugly/20, recommends Name Change endorsement IL 12 01 on six 'Inc' policies. Architectural success. |
| **GAP-02 EXPANDED** cancellation-notice-verification | 0 MISSED | **PARTIAL** | Auto/WC/Pkg/Umbrella cancellation policies inferred via the new `cancellation_notice_days` schema field but no dedicated benchmark-vs-policy finding ("Auto = 30 days vs 90-day expectation") emitted. The Designated Entity NOC findings substitute for the program-wide notice-comparison story. |
| **GAP-08 EXPANDED** umbrella-structure | 0 CAUGHT / 1 PARTIAL | **CAUGHT (partial scope)** | "Umbrella Schedule of Underlying — Multiple Subsidiary Entities Not Aligned" Ugly/20 captures the entity-misalignment angle very well. **MISSED:** the Convex-Tech-E&O-coordination angle didn't surface (v3 has no finding linking Convex's existence to the Umbrella's PL exclusion). The v2 Ugly/15 "Umbrella excludes PL/Cyber/D&O" finding was LOST and is not adequately replaced. |
| **GAP-17** contract-specific-coverage-satisfaction | 0 CAUGHT / 2 PARTIAL / 6 MISSED | **PARTIAL** — pipeline architecturally fires but contract interpretation defaulted to permissive | **Flagship test result:** v3 contract extraction set `Maricopa.auto_liability.umbrella_may_satisfy_minimum: True`. Compliance matrix verdict became "met" via umbrella stacking. v3 emitted **a Good finding** "Umbrella — $10M Stacks Over GL/Auto/EL to Meet Maricopa $2M Auto" — *contradicting* the master annotator's strict reading that §8.2.10's inline umbrella permission for CGL plus §8.2.11's lack of inline language for Auto means umbrella attachment is structurally barred for Auto. Defensible legal interpretation but more permissive than your master annotation. The matrix code, flagship logging, and KB injection all worked correctly given the AI's contract reading. **The needle moved on infrastructure; the needle did not move on the headline test outcome.** |
| **GAP-18** coverage-specific-sublimits | 3 CAUGHT / 1 MISSED | **CAUGHT (sustained)** + **PARTIAL on Property** | Cyber phantom-coverage Ugly/20 caught; Cyber DWL Ugly/20 caught; Cyber Proof of Loss $250K Bad/6 caught; Cyber Continuity/Retro Bad/12 caught. **REGRESSION:** v2's Property Electronic Data ($2,500 sublimit) Bad/9 + Computer Operations Sublimit Bad/9 are LOST in v3. v3 replaced them with one composite Good "Equipment Breakdown $49M Adequate" — but doesn't surface the data-sublimit issues. |
| **GAP-19** named-driver-exclusions | 1/1 CAUGHT | **MISSED (regression)** | Auto Malina Trujillo named-driver exclusion was caught in v2 (Bad/6); **gone in v3.** Possible cause: per-policy re-analysis with new schema shifted attention; or AI confused the named-driver content with cross-policy entity-matrix work. Concrete regression. |
| **GAP-20** cross-policy-named-insured-inconsistency | 0 MISSED | **CAUGHT (multi-pattern)** | Lincoln Shields LLC missing from Umbrella/Pkg/ML — Ugly/20. Black Mountain Investment Co LLC missing — Ugly/20. Runbeck Properties LLC on Umbrella but missing from Pkg CGL — Ugly/25 (highest score in v3). Runbeck Investments + Graphics missing from ML — Bad/16. ARC Airport 2800 LLC missing from Umbrella — Bad/9. Benton County WA on Pro Liab only — Bad/9. Marquee Stage-1 success. |
| **GAP-21** designated-entity-cancellation-notice | 0 MISSED | **CAUGHT (multi-pattern)** | Designated Entity NOC — Maricopa County missing from 9 policies (Ugly/9). Designated Entity NOC Asymmetry — customer counties on Auto/WC but missing from Pkg CGL (Bad/12). Designated Entity NOC — Endorsement entirely absent from 6 program policies (Bad/12). Three findings cover the asymmetry pattern from different angles. |
| **GAP-22** cyber-dec-sheet-patterns | 1/6 CAUGHT (phantom only) | **5/6 CAUGHT** | Phantom $250K=$250K — kept Ugly/20. **NEW catches:** DWL + Shared Aggregate Erosion (Ugly/20) ✅; Maricopa $5M vs $4M shortfall (Ugly/20) ✅; Proof of Loss Sublimit $250K (Bad/6) ✅; AI/PNC/WOS for Maricopa on Cyber (Ugly/12, Ugly/12, Bad/6) ✅. **STILL MISSED:** NY choice-of-law on AZ insured. Best multi-pattern KB performance in v3. |

**Files demonstrably firing v3:** GAP-01 EXPANDED, GAP-08 EXPANDED (entity scope), GAP-18 (Cyber only), GAP-20, GAP-21, GAP-22. **6 of 9 KB files** firing now (vs 2 of 9 in v2).

**Files needing sharpening:** GAP-17 (contract-extraction permissiveness — see Stage 2 punch list), GAP-08 EXPANDED (Convex tower-coordination angle), GAP-22 (NY choice-of-law).

**Files with regressions:** GAP-18 (Property side regressed), GAP-19 (entirely lost).

---

# Section 4 — Auto master ground truth recovery

v2 caught **0 of 14** master items. v3 progress on each:

| # | Master item | v3 verdict |
|---|---|---|
| 1 | pg 24 highlight: `LIABILITY $1,000,000 COMBINED SINGLE LIMIT` (red) | ⚠ **PARTIAL — wrong direction.** v3 Good "Umbrella Stacks Over Maricopa $2M Auto" treats this as resolved-via-umbrella; master treats it as bare violation |
| 2 | **pg 24 FreeText sticky note: "$2M Maricopa CSL... contract DOES NOT permit umbrella for Auto"** | ⚠ **PARTIAL — caught as Good instead of Ugly.** This is the flagship test. The pipeline fired the matrix and generated a finding tied to Maricopa Auto $2M; the verdict was "met" instead of "violation" because contract extraction set `umbrella_may_satisfy_minimum: True`. **The single moment that would have justified the entire Stage 1 effort did not deliver as intended** — though the architecture is now in place to deliver it after a Stage 2 contract-extraction prompt sharpening |
| 3 | pg 24 line + blue Square (column markup against $1M CSL) | ⚠ same as #2 — surfaces only via the Good "stacks" finding |
| 4 | **pg 28 red Square: ADDITIONAL NAMED INSURED ENDORSEMENT entity list** | ✅ **CAUGHT** via 3 cross-policy NI findings (Lincoln Shields Ugly/20, Black Mountain Ugly/20, Properties LLC Ugly/25) and the Schedule-of-Underlying alignment finding (Ugly/20) |
| 5 | **pg 28 FreeText sticky note: "okay... where were these on the CGL and Auto policies?"** | ✅ **CAUGHT** — exactly the cross-policy NI asymmetry the master sticky note pointed at. Top-3 recommended action #3 in v3 .txt explicitly addresses adding Lincoln Shields to the Umbrella/Pkg/ML schedules to match the Auto schedule |
| 6 | pg 32 red highlights: B. Exclusions / 2. Contractual / Liability assumed under any contract | ❌ MISSED |
| 7 | pg 33 red highlight: 5. Fellow Employee | ❌ MISSED |
| 8 | pg 38 red highlights: excess for non-owned auto / primary for insured contract | ❌ MISSED |
| 9 | pg 38 cyan highlight: primary-for-insured-contract carve-back (Good) | ❌ MISSED |
| 10 | pg 39 orange highlight: BI definition omits Mental Anguish | ❌ MISSED |
| 11 | pg 44 orange highlight: BLANKET WHERE REQUIRED BY WRITTEN CONTRACT 30 (cancellation 30) | ⚠ **PARTIAL** — captured in the new schema's `cancellation_notice_days: {for_other_reasons: 30, page_ref: pg 44}` field but no Bad/Ugly finding emitted (v3 .txt slide-18 30-day-vs-90-day comparison missing) |
| 12 | pg 47 cyan: Blanket WOS by contract (Good) | ✅ **CAUGHT** in Auto Good "AI + P&NC + WOS Blanket" |
| 13 | pg 48 cyan: 60-day cancel extension (Good) | ❌ MISSED — v3 has no finding crediting this |
| 14 | pg 54 cyan: Mental Anguish giveback (Good) | ❌ MISSED |

**v3 Auto master coverage: 3 CAUGHT / 4 PARTIAL / 7 MISSED = 21% full + 29% partial.**

Compared to v2's **0 of 14**, that's a 50%+ improvement on touch coverage — but the highest-value item (the GAP-17 flagship sticky note) reached the wrong verdict. The pg 28 cross-policy sticky note (item #5) is the single clean Stage-1 win that justifies the architectural investment.

---

# Section 5 — Material regressions check

| Regression | v1 / v2 status | v3 status |
|---|---|---|
| **ML pg 73 Entity Regulatory Proceedings** (Bad/12 in v1, missing in v2) | Lost in v2 | **STILL MISSED in v3** — D&O/regulatory-proceedings exposure not surfaced. Election-services regulatory exposure remains uncovered in the audit. |
| **WC pg 137 Ownership Change Reporting** (Bad/6 in v1 PE-critical, missing in v2) | Lost in v2 | **STILL MISSED in v3** — PE-relevant ownership-change defect remains uncovered. |

**Net v3 regressions vs v2 (new):**

| Lost in v3 | v2 score | Notes |
|---|---|---|
| PL — Mail Processing Restricted Retro Date | Ugly/15 | Confirmed material per prior verification report |
| PL — Network Security & Privacy Breach Exclusion | Ugly/20 | Highest-tier substantive PL finding — gone |
| PL — Ransomware/Extortion Exclusion | Ugly/16 | |
| PL — BIPA / Biometric Identifiers Exclusion | Ugly/15 | |
| PL — Hammer Clause Dual Structure | Bad/9 | |
| Convex — Excess Tower Policy Number Documentation Defect | Ugly/10 | |
| GL — Classification Limitation on Arch Policy | Ugly/12 | |
| Property — Electronic Data Sublimit ($2,500) | Bad/9 | |
| Property — Interruption of Computer Operations Sublimit | Bad/9 | |
| Per-Project Aggregate Cap Limitation | Bad/6 | |
| Auto — Care, Custody, or Control Exclusion (Ballot Transit) | Bad/9 | |
| Auto — Named Driver Exclusion (Malina Trujillo) | Bad/6 | **Direct GAP-19 regression** — was the marquee KB-fires-cleanly catch in v2 |
| WC — Waiver of Subrogation Gap GA/NC/IL | Bad/9 | |
| California Employers' Liability — Labor Code §2810.3 | Bad/8 | |
| EPLI — Wage & Hour Defense Sublimit | Bad/9 | |
| Property — Equipment Breakdown Limit Adequacy (Good) | Good | |
| WC — Stop Gap for Monopolistic States (Good) / EMR 0.690 (Good) | 2× Good | Reframed but not retained as separate cards |
| PE Co-Defendant Extension on Management Liability (Good) | Good | |

**Total v3 regressions: ~17 findings** (with informational-tier reframings excluded, ~12 substantive losses). Concentrated in PL (5), Property/Pkg (3), Auto (2), WC (2), ML (1), SG (1), Convex (1).

The pattern suggests the per-policy re-analysis with the expanded schema directed AI attention toward populating new entity/endorsement fields at the expense of substantive coverage-gap depth. **This is the Stage 2 punch list's #1 priority.**

---

# Section 6 — Per-policy improvement breakdown

| Slug | v2 → v3 | One-line read |
|---|---|---|
| **ml** | improved (+2) | Mfg Exclusion preserved; D&O Prior Acts upgraded; gained 2 cross-policy entity findings. Lost EPLI Wage & Hour. Net positive. |
| **pl** | **regressed** (−2) | Lost all 4 v2 Ugly findings (Network Security, Ransomware, BIPA, Mail Processing); added 2 contract-compliance Goods. **Largest substance loss in v3.** |
| **sg** | regressed (flat count, swap from Ugly/12 → Good) | GL Classification Limitation Ugly was lost; replaced with CA Civil Code §2782(b) Good ack. Net regression on substance. |
| **convex** | regressed (−1) | Convex Policy Number Doc Defect lost; Convex now only appears as a multi-policy semicolon-list participant. No standalone finding. |
| **cyber** | **improved (+7)** | GAP-22 multi-pattern firing: DWL erosion, $5M Maricopa shortfall, AI/WOS/PNC for Maricopa, Proof of Loss sublimit. Largest single-slug gain. |
| **auto** | regressed (−1) | Lost both v2 Bad findings (Care/Custody/Control, Malina Trujillo). Flagship Maricopa $2M test reached wrong verdict (Good instead of Ugly). |
| **pkg** | mixed (+3 count, −3 substance) | Gained contract-compliance acks (GL AI/P&NC/WOS blanket). Lost 3 substantive property sublimit findings. |
| **umb** | improved (+4 count, mixed substance) | Gained Schedule of Underlying alignment finding (Ugly/20) and ARC Airport landlord AI gap. Lost the v2 PL/Cyber/D&O excess-tower exclusion finding (Ugly/15) — partially compensated but the simple narrative is gone. |
| **wc** | flat (composition shift) | Lost both Bads (WOS gap, CA §2810.3); gained NOC-Maricopa Ugly/9 + 3 contract-compliance Goods. Net wash. |

---

# Section 7 — Honest bottom-line recommendation

## Verdict: **B — Stage 1 produced major improvement; Stage 2 (KB sharpening) needed for specific patterns.**

Stage 1 closed the largest validation gap from the v1→v2 rollup (the cross-policy matrix gap that GAP-20/21 needed). The 11 cross-policy findings (Inc-vs-LLC, Lincoln Shields, Black Mountain, Properties LLC, Schedule of Underlying, NOC asymmetries) are exactly the kind of program-level intelligence v2 was structurally incapable of producing — and they're high-value findings that map directly to your master annotation's "where were these on the CGL and Auto policies?" sticky note. The infrastructure works.

But Stage 1 introduced ~17 per-policy substantive regressions, mostly concentrated in PL (the entire Ugly tier — Mail Processing, Network Security, Ransomware, BIPA — disappeared). The flagship GAP-17 test (Maricopa $2M Auto) reached the wrong verdict because the new contract-extraction prompt didn't sharpen the structural-vs-permissive umbrella-attachment distinction. Two production KB files (GAP-19 named-driver, GAP-18 Property side) regressed entirely.

**This is not a "Stage 1 didn't work" verdict — it's a "Stage 1 worked on the cross-policy axis but the schema expansion redirected per-policy AI attention away from substance." The fix is in two specific places, not a wholesale rework.**

### Stage 2 punch list (ranked by impact, scoped tight)

1. **Per-policy depth recovery (highest priority).** Tweak `_POLICY_STRUCTURED_FIELDS_BLOCK` to make the entity/endorsement extraction additive rather than displacing the existing substantive analysis. Specifically: separate the "fill in these fields" instruction from the "find substantive coverage gaps" instruction with a strong "do BOTH, don't pick one" directive, and add explicit examples of the v2 PL findings (Mail Processing retro, Network Security/Privacy, Ransomware, BIPA) as patterns the AI must still surface. Re-run only the PL, Property, and Auto policies to validate.

2. **GAP-17 contract-interpretation sharpening.** Add to `build_contract_prompt`: *"If a coverage-line clause does NOT contain inline 'Commercial Umbrella'/'Excess' attachment language, set `umbrella_may_satisfy_minimum: false` for that line — even if a general umbrella permission clause exists elsewhere in the insurance section. Capture the structural reading, not the permissive one. Per-line specificity overrides general clauses."* Re-extract the Maricopa contract and confirm the matrix verdict flips to "violation".

3. **GAP-19 recovery.** The named-driver-exclusion KB file's content didn't fire in v3. Investigate: is the GAP-19 KB still being loaded by `_load_kb_for_policy_type` for `auto`? Is the per-policy prompt mentioning `[COVERAGE-AUTO]` getting truncated by the cap? Add the Malina Trujillo example as a smoke-test case.

4. **GAP-08 Convex tower coordination.** Add a synthesis-prompt instruction to cross-reference Umbrella PL exclusion against the Convex Excess Tech E&O presence — the missed connection is "your Umbrella excludes PL but you have a Convex tower above your PL, so the tower coordinates around Umbrella's exclusion at $5M." Mid-priority.

5. **GAP-22 NY choice-of-law.** Single missing pattern in an otherwise strong GAP-22 catalog. Add a single bullet to the Cyber KB content. Lowest priority of the five.

### Caveats / non-Stage-2 items

- **The pg 73 Entity Regulatory Proceedings + pg 137 WC Ownership Change Reporting regressions** persist from the v1→v2 rollup. These are independent of Stage 1; they need separate KB content additions.
- **The v3 .txt summary's Top-3 Recommended Actions are entirely cross-policy entity issues** (Properties LLC missing, Inc-vs-LLC fix, Lincoln Shields entity additions). For the actual client meeting these are real and material. But they're NOT what the master annotator's audit emphasized — the master led with the Maricopa $2M Auto contract breach and the PL exclusions. **Recommend a manual review pass before sending the v3 .txt to the client** to ensure the deliverable matches the strategic narrative you'd build at the table.
- **The Stage 2 work is bounded** — 5 specific items, ~3-4 hours of KB editing + 1 targeted re-run. Not a rewrite.

After Stage 2, the v3 deliverable will likely retain its 11 cross-policy wins, recover the 5 PL Ugly findings + the GAP-19 Malina catch, and deliver the GAP-17 flagship as a real Ugly-tier violation. That's the test for whether Stage 2 worth running. Until then, the v3 output is **production-usable for similar audits** with the explicit caveat that per-policy substantive depth is currently 60-70% of v2's level — paired with 100%+ improvement on cross-policy intelligence.
