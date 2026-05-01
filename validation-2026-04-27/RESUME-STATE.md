# Phase 2B-2 — Resume State

Last updated: 2026-05-01 after v3e full run (autonomy mode complete).

## Where we are

**v3e shipped.** Final deliverable: `phase-2b-2/findings_v3e.json` (449 findings = 58U + 128B + 147R + 116G). RMF coverage: 50% keyword grade, **73% tag-aware grade**. Full report: `phase-2b-2/V3E_FINAL_REPORT.md`.

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
