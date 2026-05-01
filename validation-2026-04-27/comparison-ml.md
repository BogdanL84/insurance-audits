# Comparison — Management Liability (Hartford / Twin City Fire)

**Slug:** `ml` · **Audited PDF (v2):** `Redacted2024-26 Management Liability Policy-AUDITED (1).pdf` (110 pages)

## 1. SOURCES

| Source | Available | Notes |
|---|---|---|
| Presentation slides | ✅ | Slides 10 (Good), 24 (NI multi-policy), 18 (cancellation) |
| Prior verification report | ✅ | Handoff + interim-report-batch1 — full verification |
| Annotation-level master | ❌ | Only redacted copies on disk |
| App v1 (older Downloads run) | ✅ | 6 Text findings + 10 bookmarks |
| App v2 (today's Desktop run) | ✅ | 4 Text findings + 3 Highlight + 8 bookmarks |

## 2. APP V1 → V2 NET CHANGE

### UNCHANGED OR REWORDED (4)
| v1 Title | v2 Title | Note |
|---|---|---|
| pg 15 "D&O — Wage & Hour: No Carrier Defense Duty" (Bad/9) | pg 36 "EPLI — Wage & Hour Defense Sublimit" (Bad/9) | **Quality improvement.** Relabel D&O→EPLI is more accurate (wage & hour is an employment claim → EPLI scope). Same defect, more useful framing for the client. |
| pg 74 "Management Liability — PE Co-Defendant Extension and Shadow Director" (Good) | pg 105 "PE Co-Defendant Extension on Management Liability" (Good) | Reworded, Lincoln Shields/Black Mountain explicitly named in v2 underlying highlight |
| pg 86 "D&O — Manufacturing/Professional Services Exclusion Bars Entity" (Ugly/12) | pg 86 "D&O Entity Coverage — Manufacturing & Professional Services Exclusion" (Ugly/20) | **Score upgrade 12→20.** Same defect, severity recalibrated to the catastrophic level it deserves for an election-services company. KB cleanup working. |
| pg 107 "D&O — Split Prior/Pending Date Leaves $1M Gap on Excess Layer" (Bad/12) | pg 107 "D&O — Split Prior/Pending Date on Excess Layer" (Bad/8) | Score downgrade 12→8 — defensible re-calibration; the gap is real but conditional on a 7.5-month window. |

### NEW IN V2 (0)
None. Every v2 finding maps to a v1 ancestor.

### REMOVED IN V2 — REGRESSIONS (2)
| v1 Page | v1 Title | v1 Cat/Score | Bucket |
|---|---|---|---|
| pg 60 | "Management Liability — Crime Coverage $2M Included in Package" | Good | **Good-tier informational regression** — lost a Good ack |
| pg 73 | "D&O — Entity Regulatory Proceedings Not Covered Unless Individual" | Bad / 12 | **MATERIAL REGRESSION** — Bad/12 finding gone in v2; relevant for election-services regulatory exposure (counties, AGs, FEC) |

**Net change for ML: 0 NEW, 1 score-improvement, 1 informational regression, 1 material regression.**

## 3. GROUND TRUTH COVERAGE

### A. Presentation claims for ML

| Slide | Claim | Prior report verdict | App v2 catch |
|---|---|---|---|
| 10 (G1) | Notice of Knowledge constricted to CEO/CFO only — pg 74 | ⚠ PAGE WRONG (lives at pp 20/25/42/58); substance ✓ | ❌ MISSED |
| 18 (B4) | ML cancellation 10 days | ⚠ PARTIAL (10-day non-pay only; 20-day for other per PP00H10700 pg 70) | ❌ MISSED |
| 24 (U4) | Multi-policy NI missing/partial | (no specific verification) | ❌ MISSED — v2 has no entity-naming finding for ML |

**Presentation coverage: 0 of 3 claims caught.**

### B. Prior verification report claims (handoff)

| Prior finding | Where (per handoff) | App v2 catch |
|---|---|---|
| Wage & Hour no carrier defense duty / sub-limit | p15 | ✅ CAUGHT (v2 pg 36 reworded EPLI Wage & Hour) |
| Crime coverage $2M Included | p60 (Good) | ❌ REMOVED IN V2 |
| Entity Regulatory Proceedings excluded | p73 (Bad/12) | ❌ REMOVED IN V2 — regression |
| PE Co-Defendant + Shadow Director | p74 (Good) | ✅ CAUGHT (v2 pg 105) |
| Mfg/Prof Services exclusion bars Entity | p86 (Ugly/12) | ✅ CAUGHT + UPGRADED (v2 pg 86, score 20) |
| Split Prior/Pending Date $1M gap on excess | p107 (Bad/12) | ✅ CAUGHT (v2 pg 107) |

**Prior-report coverage: 4 of 6 caught (67%).** Two regressions vs prior baseline.

## 4. GAP-XX SPECIFIC VERIFICATION

| GAP | Description | Status | Audited Page | Note |
|---|---|---|---|---|
| GAP-01 EXPANDED | Inc-vs-LLC entity-type mismatch caught here? | ❌ **MISSED** | — | v2 ML has no finding about NI entity-type. Per handoff, the ML dec is a candidate (handoff §"Inc not LLC" pattern). Presentation slide 24 calls it out. v2 silent. |
| Cross-coverage check | PE Co-Defendant finding mentions Lincoln Shields + Black Mountain by name (pg 105 highlight) | ✅ Names surface, but as Good D&O coverage, not as cross-policy NI inconsistency (GAP-20 framing) | pg 105 | Useful but doesn't substitute for GAP-20 |

**ML-specific GAP-XX scorecard: 0 CAUGHT / 0 PARTIAL / 1 MISSED** (only GAP-01-EXPANDED applies broadly here).

## 5. POTENTIAL FALSE POSITIVES

All 4 v2 findings verify against the policy text per the prior report. **No false positives.** The Mfg-Exclusion finding's recalibration to score 20 is well-supported; if anything it's still understated for an election-services company that ballet-prints AND services governments.

## Summary for ML

- **v1→v2 net: 0 NEW catches, 1 score improvement (Mfg Exclusion 12→20), 2 regressions (1 Good informational + 1 Bad material).**
- **Prior-report coverage: 4/6 caught.** Two regressions (Entity Regulatory Proceedings + Crime $2M ack).
- **Presentation coverage: 0/3.** Page-citation issues in the presentation are unresolved.
- **GAP-XX scorecard: 0 CAUGHT / 0 PARTIAL / 1 MISSED.**
- **Net assessment:** Quality is up (Mfg Exclusion calibration) but quantity is down. The Entity Regulatory Proceedings regression is the single biggest concern — that's a genuine coverage gap that disappeared from the v2 catalog. Investigate whether the post-cleanup KB reduced D&O detection coverage.
