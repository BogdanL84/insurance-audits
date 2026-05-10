# Phase 2B-2 — Resume State

Last updated: 2026-05-08 after OCR pre-processing landed and Precision Aero audit re-ran end-to-end on the OCR'd data.

## Where we are

**OCR pre-processing landed; Precision Aero audit re-shipped at 2.6× findings.** The 2026-05-04 OCR blocker (Tesseract install required admin) was resolved when Bogdan installed the UB-Mannheim Windows installer. Three OCR pieces shipped: (a) Stage A intake fallback in `pdf_extractor.py:_extract_pdf` (PyMuPDF first, Tesseract on <50-word PDFs), (b) Document Intake UI shows `(OCR'd)` badge and real word count, (c) optional text-layered PDF generator (`_make_text_layered_pdfs.py`) so the annotator can anchor highlights on previously-image-only PDFs.

Precision Aero deliverable now ships at **144 findings (30 Ugly + 49 Bad + 43 Review + 22 Good)** vs the prior 55 from the metadata-only-on-3-PDFs recovery. All 5 marked-up PDFs generated (BOP/UMBRELLA/WC PEKIN now annotatable thanks to text-layered versions). Markdown report regenerated.

**v3e shipped + Friday-evening hardening complete.** Three architectural fixes landed 2026-05-01 addressing field-test failure modes from the Run-test → Precision Aero shakedown. All committed to https://github.com/BogdanL84/insurance-audits.

### Friday hardening (2026-05-01 evening)
1. **Persist findings per stage** (`91e6a50`) — `_Analyze.py` now writes `findings_synthesis.json` → `findings_crosspolicy.json` → `findings.json` after each successful pipeline stage, with incremental atomic updates to `audit-state.json`. Prevents the Precision Aero "lost in session_state" data loss.
2. **PDF annotator skip on image-only PDFs** (`7f982d1`) — `pdf_annotator.py` probes word count on first 3 pages; skips with clear reason if <50 words. Fixes the "Generate Marked-up PDFs" hang on scanned policies.
3. **Live progress UX on Analyze page** (`14a384f`) — expected-time hints, technical-log expander, higher-contrast text, cumulative-elapsed display on chunk transitions.

### v3e shipping state
Final deliverable: `phase-2b-2/findings_v3e.json` (449 findings = 58U + 128B + 147R + 116G). RMF coverage: 50% keyword grade, **73% tag-aware grade**. Full report: `phase-2b-2/V3E_FINAL_REPORT.md`.

### First real client (Precision Aero)
55 findings = 4U + 16B + 24R + 6G + 5 Informational, recovered after a Streamlit hang via runner-tempfile parsing. `clients/precision-aero/output/findings.json`. Top items: document-integrity Ugly on 3 scanned PDFs, no Cyber program (Ugly), Auto Hired Auto Phys Damage missing (Ugly).

The K+L per-coverage prompt design hit its target (55%+ tag-aware). The stream-json runner migration eliminated the binary-side output truncation that was the chronic ceiling on every prior iteration.

## Coverage trajectory

| Iteration | Findings | Keyword RMF | Tag-aware RMF | Notes |
|---|---:|---:|---:|---|
| v3c (2026-04-29) | 56 | 43% | n/a | Baseline; 22.6 min full pipeline |
| v3d (2026-04-30) | 139 | 45% | n/a | 3-chunk; Chunk 1 hung |
| v3d-split (2026-04-30) | 195 | 48% | n/a | 4-chunk via 1A/1B; Chunk 1A truncated |
| v3e-partial (2026-05-01) | 243 | 48% | 72% | Salvaged 1A1+1B; rest v3d-vintage |
| **v3e (2026-05-01)** | **449** | **50%** | **73%** | **Full 6-chunk on stream-json runner** |

## Infrastructure state

### Binary protection (3 layers, unchanged)
| Layer | Status |
|---|---|
| `autoUpdates: false` in `~/.claude.json` | set |
| `attrib +R` on `bin/claude-pinned-2.1.121.exe` | set |
| `_CLAUDE_BIN` references pinned path | set |

### Runner (`app/core/claude_runner.py`)
| Feature | Status |
|---|---|
| shell=False + Popen | landed (v3d post-mortem) |
| taskkill /T /F /PID on timeout | landed (v3d post-mortem) |
| Always-capture stderr | landed (v3d post-mortem) |
| `extract_json` json_repair fallback | landed (v3d-split post-mortem) |
| **stream-json line-by-line drain (default)** | **landed (v3e post-mortem 2026-05-01)** |
| Text-mode fallback via `_USE_TEXT_MODE=1` env | preserved |
| Per-call usage / rate-limit metrics → stderr | landed (stream-json migration) |

### Synthesis prompt (`build_crossref_prompt`)
- K + L always-emit list expanded to per-coverage (CGL / Auto / Umbrella / WC / General)
- 13 CA always-emit items, 11 WC always-emit items
- 8 conditional N/A items (CA-4/5/11/15, WC-7/9/13/14) — pattern partially generalizes
- Total prompt size addition: ~3.5 KB

## Open issues / next-iteration leverage

1. **Conditional N/A pattern didn't generalize cleanly** — only 1/8 emitted as N/A-Good in v3e. Promote to always-emit with explicit N/A guidance to fix.
2. **Per-item tag emission inconsistent** — model bundles related items into single findings (e.g., CA-12+16+17+18 in one), defeating tag-based grading. Tighten prompt to require explicit `rmf-XX-N` tag on every emit.
3. **Keyword grader systematically undercounts** — false positives AND false negatives. Migrate `_rmf_grade.py` to tag-aware as primary; keep keyword as heuristic fallback.
4. **Cache stats not aggregated** — `cache_read_input_tokens` is logged to stderr per call but not captured in `chunk_metrics_v3e.json`. Easy enhancement for future runs.
5. **TRIA / CGL-32, CGL-4, CGL-7, CGL-8 still uncaught** — CGL-specific items the K+L list doesn't include. Possible CGL-tab expansion target.

## How to resume

If continuing v3e refinement:
1. Read `phase-2b-2/V3E_FINAL_REPORT.md` for full context
2. Pick from "Recommended next steps" in that report
3. Most leverage: tighten per-item tag emission (#2 above)

If starting a new client:
1. Update CLAUDE.md / client paths
2. Re-run Stage A (contract extractions) for new client
3. Run `_run_v3e_chunked.py` (will need chunk-keyword updates if policy filenames differ)

## Files of interest

| Path | Purpose |
|---|---|
| `phase-2b-2/findings_v3e.json` | Final deliverable (449 findings) |
| `phase-2b-2/V3E_FINAL_REPORT.md` | Detailed report |
| `phase-2b-2/_run_v3e_chunked.py` | 6-chunk driver |
| `phase-2b-2/_rmf_grade_tag_aware.py` | New supplementary grader |
| `app/core/claude_runner.py` | Runner with all current fixes (stream-json default) |
| `bin/claude-pinned-2.1.121.exe` | Pinned binary (read-only) |
| `BINARY_VERSIONING.md` | Pin doc + field test log |
| `RMF-GROUND-TRUTH-SCORECARD.md` | Scorecard methodology + grader limitation note |

## Baselines preserved (do not modify)

- `findings_v3c.json` — 56 findings, 2026-04-29 known-good
- `findings_v3d.json` — 139 findings, v3d_chunked
- `findings_v3d-split.json` — 195 findings, v3d-split path
- `findings_v3e-partial.json` — 243 findings, salvage path
- `findings_v3e.json` — 449 findings, full v3e (Run-test, stream-json runner)
- `findings_v3e_app.json` — 410 findings, app-refactor validation (Run-test)
- `findings_precision_aero_v3e.json` — 55 findings, first real client recovery snapshot

## Open issues (deferred, in rough priority order)

1. ~~**OCR pre-processing in Stage A document intake.**~~ **CLOSED 2026-05-08.** Resolved with Tesseract 5.5.0 (UB-Mannheim Windows installer) + pytesseract. Stage A's `_extract_pdf` now runs Tesseract on PDFs whose PyMuPDF-extracted word count is <50, returning OCR'd text per page. Document Intake UI shows `(OCR'd)` badge. Separately, `_make_text_layered_pdfs.py` produces text-layered PDFs (Tesseract `image_to_pdf_or_hocr` mode) so the annotator can anchor highlights on previously-image-only PDFs. Precision Aero validation: BOP/UMBRELLA/WC PEKIN went from 0 words → 9263/10595/3182 words; per-policy analyses went from 1.6 KB metadata stubs → 17 KB / 18 KB / 10 KB substantive; final synthesis ran 4 chunks → 144 findings. Cross-policy intel pass timed out at 158 KB prompt (compressed-findings list exceeded threshold); fallback to synthesis findings worked, matrix AI pass added 9 more on top. New deferred item #9 below.

2. **Findings dashboard "E&O misclassified as Auto" pattern (Bogdan flagged).** When a single chunk holds both Auto and an E&O-related policy (or when the synthesis prompt's policy_type cues are ambiguous), some findings are emitted with `policy_file: AUTO.pdf` but the substantive content is E&O. Causes incorrect annotations on AUTO.pdf and confuses the dashboard's per-policy grouping. Likely fix: tighten the synthesis prompt to require `policy_file` to match the policy that actually carries the issue, plus a post-synthesis validator that cross-checks `policy_file` against `requirement_type` keyword and warns on mismatches.

3. **Threaded heartbeat for live ticking clock during single blocking calls.** Today's Task 3 added cumulative-elapsed updates between chunks; during a single 4-minute blocking `run_claude` call the clock doesn't tick. A worker thread updating `_timer_display` every 2 seconds (with `add_script_run_ctx` so widget updates work from the thread) would give true liveness. Skipped this round as too risky for autonomy mode.

4. **Full UI redesign for client-grade polish.** Current UI is functional but visibly "engineering tool"-grade. CFO-facing pages (Findings Dashboard, Strategic Advisor, Build Report) should get a typography/layout pass. Out of scope for the iteration cycle so far.

5. **Tag emission tightening.** Per-item `rmf-XX-N` tag emission is non-deterministic — sometimes the model uses item-level tags (rmf-ca-1), sometimes tab-level (rmf-cgl), sometimes none. Tag-aware grader becomes more reliable when tags are consistent. Prompt change: require explicit `rmf-XX-N` tag on every emit, not just topic-level.

6. **Migrate keyword grader to tag-aware as primary.** Current `_rmf_grade.py` keyword matching has documented false positives (CA-2 credited from CGL-23 hit) and false negatives. Tag-aware supplementary grader (`_rmf_grade_tag_aware.py`) should become primary once tag emission is reliable.

7. **`cache_read_input_tokens` in per-chunk metrics.** Stream-json mode now logs cache hit data to stderr per call but doesn't aggregate into `chunk_metrics.json`. Easy enhancement.

8. **Multi-policy `policy_file` parsing in PDF annotator.** Findings with `policy_file: "BOP.pdf, UMBRELLA.pdf, WC PEKIN 24.pdf"` (comma-separated) are treated as a single non-existent filename. `annotate_all_policies` splits on `;` but not `,`. Pre-existing bug surfaced during today's Precision Aero annotator test. Trivial fix.

9. **Cross-policy intel pass times out on programs with many findings.** With 135 synthesis findings × ~1 KB each compressed + 5 policy analyses, the cross-policy intel prompt hit 158 KB and timed out at 300 s. Fallback worked (kept synthesis findings, matrix AI pass added 9 more). Fix options: (a) compress findings more aggressively (drop full `gap_description`, summarize), (b) chunk the cross-policy pass over findings the way synthesis is chunked, (c) raise per-call timeout to 600s but accept higher latency. Lowest-risk: (a) — the cross-policy pass mainly needs `requirement_type`, `policy_file`, and brief gap text, not the full description.

10. **Text-layered PDF generation is a one-shot script, not pipeline-integrated.** `_make_text_layered_pdfs.py` runs OCR + Tesseract `image_to_pdf_or_hocr` to bake a hidden text layer into scanned PDFs so the annotator can anchor highlights. Today this is a manual step run from the repo root. Next: integrate as an automatic Stage A side-effect (when an OCR'd extraction is taken, also write `<stem>-text-layered.pdf` next to the original, and have the annotator prefer the layered version when both exist) — keeps the original byte-identical while giving the annotator searchable text. **Field-test 2026-05-08:** annotator highlights on text-layered OCR'd PDFs misalign with visual text positions (Tesseract pixel coordinates ≠ rendered glyph positions); marked-up-PDF deliverable being dropped in favor of HTML-only output, so this issue is no longer blocking but worth solving if marked-up PDFs are ever re-introduced.

11. **Synthesis prompt should include a PROGRAM INVENTORY block in every chunk.** Each chunked synthesis call currently sees only the policies in its coverage cluster, which lets the model emit "Program Gap — No Workers' Comp Policy" from the core-liability chunk because *that chunk* doesn't see WC PEKIN — even though the merge then surfaces those false claims. The defensive `core/findings_filter.py` filter (added 2026-05-08) drops the canonical hallucinations after merge, but the proper upstream fix is to prepend every chunk prompt with: "PROGRAM INVENTORY (all policies in this client's program, even those not analyzed in this chunk): [list filenames + policy_type + coverage_parts]" plus an explicit "Do not flag a coverage type as missing if it appears in the PROGRAM INVENTORY above, even if its full analysis is not in this chunk." Defer until next client onboarding where we have a clean test bed; the filter is sufficient safety until then.

12. ~~**Synthesis prompt emits "Audit Scope Limitation" meta-findings when no contract requirements are loaded.**~~ **RESOLVED 2026-05-09** by commit `a85114a` — added a "DO NOT EMIT META-FINDINGS ABOUT THE AUDIT PROCESS ITSELF" rule to `build_crossref_prompt` in `claude_runner.py` (around L1609) with explicit forbidden-list (Audit Scope Limitation, Contract Requirements Not Loaded, Renewal Certificate provided instead of full form, etc.) and an explicit "treat empty contract requirements as policy-only audit, surface scope context in audit metadata not in findings" instruction. Verified on Precision Aero WC chunk: meta-finding suppressed in 2 of 2 RULE-ON runs; 1 of 2 emitted TRIA (variance, not rule-caused — confirmed by control run that also missed TRIA in 1 of 1 attempts and a CONTROL run that emitted both meta-finding and TRIA). Original 2026-05-08 deferral context retained below for record:

    *Original issue (deferred):* When the audit runs in standalone mode (no contracts uploaded), per-policy synthesis emits a Needs-Review meta-finding flagging the audit-scope limitation ("The contract requirements file passed into this audit was empty"). This belongs in audit-state metadata or the report cover-page, not the findings list — it's a fact about the audit process, not about the policy. Manually dropped on 2026-05-08 for Precision Aero (drop record in `audit-state.json:filter_drops`).

13. ~~**Synthesis prompt classifies "Pending Rate Change — Mid-Term Premium Risk" as Needs Review when it should be Bad.**~~ **RESOLVED 2026-05-09** by *"Synthesis prompt: classify carrier-controlled mid-term rate/term changes as Bad"* (commit dated 2026-05-09 immediately following item 12's resolution) — added a "CONCRETE CARRIER-CONTROLLED MID-TERM CHANGES → Bad, not Needs Review" rule to `build_crossref_prompt` in `claude_runner.py` (around L1635). The rule is broader than the original issue: it covers the whole class of carrier-controlled mid-term changes (Pending Rate Change endorsements, Audit Noncompliance Charges, any clause reserving carrier discretion to change terms/rates/charges mid-policy without insured consent) with typical-scoring guidance (severity 3 = premium movement; likelihood 3 for state rate changes, 1-2 for audit noncompliance, 2 for carrier-discretion coverage changes). Verified on Precision Aero WC chunk: Pending Rate Change classified Bad with L=3 S=3 R=9 (matches rule's prescription); Audit Noncompliance Charge classified Bad with L=2 S=3 (matches "audit noncompliance: likelihood 1-2"); item 12's meta-finding suppression still holds (no canonical "Audit Scope Limitation" / "Program Scope" leaks). Original 2026-05-08 deferral context retained below for record:

    *Original issue (deferred):* The Pending Rate Change endorsement (e.g. WC 00 04 04 in NCCI WC forms) permits the carrier to adjust rates mid-term once a state filing is approved. Concrete policy provision with material premium-impact downside, not a confirm-with-carrier checklist item. Model classified as Needs Review on Precision Aero. Manually reclassified 2026-05-08 (severity 3 × likelihood 3 = risk 9).

14. **Hallucination filter pattern gap — "Program-Level Coverage Gap — X Not in Audit Scope" shape.** The existing filter at `core/findings_filter.py` (added 2026-05-08) catches the canonical chunk-induced hallucination shapes via `^Program Gap.*\bNo X\b` and `^Missing Policy.*X` regex. During item 13 verification on 2026-05-09 (single-WC synthesis test), the model emitted a NEW phrasing the filter does not catch: `Program-Level Coverage Gap — General Liability Policy Not in Audit Scope` (and similar — Umbrella, Auto/Property/Cyber/ML/EPLI bundle). Same single-policy-chunk artifact (model sees only WC and concludes other coverages are missing), new title shape. The findings did not surface in the live Precision Aero pipeline run because the multi-policy chunk synthesis sees more policies — but the gap is real and a future client whose chunked synthesis hits this phrasing would see it leak. Short-term fix: extend `_PROGRAM_COVERAGE_PATTERNS` (or add a new pattern family) in `core/findings_filter.py` to match `^Program-Level Coverage Gap.*Not in Audit Scope` and similar variants. **Long-term fix:** item 11 (PROGRAM INVENTORY block in every chunk prompt) makes this entire class of bug obsolete — when the model sees the full program inventory in every chunk, it stops fabricating "Coverage X is missing" claims based on its limited per-chunk view. Filter pattern extension is the short-term defense; PROGRAM INVENTORY is the upstream fix. Defer to next session.

## Friday hardening commits

- `91e6a50` Persist findings to disk after each pipeline stage
- `7f982d1` PDF annotator: skip image-only PDFs instead of hanging
- `14a384f` Live progress UX on Analyze page
- `2bfdfbe` Recover Precision Aero findings from preserved runner tempfile
- `c741f33` Document PDF annotator hang on scanned PDFs as known issue
