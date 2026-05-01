# Binary Versioning — Claude Code CLI

This repo pins the Claude Code CLI binary used by the audit pipeline. The
pinned binary lives at `bin/claude-pinned-<version>.exe`, is marked read-only
to defeat the bundled-runtime auto-updater, and is referenced explicitly by
`_CLAUDE_BIN` in `app/core/claude_runner.py`.

## Why we pin

On **2026-04-29 20:39:03 USMST**, Claude Code's bundled-runtime auto-updater
silently replaced `~/.local/bin/claude.exe` (version 2.1.121) with version
**2.1.123**. 2.1.123 introduced a streaming-output regression that truncates
large synthesis responses: in the Phase 2B-2 v3c control rerun on 2026-04-30,
a 165 KB synthesis response (120 findings) was captured as 93 KB (48 findings,
IDs 073–120). The first ~72 KB / 72 findings were dropped from the **start**
of the stream — classic ring-buffer / streaming-buffer truncation.

The Phase 2B-2 5A `--output-format text` workaround that handled an earlier
truncation bug does **not** fix the 2.1.123 regression.

Pinning to 2.1.121 restores the previous, working behavior until either
2.1.124+ ships a fix or we engineer a Python-side workaround.

## Current pin

| | |
|---|---|
| Version | **2.1.121** |
| Path | `bin/claude-pinned-2.1.121.exe` |
| Source | Copied from `C:\Users\Bogdan\.local\bin\claude.exe.old.1777520343473` (auto-updater's pre-swap backup) |
| sha256 | `0a85980a38e9d8fbb2ba51f1d27c3425c7870f75e053ae4be266d23e10edde4a` |
| Size | 253,241,504 bytes |
| Attribute | Read-only (`attrib +R`) |
| Referenced from | `app/core/claude_runner.py` → `_CLAUDE_BIN` |

The pinned binary is self-contained — the bundled-runtime distribution does
not require an accompanying `node_modules/` directory or PATH entry.

## How auto-update was disabled

The audit pipeline is protected from binary-version drift by **three layers**.
Layer 1 is best-effort cooperation by the binary; Layers 2 and 3 are the real
load-bearing protection.

### Layer 1 — `autoUpdates: false` in `~/.claude.json` *(best-effort)*

The bundled-runtime Claude Code installer reads `~/.claude.json` on startup.
The `autoUpdates` key is documented (informally — surfaces in the binary's
config-editing UI) and intended to disable startup-time auto-update.

**Verified state (2026-04-30):** `autoUpdates: false`. We idempotently rewrote
the value via atomic-replace tempfile and re-read to confirm.

```python
# rewrite was via tempfile + os.replace (atomic on Windows)
import json, os, tempfile
from pathlib import Path
cfg_path = Path(os.path.expanduser("~/.claude.json"))
cfg = json.load(cfg_path.open(encoding="utf-8"))
cfg["autoUpdates"] = False
fd, tmp = tempfile.mkstemp(prefix=".claude.json.", dir=str(cfg_path.parent))
with os.fdopen(fd, "w", encoding="utf-8") as t:
    json.dump(cfg, t, indent=2, ensure_ascii=False); t.write("\n")
os.replace(tmp, cfg_path)
```

**What this layer actually controls:** auto-update at binary startup. The
manual `claude update` command **ignores this setting** — confirmed by test on
2026-04-30 (running `claude update` from the pinned 2.1.121 reported
"Successfully updated from 2.1.121 to version 2.1.123" despite
`autoUpdates: false`). That's normal software behavior — manual commands
typically override config defaults.

**What we don't know:** whether `autoUpdates: false` actually prevents
auto-update at startup. The 2026-04-29 20:39:03 swap fired without our
knowledge, but we can't tell from disk forensics whether the setting was
`true` at that moment or whether the binary ignored the setting and updated
anyway. A definitive test would require waiting for a Claude Code release
newer than 2.1.123 and observing whether `~/.local/bin/claude.exe`'s mtime
changes at the next startup.

### Layer 2 — `attrib +R` on the pinned binary *(load-bearing)*

`bin/claude-pinned-2.1.121.exe` is marked read-only at the Windows filesystem
level. Any process trying to overwrite this file — including the auto-updater
running as the user — will fail with a permission error rather than silently
replacing the file. This is the same protection a sysadmin would use on a
critical config file.

A determined attacker (or a buggy auto-updater) could `attrib -R` it first,
but no observed Claude Code update path does that.

### Layer 3 — `_CLAUDE_BIN` references the pinned path explicitly *(load-bearing)*

`app/core/claude_runner.py` resolves the binary by a fixed, repo-relative path
(`bin/claude-pinned-2.1.121.exe`), not by `shutil.which("claude")` or by
honoring the `CLAUDE_CODE_EXECPATH` environment variable. So even if the
auto-updater swaps `~/.local/bin/claude.exe` from under us, the audit pipeline
keeps invoking the pinned copy.

The startup health-check log line accurately reports what's about to be
invoked: `[claude_runner] claude (pinned): 2.1.121 (Claude Code) at <pinned path>`.

### Why all three together

| Threat | Mitigated by |
|---|---|
| Startup-time auto-update modifies `~/.local/bin/claude.exe` | Layer 1 (best-effort) — but Layers 2 + 3 mean we don't care if Layer 1 fails |
| Manual `claude update` modifies `~/.local/bin/claude.exe` | We tolerate this — Layers 2 + 3 isolate the audit pipeline |
| Anything tries to overwrite the pinned `bin/` copy | Layer 2 (filesystem read-only) |
| Code resolves the wrong binary at runtime | Layer 3 (explicit path) |

**The audit pipeline is protected by Layers 2 + 3 regardless of Layer 1's
behavior.** Layer 1 is hygiene; Layers 2 + 3 are the actual protection.

### Empirical Layer 1 monitoring plan

Watch `~/.local/bin/claude.exe`'s mtime over the next several days:

```bash
ls -la ~/.local/bin/claude.exe
```

- If mtime changes without anyone manually running `claude update` →
  Layer 1 (`autoUpdates: false`) is being ignored at startup. Document the
  failure mode; rely on Layers 2 + 3.
- If mtime stays at 2026-04-29 20:39 across multiple days that include new
  Claude Code releases → Layer 1 is working at startup as advertised.

Either outcome is fine for the audit pipeline. This monitoring is purely to
accumulate ground truth about the auto-updater's actual behavior.

### `claude doctor` quirk

The `claude doctor` subcommand (advertised in `claude --help` as "Check the
health of your Claude Code auto-updater") **hangs in non-interactive mode**.
We discovered this trying to run it as part of preflight inventory; it
produced no output and had to be killed via `Stop-Process`. Don't bother
running it from a script. If you need updater diagnostics, run it from an
interactive shell directly.

### `CLAUDE_CODE_EXECPATH` is not honored

The parent claude session sets `CLAUDE_CODE_EXECPATH` in the environment
(e.g., `C:\Users\Bogdan\.local\bin\claude.exe`). This points at the
auto-updated binary, not the pinned one. Our pipeline ignores it — `_CLAUDE_BIN`
in `claude_runner.py` is computed from `__file__`, not from the environment.
This is intentional.

### `.old.<unix_ms>` rollover trap

The bundled-runtime auto-updater preserves only **one** prior version, named
`claude.exe.old.<unix_ms_timestamp>`. If a second auto-update fires before we
do anything about it, the existing `.old.<timestamp>` file is replaced — so
`~/.local/bin/claude.exe.old.1777520343473` (the 2.1.121 backup) would be
overwritten by whatever was last replaced. **Our pinned copy in
`insurance-audits/bin/` is the only durable preservation of 2.1.121.** If you
need to re-pin from the `.old` backup later, do it before the next auto-update
fires.

## Runtime PATH vs. pinned binary

`_CLAUDE_VERSION_CMD = "claude --version"` runs at module load and prints a
"claude found: <version>" line. **This is a PATH-based health check** that
finds whatever `claude` resolves to on `$PATH` (typically the auto-updated
`~/.local/bin/claude.exe`), which may report a different version than the
pinned binary. The discrepancy is by design — the startup line tells us what
the auto-updater has done; the actual subprocess invocation uses the pinned
binary regardless.

If you see a startup line like `[claude_runner] claude found: 2.1.123` but
the real call uses `bin/claude-pinned-2.1.121.exe`, that's correct.

## How to upgrade the pin

When a new Claude Code version (e.g. 2.1.124) ships and we want to evaluate
it:

1. **Acquire the new binary.** Either let the auto-updater run on
   `~/.local/bin/claude.exe` (it will preserve the old one as
   `claude.exe.old.<unix_ms_timestamp>`), or download a release artifact
   directly.
2. **Copy + verify.**
   ```bash
   cp ~/.local/bin/claude.exe insurance-audits/bin/claude-pinned-<new-version>.exe
   sha256sum insurance-audits/bin/claude-pinned-<new-version>.exe
   insurance-audits/bin/claude-pinned-<new-version>.exe --version
   ```
3. **Mark read-only.**
   ```bash
   attrib +R "C:\Users\Bogdan\Documents\insurance-audits\bin\claude-pinned-<new-version>.exe"
   ```
4. **Temporarily flip the pin** in `app/core/claude_runner.py`:
   ```python
   _CLAUDE_BIN = str(Path(__file__).parent.parent.parent / "bin" / "claude-pinned-<new-version>.exe")
   ```
5. **Run the v3c control test.** From repo root:
   ```bash
   cd "Desktop/Run-Test Policies, Contracts/validation-2026-04-27/phase-2b-2"
   _keep_artifacts=1 python _run_v3c.py
   ```
6. **Validate the result.** A passing v3c control on the new pin must show:
   - All 3 stages complete (A → B → C); driver does not crash on JSON parse
   - **~56 final findings** (yesterday's good v3c on 2.1.121 produced 56 = 13U + 26B + 5R + 12G)
   - **Maricopa Auto** flagship: contract extraction has
     `umbrella_may_satisfy_minimum: false` (strict-reading rule
     applied; with `umbrella_interpretation_ambiguous: true` if the
     contract is genuinely ambiguous)
   - Synthesis stdout starts with a proper opening object (`{` or
     ```` ```json{ ````), not mid-array
   - Synthesis response size in the ~115 KB range, not a truncated ~93 KB
7. **If the v3c control passes**, swap the pin permanently — keep the new
   version's pinned file, leave the old version's pinned file in `bin/` for
   one cycle as a rollback target, then remove on the next upgrade.
8. **If the v3c control fails**, immediately revert (see rollback).

## How to roll back

If a newly-pinned binary breaks the pipeline:

1. Edit `app/core/claude_runner.py` and change `_CLAUDE_BIN` back to the
   previous pin path.
2. (Optional) Delete the new failed pin: `rm bin/claude-pinned-<bad-version>.exe`
   (clear the read-only attribute first if needed: `attrib -R ...`).
3. Re-run the smoke test from `claude_runner.py`'s history (Tests A/B with
   `_keep_artifacts=1`/unset) to confirm the pipeline is healthy on the
   restored pin.
4. Re-run a fast pipeline check (Stage A only is sufficient if you're
   trying to avoid burning a full v3c).

## Why not pin via `shutil.which`?

Earlier versions of `claude_runner.py` resolved the binary via
`shutil.which("claude")`, which returns whatever's first on `$PATH`. That
made the pipeline silently dependent on whatever the bundled-runtime
auto-updater had most recently installed — exactly the failure mode we're
working around. The current code resolves the binary by a fixed,
repo-relative path so the audit pipeline is reproducible regardless of
what's on PATH.

The PATH-based `claude --version` health check at module load is retained
as a separate diagnostic — it tells us what the auto-updater has done
without affecting which binary gets invoked.

## Ghost diagnostic — v3d attempt 2 (2026-04-29 20:32–20:37)

The v3d synthesis run "attempt 2" exited silently with `rc=1`, empty
`stdout`, and empty `stderr` after 5.6 minutes. It looked like a rate-limit
hit or a license issue, but neither matched: the runner's rate-limit
phrase detection saw nothing, and the binary kept working on smaller calls
right after.

The actual cause: the bundled-runtime auto-updater fired at **20:39:03**,
just **~2 minutes after attempt 2 exited**. The replacement
(2.1.121 → 2.1.123) was already in flight while attempt 2 was running.
Either the in-flight subprocess got its binary or auth state replaced
underneath it, or the updater killed it as part of the swap. Either way,
the silent failure was a **timing collision with the auto-updater**, not a
prompt issue and not a rate-limit hit.

This is documented here so future-us doesn't go chasing "K+L prompt
additions broke synthesis" or "rate limits caused silent crashes" again.
The K+L prompt diffs were applied but had not been tested under good
conditions when this issue manifested.

## Field test log

### 2026-05-01 — stream-json runner migration fixes truncation on 2.1.121

The 2.1.121 binary (the pinned version) also has a truncation issue at the
output buffer level — discovered during v3e Chunk 1A1 (151 KB prompt) and
Chunk 1B (144 KB prompt) on 2026-05-01 morning. Both ran rc=0 but produced
mid-stream-truncated responses (~50 KB and ~64 KB visible vs ~100 KB+
intended). Same family as the 2.1.123 bug, just at a different threshold.

**Diagnosis:** when the binary's output is buffered as a single large block
(text mode), and generation is slow enough that the buffer pressure builds,
the binary drops the OLDEST bytes when the buffer fills. Result: response
arrives mid-sentence, with the JSON envelope opening + first findings lost.

**Fix:** switched `run_claude` default from `--output-format text` to
`--output-format stream-json --verbose --include-partial-messages`. The CLI
now emits the response as many small JSONL events with `text_delta` chunks
(typically 5–50 chars each); `run_claude` drains stdout line-by-line in a
reader thread and accumulates the deltas. Even if the buffer drops a single
event line, only a few chars are lost — not 50 KB at the start.

**Verification (2026-05-01 stress test):**
- Same 1A1 prompt (151,013 chars) that produced 51,234-char truncated text
  in text mode now produces **190,921 chars** in stream-json — 3.7× more.
- 2,686 JSONL events parsed cleanly, 0 parse failures.
- 70 findings recovered cleanly via `extract_json` (with one `json_repair`
  fallback fire on a control-character escape, which the existing fallback
  handled).
- `extract_json` now also surfaces rate-limit info (`rateLimitType`,
  `overageStatus`, `overageDisabledReason`) and per-call usage metrics
  (`input_tokens`, `cache_read_input_tokens`, `cache_creation_input_tokens`,
  `output_tokens`) to stderr for observability.

**Fallback:** the legacy text-mode path is preserved in `_CLAUDE_TEXT_LAUNCH`
and selectable via `_USE_TEXT_MODE=1` environment variable. Default is
stream-json.

**Code location:** `app/core/claude_runner.py:run_claude`. Reader thread,
JSONL event handling, taskkill on timeout, and tempfile diagnostics are all
in the same function.

### 2026-04-30 ~08:50 — first real hang test of the new runner

Ran the full v3c pipeline on the pinned 2.1.121 binary with `_keep_artifacts=1`
to validate (a) the new runner under load and (b) the pinned binary's behavior
on a known-good prompt.

**Runner: verified working under timeout conditions.**

Stage B (synthesis) hung silently. `claude.exe` was alive for the full 30-minute
subprocess timeout window, wrote zero bytes to both stdout and stderr, and
never returned. The runner correctly fired `taskkill /T /F /PID` at exactly
1800s, walked the process tree, drained the file handles, and returned a clean
error string with `stderr_tail=''`. Pre-fix, the same hang would have
wallclocked at 3+ hours because `shell=True` orphaning would have left
`claude.exe` running until it self-terminated. The new runner saved
~150 minutes of wasted clock time and returned a deterministic timeout error
instead of an indefinite hang. **This is the first real-world validation of
the `taskkill /T` branch.**

**Stage B: silent hang — distinct from previous failure modes.**

| Date | Failure mode | Bytes captured | Wallclock |
|---|---|---|---|
| 2026-04-29 v3d attempt 1 (2.1.121, pre-runner-fix) | partial-response idle | 59 (`"API Error: Stream idle timeout - partial response received"`) | 10,920 s (orphan never killed) |
| 2026-04-30 morning v3c (2.1.123, runner fix in place) | mid-response truncation | 92,690 (lost first ~72 KB / 72 findings) | 1,365 s |
| **2026-04-30 v3c on pinned 2.1.121 (runner fix in place)** | **zero-byte silent hang from start** | **0** | **1,800 s (clean timeout via taskkill /T)** |

Three different failure modes; only one (the 2.1.123 truncation) is
binary-specific. The other two share a "stream-idle" upstream behavior
pattern that's independent of binary version.

**Hypotheses (cannot disambiguate without different-time retries):**

1. *Anthropic API regional/load-based behavior.* This morning's calls hit
   different upstream behavior than yesterday afternoon's identical calls.
2. *Cumulative Max-plan usage in the rolling 5-hour window.* Today's
   pre-Stage-B activity (smoke tests, `claude update` test, partial v3c run)
   may have tripped a soft throttle that manifests at the SSE-stream layer
   rather than as an explicit rate-limit error.
3. *Session/auth state issue specific to long-running calls.* All four
   Stage A calls (≤3 min each) succeeded with rc=0 immediately before; only
   the ≥10-min synthesis call hung. Possible auth/session timeout interaction
   specific to long requests.

**Recommend tomorrow morning as the first retry window** — fresh 5-hour quota,
fresh session state, lower API load. If the same hang reproduces tomorrow,
the throttle hypothesis is weakened and we'd prioritize a debug-flag retry
(`claude --debug api,hooks`) to capture upstream signal, or a chunked-synthesis
refactor to insulate against per-call stream-idle.

**State on disk after this run:**
- `findings_v3c.json` — sha256-verified intact (yesterday's good run, never overwritten by today's crashed pipeline)
- `findings_v3c-prepin.json` — explicit yesterday backup, identical sha256
- `contract_extractions_v3c.json` — today's Stage A output (more thorough Maricopa §8.2.9/§8.2.11 reasoning + `umbrella_interpretation_ambiguous: true`)
- `contract_extractions_v3c-postpin.json` — explicit copy of today's Stage A
- `synthesis_v3c.json`, `matrix_v3c_*.json` — yesterday's good run, never reached during today's crash
- Stage B tempfile preserved at `C:\Users\Bogdan\AppData\Local\Temp\claude_runner_ooh5_5zc\` with 0-byte stdout + 0-byte stderr — the smoking gun for the silent-hang hypothesis

## After-change verification

Run the smoke test AFTER any system change before trusting the pipeline on
real client work. System changes that warrant a smoke test:

- Claude Code CLI update (auto or manual)
- OS update (Windows feature update, .NET runtime, etc.)
- Python or dependency upgrade (`pip install -U ...`)
- Edits to `app/core/claude_runner.py`, `build_crossref_prompt`, or `extract_json`
- Anaconda environment changes
- New machine / restored backup

**The smoke test:** `validation-2026-04-27/phase-2b-2/_smoke_test.py`

```bash
cd "validation-2026-04-27/phase-2b-2"
python _smoke_test.py
```

**What it does:** loads the v3c contract baseline + the smallest per-policy
analysis (Convex Cyber, ~14 KB), builds a one-policy synthesis prompt, calls
`run_claude` with a 600-second timeout, verifies the response parses as JSON
with at least one finding. Exit code 0 = PASS, 1 = FAIL.

**Expected runtime:** 1–10 minutes. Typical clean runs finish in 1–3 min.
Slower 5–10 min runs indicate quota pressure or transient API slowness but
are still PASS if findings come back. Outright timeout or parse failure is
the FAIL signal that should block downstream work until investigated.

**What FAIL means by failure mode:**
- "Timed out after 600s" → real call hung or generation slowed beyond
  threshold; check `_USE_TEXT_MODE=1` to compare; check rate-limit info in
  stderr; possibly Anthropic API issue
- "extract_json returned None" → response shape changed (model variation,
  prompt regression, or new escape pattern that json_repair can't recover);
  inspect `_stage_b_*_response_raw.txt` from the preserved tempfile
- "claude exited 1: ..." → likely auth/permission issue; check the pinned
  binary still runs (`<pin> --version`)

## Files

- **The pin**: `bin/claude-pinned-2.1.121.exe` (read-only)
- **The reference**: `app/core/claude_runner.py:_CLAUDE_BIN`
- **This doc**: `BINARY_VERSIONING.md`
- **Pre-swap backup retained by auto-updater (do not delete; useful for
  re-pinning if `bin/` is wiped)**: `~/.local/bin/claude.exe.old.1777520343473`
