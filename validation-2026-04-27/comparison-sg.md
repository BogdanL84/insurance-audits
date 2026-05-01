# Comparison — Security Guards Liability (Arch Insurance)

**Slug:** `sg` · **Audited PDF (v2):** `Redacted2025-2026 Liability Policy - Security Guards-AUDITED (1).pdf` (69 pages)

## 1. SOURCES

| Source | Available | Notes |
|---|---|---|
| Presentation slides | ✅ | Slides 13 (Good), 15 (Bad), 22 (NI multi-policy) + 18 (cancellation) |
| Prior verification report | ✅ | Handoff + interim-report-batch1 |
| Annotation-level master | ❌ | Only redacted copies on disk |
| App v1 (older Downloads run) | ✅ | 1 Text finding + 3 bookmarks |
| App v2 (today's Desktop run) | ✅ | 1 Text finding + 1 Highlight + 3 bookmarks |

## 2. APP V1 → V2 NET CHANGE

### UNCHANGED OR REWORDED (1) — per ambiguity confirmation
| v1 Title | v2 Title | Note |
|---|---|---|
| pg 40 "GL — Security Guard Policy Covers Security Operations Only; Not Core Election Services" (Bad/4) | pg 40 "General Liability — Classification Limitation on Arch Policy" (Ugly/12) | **Same defect — the Arch policy is scope-limited to security ops and doesn't cover core election services. Score upgrade Bad/4 → Ugly/12 reflects KB cleanup recalibrating from "informational" to "material" — defensible since the policy is ineffective for the business' actual operations.** |

### NEW IN V2 (0)
None.

### REMOVED IN V2 (0)
None.

**Net change for SG: 0 NEW, 1 score upgrade (4→12 / Bad→Ugly), 0 regressions.**

## 3. GROUND TRUTH COVERAGE

### A. Presentation claims for SG

| Slide | Claim | Prior verdict | App v2 catch |
|---|---|---|---|
| 13 (G4) | AI + P/NC at pp 59-60 — "Great" | ⚠ CITES OFF BY ONE — pg 60 P/NC ✓, pg 61 AI ongoing ops ✓, separate CG 20 37 AI completed ops ✓; presentation undersold — full AI suite present | ❌ MISSED — v2 has no Good ack of the AI/P/NC suite |
| 15 (B1) | Wrongful acts — "broad definition" — pp 23/26 | ⚠ CITES WRONG (pg 23 is Canine; definition at pg 27); narrowness, not broadness, is the actual problem (only declared services covered) | ❌ MISSED — v2 has no finding on wrongful-acts/Coverage D sublimit structure |
| 18 (B4) | SG cancellation 60 days | ✓ CORRECT (AZ state endorsement pp 15-16) | ❌ MISSED — no cancellation finding |
| 22 (U2) | Multi-policy NI missing | (general) | ❌ MISSED — no entity-naming finding |

**Presentation coverage: 0 of 4 SG claims caught.**

### B. Prior verification report claims

| Prior finding | App v2 catch | Note |
|---|---|---|
| Security Guard policy covers security ops only; not core election services (Bad/4) | ✅ CAUGHT + UPGRADED to Ugly/12 (pg 40) | Same defect, recalibrated severity |
| Wrongful acts paid only under Coverage D sublimit (NOT Coverage A BI/PD) | ❌ MISSED | Handoff B1 verified; v2 silent on the Coverage A/D split |
| AI/P/NC suite at pp 60-61 + CG 20 37 (Good — full suite present) | ❌ MISSED | A Good ack worth surfacing for the client meeting |
| Cancellation 60 days (verified) | ❌ MISSED | |

**Prior-report coverage: 1 of 4 caught.** Three uncaught — including a notable Good ack (full AI suite) the client meeting could use.

## 4. GAP-XX SPECIFIC VERIFICATION

| GAP | Description | Status | Audited Page | Note |
|---|---|---|---|---|
| GAP-01 EXPANDED | Inc-vs-LLC entity-type mismatch on SG Dec | ❌ **MISSED** | — | Per handoff, SG is in the entity-naming-error pattern set. Presentation slide 22 includes SG in the "Multiple Policies" NI gap. v2 silent. |

## 5. POTENTIAL FALSE POSITIVES

The 1 v2 finding (Classification Limitation, Ugly/12) verifies against the policy. **No false positives.** Score recalibration from 4 → 12 is defensible given the policy is functionally inoperative for the client's core operations.

## Summary for SG

- **v1→v2 net: 0 NEW, 1 score upgrade (Bad/4 → Ugly/12), 0 regressions.**
- **Prior-report coverage: 1/4** — only the headline finding caught.
- **Presentation coverage: 0/4** — including the Good AI/P/NC suite ack that's missing from v2.
- **GAP-XX scorecard: 0 CAUGHT / 0 PARTIAL / 1 MISSED.**
- **Net assessment:** Mild improvement (severity recalibration). The Coverage A/D wrongful-acts split is a notable miss — that's the substance of presentation slide 15. Recommend KB tweaks for: wrongful-acts coverage triggers, AI/P/NC suite recognition (Good ack worth surfacing), cross-policy entity audit.
