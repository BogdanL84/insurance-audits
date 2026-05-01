# Comparison — Hanover Commercial Umbrella

**Slug:** `umb` · **Audited PDF (v2):** `RedactedHanover - Commercial Umbrella - 4.1.25-4.1.26-AUDITED (1).pdf` (78 pages)

## 1. SOURCES

| Source | Available | Notes |
|---|---|---|
| Presentation slides | ✅ | Slides 25 (NI multi-policy), 27 (Horizontal Exhaustion) + 18 (cancellation) |
| Prior verification report | ❌ | Umbrella was in the "remaining 5 policies" — never reached |
| Annotation-level master | ❌ | Only redacted copies on disk |
| App v1 (older Downloads run) | ✅ | 1 Text finding + 3 bookmarks |
| App v2 (today's Desktop run) | ✅ | 1 Text finding + 1 Highlight + 3 bookmarks |

## 2. APP V1 → V2 NET CHANGE

### UNCHANGED OR REWORDED + EXPANDED (1) — per ambiguity confirmation
| v1 Title | v2 Title | Note |
|---|---|---|
| pg 36 "Professional Liability — No Umbrella Excess Coverage Over Tech [E&O]" (Ugly/20) | pg 31 "Umbrella — Professional Liability, Cyber, and D&O Excluded" (Ugly/15) | **REWORDED + EXPANDED.** Same root defect (Umbrella doesn't sit over Pro Liability), but v2 broadens detection from one excluded coverage (PL) to three (PL + Cyber + D&O). This is **GAP-08 EXPANDED working as designed** — the KB file expanded from a single-line PL finding into a tower-coordination finding. Score nominally dropped 20→15; defensible because v1 was on the high end for a follow-form gap and v2 is calibrated for what the missing-excess actually risks. |

### NEW IN V2 (0)
None.

### REMOVED IN V2 (0)
None.

**Net change for Umb: 0 NEW count change, 1 reworded with expanded coverage detection (PL → PL + Cyber + D&O), score recalibration 20→15.** Quality improvement via broader pattern-matching.

## 3. GROUND TRUTH COVERAGE

### A. Presentation claims for Umb

| Slide | Claim | App v2 catch | Note |
|---|---|---|---|
| 18 (B4) | Umbrella cancellation 60 days | ❌ MISSED | No cancellation finding |
| 25 (U5) | Multi-policy NI missing on Umbrella; "LLC not INC" | ❌ MISSED | v2 silent on Umbrella NI. Per handoff: Umbrella's Multiple Named Insured endorsement 475-0174 should list every entity — likely doesn't. |
| 27 (U7) | Causes Horizontal Exhaustion — pg 37 | ⚠ **PARTIAL** | v2's pg 31 finding is about which underlying coverages the umbrella sits over (PL/Cyber/D&O excluded). It does not specifically address horizontal exhaustion (the requirement that ALL underlying policies be exhausted before umbrella drops down). The presentation's claim and v2's finding are related but address different mechanics. |

**Presentation coverage: 0/3 fully caught, 1 partial.** The Horizontal Exhaustion claim and the v2 finding are adjacent issues but not the same.

### B. Prior verification report

Not available for Umbrella.

## 4. GAP-XX SPECIFIC VERIFICATION

| GAP | Description | Status | Audited Page | Note |
|---|---|---|---|---|
| **GAP-08a** | Schedule of Underlying Policies blank lines for Tech E&O / D&O | ⚠ **PARTIAL** | pg 31 | v2 finding identifies that the Umbrella excludes PL/Cyber/D&O — which is the *consequence* of the Schedule of Underlying being blank for those lines. But v2 doesn't articulate the *mechanism* (Form 475-0031 PL Exclusion, Coverage B Section VII.3.k, blank Schedule lines f and g) that the GAP-08 EXPANDED KB file calls out specifically. CAUGHT the headline; PARTIAL on the structural detail. |
| **GAP-08b** | Hanover Umbrella does NOT sit over Convex Tech E&O (cross-tower coordination) | ❌ **MISSED** | — | v2 makes no connection between the Umbrella and the Convex policy. The recommendation says "build a proper excess tower" but doesn't reference Convex by name as the existing partial-tower above PL. |
| **GAP-08c** | Coverage B direct exclusions strip professional services | ❌ **MISSED** | — | v2 lists "Professional Liability, Cyber, and D&O Excluded" without specifying that the Coverage B exclusions are *direct* exclusions (not just follow-form gaps). Important nuance for renewal positioning. |

**GAP-XX scorecard for Umbrella: 0 CAUGHT / 1 PARTIAL (GAP-08a) / 2 MISSED.** GAP-08 EXPANDED partially fired but didn't reach the structural depth the KB file targets.

## 5. POTENTIAL FALSE POSITIVES

The 1 v2 finding verifies. **No false positives.** The recommendation ("build a proper excess tower above the management liability and cyber primaries") is appropriately framed for the CFO audience.

## Summary for Umb

- **v1→v2 net: 0 NEW count change, but 1 finding expanded scope from PL-only to PL+Cyber+D&O.** GAP-08 EXPANDED working at the broad level, partially at the depth level.
- **Presentation coverage: 0/3 (1 partial).** Horizontal Exhaustion (slide 27) caught at the headline level but missing the specific mechanic.
- **GAP-XX scorecard: 0 CAUGHT / 1 PARTIAL / 2 MISSED.**
- **Net assessment:** Mild positive. The expansion from PL-only to PL+Cyber+D&O is a real improvement, but the structural detail (blank Schedule of Underlying lines, Coverage B direct exclusions, Convex-tower coordination) didn't surface. Recommend: KB tweak to make GAP-08 EXPANDED extract the Schedule of Underlying form and identify blank lines explicitly + cross-reference any policies in the program above the umbrella threshold.
