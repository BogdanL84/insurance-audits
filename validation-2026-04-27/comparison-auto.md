# Comparison — Hanover Commercial Auto

**Slug:** `auto` · **Audited PDF (v2):** `RedactedHanover - Auto - 4.1.25-4.1.26-AUDITED.pdf` (78 pages)

## 1. SOURCES

| Source | Available | Notes |
|---|---|---|
| Presentation slides | ✅ | Slides 11, 12, 21 + cancellation slide 18 |
| Prior verification report | ❌ | Not in handoff or interim reports |
| Annotation-level master | ✅ | `Downloads\Hanover - Auto - 4.1.25-4.1.26.pdf` — 19 annots (14 Highlight + 2 FreeText + 2 Square + 1 Line) by "Bogdan Laza" + 10 hand-titled bookmarks |
| App v1 (older Downloads run) | ❌ | No v1 Auto audited file exists; only Auto v2 |
| App v2 (today's Desktop run) | ✅ | 3 Text findings + 3 Highlight markup |

**Auto is the highest-confidence policy in this validation** because the annotation-level master is preserved.

## 2. APP V1 → V2 NET CHANGE

No v1 baseline for Auto exists. **All 3 v2 findings are NEW catches** by definition (no prior comparison).

| Page | Cat | Score | Finding | Status |
|---|---|---|---|---|
| 9   | Bad  | 6  | Auto — Named Driver Exclusion (Malina Trujillo) | NEW IN V2 (likely from GAP-19 KB file) |
| 28  | Good | —  | Auto — Hired & Non-Owned Auto Coverage           | NEW IN V2 |
| 34  | Bad  | 9  | Auto — Care, Custody, or Control Exclusion (Ballot Transit) | NEW IN V2 |

## 3. GROUND TRUTH COVERAGE

### A. Master annotation ground truth (Bogdan Laza markup)

Color legend used by Bogdan: **red = concern**, **cyan = good**, **orange = noteworthy/cancellation**.

| Pg | Type | Color | Anchored text | App v2 catch? |
|---|---|---|---|---|
| 24 | Highlight | red | `LIABILITY $1,000,000 COMBINED SINGLE LIMIT` | ❌ MISSED |
| 24 | FreeText (sticky note) | — | *"not a great start - Maricopa contract expressly states $2M CSL required - contract DOES NOT state that auto limits can be met via use of an Umbrella. ((states so for GL but not Auto))"* | ❌ MISSED — this is GAP-17 verbatim and v2 did not catch it |
| 24 | Line + Square | red + blue | column markup against the $1M CSL line | ❌ MISSED |
| 28 | Square (red) | red | `ADDITIONAL NAMED INSURED ENDORSEMENT … RUNBECK ELECTION SERVICES INC, RUNBECK INVESTMENTS LLC, RUNBECK PROPERTIES LLC, RUNBECK GRAPHICS INC` | ❌ MISSED — Inc-vs-LLC defect on the Named Insured |
| 28 | FreeText | — | *"okay... where were these on the CGL and Auto policies?"* | ❌ MISSED — cross-policy NI inconsistency (GAP-20) |
| 32 | Highlight ×3 | red | `B. Exclusions` / `2. Contractual` / `Liability assumed under any contract or agreement.` | ❌ MISSED — Contractual Liability assumption exclusion |
| 33 | Highlight | red | `5. Fellow Employee` | ❌ MISSED — Fellow Employee Exclusion |
| 38 | Highlight ×2 | red + cyan | `excess for non-owned auto` / `primary for any liability assumed under an "insured contract"` | ❌ MISSED — Other Insurance / "primary insured contract" carve-back |
| 39 | Highlight | orange | `C. "Bodily injury" means bodily injury, sickness or disease …` (no Mental Anguish) | ❌ MISSED — BI definition omits Mental Anguish |
| 44 | Highlight | orange | `BLANKET WHERE REQUIRED BY WRITTEN CONTRACT 30` (cancellation notice 30) | ❌ MISSED — cancellation 30-day, presentation flagged as inadequate |
| 47 | Highlight | cyan | `BLANKET WHERE REQUIRED BY WRITTEN CONTRACT` (Waiver of Subrogation) | ❌ MISSED — Blanket WOS by contract (Good) |
| 48 | Highlight | cyan | `60 days before the effective date of cancellation if we cancel for any other reason.` | ❌ MISSED — 60-day cancel extension (Good) |
| 54 | Highlight | cyan | `20. MENTAL ANGUISH … "Bodily injury" … is replaced by the following …` | ❌ MISSED — Mental Anguish giveback (Good) |
| 61 | Highlight | orange | `30 days … nonrenewal` | ❌ MISSED — 30-day nonrenewal notice |

**Master coverage: 0 of 14 highlight/sticky-note items caught by v2.**

### B. Presentation claims for Auto

| Slide | Claim | App v2 catch? |
|---|---|---|
| 11 (Good) | BI definition includes Mental Anguish — pg 54 | ❌ MISSED (master pg54 confirms the giveback exists, v2 silent) |
| 12 (Good) | Other Insurance clause well-built — pg 38 | ❌ MISSED (master pg38 confirms, v2 silent) |
| 18 (Bad) | Auto cancellation 30 days (vs 90 expected) | ❌ MISSED — no v2 cancellation finding for Auto |
| 21 (Ugly) | Additional Named Insureds missing/partial; "LLC not INC" — pg 28 | ❌ MISSED — entity-naming + cross-policy NI gap |

**Presentation coverage: 0 of 4 Auto claims caught by v2.**

### C. Prior verification report

Not available for Auto.

## 4. GAP-XX SPECIFIC VERIFICATION

| GAP | Description | Status | Audited Page | Note |
|---|---|---|---|---|
| **GAP-17** | Maricopa $2M CSL breach + contract bars umbrella attachment for Auto | ❌ **MISSED** | — | Master sticky note on pg 24 articulates this exactly; v2 has zero findings about Maricopa, $2M, or umbrella-attachment limitation for Auto. The "Care, Custody, or Control" finding on pg 34 is a different issue (cargo, not CSL). |
| **GAP-18** | $500 electronic equipment sublimit (form 461-0155 §11) | ❌ **MISSED** | — | No v2 finding mentions $500, electronic equipment sublimit, or audio/visual cargo. Master also did not flag this (likely because the master audit predated GAP-18); but the KB file expects this catch. |
| **GAP-19** | Malina Trujillo named driver exclusion | ✅ **CAUGHT** | pg 9 (Bad, Risk 6) | v2 finding articulates the defect (Malina excluded) AND a consequence (HR/dispatch needs to know; insurance won't cover even an emergency). Misses the deeper "verify with insured: is Malina currently employed? has employment ended?" framing GAP-19 KB file emphasizes, but core defect + consequence are both there. |
| **GAP-20** | Lincoln Shields LLC + Black Mountain on Auto but missing from Umbrella's Multiple Named Insured endorsement 475-0174 | ❌ **MISSED** | — | Master pg 28 sticky note says *"okay... where were these on the CGL and Auto policies?"* — the cross-policy entity inconsistency is acknowledged. v2 has no Auto finding about this; the v2 ML finding on pg 105 does name Lincoln Shields/Black Mountain but for D&O Co-Defendant Extension (Good), not for cross-policy NI gap. |
| **GAP-21** | Auto missing 401-1235 Designated Entity NOC (when Pkg has it) | ❌ **MISSED** | — | v2 has no Auto finding about cancellation notice or Designated Entity. Master pg 44/48 highlights cancellation language but not the Designated Entity NOC asymmetry vs Commercial Package. Presentation slide 18 stops at the headline "30 days" without the cross-policy 401-1235 framing. |
| **GAP-01** | Inc-vs-LLC entity-type mismatch on Named Insured | ❌ **MISSED** | — | Master pg 28 rectangles around "RUNBECK ELECTION SERVICES INC, RUNBECK INVESTMENTS LLC, RUNBECK PROPERTIES LLC, RUNBECK GRAPHICS INC" — three different entity-type variations on the same endorsement. Presentation slide 21 also calls this out. v2 silent. |

**GAP-XX scorecard for Auto: 1 CAUGHT / 0 PARTIAL / 5 MISSED.**

## 5. POTENTIAL FALSE POSITIVES

The 3 v2 findings each verified against the policy text via the master:

- **pg 9 Malina Trujillo** — confirmed real; the master's redactions cluster around named-driver exclusion forms.
- **pg 28 HNOA Good** — confirmed real; master pg 28 doesn't mark this specifically but the policy does carry blanket HNOA via 461-0174.
- **pg 34 Care, Custody, Control** — confirmed real; ballot-transit cargo exclusion is standard auto language and is genuine for an election-services client. Slight padding risk — finding cites "$100K transit, $250K off-premises" property fallback which the master does not validate; defer to property-side review.

**No clear false positives.** Three legitimate findings, but the audit is dramatically narrower than the master ground truth supports.

## Summary for Auto

- **Master vs v2 catch rate: 0 of 14** master annotations / **0 of 4** presentation claims caught.
- **GAP-XX scorecard: 1/6 CAUGHT** (GAP-19 only).
- **Quality of catches: high** — the 3 findings are real and well-articulated.
- **Quantity gap is severe.** The biggest miss is GAP-17 (the $2M Maricopa CSL contract breach) — which has a verbatim master sticky note pointing right at it. This is an Ugly-tier, contract-breach-of-the-day finding that the v2 missed entirely.
- **Recommended next-session priority: investigate why GAP-17 didn't fire on Auto.** The KB file exists in `knowledge-base/universal/GAP-17-contract-specific-coverage-satisfaction.md`, the contract is in the program (Maricopa), and the master sticky note shows the defect was right there. The catch chain broke somewhere between contract extraction → policy analysis → cross-reference.
