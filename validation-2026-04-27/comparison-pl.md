# Comparison — Professional Liability / E&O (Gemini / WR Berkley)

**Slug:** `pl` · **Audited PDF (v2):** `Redacted2025 - 2026 Professional Liability Policy-AUDITED (1).pdf` (46 pages)

## 1. SOURCES

| Source | Available | Notes |
|---|---|---|
| Presentation slides | ✅ | Slides 16, 23, 26, 33, 34 + cancellation slide 18 |
| Prior verification report | ✅ | Handoff + interim-report-batch2-eo (full E&O verification) |
| Annotation-level master | ❌ | Only redacted copies on disk |
| App v1 (older Downloads run) | ✅ | 2 Text findings + 4 bookmarks |
| App v2 (today's Desktop run) | ✅ | 6 Text findings + 5 Highlight + 9 bookmarks |

## 2. APP V1 → V2 NET CHANGE

### UNCHANGED OR REWORDED (2)
| v1 Title | v2 Title | Note |
|---|---|---|
| pg 20 "Professional Liability — Mail Processing Services Retroactive" (Ugly/12) | pg 20 "Professional Liability — Mail Processing Services Restricted Retroactive Date" (Ugly/15) | Score upgrade 12→15. Same defect. |
| pg 27 "Professional Liability — Network Security/Privacy Breach Excluded" (Ugly/20) | pg 45 "Professional Liability — Network Security & Privacy Breach Exclusion" (Ugly/20) | Same defect at the broader Privacy/Network exclusion form (pg 45 is the form itself; v1 cited the carve-out at pg 27). Page choice in v2 is more accurate. |

### NEW IN V2 (4) — meaningful KB-cleanup wins
| Page | Cat | Score | Finding | Likely KB source |
|---|---|---|---|---|
| 23 | Ugly | 12 | Professional Liability — Split Limits of Liability Tower | This was a **handoff "MISSED BY V1"** finding — KB cleanup added a real catch. The hidden $1M effective limit on pre-2019 acts is a major substantive find. |
| 27 | Ugly | 16 | Professional Liability — Ransomware / Extortion Exclusion | New catch — closes the "PL excludes extortion" gap that pairs with Cyber's social-engineering finding |
| 34 | Bad | 9  | PL Hammer Clause — Dual Structure (50/50 in SIR Context) | New catch — captures the SIR/deductible split-hammer mechanic |
| 45 | Ugly | 15 | Professional Liability — Biometric Identifiers Exclusion (BIPA) | New catch — Illinois BIPA + state equivalents, $1K/$5K per person statutory damages |

### REMOVED IN V2 (0)
None. v2 retains every v1 finding (with reworded titles).

**Net change for PL: +4 NEW catches (3 Ugly + 1 Bad), 1 score upgrade, 0 regressions.** This is the largest improvement in the v1→v2 set.

## 3. GROUND TRUTH COVERAGE

### A. Presentation claims for PL

| Slide | Claim | Prior verdict | App v2 catch |
|---|---|---|---|
| 16 (B2) | Tech services carve-back at pp 25/26 | ⚠ CITES OFF BY ONE (pp 26-27) | ❌ MISSED in v2 — no specific finding on the tech-carve-back exclusions A/B/D/E/F |
| 18 (B4) | E&O cancellation 60 days | ✓ correct | ❌ MISSED — no v2 cancellation finding for PL |
| 23 (U3) | Multi-policy NI missing | (general) | ❌ MISSED — no entity-naming finding on PL |
| 26 (U6) | AI defense-only no indemnity at pg 20 | ⚠ CITE OFF (lives at pg 21); substance ✓ | ❌ MISSED — v2 has no AI-scope finding for PL |
| 33 (U13) | Recall/reprinting exclusion at pg 23 | ⚠ CITE WRONG (pg 23 is Split Limits; recall at pg 24) — but presentation overstated; the real bar is Loss-definition carve-outs at pg 15 | ❌ MISSED — but v2 caught the Split Limits finding at pg 23 (the real significance of that page) |
| 34 (U14) | NI listed as AI; no counties; pg 27 wrong | ⚠ MOSTLY WRONG (pg 27 is Tech Services not AI; real issues distributed across pp 5/28/31/37) | ❌ MISSED — v2 has no AI/NI scope finding for PL |

**Presentation coverage: 0 of 6 PL claims caught directly by v2.** However, v2's Split Limits catch (pg 23) is on the same page the presentation incorrectly cited for recall — which means **v2 found the right defect at the page the presentation pointed to, even though the presentation thought it was a different defect**.

### B. Prior verification report claims

| Prior finding | App v2 catch | Note |
|---|---|---|
| Tech services carve-back (hardware malfunction, electrical, delay, ISP) at pp 26-27 | ❌ MISSED | Verbatim language not in any v2 finding |
| Mail processing restricted retro 4/1/2021 at pg 20 | ✅ CAUGHT (pg 20, Ugly/15) | Caught in both v1 and v2; score upgrade in v2 |
| Network Security / Privacy Breach + BIPA at pp 45-46 | ✅ CAUGHT (pg 45, Ugly/20 + Ugly/15 BIPA) | v2 splits into 2 separate findings — Network/Privacy AND BIPA — better catalog granularity |
| Blanket AI: Claim Expenses only, no Loss; "solely" arising | ❌ MISSED | Handoff U6 verified; v2 silent |
| Split Limits $1M/$1M / +$1M xs $1M / +$3M xs $2M trigger-date buckets at pg 23 | ✅ **CAUGHT** (pg 23, Ugly/12) — was MISSED BY V1 | **Major v2 win** — KB cleanup directly addressed this gap |
| M&A auto-termination at pp 17-18 | ❌ STILL MISSED | Handoff flagged as MISSED BY V1; still missed in v2 |
| AZ guaranty fund disclaimer (Gemini surplus lines) at pg 3 | ❌ STILL MISSED | KB universal/GAP-22 cyber file mentions surplus-lines/non-admitted carrier — could apply to PL too but didn't fire |
| Mandatory binding arbitration in Chicago at pg 18 | ❌ STILL MISSED | |
| ERP pricing 75/125/175% of annual ≈ $188k for 36-mo on $107k premium | ❌ STILL MISSED | Tail-cost specifics; useful for renewal posture |

**Prior-report coverage: 3 of 9 caught (33%).** v2 added the Split Limits catch (a known prior gap). 6 prior items remain uncaught.

## 4. GAP-XX SPECIFIC VERIFICATION

| GAP | Description | Status | Audited Page | Note |
|---|---|---|---|---|
| GAP-01 EXPANDED | Inc-vs-LLC entity-type mismatch on PL Dec | ❌ **MISSED** | — | Per handoff, PL Dec reads "Runbeck Election Services, **Inc.**" — third policy with this error. Presentation slide 23 lists PL among the entity-naming-error set. v2 silent. |
| GAP-22 (cross-applies from Cyber) | PL excludes ransomware (which Cyber sublimits at $250K=$250K → no excess) | ✅ **CAUGHT** | pg 27 | v2 finding "Professional Liability — Ransomware / Extortion Exclusion" articulates the defect AND consequences (calls out the $4M cyber aggregate must cover everything). Pairs cleanly with the Cyber GAP-22 catch. |

## 5. POTENTIAL FALSE POSITIVES

All 6 v2 findings verify against the policy via the prior report. **No false positives.** Two notable strengths:

- **Split Limits catch** is well-articulated — calls out the trigger-date buckets explicitly and quantifies the hidden $1M effective limit on pre-2019 acts.
- **BIPA + Network/Privacy split** improves catalog granularity over v1's single combined finding.

## Summary for PL

- **v1→v2 net: +4 NEW catches (3 Ugly, 1 Bad), 1 score upgrade, 0 regressions.** Largest single-policy improvement.
- **Prior-report coverage: 3/9 caught** — v2 closes the Split Limits gap; 6 still missed.
- **Presentation coverage: 0/6** — but v2 found the right defect at pg 23 even though presentation cited it for the wrong reason.
- **GAP-XX scorecard: 1 CAUGHT (Ransomware / GAP-22 cross-apply), 0 PARTIAL, 1 MISSED (GAP-01).**
- **Net assessment:** Strongest demonstration in this validation that the KB cleanup moved the needle. The Split Limits catch alone is a significant client-facing improvement. Remaining work: AI scope (defense-only, "solely arising"), tech-services carve-back exclusions A/B/D, surplus-lines guaranty fund disclaimer, M&A auto-termination, mandatory arbitration, ERP pricing.
