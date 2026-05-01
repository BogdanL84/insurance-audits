# Comparison — Hanover Workers' Compensation

**Slug:** `wc` · **Audited PDF (v2):** `redacted - Hanover - WC - 4.1.25-4.1.26-AUDITED (1).pdf` (206 pages)

## 1. SOURCES

| Source | Available | Notes |
|---|---|---|
| Presentation slides | ✅ | Slide 23 (NI multi-policy) + 18 (cancellation) |
| Prior verification report | ✅ | Handoff + interim-report-batch1 |
| Annotation-level master | ❌ | Only redacted copies on disk |
| App v1 (older Downloads run) | ✅ | 4 Text findings + 7 bookmarks |
| App v2 (today's Desktop run) | ✅ | 4 Text findings + 4 Highlight + 7 bookmarks |

## 2. APP V1 → V2 NET CHANGE

### UNCHANGED OR REWORDED (3) — per ambiguity confirmation
| v1 Title | v2 Title | Note |
|---|---|---|
| pg 61 "Workers' Comp — Favorable EMR of 0.690 — Strong Safety" (Good) | pg 133 "Workers' Comp — Experience Modification Rate" (Good) | Same finding, page changed (61→133), wording streamlined. EMR 0.69 detail still in content body. |
| pg 61 "Workers' Comp — Multi-State Coverage with Stop Gap" (Good) | pg 109 "WC — Stop Gap for Monopolistic States" (Good) | Same finding, page changed (61→109), reframed around the 4 monopolistic states (ND, OH, WA, WY). |
| pg 114 "Workers' Comp — Waiver of Subrogation Gap in GA, NC, IL" (Bad/9) | pg 114 "Workers' Compensation — Waiver of Subrogation Gap (GA, NC, IL)" (Bad/9) | Identical defect, same page, same score. Pure rewording. |

### NEW IN V2 (1)
| Page | Cat | Score | Finding | Likely KB source |
|---|---|---|---|---|
| 148 | Bad | 8 | California Employers' Liability — Labor Code §2810.3 Exclusion | Net new catch — California labor-contractor liability for staffing-vendor non-compliance |

### REMOVED IN V2 (1) — REGRESSION
| v1 Page | v1 Title | v1 Cat/Score | Bucket |
|---|---|---|---|
| pg 137 | "WC — Ownership Change Reporting Obligation Critical for PE-Backed" | Bad / 6 | **MATERIAL REGRESSION (Bad-tier).** Was a PE-backed-relevant catch; gone in v2. Per user instruction: flag prominently in rollup, add to next-session punch list, "investigate KB cause." |

**Net change for WC: +1 NEW (CA Labor Code §2810.3), 0 score changes, 1 material regression (Ownership Change Reporting).** Net = wash on count, with regression on PE-relevance dimension.

## 3. GROUND TRUTH COVERAGE

### A. Presentation claims for WC

| Slide | Claim | Prior verdict | App v2 catch |
|---|---|---|---|
| 18 (B4) | WC cancellation 30 days | ✓ CORRECT (pg 149) | ❌ MISSED — no cancellation finding |
| 23 (U3) | Multi-policy NI missing | Per handoff: "ELECTION SERVICES INC" appears on 18 state schedules; Dec page redacted; "RUNBECK" appears once — UNDERSTATED in presentation, deserves standalone slide | ❌ MISSED — v2 has no entity-naming finding for WC |

**Presentation coverage: 0 of 2 WC claims caught.**

### B. Prior verification report claims

| Prior finding | App v2 catch | Note |
|---|---|---|
| Favorable EMR 0.690 — Good | ✅ CAUGHT (pg 133) — reworded |
| Multi-state with Stop Gap — Good | ✅ CAUGHT (pg 109) — reworded |
| Waiver of Subrogation gap GA/NC/IL — Bad/9 | ✅ CAUGHT (pg 114) |
| Ownership Change Reporting Obligation — Bad/6 (PE-critical) | ❌ **REGRESSION** — was caught in v1, gone in v2 |
| Cancellation 30 days — verified | ❌ MISSED |
| NI: "ELECTION SERVICES INC" on 18 state schedules; standalone slide warranted | ❌ MISSED |

**Prior-report coverage: 3 of 6 caught (50%).** One regression (Ownership Change). Two presentation-flagged items still uncaught (cancellation, NI inconsistency).

## 4. GAP-XX SPECIFIC VERIFICATION

| GAP | Description | Status | Audited Page | Note |
|---|---|---|---|---|
| GAP-01 EXPANDED | Inc-vs-LLC entity-type mismatch on WC (state schedules say "ELECTION SERVICES INC") | ❌ **MISSED** | — | Per handoff, WC has "ELECTION SERVICES INC" on 18 pages of state schedules. Presentation slide 23 calls it out. v2 silent on the entity-naming defect — only handles the substantive coverage findings. |

## 5. POTENTIAL FALSE POSITIVES

All 4 v2 findings verify. **No false positives.** The Labor Code §2810.3 catch is well-articulated — names the statute, identifies staffing-vendor exposure, recommends COI-currency monitoring.

## Summary for WC

- **v1→v2 net: +1 NEW (CA Labor Code §2810.3), 1 material regression (Ownership Change Reporting / PE-critical).** Net = 0 on count.
- **Prior-report coverage: 3/6.** Two genuine misses (cancellation, NI inconsistency) + one regression.
- **Presentation coverage: 0/2.**
- **GAP-XX scorecard: 0 CAUGHT / 0 PARTIAL / 1 MISSED.**
- **Net assessment:** Trade-off scenario. v2 added a genuine new catch (CA staffing exposure, important for election-cycle temp use) but lost the PE-critical Ownership Change Reporting finding. For a PE-backed client like Runbeck, the regression matters more than the new catch. **Highest-priority next-session investigation:** why did Ownership Change Reporting drop out? Was it a KB file deletion in cleanup, a confidence-threshold change, or a regression in the WC analysis chain?
