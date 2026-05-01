# Comparison — Hanover Commercial Package

**Slug:** `pkg` · **Audited PDF (v2):** `RedactedHanover - Commercial - 4.1.25-4.1.26-AUDITED (1).pdf` (254 pages)

## 1. SOURCES

| Source | Available | Notes |
|---|---|---|
| Presentation slides | ✅ | Slides 24 (NI), 28 (BPP exclusions), 29 (BI / equipment breakdown), 30 (BI / unfinished stock), 31 (Ordinance or Law) + 18 (cancellation) |
| Prior verification report | ❌ | Pkg was the largest of the "remaining 5 policies" — never reached |
| Annotation-level master | ❌ | Only redacted copies on disk |
| App v1 (older Downloads run) | ✅ | 1 Text finding + 3 bookmarks |
| App v2 (today's Desktop run) | ✅ | 4 Text findings + 4 Highlight + 7 bookmarks |

## 2. APP V1 → V2 NET CHANGE

### UNCHANGED OR REWORDED (1)
| v1 Title | v2 Title | Note |
|---|---|---|
| pg 144 "Commercial Property — Electronic Data and Computer Operation" (Bad/9) | pg 144 "Property — Electronic Data Sublimit" (Bad/9) | v1 combined the two related sublimits in one finding; v2 split into Electronic Data (pg 144) + Interruption of Computer Operations (pg 158). The v1 catch maps to v2's pg 144 finding. |

### NEW IN V2 (3)
| Page | Cat | Score | Finding | Likely KB source |
|---|---|---|---|---|
| 137 | Good | — | Property — Equipment Breakdown Limit Adequacy | New Good ack — $49M equipment breakdown with cyber-caused-damage exclusion noted |
| 158 | Bad | 9 | Property — Interruption of Computer Operations Sublimit | Split out from the v1 combined finding — better catalog granularity |
| 205 | Bad | 6 | Per-Project Aggregate Cap Limitation | New catch — $2M policy aggregate cap applies above per-project aggregates |

### REMOVED IN V2 (0)
None.

**Net change for Pkg: +3 NEW (1 Good + 2 Bad), 0 score changes, 0 regressions, 1 finding split into two for granularity.** Quality improvement on count and structure.

## 3. GROUND TRUTH COVERAGE

### A. Presentation claims for Pkg

| Slide | Claim | App v2 catch | Note |
|---|---|---|---|
| 18 (B4) | Pkg cancellation 45 days | ❌ MISSED | No cancellation finding |
| 24 (U4) | Multi-policy NI missing — Pkg | ❌ MISSED | No entity-naming finding |
| 28 (U8) | BPP excludes fire, smoke, lightning, windstorm, hail — pg 130 | ❌ MISSED | This is the headline Ugly Property finding from the presentation. No v2 catch. |
| 29 (U9) | No BI for revenue loss from equipment breakdown — pg 130 | ⚠ **PARTIAL** | v2 has a Good ack on equipment breakdown limits at pg 137 but not the BI carve-out the presentation flagged. The Good and Bad are at different pages and address different facets — v2 did not catch the BI exclusion. |
| 30 (U10) | No BI for unfinished stock; finished stock $100K sublimit — pp 179-180/75 | ❌ MISSED | No v2 finding on stock sublimits |
| 31 (U11) | Ordinance or Law exclusion for building reconstruction — pg 175 | ❌ MISSED | No v2 finding on Ord-or-Law |

**Presentation coverage: 0 of 6 caught (1 partial overlap at different page).** The four headline Ugly findings from the presentation (slides 28-31) all missed in v2.

### B. Prior verification report

Not available for Pkg.

## 4. GAP-XX SPECIFIC VERIFICATION

| GAP | Description | Status | Audited Page | Note |
|---|---|---|---|---|
| **GAP-20a** | Properties LLC missing from CGL but present on Auto/Umbrella/Cyber | ❌ **MISSED** | — | Per handoff context: this is exactly the pattern GAP-20 KB file expects — same entity present on some policies, missing from others. v2 silent on entity coverage on the CGL side. |
| **GAP-20b** | Cross-policy entity inconsistency pattern (Lincoln Shields / Black Mountain) | ❌ **MISSED** | — | v2 ML pg 105 names them as Co-Defendant Extension on D&O (Good); no Pkg-side finding about CGL entity inclusion. |
| **GAP-21** | Designated Entity NOC 401-1235 details (Pkg has it; pairs with GAP-21 Auto-missing finding) | ❌ **MISSED** | — | Per Auto's GAP-21: "Pkg has 401-1235 Designated Entity NOC for 8 customer counties; Auto does not." v2 silent on the 401-1235 form on either side. |
| GAP-01 EXPANDED | Inc-vs-LLC entity-type mismatch on Pkg Dec | ❌ **MISSED** | — | Per presentation slide 24, Pkg is in the entity-naming-error pattern set. v2 silent. |

**GAP-XX scorecard for Pkg: 0 CAUGHT / 0 PARTIAL / 4 MISSED.**

## 5. POTENTIAL FALSE POSITIVES

All 4 v2 findings verify against standard Hanover Commercial Package language. **No false positives.** Per-Project Aggregate Cap Limitation (pg 205, Bad/6) is a slightly soft catch — the $2M cap is mitigated by the $10M umbrella attaching at $2M, which v2 acknowledges in the recommendation. Score 6 is appropriately calibrated to reflect the umbrella mitigation.

## Summary for Pkg

- **v1→v2 net: +3 NEW (1 Good + 2 Bad), 1 finding split for better granularity, 0 regressions.**
- **Presentation coverage: 0/6.** All four presentation Ugly findings (BPP exclusions, BI/equipment-breakdown, BI/unfinished-stock, Ord-or-Law) missed.
- **No prior report.**
- **GAP-XX scorecard: 0 CAUGHT / 0 PARTIAL / 4 MISSED.**
- **Net assessment:** The new catches (Per-Project Aggregate, computer-ops sublimit split) are useful additions, but the four headline presentation findings (the Ugly Property findings from slides 28-31) all missed. These are first-party property exclusions that the GAP-XX KB files don't specifically target — likely a coverage-area where the property KB content needs strengthening. Recommend KB additions for: BPP cause-of-loss exclusions, BI/equipment-breakdown carve-outs, BI/unfinished-stock sublimit detection, Ordinance-or-Law exclusion patterns.
