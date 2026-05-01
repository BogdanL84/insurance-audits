# Comparison — Cyber (AmTrust)

**Slug:** `cyber` · **Audited PDF (v2):** `RedactedCyber_Assoc Industries.AmTrust_04.25-04.26 #AES123191302-AUDITED (1).pdf` (5 pages — declarations only)

## 1. SOURCES

| Source | Available | Notes |
|---|---|---|
| Presentation slides | ✅ | Slides 17 (Bad — phantom Cyber Deception), 22 (NI multi-policy), 32 (Maricopa $5M vs $4M) + 18 (cancellation, not specified for Cyber) |
| Prior verification report | ❌ | Cyber was in the "remaining 5 policies" list — never reached in prior sessions |
| Annotation-level master | ❌ | Only redacted copies on disk |
| App v1 (older Downloads run) | ✅ | 1 Text finding + 3 bookmarks |
| App v2 (today's Desktop run) | ✅ | 1 Text finding + 1 Highlight + 3 bookmarks |

**Note:** The audited PDF is only 5 pages. This is a Dec-page-only redacted copy — not the full Cyber policy. v2 had limited material to analyze.

## 2. APP V1 → V2 NET CHANGE

### UNCHANGED OR REWORDED (0)
None — v1 and v2 findings address different defects (per ambiguity confirmation).

### NEW IN V2 (1) — quality improvement per ambiguity confirmation
| Page | Cat | Score | Finding | Likely KB source |
|---|---|---|---|---|
| 4 | Ugly | 16 | Cyber — Social Engineering / Cyber Deception Coverage | **GAP-22 file directly responsible.** v2 articulates the $250K=$250K phantom-coverage math + government-vendor wire-fraud context. Major upgrade over v1. |

### REMOVED IN V2 (1) — Good ack lost (intentional, per ambiguity confirmation)
| v1 Page | v1 Title | v1 Cat/Score | Bucket |
|---|---|---|---|
| pg 3 | "Cyber Liability — Standalone Comprehensive Cyber Policy in Place" | Good | **Good-tier informational regression — but intentional.** v1's Good ack was superficial ("you have cyber"); v2 replaced it with the deeper $250K=$250K phantom-coverage analysis. Per user confirmation: this is the GAP-22 upgrade we wanted; document as a meaningful quality improvement, not a wash. |

**Net change for Cyber: +1 high-quality material catch, -1 low-value Good ack — net quality improvement.**

## 3. GROUND TRUTH COVERAGE

### A. Presentation claims for Cyber

| Slide | Claim | App v2 catch | Note |
|---|---|---|---|
| 17 (B3) | Cyber Deception $250K sublimit + $250K deductible — pg 7 | ✅ **CAUGHT** (pg 4 of redacted Dec) | Pages differ because audited PDF is 5-page Dec-only excerpt vs full policy 41-page; finding articulates the phantom-coverage math identically |
| 22 (U2) | Multi-policy NI missing | ❌ MISSED | v2 silent on Cyber's NI |
| 32 (U12) | Maricopa requires $5M, policy has $4M; doesn't sit under umbrella | ❌ MISSED | No v2 finding about Maricopa $5M shortfall or umbrella attachment |

**Presentation coverage: 1 of 3 caught.** The headline phantom-coverage finding caught well; the Maricopa $5M and NI items missed.

### B. Prior verification report

Not available for Cyber. Per Phase 2 confirmation, this is one of the policies without prior ground truth.

## 4. GAP-XX SPECIFIC VERIFICATION

| GAP | Description | Status | Audited Page | Note |
|---|---|---|---|---|
| **GAP-22a** | Cyber Deception $250K=$250K phantom coverage | ✅ **CAUGHT** | pg 4 (Ugly/16) | Finding articulates BOTH defect (sublimit = retention → effective $0 recovery on most losses) AND consequence (gov vendor wire-fraud = #1 attack vector, no real coverage). Recommendation cites alternate carriers (Coalition, At-Bay, Beazley). Direct hit on GAP-22 KB file. |
| **GAP-22b** | Defense Within Limits + Shared Aggregate erosion math | ❌ **MISSED** | — | KB file `GAP-22-cyber-dec-sheet-patterns.md` flags this pattern; no v2 finding addresses DWL erosion. The redacted Dec is only 5 pages so the v2 analyst may not have seen the relevant terms — but the underlying defect is in the full policy. |
| **GAP-22c** | $4M aggregate vs Maricopa $5M shortfall | ❌ **MISSED** | — | Presentation slide 32 calls this out exactly. No v2 finding mentions Maricopa, $5M, or aggregate-shortfall. This is a contract-breach finding that should have fired with GAP-17 (contract-specific coverage satisfaction) — same root failure as Auto's $1M vs $2M Maricopa miss. |
| **GAP-22d** | NY choice-of-law on AZ insured | ❌ **MISSED** | — | KB pattern about jurisdiction. v2 silent. Possibly outside the 5-page Dec excerpt. |
| **GAP-22e** | Proof of Loss $250K secondary sublimit | ❌ **MISSED** | — | KB pattern. v2 silent. |
| **GAP-22f** | Cyber is the ONLY policy with correct LLC entity name | ❌ **MISSED** | — | Per handoff: AmTrust Cyber's Policy Change #1 (4/1/2025) corrected the NI to "Runbeck Election Services LLC" — making Cyber the only correctly-titled policy in the program. This is a strong asymmetry finding (informational on Cyber, Risk 24/25 on the OTHER 6 policies). v2 missed entirely — across both this policy AND the others. |

**GAP-XX scorecard for Cyber: 1 CAUGHT / 0 PARTIAL / 5 MISSED.** The headline phantom-coverage catch is solid; everything else in GAP-22 missed.

## 5. POTENTIAL FALSE POSITIVES

The 1 v2 finding (Cyber Deception $250K=$250K, Ugly/16) verifies against the presentation and the GAP-22 KB file. **No false positives.** Strong, well-articulated catch — quantifies the loss-recovery math and names target restructure terms.

## Summary for Cyber

- **v1→v2 net: +1 high-quality material catch (Ugly/16), -1 low-value Good ack — net quality improvement** per ambiguity confirmation.
- **Presentation coverage: 1/3 caught.** Headline phantom-coverage caught; Maricopa $5M and NI missed.
- **No prior report comparison available** (Cyber was in the "remaining" set).
- **GAP-XX scorecard: 1 CAUGHT (phantom math) / 5 MISSED.**
- **Net assessment:** Single biggest GAP-22 win is on the table — the social-engineering phantom finding is a poster-child for KB-driven catches. But the broader GAP-22 catalog (DWL, Maricopa $5M, NY choice-of-law, Proof of Loss, LLC asymmetry) didn't fire. Possibly limited by the 5-page Dec excerpt — investigate whether the audit ran on the truncated version vs the full policy. Also: the Maricopa $5M shortfall is a contract-breach finding paired with the Auto $2M miss; both point to the same systemic GAP-17 failure to surface contract-vs-policy limit comparisons.
