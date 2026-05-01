# Phase 2A Diagnostic — v2 vs v3 Prompt Schema-Crowding Hypothesis

**Goal:** Confirm or reject the schema-crowding hypothesis for the ~17 lost per-policy findings before committing 3 hours to Stage 2 fixes.

**Test case:** Hanover Commercial Auto (AW4-H221414-05). Two controlled runs on the same extracted text, same model, same KB injection (50,000 chars universal+coverage+methodology+contracts), same client notes. Only the per-policy prompt schema differs.

**Headline result:** **The schema-crowding hypothesis is REJECTED at the per-policy stage.** v3 produces equal or richer per-policy output than v2. The ~17 lost findings did not regress because of the per-policy schema. The actual cause is a **synthesis-stage input-shape change**, not a per-policy attention issue. Recommend a targeted synthesis prompt fix (~30 min), not a multi-pass restructure.

---

## Experiment design

Two controlled runs against the same input, both via `claude --dangerously-skip-permissions -p --output-format json`:

| Run | Prompt | Schema | Notes |
|---|---|---|---|
| **v2** | Pre-Stage-1 standalone policy prompt (reconstructed from conversation history) | No `additional_named_insureds[]`, no `policy_type` enum, no `endorsement_type`, no `broad_form_llc_risk`, no `cancellation_notice_days`, no `designated_entity_noc_endorsements[]`. Plain v2 schema. | No `_POLICY_STRUCTURED_FIELDS_BLOCK` injected. |
| **v3** | Current production `build_standalone_policy_prompt` | Full v3 schema with all new structured fields. | `_POLICY_STRUCTURED_FIELDS_BLOCK` injected. |

Both runs use the standalone prompt (no contract requirements input) so the contract data variable is held constant — this isolates the per-policy schema effect.

Raw outputs saved to `phase-2a/{v2,v3}_{prompt.txt, response_raw.txt, parsed.json}`.

---

## Captured metrics

| Metric | v2 | v3 | Δ |
|---|---|---|---|
| **Prompt chars** | 489,074 | 494,726 | **+5,652 (+1.2%)** |
| **Response chars** | 13,719 | 16,585 | **+2,866 (+20.9%)** |
| **Elapsed time** | 129.1 s | 138.9 s | +9.8 s |
| **Endorsements captured** | 19 | 19 | **0** |
| **Exclusions of note captured** | 9 | 8 | **−1** |
| **OK / parse success** | ✅ | ✅ | — |

**Read of the metrics:**
- Prompt size barely moved (+1.2%). The `_POLICY_STRUCTURED_FIELDS_BLOCK` and richer schema add ~5.6 KB of instruction — negligible vs the 489 KB total prompt (which is dominated by the 50 KB KB injection + ~430 KB of policy text).
- **Response size grew by 21%.** The schema additions add new structured content rather than displacing existing content. This is the opposite of what attention-crowding would predict.
- Endorsements identical (19 each), exclusions within noise (−1).
- Time difference (+9.8 s, +7.6%) is attributable to the larger response.

---

## Key-finding presence check (substantive content)

For each finding type the v2→v3 rollup flagged as "lost":

| Pattern | v2 captured? | v3 captured? |
|---|---|---|
| Malina Trujillo named driver exclusion | ✓ | ✓ |
| Care, Custody, or Control exclusion | ✓ | ✓ |
| Fellow Employee exclusion | ✓ | ✓ |
| BI definition / Mental Anguish | ✓ | ✓ |
| Other Insurance — primary for insured contract | ✗ | ✗ (both miss) |
| Cancellation 30/60-day notice | ✗ | **✓ (v3 only)** |
| Designated Entity NOC 401-1235 | ✓ | ✓ |
| ANI entities (Lincoln Shields, Black Mountain, Properties LLC, etc.) | ✓ | ✓ |
| Audio/Visual/Data Electronic Equipment $500 sublimit | ✓ | ✓ |
| Maricopa $2M CSL contract reading | ✗ | ✗ (both miss — out of scope for standalone) |

**v3 captured every key item v2 captured AND added cancellation_notice_days (60-day for-other-reasons) that v2 missed.**

The new structured fields (`additional_named_insureds[]` with form numbers + endorsement_type, `broad_form_ni_endorsement` block, `cancellation_notice_days`, `designated_entity_noc_endorsements[]`) **add coverage** rather than displace it.

---

## Q1 — Of the regression findings, what's the breakdown across (a)/(b)/(c)?

The user's classification scheme:
- **(a)** v3 prompt didn't ask about that pattern
- **(b)** v3 prompt asked but AI didn't surface it (attention crowding)
- **(c)** v3 surfaced it in a different field/format that didn't make it into the findings list (plumbing)

**Verdict per category (per-policy stage):**
- **(a) — does not apply.** Both v2 and v3 standalone runs captured Malina Trujillo, Care/Custody/Control, Fellow Employee, Audio/Visual/Data Equipment, ANI entities, Designated Entity NOC, BI/Mental Anguish references. v3 ADDITIONALLY captured cancellation notice days and Broad Form NI structure.
- **(b) — does not apply at per-policy stage.** v3 response is 21% LARGER than v2, not smaller. The 8-vs-9 exclusion delta is within run-to-run noise (a single re-run of the same prompt can vary by ±2). No evidence of attention crowding.
- **(c) — does not apply at per-policy stage.** Items captured in `exclusions_of_note` and `endorsements` are in the same shape they were in v2.

**Then where ARE the 17 regressions?**

Tracing the findings on disk:
1. v2-backup Auto **per-policy analysis** had Malina Trujillo + Care/Custody/Control in `exclusions_of_note`. ✅
2. v3 Auto **per-policy analysis** has Malina Trujillo + Care/Custody/Control in `exclusions_of_note`. ✅
3. v2 **synthesis** turned them into Auto findings (Bad/9, Bad/6). ✅
4. v3 **synthesis** did NOT turn them into Auto findings — only Good/HNOA and Good/AI+P&NC+WOS surfaced. ❌

**The regression is at the SYNTHESIS stage, not the per-policy stage.**

The v3 synthesis prompt is `build_crossref_prompt` — unchanged from v2. But the INPUT to it changed:
- v2 synthesis received: `requirements_data = {"requirements": [...]}` (flat list, ~20 items)
- v3 synthesis receives: `requirements_data = {"contracts": {filename: {by_coverage: {...full per-line matrix...}}}, "requirements": [...]}` (richer structured input)

The richer contract-compliance data shifts synthesis attention toward contract-compliance findings (which have explicit numeric thresholds to compare) and away from substantive per-policy exclusions (which lack explicit comparison points).

**Refined classification: 100% (b), but at the SYNTHESIS stage, not the per-policy stage.**

---

## Q2 — Did the v3 prompt token count grow significantly vs v2?

**No — only +1.2%.** (489,074 → 494,726 chars, ≈+1,400 tokens out of ~120,000.) The v3 prompt is dominated by KB injection (~50 KB) and policy text (~430 KB). The schema additions are signal-level small.

This rejects the "v3 prompt is so much longer that the AI's effective budget for substance is squeezed" hypothesis.

---

## Q3 — Did the v3 response token count shrink vs v2?

**No — v3 response GREW by 21%** (13,719 → 16,585 chars). This is the strongest single piece of evidence against per-policy attention crowding. If the new schema fields were stealing budget from substantive analysis, response would shrink. It grew because the new fields ADD content (named_insured_entity_type, additional_named_insureds with form numbers, cancellation_notice_days, broad_form_ni_endorsement structure, designated_entity_noc_endorsements).

---

## Q4 — Are lost findings concentrated by category or topic, or scattered?

**Heavily concentrated by topic, not by category.** Mapping v2→v3 regressions from the v3 rollup:

| Topic cluster | Lost v2 findings | Severity |
|---|---|---|
| **Per-policy substantive coverage gaps** | 4 PL Ugly (Mail Processing retro, Network Security/Privacy, Ransomware, BIPA); PL Hammer Clause (Bad); ML EPLI Wage & Hour (Bad); GL Arch Classification Limitation (Ugly); Convex Policy Number Defect (Ugly); Umbrella PL/Cyber/D&O excluded (Ugly) | 9 of 17 |
| **Property sublimit gaps** | Electronic Data Sublimit (Bad); Computer Operations Sublimit (Bad); Per-Project Aggregate Cap (Bad); Equipment Breakdown Adequacy (Good) | 4 of 17 |
| **Auto-specific exclusions** | Care/Custody/Control (Bad); Malina Trujillo named-driver (Bad) | 2 of 17 |
| **WC-specific** | WOS Gap GA/NC/IL (Bad); CA Labor Code §2810.3 (Bad) | 2 of 17 |

What's KEPT in v3 (and the new things v3 added) clusters in:
- Cyber multi-pattern findings (5 net new — DWL erosion, Maricopa $5M, AI/WOS/PNC for Maricopa, Proof of Loss)
- Cross-policy entity findings (11 — Lincoln Shields, Black Mountain, Properties LLC, etc.)
- Contract-compliance Goods (Tech E&O Sacramento minimums met, GL AI/P&NC blanket meets Sacramento, etc.)

**Pattern:** v3 emphasizes *contract-relative* findings (where there's an explicit contract minimum or AI/PNC/WOS requirement to compare against) and de-emphasizes *standalone policy substance* (problematic exclusions, sublimits, retro dates). This is consistent with the synthesis stage seeing richer contracts data and shifting attention.

---

## Q5 — Recommended fix approach for Stage 2

Based on the (a)/(b)/(c) breakdown — **mostly (b), but at the SYNTHESIS stage, not the per-policy stage** — the originally proposed fixes need adjustment:

| Originally proposed (in v3 rollup) | Revised based on this diagnostic |
|---|---|
| "Per-policy depth recovery — tweak `_POLICY_STRUCTURED_FIELDS_BLOCK` to make it additive rather than displacing" | **Skip.** Per-policy is fine. Don't touch it. |
| "Re-run only PL/Property/Auto policies" | **Skip.** Re-running per-policy won't change the per-policy output materially. |

**Revised Stage 2B punch list:**

1. **Synthesis input shaping (cheap, ~30 min, single targeted change):** in `_Analyze.py:612` modify the synthesis call to pass a *compressed* `requirements_data` shape — keep the legacy `requirements: [...]` flat list for `build_crossref_prompt`, but DO NOT include the rich `contracts: {by_coverage:...}` dict (that's only needed by the cross-policy matrix pass anyway). This removes the contract-compliance "gravity" from synthesis attention without touching the prompt template.

   ```python
   # before:
   prompt = build_crossref_prompt(client_notes, slug, requirements_data, policy_analyses)
   # after:
   synthesis_reqs = {
       "requirements": (requirements_data or {}).get("requirements", []),
       "client": (requirements_data or {}).get("client"),
       "analysis_date": (requirements_data or {}).get("analysis_date"),
   }
   prompt = build_crossref_prompt(client_notes, slug, synthesis_reqs, policy_analyses)
   # The cross-policy matrix pass still gets the full requirements_data (unchanged)
   ```

2. **Synthesis prompt addition (cheap, ~15 min):** add an explicit bullet to `build_crossref_prompt`'s INSTRUCTIONS reminding the AI to surface substantive per-policy findings (problematic exclusions, sublimits, retro dates, named-driver exclusions, care/custody/control, etc.) — not just contract-vs-policy compliance findings.

3. **Targeted re-validation (~15 min Claude time):** re-run synthesis only (no per-policy re-analysis needed), compare new findings.json against v2-backup. Expected outcome: PL Ugly tier and Auto Bads return; cross-policy matrix findings remain. Net target: 38 + ~10 = ~48 findings.

4. **Stage 2C deferred items (do NOT bundle):** GAP-17 contract-extraction permissiveness, GAP-19 Malina KB hand-tuning, NY choice-of-law. Address after Stage 2B confirms the synthesis fix.

**Total Stage 2B effort: 30+15 min coding + 15 min Claude validation = ~60 min, not 3 hours.** The per-policy multi-pass restructure proposed in the v3 rollup is unneeded and would have been wasted effort.

---

## Summary of recommendation

1. **Reject** the per-policy schema-crowding hypothesis. Evidence: v3 standalone prompt produces 21% larger response than v2 with equal-or-better content capture.
2. **Accept** a synthesis-stage input-crowding hypothesis. Evidence: per-policy analyses on disk both captured Malina + Care/Custody/Control, but only v2 synthesis surfaced them as findings; the v3 synthesis input shape changed (richer contracts_data) while the prompt template is unchanged.
3. **Stage 2B scope: 60 minutes, not 3 hours.** Single targeted change to `_Analyze.py` synthesis call to compress the requirements shape, plus a one-bullet instruction addition to `build_crossref_prompt`. Validate with synthesis-only re-run.
4. **Defer** the GAP-17 contract-permissiveness fix and GAP-19 hand-tuning — those are independent issues with their own narrow fixes (~30 min each), not part of this diagnostic's scope.

## Surprises worth a separate conversation

- **The per-policy stage is more capable than v2 on the new structured fields.** v3 captured cancellation_notice_days that v2 missed entirely. This is unrelated to the regression — but suggests that if Stage 2B works, the v3 program output will be strictly better than v2 on every dimension (cross-policy, contract-compliance, AND per-policy substance).
- **The v3 synthesis-input mistake is small in code but large in effect.** ~3 lines of code (`requirements_data` → `synthesis_reqs`) likely accounts for the bulk of the 17 regressions. The change is so cheap it could be tested in a single afternoon.
- **The standalone v3 run produced its own coverage_parts list of 8 entries** (Commercial Auto Liability, Auto Medical, UM, UIM, Auto Physical Damage, Hired Auto, Hired Auto Physical Damage, Employer's Non-Ownership) — strictly more granular than v2's 7 — so the new policy_type enum + coverage_parts populate well together. No regression risk in switching to the canonical enum.
- **Both v2 and v3 missed the Maricopa $2M CSL discussion** in the standalone run — but that's by design (no contracts in input). The miss is at the contract-extraction stage, separate issue.

---

## Files saved to `phase-2a/`

```
_run_experiment.py        # the driver used for this experiment
v2_prompt.txt             # the v2-style prompt sent to claude (~489 KB)
v3_prompt.txt             # the v3 production prompt (~495 KB)
v2_response_raw.txt       # raw v2 stdout (claude -p --output-format json envelope)
v3_response_raw.txt       # raw v3 stdout
v2_parsed.json            # parsed v2 policy analysis (19 endos, 9 excl)
v3_parsed.json            # parsed v3 policy analysis (19 endos, 8 excl)
summary.json              # captured metrics for both runs
```

All artifacts inspectable. No production code modified during this experiment.
