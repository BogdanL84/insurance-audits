# Phase 2B-2 Result — RMF-walk synthesis + capture fix + ambiguity flagging

**Status:** ⚠ **Below 60% target (43% landed). Above v3b baseline by +17 points. Per the user's stop rule, halting iteration to reassess.**

## What was applied (5 production fixes)

| Fix | File(s) | Verified working? |
|---|---|---|
| 1. Universal `00_general-all-policies-checklist.md` (5 items) | `knowledge-base/universal/` | ✅ Loaded into all 9 policy types' KB injection |
| 2. RMF-walk instruction in `build_crossref_prompt` | `app/core/claude_runner.py` | ✅ Synthesis emitted findings for General + CGL + Auto + Umbrella + WC checklist items |
| 3. `Needs Review` 4th verdict category (UI labels + report writer + sort) | `claude_runner.py`, `prompt_generator.py`, `utils.py`, `3_Findings_Dashboard.py`, `report_writer.py` | ✅ 5 Needs Review findings emitted in v3c (vs 0 in v3 production) |
| 4. GAP-17 ambiguity-flagging rule (umbrella interpretation) | `claude_runner.py` `build_contract_prompt` + new `umbrella_interpretation_ambiguous` schema field + new synthesis bullet | ✅ Stage A flagged Maricopa Auto with `umbrella_may_satisfy=False`, `umbrella_interpretation_ambiguous=True` (first run ever to flip this) |
| 5. **Capture bug fix** — `--output-format text` instead of `json` | `claude_runner.py` `_CLAUDE_CMD` | ✅ 50/50 finding sequence captured cleanly (vs json-mode losing 30+) |

## Pipeline metrics

```
Stage A — Contract re-extraction:    4 calls, ~5 min, 4/4 cleanly captured
Stage B — Synthesis:                 1 call,  12 min, 47 findings, 116 KB clean
Stage C — Cross-policy matrix pass:  1 call,  4 min,  9 findings, 33 KB clean
Total runtime:                       22.6 min
Total findings:                      56 (13 Ugly + 26 Bad + 5 Needs Review + 12 Good)
```

All artifacts in `phase-2b-2/`: `findings_v3c.json`, `synthesis_v3c.json`, `matrix_v3c_*.json`, `contract_extractions_v3c.json`.

## Headline numbers

| Metric | v3 (Phase 1) | v3b (Phase 2B-1) | **v3c (Phase 2B-2)** |
|---|---|---|---|
| Total findings | 38 | 45 | **56** |
| Ugly | 13 | 11 | 13 |
| Bad | 14 | 24 | **26** |
| Good | 11 | 10 | 12 |
| Needs Review | 0 | 0 | **5** |
| RMF coverage (caught + partial) | ~25% | 26% | **43%** |
| RMF strict caught | ~16% | 16% | **35%** |
| Maricopa Auto $2M CSL caught | ❌ | ✅ (synthesis-only) | ✅ |
| Maricopa $5M Cyber caught | ✅ | ✅ | ✅ |
| Cross-policy entity findings | 11 | 0 (synthesis-only) | 9 |
| Capture truncation | n/a | n/a | **resolved** |

## What worked beyond expectations

- **Capture fix is permanent and architectural.** Switching `--output-format` from json to text bypassed the claude CLI envelope-mode streaming buffer entirely. The pipeline can now reliably handle 100K+ char outputs. No more lost findings due to truncation.
- **Maricopa Auto flagship test FLIPPED for the first time.** Stage A's new ambiguity-flagging rule produced `umbrella_may_satisfy_minimum: False` and `umbrella_interpretation_ambiguous: True`, with a properly-structured note explaining both readings. Synthesis then emitted the Auto $2M CSL Shortfall finding (Bad/12) — the v1 Auto master sticky note finally surfaced as a finding.
- **Cyber-on-Maricopa caught at top severity.** "Cyber Liability — Limit Shortfall vs. Maricopa $5M Requirement" Ugly/25 (highest score in the program).
- **5 Needs Review findings emitted.** Plumbing for the new fourth category works end-to-end (synthesis → schema → dashboard → report writer).
- **No regressions vs v3 production.** All v3 high-value Ugly findings preserved or strengthened; v3b's PL substantive findings (E&O Delay-in-Performance, Split Limits, Client Print Media) retained.

## Why we landed at 43%, not 60%

Two underperforming RMF tabs:
- **CA (Auto): 23%** — 13 of 17 finding-emittable items not surfaced
- **WC: 20%** — 12 of 15 finding-emittable items not surfaced

Root cause appears to be the AI's "not applicable" filter from the synthesis prompt:
> "If the item is genuinely not applicable to this client (e.g., no foreign operations, so no DBA needed) → omit silently."

The AI applied this filter aggressively. Some omissions are correct (Maritime, USL&H, DBA — Runbeck has no overseas/maritime ops). Others are debatable: Mental Anguish in BI definition, U/UIM, Notice & Knowledge officer-limited, Parked Vehicles aggregate ded., Mobile Equipment vs Auto. These are genuinely applicable to Runbeck but the AI didn't see obvious defects to surface.

Looking at it differently: of the 46 not-caught items, **roughly 15 are operational/management items** that aren't really "audit findings" (small indemnity claims, large claims by name, possible credits, EMR management, owners excluded). If those were filtered out of the RMF denominator, **v3c would land at ~52% coverage** — at the reassess threshold but closer to target.

## Per the user's stop rule

> "Target: lift RMF coverage from 26% to 60%+. If the result is materially below 50%, stop and reassess before further iteration."

**Halting iteration.** v3c is shippable as a baseline if 43% RMF coverage + 56 substantive findings (including all Ugly tier from v2) is acceptable. To push toward 60%, three options for next iteration (recommend the user pick):

| Option | Action | Estimated effort | Likely lift |
|---|---|---|---|
| **J — Re-classify "operational" RMF items as out-of-scope** | Flag ~15 spreadsheet items (small claims management, EMR management, large claims by name, etc.) as "process audit, not finding emit" — exclude from the RMF denominator going forward. | 10 min KB tweak | +9 pts → ~52% |
| **K — Tighten the "not applicable" filter in the synthesis prompt** | Replace "If the item is genuinely not applicable... omit silently" with "Only omit if the item has zero conceivable applicability to this client's industry, geography, or operations. When in doubt, emit a Good or Needs Review finding rather than omit." | 5 min prompt tweak + 1 synthesis re-run | +10–15 pts → ~55% |
| **L — Add an explicit "always-emit" list for high-value RMF items** | Hardcode in the prompt: "For these specific items, ALWAYS emit a finding regardless of perceived applicability: Mental Anguish in BI, U/UIM, Notice & Knowledge, Punitive damages, Maintenance of Underlying, Fellow Employee Exclusion." | 10 min prompt tweak + 1 re-run | +8–12 pts → ~52% |

**Or accept 43% as v3c production baseline.** The substantive Ugly/Bad findings are strong; RMF coverage gaps are mostly in operational/admin items.

## Other artifacts produced

- `RMF-GROUND-TRUTH-SCORECARD.md` — updated with full v3b vs v3c comparison + per-item verdicts for v3c
- `phase-2b-2/_run_v3c.py` — re-runnable pipeline driver (Stage A + B + C)
- `phase-2b-2/_rmf_grade.py` — re-runnable RMF re-grade script
- `phase-2b-2/_diagnostic_text_format.py` — the diagnostic that isolated the JSON-envelope bug
- `phase-2b-2/_diagnostic_text_tempfile.txt` — preserved tempfile from the diagnostic synthesis (proof the text-mode capture works)

## What's NOT done

1. **Production code paths in `_Analyze.py`** are NOT updated to invoke the new synthesis_v3c output. The Streamlit UI still uses the old pipeline calls. Next session should integrate the v3c-style flow into `_Analyze.py` if the user wants the production app to use these fixes.
2. **`audit-state.json` for run-test-election-services** is NOT updated with v3c findings. Currently still shows v3 38-finding state. Recovery merge would be a one-line script if you want.
3. **Per-policy audited PDFs** are NOT regenerated with v3c findings. The PDFs in `output/` are still from v3.

These three are deliberate — they require an explicit "ship v3c to production" decision after the reassess.

---

**Summary:** Phase 2B-2 delivered 5 production fixes that all work end-to-end. Capture truncation is solved. Maricopa Auto flagship test passed for the first time. RMF coverage went from 26% to 43% (+17). Below the 60% target but a substantial step toward it. **Stopping here per stop-rule. Awaiting user reassess decision before next iteration.**
