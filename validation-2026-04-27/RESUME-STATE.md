# Phase 2B-2 — Resume State

Last updated: 2026-05-01 after Friday-evening hardening sprint (3-task autonomy run).

## Where we are

**v3e shipped + Friday-evening hardening complete.** Three architectural fixes landed today addressing field-test failure modes from the Run-test → Precision Aero shakedown. All committed to https://github.com/BogdanL84/insurance-audits.

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

1. **OCR pre-processing in Stage A document intake.** When extracted text has `word_count: 0` (scanned image-only PDF), Stage A should run Tesseract / a cloud OCR pass and write OCR'd text back as the source. Today the per-policy analyses on those PDFs are minimal (~1.6 KB metadata-only vs ~16 KB on text-extracted policies) and the marked-up PDF generator can't anchor annotations. 3 of 5 Precision Aero PDFs hit this. Highest-impact next investment for client-readiness.

2. **Findings dashboard "E&O misclassified as Auto" pattern (Bogdan flagged).** When a single chunk holds both Auto and an E&O-related policy (or when the synthesis prompt's policy_type cues are ambiguous), some findings are emitted with `policy_file: AUTO.pdf` but the substantive content is E&O. Causes incorrect annotations on AUTO.pdf and confuses the dashboard's per-policy grouping. Likely fix: tighten the synthesis prompt to require `policy_file` to match the policy that actually carries the issue, plus a post-synthesis validator that cross-checks `policy_file` against `requirement_type` keyword and warns on mismatches.

3. **Threaded heartbeat for live ticking clock during single blocking calls.** Today's Task 3 added cumulative-elapsed updates between chunks; during a single 4-minute blocking `run_claude` call the clock doesn't tick. A worker thread updating `_timer_display` every 2 seconds (with `add_script_run_ctx` so widget updates work from the thread) would give true liveness. Skipped this round as too risky for autonomy mode.

4. **Full UI redesign for client-grade polish.** Current UI is functional but visibly "engineering tool"-grade. CFO-facing pages (Findings Dashboard, Strategic Advisor, Build Report) should get a typography/layout pass. Out of scope for the iteration cycle so far.

5. **Tag emission tightening.** Per-item `rmf-XX-N` tag emission is non-deterministic — sometimes the model uses item-level tags (rmf-ca-1), sometimes tab-level (rmf-cgl), sometimes none. Tag-aware grader becomes more reliable when tags are consistent. Prompt change: require explicit `rmf-XX-N` tag on every emit, not just topic-level.

6. **Migrate keyword grader to tag-aware as primary.** Current `_rmf_grade.py` keyword matching has documented false positives (CA-2 credited from CGL-23 hit) and false negatives. Tag-aware supplementary grader (`_rmf_grade_tag_aware.py`) should become primary once tag emission is reliable.

7. **`cache_read_input_tokens` in per-chunk metrics.** Stream-json mode now logs cache hit data to stderr per call but doesn't aggregate into `chunk_metrics.json`. Easy enhancement.

8. **Multi-policy `policy_file` parsing in PDF annotator.** Findings with `policy_file: "BOP.pdf, UMBRELLA.pdf, WC PEKIN 24.pdf"` (comma-separated) are treated as a single non-existent filename. `annotate_all_policies` splits on `;` but not `,`. Pre-existing bug surfaced during today's Precision Aero annotator test. Trivial fix.

## Friday hardening commits

- `91e6a50` Persist findings to disk after each pipeline stage
- `7f982d1` PDF annotator: skip image-only PDFs instead of hanging
- `14a384f` Live progress UX on Analyze page
- `2bfdfbe` Recover Precision Aero findings from preserved runner tempfile
- `c741f33` Document PDF annotator hang on scanned PDFs as known issue
