# Validation Rollup — KB Cleanup v1 → v2 (Run-Test Election Services)

**Run date:** 2026-04-27 · **Policies analyzed:** 9 · **Contracts:** 4 (2 with insurance provisions) · **Ground truth sources combined:** presentation (37 slides), prior verification reports (4 of 9 policies), annotation master (Auto only), v1 baseline (8 of 9 policies), v2 (all 9).

---

# Section 1 — Headline answer

The KB cleanup moved the needle, but modestly and unevenly. Across 9 policies, v2 produced **25 sticky-note findings** vs v1's **17** — net **+8 (+47%)**, with **12 NEW catches** (4 Ugly, 6 Bad, 2 Good) offset by **4 regressions** (2 Bad, 2 Good). The clearest wins are Professional Liability (+4 NEW catches including the previously-missed Split Limits Tower at pg 23) and Cyber (the GAP-22 social-engineering phantom-coverage finding at pg 4). But against the highest-confidence ground truth available — the Auto Downloads master with 14 annotations and 10 hand-titled bookmarks — **v2 caught 0 of 14 master items**, and the flagship **GAP-17 contract-coverage-satisfaction file did not fire on its own example case (Maricopa $2M Auto CSL breach)**. Two material Bad-tier findings regressed (ML pg 73 Entity Regulatory Proceedings, WC pg 137 Ownership Change Reporting). The highest-priority next-session work is fixing a precondition failure: the app's contract-extraction step processed only 1 of 4 contracts and extracted 0 insurance requirements, which blocks GAP-17 / GAP-21 from firing on any policy regardless of how the KB files are written.

---

# Section 2 — v1 → v2 net change scorecard

| Slug | v1 count | v2 count | Net Δ | NEW (v2 only) | REMOVED (regressions) | Notes |
|---|---|---|---|---|---|---|
| auto | 0 | 3 | **+3** | 3 (1 Good + 2 Bad) | 0 | No v1 baseline; all NEW by definition. GAP-19 (Malina) caught. |
| convex | 1 | 1 | 0 | 0 | 0 | Score upgrade Bad/8 → Ugly/10. |
| cyber | 1 | 1 | 0 | 1 (Ugly/16 phantom) | 1 (Good intentional) | GAP-22 quality upgrade per user confirmation. |
| ml | 6 | 4 | **−2** | 0 | 2 (1 Bad/12 + 1 Good) | Two regressions; Mfg Exclusion score upgrade 12→20. |
| pkg | 1 | 4 | **+3** | 3 (1 Good + 2 Bad) | 0 | Granularity improvement; computer-ops sublimit split from v1 combined. |
| pl | 2 | 6 | **+4** | 4 (3 Ugly + 1 Bad) | 0 | Largest single-policy improvement. Split Limits Tower captured. |
| sg | 1 | 1 | 0 | 0 | 0 | Score upgrade Bad/4 → Ugly/12. |
| umb | 1 | 1 | 0 | 0 | 0 | GAP-08 EXPANDED scope: PL-only → PL+Cyber+D&O. |
| wc | 4 | 4 | 0 | 1 (Bad/8) | 1 (Bad/6 PE-critical) | Net wash on count; regression on PE dimension. |
| **TOTAL** | **17** | **25** | **+8** | **12** | **4** | |

**Category breakdown — NEW catches (12):**
| Category | Count | Findings |
|---|---|---|
| Ugly | 4 | Cyber phantom (16), PL Split Limits (12), PL Ransomware (16), PL BIPA (15) |
| Bad  | 6 | Auto Malina (6), Auto Ballot Transit (9), Pkg Computer Ops (9), Pkg Per-Project (6), PL Hammer Clause (9), WC CA Labor Code §2810.3 (8) |
| Good | 2 | Auto HNOA, Pkg Equipment Breakdown |

**Category breakdown — REMOVED (4):**
| Category | Count | Findings |
|---|---|---|
| Ugly | 0 | — |
| Bad  | 2 | ML Entity Regulatory Proceedings (12), WC Ownership Change Reporting (6) |
| Good | 2 | ML Crime $2M Included, Cyber Standalone Comprehensive ack (intentional trade) |

---

# Section 3 — Material regressions (action required)

| # | Policy | Page | Finding | v1 Cat/Score | Why it matters | Suspected KB cause |
|---|---|---|---|---|---|---|
| 1 | ML | pg 73 | "D&O — Entity Regulatory Proceedings Not Covered Unless Individual" | Bad / 12 | Election services are heavily regulated — counties, AGs, FEC, secretaries of state. The entity-coverage limitation on regulatory proceedings is a real exposure for a Runbeck-class operator. Was a Risk-12 catch in v1; gone in v2. | Possible: cleanup may have removed a D&O detection rule, or the prompt's coverage of "entity vs individual" insuring agreement nuance regressed. Investigate `do-epli/` KB content + the methodology block. |
| 2 | WC | pg 137 | "WC — Ownership Change Reporting Obligation Critical for PE-Backed" | Bad / 6 | Runbeck is PE-backed (Lincoln Shields, Black Mountain). The WC carrier requires ownership-change reporting; missing it can trigger policy cancellation or denial. Specifically PE-critical and was caught in v1. | Possible: the WC KB content focused on classification/state coverage and dropped the ownership-change pattern. Re-add explicit detection of WC ownership-change reporting clauses. |

**Both should be on the next-session punch list with KB-investigation flags.** Per user's instruction: investigate KB cause; if a deletion in cleanup is responsible, restore the relevant detection language; if a confidence-threshold change is responsible, recalibrate.

---

# Section 4 — Informational regressions (Good-tier validations lost)

| # | Policy | Page | Finding | v1 Category | Note |
|---|---|---|---|---|---|
| 1 | ML | pg 60 | "Management Liability — Crime Coverage $2M Included in Package" | Good | Ack of $2M Crime coverage — useful for the client meeting as a "you're covered here" confirmation. Lost without replacement. |
| 2 | Cyber | pg 3 | "Cyber Liability — Standalone Comprehensive Cyber Policy in Place" | Good | **INTENTIONAL TRADE** per user confirmation. v1's Good ack was superficial; v2 replaced it with the GAP-22 phantom-coverage Ugly/16 finding. Document as a quality improvement, not a wash. |

Lower stakes — these were validations, not defects — but the ML Crime-$2M ack is worth a follow-up to surface in client materials manually if the v3 audit doesn't restore it.

---

# Section 5 — GAP-XX scorecard

Per KB file we built or expanded, scoring CAUGHT / PARTIAL / MISSED across all per-policy comparison files.

| KB File | Patterns tested | CAUGHT | PARTIAL | MISSED | Status |
|---|---|---|---|---|---|
| **GAP-19** named-driver-exclusions | 1 (Malina Trujillo) | **1** | 0 | 0 | ✅ **DEMONSTRABLY FIRING** — clean catch on Auto pg 9 |
| **GAP-18** coverage-specific-sublimits | 4 (Auto $500 elec, Cyber $250K=$250K, Pkg Electronic Data, Pkg Computer Ops) | **3** | 0 | 1 | ✅ **DEMONSTRABLY FIRING** — Auto $500 elec equipment is the only miss |
| **GAP-22** cyber-dec-sheet-patterns | 6 (phantom, DWL, Maricopa $5M, NY choice-of-law, Proof of Loss, LLC asymmetry) | 1 | 0 | 5 | ⚠ **NEEDS SHARPENING** — caught the headline phantom-coverage but missed every structural detail |
| **GAP-08 EXPANDED** umbrella-structure | 3 (Schedule of Underlying blank, Convex tower coordination, Coverage B exclusions) | 0 | 1 | 2 | ⚠ **PARTIALLY FIRING** — broad detection works, structural detail missing |
| **GAP-17** contract-specific-coverage-satisfaction | 8+ (Maricopa Auto $2M, Maricopa Cyber $5M, Sacramento $1M Auto, Sacramento Per-Project, Sacramento PL retro/ERP, Maricopa AI/WOS/PNC, carrier rating) | 0 | 2 | 6+ | ❌ **NOT FIRING** — precondition failure (contract requirements not extracted) |
| **GAP-20** cross-policy-named-insured-inconsistency | 2+ (Lincoln Shields/Black Mountain on Auto missing from Umbrella; Properties LLC missing from CGL) | 0 | 0 | 2+ | ❌ **NOT FIRING** |
| **GAP-21** designated-entity-cancellation-notice | 2 (Pkg has 401-1235, Auto missing; cross-policy 30-day notice) | 0 | 0 | 2 | ❌ **NOT FIRING** |
| **GAP-01 EXPANDED** named-insured-verification | 9 (one per policy — Inc-vs-LLC entity-type) | 0 | 0 | 9 | ❌ **NOT FIRING** |
| **GAP-02 EXPANDED** cancellation-notice-verification | 7+ (per policy notice vs benchmark) | 0 | 0 | 7+ | ❌ **NOT FIRING** |

- **Files demonstrably firing: GAP-18, GAP-19** (2 of 9)
- **Files needing sharpening: GAP-08 EXPANDED, GAP-22** (caught headline patterns but missed structural detail)
- **Files not firing at all: GAP-01 EXPANDED, GAP-02 EXPANDED, GAP-17, GAP-20, GAP-21** (5 of 9 KB files yielded zero CAUGHT verdicts in this validation)

---

# Section 6 — Per-policy ground truth coverage

For each policy: presentation slide claims caught vs total · prior-report findings caught vs total (where available) · master annotations caught vs total (Auto only).

| Slug | Presentation | Prior report | Master | Roll-up |
|---|---|---|---|---|
| auto | 0/4 | n/a | **0/14** | **0/18** = **0%** |
| ml | 0/3 | 4/6 (1 partial) | n/a | 4/9 = **44%** |
| pl | 0/6 (v2 hit pg 23 for different reason) | 3/9 | n/a | 3/15 = **20%** |
| sg | 0/4 | 1/4 | n/a | 1/8 = **12.5%** |
| wc | 0/2 | 3/6 | n/a | 3/8 = **37.5%** |
| cyber | 1/3 | n/a | n/a | 1/3 = **33%** |
| pkg | 0/6 (1 partial) | n/a | n/a | 0–0.5/6 ≈ **0–8%** |
| umb | 0/3 (1 partial) | n/a | n/a | 0–0.5/3 ≈ **0–17%** |
| convex | 0/0 | n/a | n/a | n/a (exploratory) |

**Overall ground-truth coverage: ~12 of 71 verified claims caught ≈ 17%.**

The Auto 0/18 result is the most damning: it's the highest-confidence ground truth in the entire validation (you marked the policy yourself with red/cyan/orange color codes and hand-titled bookmarks), and v2 caught zero of it — including the Maricopa $2M CSL breach that has a verbatim sticky note on pg 24.

---

# Section 7 — Contract overlay summary

From `contract-overlay.md`:

| Contract | Insurance provisions present? | App extracted? | Defects v2 caught vs flagged in contract |
|---|---|---|---|
| Maricopa County | ✅ Full §8.1–8.2 | ❌ Not extracted | 0 of 5+ defects (Auto $2M CSL, Cyber $5M, AI/WOS/PNC, carrier rating, 30-day NOC) |
| Sacramento County (Appendix G) | ✅ Full | ❌ Not extracted | 0 of 4 defects (Per-Project structure caught but not contract-linked; PL retro caught but not effective-date-linked; AI/WOS missing; 10-day renewal evidence missing) |
| LA County | ❌ None in this file (amendment only) | ✅ Processed → returned `requirements: []` correctly | n/a |
| Douglas County | ❌ None (print/mail order) | ❌ Not processed | n/a |

**GAP-17 verdict on the headline test (Maricopa $2M Auto CSL breach): ❌ MISSED.**

The master sticky note on Auto pg 24 articulates this defect verbatim: *"not a great start - Maricopa contract expressly states $2M CSL required - contract DOES NOT state that auto limits can be met via use of an Umbrella."* The KB file `knowledge-base/universal/GAP-17-contract-specific-coverage-satisfaction.md` references this exact pattern as its example. The catch chain broke at the contract-extraction step: only 1 of 4 contracts was processed, and the one processed (LA County amendment) had no insurance provisions to extract. Maricopa was never extracted into the requirements JSON, so no cross-reference could fire for Auto, Cyber, ML, Pkg, or any other policy.

---

# Section 8 — Recommended next-session punch list

Ranked highest → lowest impact. Each item: 1–2 sentences.

### Tier 1 — Fix the broken catch chain (single highest-leverage)

1. **Re-run contract extraction on Maricopa + Sacramento contracts directly.** The current extraction processed only LA County (amendment, no insurance provisions). Without contract data, GAP-17 / GAP-21 cannot fire on any policy.
2. **Add a contract-extraction-completeness guard.** If `requirements: []` and the source PDF is >10 pages, flag for manual re-run; don't silently proceed to cross-reference with empty data.

### Tier 2 — Investigate two material regressions

3. **ML pg 73 Entity Regulatory Proceedings regression.** Was Bad/12 in v1, gone in v2. Investigate whether `do-epli/` KB cleanup removed the entity-vs-individual insuring-agreement detection language; if so, restore it.
4. **WC pg 137 Ownership Change Reporting regression.** Was Bad/6 in v1 (PE-critical), gone in v2. Likely the `workers-comp/` KB content over-focused on classification + state coverage and dropped the ownership-change pattern; re-add explicit detection.

### Tier 3 — Sharpen partially-firing KB files

5. **GAP-22 (cyber-dec-sheet-patterns).** Headline catch works (phantom $250K=$250K) but 5 of 6 sub-patterns missed. Add prompts for: Defense Within Limits + Shared Aggregate erosion math; aggregate-vs-contract-minimum cross-check (Maricopa $5M); choice-of-law jurisdiction extraction; Proof of Loss secondary sublimit; cross-policy LLC-entity asymmetry recognition.
6. **GAP-08 EXPANDED (umbrella-structure).** Catches "umbrella excludes PL/Cyber/D&O" at the headline level but doesn't cite the Schedule of Underlying form, blank lines, or the Convex tower-coordination opportunity. Add explicit Schedule-of-Underlying-form extraction + tower-coordination cross-policy reasoning.

### Tier 4 — Make non-firing KB files actually fire

7. **GAP-01 EXPANDED (named-insured-verification).** Tested across all 9 policies; caught zero. The KB file expects detection of Inc-vs-LLC entity-type mismatch on the Dec page; either the prompt doesn't surface this consistently or the post-cleanup Critical Thinking block is over-suppressing it. Investigate the prompt's "do not pad findings" balance vs Inc/LLC detection.
8. **GAP-02 EXPANDED (cancellation-notice-verification).** Same shape: not firing on any of the 7 policies where notice is in the master/presentation. Add explicit per-policy cancellation-notice extraction + benchmark comparison.
9. **GAP-20 (cross-policy named insured inconsistency).** Properties LLC missing from CGL but on Auto/Umbrella/Cyber is the headline test — uncaught. Add cross-policy entity-name matrix as a synthesis-stage check (after individual policy analysis, before final report).
10. **GAP-21 (designated-entity-cancellation-notice).** Form 401-1235 detection on Pkg + Auto-asymmetry test — uncaught. Add specific form-number detection + cross-policy-presence check.

### Tier 5 — Net-new KB content needed (defects we know are real, neither v1 nor v2 caught)

11. **First-party property exclusions.** Pkg pg 130/175/179-180 BPP exclusions, BI for equipment breakdown, BI for unfinished/finished stock, Ordinance-or-Law — four presentation Ugly findings, none caught in either v1 or v2. The property KB content needs a coverage-cause-of-loss + sublimit-detection layer.
12. **AI scope analysis on PL.** Defense-only / "solely arising" qualifier patterns — handoff-verified, uncaught in either run. Add to PL KB content.
13. **Surplus-lines / guaranty fund disclaimer detection.** Gemini PL is non-admitted in AZ — uncaught. Useful for client renewal posture. Add to PL + Cyber KB content.
14. **M&A auto-termination clauses (PE-critical).** PL pp 17-18 — uncaught in either run. Add to do-epli + professional-liability KB content.
15. **Mandatory arbitration / forum-selection clauses.** PL pg 18 (Chicago binding arbitration) — uncaught. Add to methodology KB content.

---

# Section 9 — Bottom-line recommendation

**Was the KB cleanup worth doing? Yes — but barely on its own merits.** The +12 NEW catches (especially the 4 Ugly findings on PL: Split Limits Tower, Ransomware, BIPA, plus the GAP-22 Cyber phantom) genuinely improved the deliverable, and 2 of 9 KB files (GAP-18, GAP-19) are demonstrably firing. But against the highest-confidence ground truth (Auto master 0/14, Maricopa $2M GAP-17 example case missed) and the regressions on ML pg 73 + WC pg 137, the net quality improvement is real but modest — perhaps 1.5x more useful than v1, not the 3x–5x the new KB content theoretically enables.

**Most efficient next step: pause large-scale KB authoring and run one targeted KB-fix session of ~3 hours scoped to two things only: (1) repair the contract-extraction step so GAP-17 / GAP-21 actually receive input data, and (2) restore the two regressions.** Both are precondition fixes, not new content. Once those are in place, the KB files we already wrote will fire substantially better on the next run, and we'll have a clean baseline for the next round of authoring.

After that, go back to client-deliverable work. The remaining KB authoring (Tier 4 + 5 in the punch list) is genuinely valuable but lower-leverage than fixing what we already shipped — and the Runbeck account itself needs the client-meeting prep more than the audit engine needs more KB files.

**Honest assessment of effort allocation:** the v2 KB cleanup was probably 30–40% over-invested for the catch-rate gain it produced. The investment paid off most clearly on PL (where the prior reports already told us what was missing), and least clearly on Auto (where the master was right there and v2 caught none of it). For future KB sessions, prefer tighter loops: write one KB file → re-run on a single policy → verify with annotation-level ground truth → iterate. The "write 9 KB files in one session, then validate" approach we ran here surfaced a long miss list but burned more budget than incremental validation would have.
