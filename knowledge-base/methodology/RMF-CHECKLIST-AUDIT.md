# RMF Checklist Audit — Spreadsheet vs `00_RMF-checklist.md` files

**Audit date:** 2026-04-29 · **Source of truth:** `Template_Contract_Analysis.xlsx` (now in `knowledge-base/methodology/`).

The spreadsheet contains **86 RMF items** across the user-named tabs:

| Tab | Items | Status | Has `00_RMF-checklist.md`? |
|---|---|---|---|
| General All Policies | 5 | active | ❌ **NO checklist file** — gap |
| CGL | 33 | active | ✅ `by-coverage/gl/00_RMF-checklist.md` |
| CA | 18 | active | ✅ `by-coverage/auto/00_RMF-checklist.md` |
| UMB | 14 | active | ✅ `by-coverage/umbrella-excess/00_RMF-checklist.md` |
| WC | 16 (incl. one "Intentionally Left Blank") | active | ✅ `by-coverage/workers-comp/00_RMF-checklist.md` |
| CP - na | 31 | marked "na" | ✅ `by-coverage/property/00_RMF-checklist.md` exists anyway |
| IM - na | 14 | marked "na" | ✅ `by-coverage/inland-marine/00_RMF-checklist.md` exists anyway |
| Misc - na | various | marked "na" | (no checklist; matches spreadsheet status) |

## Drift check — every checklist item in the spreadsheet vs the .md

For each .md file: walked every `## N. ...` header, compared against the corresponding spreadsheet tab's row N item description.

### `by-coverage/auto/00_RMF-checklist.md` ↔ CA tab (18 items)

✅ **All 18 items present, in the same order, with the same numbering.** Headers and body text match the spreadsheet verbatim. No drift.

### `by-coverage/gl/00_RMF-checklist.md` ↔ CGL tab (33 items)

✅ **All 33 items present, in the same order, with the same numbering.** Headers and body text match the spreadsheet verbatim. No drift.

### `by-coverage/umbrella-excess/00_RMF-checklist.md` ↔ UMB tab (14 items)

✅ **All 14 items present, in the same order, with the same numbering.** Headers and body text match the spreadsheet verbatim. No drift.

### `by-coverage/workers-comp/00_RMF-checklist.md` ↔ WC tab (16 items)

✅ **All 16 items present, in the same order, with the same numbering** — including the "Intentionally Left Blank" placeholder at #4. Headers and body text match the spreadsheet verbatim. No drift.

### `by-coverage/property/00_RMF-checklist.md` ↔ CP - na tab (31 items)

⚠ **All 31 items present and matching** despite the spreadsheet marking the CP tab "na". The .md was generated when the CP tab was active (pre-2026 cleanup) and was never regenerated when the spreadsheet de-prioritized it. **Functionally fine** (loaded by the pipeline for property analyses) but the "na" label in the spreadsheet means Bogdan considers Property RMFs lower priority for the current audit work. No content drift.

### `by-coverage/inland-marine/00_RMF-checklist.md` ↔ IM - na tab (14 items)

⚠ Same situation as Property — all 14 items present and matching, but spreadsheet marks "na". No content drift.

## Gaps identified

### Gap 1 — No `General All Policies` checklist file

The spreadsheet's **General All Policies** tab has 5 cross-cutting RMF items that the pipeline does not have a dedicated KB checklist for:

| # | Item | Currently covered by? |
|---|---|---|
| 1 | 90 day notice of cancellation | Partially covered by `universal/GAP-02-cancellation-notice-verification.md` — but GAP-02 is an audit-pattern, not a checklist; doesn't enumerate the 90-day expectation explicitly |
| 2 | Unintentional Errors and Omissions (giveback) | **NOT covered** in any KB file. This is a real coverage element (often an `Unintentional Errors and Omissions` endorsement on GL) that the pipeline never explicitly checks for. |
| 3 | Named insureds — list for each policy and highlight any that are missing | Covered by `universal/GAP-01-named-insured-verification.md` ✓ |
| 4 | Notice and Knowledge of Claims (all policies except umbrella) | **NOT covered** as a cross-policy check. Each per-coverage RMF tab does call it out (CGL #25, CA #13, UMB #7), but no synthesis-level reminder. |
| 5 | Waiver of Subrogation (cross-policy) | Per-policy mentions exist in CGL #33, CA, WC #16, UMB #3 but no cross-policy "is WoS consistent across the whole program?" check. |

**Recommended fix:** create `knowledge-base/by-coverage/general/00_RMF-checklist.md` (or add to `universal/`) covering these 5 cross-cutting items so they get loaded for every policy audit.

### Gap 2 — Property/IM checklists exist but tabs are marked "na"

If Bogdan's intent is that Property and IM are not part of the active audit methodology right now, the .md files will still get loaded by the pipeline (they're in `by-coverage/property/` and `by-coverage/inland-marine/`) and consume the per-policy KB budget when those policy types are detected. **Two options:**

- (a) Leave as-is — Property and IM rarely appear in the current Runbeck-style audits anyway, so the impact is minimal.
- (b) If we want to honor the spreadsheet's "na" marking strictly, move these two checklists to an `archive/` subfolder so the loader doesn't see them.

Recommend (a) until the next client audit produces a Property or IM policy that exercises the checklist — then revisit.

### Gap 3 — Items in .md files NOT in the spreadsheet (drift from source of truth)

**None found.** All 126 items across the 6 active checklists trace cleanly to a corresponding spreadsheet row. The .md files appear to have been mechanically generated from the spreadsheet and never edited away from it. If Bogdan has been adding KB content via the universal/ folder (GAP-01..22 files), those are additive — not drift from the RMF baseline.

## Summary

| Metric | Value |
|---|---|
| Spreadsheet active items | **86** (General 5, CGL 33, CA 18, UMB 14, WC 16) |
| .md checklist items in active tabs (gl + auto + umb + wc) | **81** (33+18+14+16 — no General checklist exists) |
| Items in .md NOT in spreadsheet (drift) | 0 |
| Items in spreadsheet NOT in any .md | **5** (the General All Policies items) |
| Net coverage | **81 of 86 = 94%** |

**Single concrete fix to bring coverage to 100%:** create the missing `General All Policies` checklist (5 items) and either place it in `universal/` (so it loads for every policy regardless of type) or in a new `by-coverage/general/` folder. Recommend `universal/` so it pairs with the existing GAP-XX universal-loader pattern.
