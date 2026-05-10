"""
claude_runner.py — Subprocess wrapper for claude -p (Claude Code print mode).

Command: claude -p --output-format json   (prompt piped via stdin)
Returns a JSON envelope; we extract the "result" field (assistant's response text),
then parse that text as JSON (our findings/requirements/policy schema).

Using shell=True + stdin avoids all quoting issues with policy/contract text
that contains double quotes, special characters, and legal language.
"""

import json
import os
import queue
import re
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path

import json_repair

# Broker name pulled from settings at runtime (falls back to generic if not configured)
def _broker_name() -> str:
    try:
        from core.settings import get as _get
        return _get("broker_name") or "the broker"
    except Exception:
        return "the broker"

try:
    import fitz as _fitz
    _FITZ_AVAILABLE = True
except ImportError:
    _fitz = None
    _FITZ_AVAILABLE = False


RATE_LIMIT_DELAY  = 5     # seconds between consecutive claude calls
ANALYSIS_TIMEOUT  = 1800  # 30 minutes per call — headroom for large chunks

# Phase 2B-2 5A: changed from --output-format json to --output-format text.
# The json-envelope mode in claude CLI has a streaming buffer that drops early
# chunks on large outputs (>~70 KB), causing mid-response truncation. text mode
# bypasses the envelope and writes the AI's raw response directly. Verified via
# diagnostic: text mode captured 50/50 findings cleanly (vs json mode losing 30+).
#
# v3d post-mortem (2026-04-29): switched from shell=True to shell=False with
# explicit argv. shell=True wrapped the call in cmd.exe; on Python's subprocess
# timeout, only cmd.exe was killed and claude.cmd / node.exe were orphaned,
# turning a 1800s timeout into a 10920s wallclock while the orphan kept retrying
# internally. We now use taskkill /T /F /PID on timeout to walk the process tree.
#
# v3c control rerun (2026-04-30): pinned to a known-good 2.1.121 binary stored
# in-repo at bin/claude-pinned-<version>.exe. The bundled-runtime auto-updater
# (`~/.local/bin/claude.exe`) replaced 2.1.121 with 2.1.123 on 2026-04-29 20:39,
# and 2.1.123 introduced a streaming-output regression that truncates large
# synthesis responses (lost the FIRST ~72 KB of a 165 KB response). The pinned
# copy is marked read-only so the auto-updater can't silently swap it. See
# BINARY_VERSIONING.md at the repo root for upgrade/rollback procedure.
_CLAUDE_BIN  = str(Path(__file__).parent.parent.parent / "bin" / "claude-pinned-2.1.121.exe")
# Stream-json args (current default — see v3e post-mortem 2026-05-01 below).
# --verbose and --include-partial-messages are required when --output-format
# stream-json is paired with -p / --print.
_CLAUDE_ARGS = ["--dangerously-skip-permissions", "-p", "--output-format", "stream-json",
                "--verbose", "--include-partial-messages"]
# Text-mode args retained for emergency fallback / diagnostics; not used by
# default. To force text mode for a specific call, set _USE_TEXT_MODE=1 in env.
_CLAUDE_TEXT_ARGS = ["--dangerously-skip-permissions", "-p", "--output-format", "text"]
# On Windows the resolved binary may be `claude.cmd` (npm shim) or `claude.exe`
# (new bundled-runtime installer). Win32 CreateProcess can't execute .cmd
# directly, so wrap those in `cmd.exe /c`. taskkill /T on timeout walks the
# resulting tree either way.
def _build_launch(args: list) -> list | None:
    if not _CLAUDE_BIN:
        return None
    if sys.platform == "win32" and _CLAUDE_BIN.lower().endswith((".cmd", ".bat")):
        return ["cmd.exe", "/c", _CLAUDE_BIN, *args]
    return [_CLAUDE_BIN, *args]

_CLAUDE_LAUNCH      = _build_launch(_CLAUDE_ARGS)
_CLAUDE_TEXT_LAUNCH = _build_launch(_CLAUDE_TEXT_ARGS)


# CLAUDE.md lives two levels above this file: app/core/ → app/ → insurance-audits/
_CLAUDE_MD_PATH = Path(__file__).parent.parent.parent / "CLAUDE.md"

# Knowledge-base path: insurance-audits/knowledge-base/by-coverage/[type]/
_KB_DIR = Path(__file__).parent.parent.parent / "knowledge-base" / "by-coverage"

# Mapping from policy_type keywords (lowercase) → KB subfolder name
_POLICY_TYPE_FOLDERS: dict[str, str] = {
    "general liability":              "gl",
    "commercial general liability":   "gl",
    " gl ":                           "gl",
    "workers compensation":           "workers-comp",
    "workers' compensation":          "workers-comp",
    "workers comp":                   "workers-comp",
    "commercial auto":                "auto",
    "business auto":                  "auto",
    "hired":                          "auto",    # hired & non-owned
    "umbrella":                       "umbrella-excess",
    "commercial umbrella":            "umbrella-excess",
    "excess":                         "umbrella-excess",
    "professional liability":         "professional-liability",
    "errors and omissions":           "professional-liability",
    "errors & omissions":             "professional-liability",
    "e&o":                            "professional-liability",
    "management liability":           "do-epli",
    "directors":                      "do-epli",
    "d&o":                            "do-epli",
    "employment practices":           "do-epli",
    "epli":                           "do-epli",
    "cyber":                          "cyber",
    "commercial property":            "property",
    "property":                       "property",
    "pollution":                      "pollution",
    "contractors pollution":          "pollution",
    "inland marine":                  "inland-marine",
}

_kb_cache: dict[str, str] = {}  # policy_type → pre-loaded reference text


def _detect_type_from_filename(filename: str) -> str:
    """Guess a policy type string from the filename for KB lookup."""
    f = filename.lower()
    if any(x in f for x in ("gl-", "-gl-", "general-liab", "cgl")):
        return "general liability"
    if any(x in f for x in ("wc-", "-wc-", "workers", "comp")):
        return "workers compensation"
    if any(x in f for x in ("auto", "vehicle")):
        return "commercial auto"
    if any(x in f for x in ("umbrella", "excess")):
        return "umbrella"
    if any(x in f for x in ("cyber",)):
        return "cyber"
    if any(x in f for x in ("pl-", "-pl-", "prof", "e&o", "eo-", "-eo-")):
        return "professional liability"
    if any(x in f for x in ("do-", "-do-", "d&o", "mgmt", "management", "epli")):
        return "management liability"
    if any(x in f for x in ("prop", "property", "building")):
        return "property"
    if any(x in f for x in ("pollut", "cpl", "environ")):
        return "pollution"
    if any(x in f for x in ("inland", "marine", "floater")):
        return "inland marine"
    return ""


def _load_kb_for_policy_type(policy_type: str) -> str:
    """
    Load reference material for a policy type from four KB sources:
      - knowledge-base/by-coverage/[type]/  up to 6 files  [COVERAGE-*]
      - knowledge-base/universal/            up to 7 files  [UNIVERSAL]
      - knowledge-base/methodology/          up to 3 files  [METHODOLOGY]
      - knowledge-base/contracts/            up to 2 files  [CONTRACTS]
    Reads .md as plain text, .pdf via PyMuPDF. 00_* files sort first within
    each source. Per-file cap: 7,500 chars. Total budget: 50,000 chars.
    Results cached per session.

    Universal cap was 6 prior to Phase 2B-2; bumped to 7 to keep all of
    {00_general-all-policies-checklist, GAP-01, GAP-02, GAP-17, GAP-18,
    GAP-20, GAP-21} in per-policy injection. Without this, GAP-21 gets
    bumped — and the per-policy AI loses the cue to populate
    designated_entity_noc_endorsements[], starving the matrix pass.
    """
    if not _KB_DIR.exists():
        return ""

    pt = (policy_type or "").lower().strip()
    if not pt:
        return ""

    if pt in _kb_cache:
        return _kb_cache[pt]

    # Map policy type to by-coverage subfolder
    folder = None
    for key, val in _POLICY_TYPE_FOLDERS.items():
        if key in pt or pt in key:
            folder = val
            break

    KB_ROOT      = _KB_DIR.parent          # knowledge-base/
    MAX_PER_FILE = 7_500
    MAX_TOTAL    = 80_000     # Phase 2B-2: bumped from 50K to fit all 7 universal files
                              # plus full coverage stack on fat-coverage policy types
                              # (Auto, GL, Property). 65K is the minimum that works for
                              # Auto today; 80K gives real headroom for GL/Property and
                              # future RMF KB additions.

    def _sort_key(p: Path) -> tuple:
        return (0 if p.name.startswith("00_") else 1, p.name.lower())

    def _read_file(f: Path) -> str:
        if f.suffix == ".md":
            return f.read_text(encoding="utf-8", errors="replace").strip()[:MAX_PER_FILE]
        if f.suffix == ".pdf" and _FITZ_AVAILABLE:
            doc = _fitz.open(str(f))
            pages: list[str] = []
            for page in doc:
                pages.append(page.get_text())
                if sum(len(t) for t in pages) >= MAX_PER_FILE:
                    break
            doc.close()
            return "\n".join(pages).strip()[:MAX_PER_FILE]
        return ""

    def _load_folder(path: Path, max_files: int, label: str) -> tuple[list[str], list[str]]:
        """Return (parts, loaded_names) for up to max_files files in path."""
        if not path.exists():
            return [], []
        candidates = sorted(
            list(path.glob("*.md")) + list(path.glob("*.pdf")),
            key=_sort_key,
        )[:max_files]
        parts: list[str] = []
        names: list[str] = []
        for f in candidates:
            try:
                text = _read_file(f)
                if len(text) > 100:
                    parts.append(f"[{label}] --- {f.name} ---\n{text}")
                    names.append(f"{label}/{f.name}")
            except Exception:
                pass
        return parts, names

    all_parts:  list[str] = []
    all_loaded: list[str] = []

    # 1. Coverage-specific files
    if folder:
        label = f"COVERAGE-{folder.upper()}"
        c_parts, c_names = _load_folder(_KB_DIR / folder, 6, label)
        all_parts.extend(c_parts)
        all_loaded.extend(c_names)

    # 2. Universal files (apply across all coverage types) — cap 7 (Phase 2B-2)
    u_parts, u_names = _load_folder(KB_ROOT / "universal", 7, "UNIVERSAL")
    all_parts.extend(u_parts)
    all_loaded.extend(u_names)

    # 3. Methodology files
    m_parts, m_names = _load_folder(KB_ROOT / "methodology", 3, "METHODOLOGY")
    all_parts.extend(m_parts)
    all_loaded.extend(m_names)

    # 4. Contracts files
    k_parts, k_names = _load_folder(KB_ROOT / "contracts", 2, "CONTRACTS")
    all_parts.extend(k_parts)
    all_loaded.extend(k_names)

    if not all_parts:
        _kb_cache[pt] = ""
        return ""

    # Enforce total budget, trimming from the end
    trimmed: list[str] = []
    total = 0
    for part in all_parts:
        if total >= MAX_TOTAL:
            break
        remaining = MAX_TOTAL - total
        trimmed.append(part[:remaining])
        total += min(len(part), remaining)

    print(
        f"[claude_runner] KB loaded for '{policy_type}': {all_loaded} "
        f"({total:,} chars)",
        file=sys.stderr,
    )
    result = (
        "\n=== REFERENCE MATERIAL FROM KNOWLEDGE BASE ===\n"
        + "\n\n".join(trimmed)
        + "\n=== END REFERENCE MATERIAL ===\n"
    )
    _kb_cache[pt] = result
    return result


# ── Methodology loader ──────────────────────────────────────────────

_CAUA_SUMMARY_PATH = (
    Path(__file__).parent.parent.parent
    / "knowledge-base" / "methodology" / "CAUA-framework-summary.md"
)


def _load_methodology() -> str:
    """Load CLAUDE.md content for injection into every analysis prompt."""
    try:
        return _CLAUDE_MD_PATH.read_text(encoding="utf-8", errors="replace")
    except Exception as exc:
        print(f"[claude_runner] WARNING: could not read CLAUDE.md: {exc}", file=sys.stderr)
        return ""


def _load_caua_summary() -> str:
    """Load the CAUA framework summary for strategic advisor prompts."""
    try:
        return _CAUA_SUMMARY_PATH.read_text(encoding="utf-8", errors="replace")
    except Exception as exc:
        print(f"[claude_runner] WARNING: could not read CAUA summary: {exc}", file=sys.stderr)
        return ""


# Coverage-type → RMF checklist file mapping (used by synthesis-stage RMF-walk)
_RMF_CHECKLIST_PATHS = [
    ("General All Policies",  "universal/00_general-all-policies-checklist.md"),
    ("CGL",                    "by-coverage/gl/00_RMF-checklist.md"),
    ("Commercial Auto",        "by-coverage/auto/00_RMF-checklist.md"),
    ("Umbrella / Excess",      "by-coverage/umbrella-excess/00_RMF-checklist.md"),
    ("Workers Compensation",   "by-coverage/workers-comp/00_RMF-checklist.md"),
]


def _load_rmf_checklists() -> str:
    """Load the active RMF checklists (universal + 4 active coverage types) for
    injection into the synthesis prompt. The synthesis stage does NOT receive the
    per-policy KB injection — these checklists must be loaded explicitly so the
    AI can walk them when generating findings.

    Total size when all 5 files present: ~12 KB.
    """
    kb_root = Path(__file__).parent.parent.parent / "knowledge-base"
    parts: list = []
    for label, rel in _RMF_CHECKLIST_PATHS:
        p = kb_root / rel
        if not p.exists():
            continue
        try:
            text = p.read_text(encoding="utf-8", errors="replace").strip()
            parts.append(f"=== RMF CHECKLIST [{label}] ===\n{text}")
        except OSError:
            pass
    if not parts:
        return ""
    return (
        "\n=== RMF (Risk Mitigation Factor) CHECKLISTS — THE AUDIT FLOOR ===\n"
        "Use these to walk every required item per policy. The synthesis output\n"
        "is graded against checklist completeness FIRST, finding depth SECOND.\n\n"
        + "\n\n".join(parts)
        + "\n=== END RMF CHECKLISTS ===\n\n"
    )


_METHODOLOGY   = _load_methodology()
_CAUA_SUMMARY  = _load_caua_summary()


# ── Startup check ───────────────────────────────────────────────────

def _check_version() -> bool:
    """Verify the pinned claude binary is reachable. Prints result to stderr."""
    try:
        r = subprocess.run(
            [_CLAUDE_BIN, "--version"],
            shell=False,
            capture_output=True,
            text=True,
            timeout=15,
            encoding="utf-8",
            errors="replace",
        )
        if r.returncode == 0:
            print(
                f"[claude_runner] claude (pinned): {r.stdout.strip()} at {_CLAUDE_BIN}",
                file=sys.stderr,
            )
            return True
        print(
            f"[claude_runner] WARNING: pinned claude --version rc={r.returncode} "
            f"stderr={r.stderr.strip()!r}",
            file=sys.stderr,
        )
        return False
    except Exception as exc:
        print(f"[claude_runner] WARNING: pinned claude not found: {exc}", file=sys.stderr)
        return False


_CLAUDE_AVAILABLE = _check_version()


# ── Core runner ────────────────────────────────────────────────────

def run_claude(prompt: str, timeout: int = ANALYSIS_TIMEOUT) -> tuple:
    """
    Invoke claude -p with the given prompt passed via stdin.

    v3e post-mortem (2026-05-01): switched default output mode from --text to
    --output-format stream-json --verbose --include-partial-messages. Rationale:
    the bundled-runtime CLI 2.1.121 has a buffer-truncation bug that drops the
    early bytes of large text-mode responses (lost the FIRST ~50 KB of a 100 KB
    response in v3e Chunk 1A1 and 1B). stream-json + partial messages emits the
    response as many small JSONL events with text_delta chunks; line-by-line
    reading bypasses the buffer-fill issue. Each delta is small enough that
    even if the buffer drops a single event, only a few chars are lost — not a
    50 KB hole at the start of the response.

    To force the legacy text-mode path for diagnostics, set _USE_TEXT_MODE=1
    in the environment before invocation. Default is stream-json.

    Process-tree kill on timeout (taskkill /T /F /PID on Windows) preserved
    from the v3d post-mortem fix.

    Returns:
        (True,  response_text)  — on success
        (False, error_message)  — on any failure
    """
    if not _CLAUDE_AVAILABLE or _CLAUDE_LAUNCH is None:
        return False, (
            "claude executable not found. "
            "Ensure Claude Code is installed and 'claude --version' works in a terminal."
        )

    use_text_mode = bool(os.environ.get("_USE_TEXT_MODE"))
    launch = _CLAUDE_TEXT_LAUNCH if use_text_mode else _CLAUDE_LAUNCH
    mode_label = "text" if use_text_mode else "stream-json"

    print(
        f"[claude_runner] run_claude mode={mode_label} bin={_CLAUDE_BIN!r} "
        f"prompt_len={len(prompt)}",
        file=sys.stderr,
    )

    tmp_dir = Path(tempfile.mkdtemp(prefix="claude_runner_"))
    tmp_out = tmp_dir / "claude_stdout.txt"  # raw output (text or JSONL)
    tmp_err = tmp_dir / "claude_stderr.txt"
    proc = None
    rc = None
    timed_out = False

    # Stream-json reconstruction state
    text_chunks: list = []
    final_result: str | None = None
    rate_limit_info: dict | None = None
    usage_info: dict | None = None
    json_lines_seen = 0
    json_lines_parse_failed = 0

    try:
        with open(tmp_out, "w", encoding="utf-8", errors="replace") as f_out, \
             open(tmp_err, "w", encoding="utf-8", errors="replace") as f_err:

            if use_text_mode:
                # Legacy text-mode path: subprocess.run with file-handle stdout.
                proc = subprocess.Popen(
                    launch,
                    stdin=subprocess.PIPE,
                    stdout=f_out,
                    stderr=f_err,
                    shell=False,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                )
                try:
                    proc.communicate(input=prompt, timeout=timeout)
                except subprocess.TimeoutExpired:
                    timed_out = True
                    if sys.platform == "win32":
                        subprocess.run(
                            ["taskkill", "/T", "/F", "/PID", str(proc.pid)],
                            capture_output=True, timeout=15,
                        )
                    else:
                        proc.kill()
                    try:
                        proc.communicate(timeout=15)
                    except subprocess.TimeoutExpired:
                        pass
            else:
                # Stream-json path: stdout=PIPE, drain line-by-line in a reader
                # thread so we can parse JSONL events incrementally and avoid
                # the buffer-fill truncation issue.
                proc = subprocess.Popen(
                    launch,
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=f_err,
                    shell=False,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    bufsize=1,  # line-buffered
                )

                line_q: queue.Queue = queue.Queue()

                def _reader():
                    """Drain proc.stdout line-by-line into the queue."""
                    try:
                        for ln in proc.stdout:
                            line_q.put(("line", ln))
                    except Exception as e:
                        line_q.put(("err", str(e)))
                    line_q.put(("eof", None))

                t = threading.Thread(target=_reader, daemon=True)
                t.start()

                # Send the prompt and close stdin so the child can finish
                try:
                    proc.stdin.write(prompt)
                    proc.stdin.close()
                except (BrokenPipeError, OSError) as e:
                    print(f"[claude_runner] stdin write error: {e}", file=sys.stderr)

                deadline = time.time() + timeout
                while True:
                    remaining = deadline - time.time()
                    if remaining <= 0:
                        timed_out = True
                        break
                    try:
                        kind, payload = line_q.get(timeout=min(2.0, remaining))
                    except queue.Empty:
                        if proc.poll() is not None:
                            # process exited — drain any remaining lines briefly
                            try:
                                while True:
                                    kind2, payload2 = line_q.get_nowait()
                                    if kind2 == "eof":
                                        break
                                    if kind2 == "line":
                                        f_out.write(payload2)
                                        json_lines_seen += 1
                                        ln = payload2.strip()
                                        if ln:
                                            try:
                                                event = json.loads(ln)
                                                _handle_stream_event(event, text_chunks,
                                                                     globals_=locals())
                                            except json.JSONDecodeError:
                                                pass
                            except queue.Empty:
                                pass
                            break
                        continue

                    if kind == "eof":
                        break
                    if kind == "err":
                        print(f"[claude_runner] reader error: {payload}", file=sys.stderr)
                        break

                    line = payload
                    f_out.write(line)
                    ln = line.strip()
                    if not ln:
                        continue
                    json_lines_seen += 1
                    try:
                        event = json.loads(ln)
                    except json.JSONDecodeError:
                        json_lines_parse_failed += 1
                        continue

                    etype = event.get("type")
                    if etype == "stream_event":
                        sub = event.get("event", {}) or {}
                        if sub.get("type") == "content_block_delta":
                            delta = sub.get("delta", {}) or {}
                            if delta.get("type") == "text_delta":
                                text_chunks.append(delta.get("text", ""))
                    elif etype == "rate_limit_event":
                        rate_limit_info = event.get("rate_limit_info") or {}
                    elif etype == "result":
                        final_result = event.get("result")
                        usage_info = event.get("usage")
                    # other event types (system init, assistant, etc.) are
                    # captured in tmp_out for diagnostics but not needed for
                    # text reconstruction.

                if timed_out:
                    if sys.platform == "win32":
                        subprocess.run(
                            ["taskkill", "/T", "/F", "/PID", str(proc.pid)],
                            capture_output=True, timeout=15,
                        )
                    else:
                        proc.kill()

                try:
                    proc.wait(timeout=15)
                except subprocess.TimeoutExpired:
                    pass

        rc = proc.returncode

        stdout_text = tmp_out.read_text(encoding="utf-8", errors="replace")
        stderr_text = tmp_err.read_text(encoding="utf-8", errors="replace")

        if use_text_mode:
            # Legacy: stdout_text IS the response text directly.
            response_text = stdout_text
            print(
                f"[claude_runner] rc={rc} stdout_len={len(stdout_text)} "
                f"stderr_len={len(stderr_text)}",
                file=sys.stderr,
            )
        else:
            # Stream-json: response_text is the reconstructed delta accumulation.
            # Fall back to final_result.result if deltas are empty (shouldn't happen).
            response_text = "".join(text_chunks) or (final_result or "")
            print(
                f"[claude_runner] rc={rc} mode=stream-json "
                f"json_lines={json_lines_seen} parse_fails={json_lines_parse_failed} "
                f"deltas={len(text_chunks)} text_chars={len(response_text)} "
                f"stderr_len={len(stderr_text)}",
                file=sys.stderr,
            )
            if rate_limit_info:
                print(
                    f"[claude_runner] rate_limit: type={rate_limit_info.get('rateLimitType')} "
                    f"status={rate_limit_info.get('status')} "
                    f"overage={rate_limit_info.get('overageStatus')} "
                    f"reason={rate_limit_info.get('overageDisabledReason')}",
                    file=sys.stderr,
                )
            if usage_info:
                print(
                    f"[claude_runner] usage: input={usage_info.get('input_tokens')} "
                    f"cache_read={usage_info.get('cache_read_input_tokens')} "
                    f"cache_create={usage_info.get('cache_creation_input_tokens')} "
                    f"output={usage_info.get('output_tokens')}",
                    file=sys.stderr,
                )

        if stderr_text.strip():
            print(
                f"[claude_runner] stderr tail (last 500): "
                f"{stderr_text.strip()[-500:]}",
                file=sys.stderr,
            )

        if timed_out:
            return False, (
                f"Timed out after {timeout}s; killed process tree. "
                f"stderr_tail={stderr_text.strip()[-300:]!r}"
            )

        _RATE_LIMIT_PHRASES = ("out of extra usage", "extra usage", "usage limit exceeded")

        if rc == 0:
            stripped = response_text.strip()
            if any(p in stripped.lower() for p in _RATE_LIMIT_PHRASES):
                print(f"[claude_runner] rate limit detected in response", file=sys.stderr)
                return False, f"RATE_LIMIT: {stripped[:600]}"
            # Legacy text-mode also tried JSON-envelope unwrap; preserve.
            if use_text_mode:
                try:
                    envelope = json.loads(stripped)
                    if isinstance(envelope, dict) and "result" in envelope:
                        return True, envelope["result"]
                except (json.JSONDecodeError, TypeError):
                    pass
            return True, stripped
        else:
            err = (stderr_text or response_text or "").strip()
            if any(p in err.lower() for p in _RATE_LIMIT_PHRASES):
                print(f"[claude_runner] rate limit detected in stderr", file=sys.stderr)
                return False, f"RATE_LIMIT: {err[:600]}"
            return False, f"claude exited {rc}: {err[:600]}"
    except FileNotFoundError as exc:
        return False, f"claude not found: {exc}"
    except Exception as exc:
        return False, f"Unexpected error: {type(exc).__name__}: {exc}"
    finally:
        keep = (
            proc is None
            or timed_out
            or rc is None
            or rc != 0
            or os.environ.get("_keep_artifacts")
        )
        if keep:
            print(
                f"[claude_runner] preserving tempfiles for diagnostics: "
                f"{tmp_out}, {tmp_err}",
                file=sys.stderr,
            )
        else:
            for p in (tmp_out, tmp_err):
                try:
                    p.unlink(missing_ok=True)
                except OSError:
                    pass
            try:
                tmp_dir.rmdir()
            except OSError:
                pass


def _handle_stream_event(event: dict, text_chunks: list, globals_=None):
    """Helper for the stream-json drain path — extract delta text only.
    rate_limit/usage are captured directly in the main loop via locals.
    Kept here for parity with the inline parsing in the drain loop."""
    etype = event.get("type")
    if etype == "stream_event":
        sub = event.get("event", {}) or {}
        if sub.get("type") == "content_block_delta":
            delta = sub.get("delta", {}) or {}
            if delta.get("type") == "text_delta":
                text_chunks.append(delta.get("text", ""))


# ── Chunking ────────────────────────────────────────────────────────

def chunk_text(text: str, max_chars: int = 80_000) -> list:
    """
    Split extracted policy text into chunks at PAGE markers, each <= max_chars chars.

    The PDF extractor writes markers in the form:
        ============================================================
        PAGE N of M
        ============================================================

    Returns a list of (chunk_text, label) tuples,
    e.g. [("...", "pages 1–80 of 300"), ("...", "pages 81–160 of 300"), ...]
    """
    if len(text) <= max_chars:
        all_m = re.findall(r'PAGE (\d+) of (\d+)', text)
        label = f"pages 1–{all_m[-1][1]} of {all_m[-1][1]}" if all_m else "all pages"
        return [(text, label)]

    # Locate every "PAGE N of M" occurrence and its position
    marker_re = re.compile(r'PAGE (\d+) of (\d+)')
    markers   = [
        (m.start(), int(m.group(1)), int(m.group(2)))
        for m in marker_re.finditer(text)
    ]

    if not markers:
        # No page markers — split on raw character count
        total_chars = len(text)
        n_chunks    = (total_chars + max_chars - 1) // max_chars
        return [
            (text[i * max_chars : (i + 1) * max_chars], f"part {i + 1} of {n_chunks}")
            for i in range(n_chunks)
        ]

    total_pages  = markers[-1][2]
    chunks       = []
    seg_start    = 0
    seg_pg_start = 1

    for j, (pos, page_num, _) in enumerate(markers):
        next_pos = markers[j + 1][0] if j + 1 < len(markers) else len(text)
        # Close the current segment when the NEXT page would push us over max_chars
        if next_pos - seg_start > max_chars and pos > seg_start:
            chunk_val = text[seg_start:pos].strip()
            if chunk_val:
                end_page = max(seg_pg_start, page_num - 1)
                chunks.append((chunk_val, f"pages {seg_pg_start}–{end_page} of {total_pages}"))
            seg_start    = pos
            seg_pg_start = page_num

    # Flush last segment
    tail = text[seg_start:].strip()
    if tail:
        chunks.append((tail, f"pages {seg_pg_start}–{total_pages} of {total_pages}"))

    return chunks or [(text, "all pages")]


# ── JSON schemas ────────────────────────────────────────────────────

_CONTRACT_SCHEMA = """{
  "source_file": "filename.pdf",
  "analysis_date": "YYYY-MM-DD",
  "contract_party": "Maricopa County",
  "contract_section_ref": "§8.1–8.2 (pp 5–7)",
  "has_insurance_provisions": true,
  "by_coverage": {
    "general_liability": {
      "minimum_per_occurrence": 2000000,
      "minimum_aggregate_general": 4000000,
      "minimum_aggregate_products": 4000000,
      "umbrella_may_satisfy_minimum": true,
      "umbrella_satisfaction_note": "Contract clause permits Commercial Umbrella attachment to meet the minimum",
      "umbrella_interpretation_ambiguous": false,
      "additional_insured_required": true,
      "additional_insured_scope": "ongoing + completed operations | ongoing only | unspecified",
      "primary_noncontributory_required": true,
      "waiver_of_subrogation_required": true,
      "section_ref": "§8.2.10",
      "exact_quote": "verbatim contract language"
    },
    "auto_liability": {
      "minimum_csl_each_occurrence": 2000000,
      "umbrella_may_satisfy_minimum": false,
      "umbrella_satisfaction_note": "Contract has program-level umbrella permission §8.2.9 but §8.2.11 Auto clause does not inline-mention umbrella. Strict reading: umbrella does NOT satisfy this line's minimum. Permissive reading: umbrella DOES satisfy. Human review required.",
      "umbrella_interpretation_ambiguous": true,
      "additional_insured_required": true,
      "primary_noncontributory_required": true,
      "waiver_of_subrogation_required": true,
      "section_ref": "§8.2.11",
      "exact_quote": "verbatim contract language"
    },
    "workers_comp": {
      "statutory_required": true,
      "waiver_of_subrogation_required": true,
      "section_ref": "§8.2.12",
      "exact_quote": "verbatim contract language"
    },
    "employers_liability": {
      "minimum_per_accident": 1000000,
      "minimum_disease_per_employee": 1000000,
      "minimum_disease_policy_limit": 1000000,
      "section_ref": "§8.2.12",
      "exact_quote": "verbatim contract language"
    },
    "professional_liability": {
      "minimum_per_claim": null,
      "minimum_aggregate": null,
      "claims_made_retro_before_contract": null,
      "extended_reporting_period_minimum_years": null,
      "additional_insured_required": null,
      "section_ref": null,
      "exact_quote": null
    },
    "cyber": {
      "minimum_per_occurrence": 5000000,
      "scope_required": ["data breach", "regulatory defense", "cyber extortion", "business interruption", "funds transfer", "third-party fidelity"],
      "section_ref": "§8.2.13",
      "exact_quote": "verbatim contract language"
    },
    "umbrella": {
      "minimum_aggregate": null,
      "follow_form_required": null,
      "section_ref": null,
      "exact_quote": null
    },
    "property": null,
    "crime": null,
    "inland_marine": null
  },
  "designated_entity_noc": {
    "required": true,
    "designated_entity": "Maricopa County",
    "notice_period_days": 30,
    "applies_to_lines": ["all"],
    "section_ref": "§8.2.15",
    "exact_quote": "verbatim contract language"
  },
  "carrier_rating_minimum": "B++",
  "claims_made_requirements": {
    "retro_must_be_before_contract_effective": true,
    "extended_reporting_period_minimum_years": 2,
    "section_ref": "§8.2.3"
  },
  "indemnification": {
    "scope": "to extent caused by contractor negligence | broad form | sole negligence carve-out",
    "section_ref": "§8.1",
    "exact_quote": "verbatim contract language"
  },
  "requirements": [
    {
      "id": "req-001",
      "type": "Additional Insured | Waiver of Subrogation | Primary & Noncontributory | Minimum Limits | Hold Harmless | Designated Entity NOC | etc.",
      "required_policy_types": ["GL", "WC", "Auto", "Umbrella", "Cyber"],
      "contract_quote": "exact verbatim text from the contract",
      "page_ref": "Section 12.3, Page 8 of 47",
      "required_by_party": "ABC General Contractor",
      "risk_flags": ["primary-noncontributory", "completed-operations", "arising-out-of"],
      "notes": "anything unusual or especially risky about this requirement"
    }
  ]
}"""

_POLICY_SCHEMA = """{
  "source_file": "filename.pdf",
  "analysis_date": "YYYY-MM-DD",
  "policy_type": "CGL | Auto | Umbrella | Workers Comp | Professional Liability | Cyber | Crime | Property | Package | Management Liability | Tech E&O | other",
  "is_package": false,
  "coverage_parts": ["GL"],
  "is_primary": true,
  "named_insured": "Company Name",
  "named_insured_entity_type": "LLC | Inc | Corp | Partnership | unspecified",
  "additional_named_insureds": [
    {
      "entity": "Runbeck Properties LLC",
      "entity_type": "LLC",
      "via_endorsement": "461-0174",
      "endorsement_name": "Multiple Named Insured Endorsement",
      "endorsement_type": "Multiple Named Insured | Schedule Named Insured | Broad Form Named Insured | Name Change | other",
      "page": 28,
      "scope_note": "Listed as Named Insured on this endorsement (LLC-friendly)",
      "broad_form_llc_risk": false
    }
  ],
  "additional_insureds": [
    {
      "entity": "Maricopa County",
      "via_endorsement": "CG 20 26",
      "endorsement_name": "Additional Insured — Designated Person or Organization",
      "page": 31,
      "scope_note": "ongoing + completed ops | ongoing only | defense only | etc."
    }
  ],
  "broad_form_ni_endorsement": {
    "present": true,
    "form_number": "421-2916",
    "page": 12,
    "excludes_llcs_or_partnerships": true,
    "excludes_note": "Item 4.b explicitly excludes LLCs, partnerships, and joint ventures from automatic coverage"
  },
  "carrier": "Hartford",
  "policy_number": "GL-XXXXXXXX",
  "effective_date": "YYYY-MM-DD",
  "expiry_date": "YYYY-MM-DD",
  "limits": {"each_occurrence": 1000000, "general_aggregate": 2000000},
  "cancellation_notice_days": {
    "for_nonpayment": 10,
    "for_other_reasons": 60,
    "page_ref": "Pg 44"
  },
  "endorsements": [
    {"form_number": "CG 20 10 04 13", "name": "Additional Insured — Scheduled", "page": 42, "notes": "Scheduled only, not blanket. Ongoing ops only."}
  ],
  "designated_entity_noc_endorsements": [
    {
      "form_number": "401-1235",
      "name": "Notice of Cancellation to Designated Entity",
      "page": 65,
      "designated_entities": ["Boulder County", "Coconino County"],
      "notice_period_days": 30
    }
  ],
  "exclusions_of_note": [
    {"name": "Total Pollution Exclusion", "form_number": "CG 21 49", "page": 38, "impact": "Absolute pollution exclusion — no coverage of any kind."}
  ],
  "checklist": {
    "additional_insured_blanket": false,
    "additional_insured_scheduled": false,
    "additional_insured_completed_ops": false,
    "waiver_of_subrogation": false,
    "waiver_of_subrogation_page": null,
    "primary_noncontributory": false,
    "contractual_liability": false,
    "per_project_aggregate": false
  }
}"""

_FINDINGS_SCHEMA = """{
  "client": "client-slug",
  "analysis_date": "YYYY-MM-DD",
  "findings": [
    {
      "id": "finding-001",
      "requirement_type": "Additional Insured — Ongoing & Completed Operations",
      "category": "Ugly | Bad | Good | Needs Review",
      "likelihood": 4,
      "severity": 4,
      "risk_score": 16,
      "contract_quote": "exact verbatim contract language",
      "contract_page": "Section 12.3, Page 8 of 47",
      "contract_file": "master-services-agreement.pdf",
      "policy_quote": "exact verbatim policy language",
      "policy_page": "Page 42 of 89",
      "policy_file": "hartford-gl-policy.pdf",
      "gap_description": "Technical explanation of the gap — what the contract requires vs. what the policy actually provides.",
      "plain_english": "CFO-friendly explanation: what this means for the business in plain English. No jargon.",
      "recommendation": "Specific action to close the gap (e.g., add CG 20 37).",
      "covered_by_other_policy": false,
      "covered_by_which_policy": null,
      "tags": ["additional-insured", "completed-operations"],
      "discoveryQuestions": [
        "Your MSA with ABC Contractor requires you to name them as an additional insured on completed operations — do you know if your current certificate reflects that, and has your carrier confirmed it?",
        "Have you ever been asked to provide proof of completed operations coverage after a project wrapped up? What happened?",
        "If a subcontractor's work caused a claim two years after project completion, do you know which policy would respond — yours or theirs?"
      ]
    }
  ]
}"""


def _methodology_header() -> str:
    """Return the CLAUDE.md methodology block for prepending to prompts."""
    if not _METHODOLOGY:
        return ""
    return (
        "=== AUDIT METHODOLOGY AND CONTEXT ===\n"
        + _METHODOLOGY
        + "\n=== END METHODOLOGY ===\n\n"
    )


# FIX 5 — Critical thinking block injected into all policy analysis prompts
_CRITICAL_THINKING_BLOCK = """
CRITICAL THINKING REQUIREMENTS — READ THIS BEFORE CATEGORIZING ANY FINDING:

THINK CRITICALLY. Do not flag something as a problem just because it looks wrong on the surface.
Before categorizing any finding as Bad or Ugly, ask yourself these questions:

1. WHY is this the way it is? Is there a legitimate reason?
   Example: NCCI class codes often have phraseology that doesn't match the common description of work.
   Class code 9014 is used for multiple types of cleaning/restoration operations — the phraseology may
   say 'Chimney Cleaning' but the code itself may be the correct classification for the work being
   performed. Before flagging a classification as wrong, consider whether the code (not just the
   description) is actually the appropriate code for the operations.

2. IS THIS CONSISTENT ACROSS THE POLICY? If the same class code, endorsement, or provision appears
   in multiple states on the same policy, that is evidence the underwriter intentionally selected it —
   not evidence of a repeated error. A code that shows up in FL, TX, AZ, and UT was probably chosen
   deliberately. Ask why before assuming it is wrong.

3. WHAT WOULD ACTUALLY HAPPEN? Think about the real-world outcome:
   - Would the carrier deny the claim based solely on a classification code? (Almost never — they would
     audit and reclassify, not deny coverage.)
   - Would there be a premium audit adjustment? (More likely.)
   - Is the rate for the 'wrong' code actually different from the 'right' code? (Often the same or very close.)

4. RESEARCH BEFORE FLAGGING: If you are unsure whether a class code, endorsement, or provision is
   correct, say so honestly. Example:
   'Class code 9014 appears on the policy for restoration operations. The phraseology reads
   "Chimney Cleaning-Residential," which does not intuitively match. However, NCCI class codes can
   cover multiple operations under a single code. This should be verified with the carrier or NCCI to
   confirm 9014 is appropriate. If it IS correct: non-issue. If it is NOT: premium implications are [X].'

5. DISTINGUISH BETWEEN REAL RISKS AND ADMINISTRATIVE ITEMS:
   - UGLY = genuine coverage gap where a claim would be DENIED. Missing state on WC (uninsured exposure),
     absolute exclusion for a covered operation, required endorsement completely absent.
   - BAD = needs attention but not claim-threatening. A sublimit, a definition that could be tighter,
     a hammer clause, a prior acts date worth verifying.
   - INFORMATIONAL NOTE (not a finding) = something that just needs verification, like a class code
     phraseology question where the code itself may be correct.
   Do NOT put a classification code phraseology question in the same severity bucket as a missing state
   on a workers' compensation policy.

6. DO NOT REPEAT THE SAME FINDING ACROSS STATES: If the same class code, exclusion, or issue appears
   in FL, TX, and AZ/UT, that is ONE finding with a note about which states it affects — not three
   separate findings. Consolidated findings are more credible and harder to dismiss than a padded list.

7. NEVER INVENT OR INFLATE: If a finding is genuinely uncertain, say so. A qualified finding with an
   honest "this needs verification" is far more credible than a confident wrong claim.

IMPORTANT ADDITIONAL RULES — READ EVERY FINDING THROUGH THESE BEFORE FINALIZING:

A. CLASS CODE 9014: NCCI class code 9014 covers multiple types of cleaning/restoration/custodial
   operations regardless of the phraseology description. The label may say "Chimney Cleaning-Residential"
   but the code is routinely applied to remediation, janitorial, custodial, and restoration operations.
   Do NOT flag 9014 (or any classification code) as wrong based on label mismatch alone. If the same
   code appears across FL, TX, AZ, UT, or other states on the same policy, it was deliberately selected.
   Flag only as Informational / "verify with carrier" — never as Bad or Ugly.

B. SURPLUS LINES / E&S CARRIERS: Many risks cannot be placed in the admitted market — that is why the
   E&S market exists. Do NOT flag a surplus lines carrier placement as critical just because the carrier
   is non-admitted. Only flag E&S placement as a concern if: (1) the same E&S carrier appears on both
   primary AND excess (concentration risk), OR (2) the risk is routine and could clearly be placed in
   the admitted market at better terms. Otherwise: Informational note only about guaranty fund
   limitations — not Ugly, not Bad.

C. SEVERITY CALIBRATION:
   - UGLY = a real claim would be DENIED. Zero coverage anywhere in the program.
   - BAD = a gap or weakness that needs attention but has partial coverage or mitigation.
   - INFORMATIONAL = needs verification but is not coverage-threatening.
   Reserve Ugly for genuine uninsured exposures. A surplus lines placement is not Ugly.
   A class code phraseology question is not Bad. Calibrate precisely.

D. QUALITY OVER QUANTITY: Fifteen well-researched findings beat thirty-five padded ones.
   If a finding is really "verify this detail with the carrier," it is Informational — period.

E. CROSS-STATE DEDUPLICATION: Same issue in FL + TX + AZ = ONE finding with multi-state note.
   Never create separate findings for the same underlying issue appearing in multiple states.
"""


# Shared instructions for populating the structured-entity fields in _POLICY_SCHEMA.
# Used by build_policy_prompt, build_standalone_policy_prompt, build_policy_chunk_prompt.
_POLICY_STRUCTURED_FIELDS_BLOCK = """
ADDITIONAL STRUCTURED FIELDS — POPULATE PRECISELY (used for cross-policy matrix analysis):

- `named_insured_entity_type`: Read the Form of Business field on the Dec page if present. Set to
  exactly one of: "LLC" | "Inc" | "Corp" | "Partnership" | "JV" | "unspecified".
  This must match the Dec page literally — do not infer from the company name.

- `additional_named_insureds[]`: List EVERY entity that appears as a Named Insured beyond the
  First Named Insured. For each, capture:
    entity            — exact entity name as it appears on the policy
    entity_type       — LLC | Inc | Corp | Partnership | JV | unspecified
    via_endorsement   — exact form number that adds this entity (e.g., "461-0174", "VP 02 79")
    endorsement_name  — full name of the endorsement
    endorsement_type  — one of: "Multiple Named Insured" | "Schedule Named Insured"
                        | "Broad Form Named Insured" | "Name Change" | "other"
    page              — page number where the entity appears
    scope_note        — short note (e.g., "Listed as Named Insured", "Added by Name Change endorsement")
    broad_form_llc_risk — true ONLY when ALL of: entity_type is LLC/Partnership/JV AND
                          endorsement_type is "Broad Form Named Insured" AND the Broad Form
                          endorsement excludes LLCs/partnerships from automatic coverage.
                          Otherwise false.
  CRITICAL — endorsement_type drives matrix reliability:
    - "Multiple Named Insured" / "Schedule Named Insured" / "Name Change" → reliable inclusion
    - "Broad Form Named Insured" → conditional inclusion. If the Broad Form text excludes
      LLCs/partnerships/JVs (very common — e.g., Hanover 421-2916 Item 4.b) and the entity
      is an LLC/Partnership/JV, set `broad_form_llc_risk: true` so the matrix flags this as
      effectively-unprotected. Also still capture the Broad Form details in
      `broad_form_ni_endorsement` below.

- `additional_insureds[]`: List entities that appear as Additional Insureds (not Named Insureds).
  Same fields plus `scope_note` describing scope (ongoing only / ongoing+completed ops / defense only).

- `broad_form_ni_endorsement`: If the policy has a Broad Form Named Insured endorsement
  (Hanover 421-2916, ISO IL 00 17, similar), capture:
    present, form_number, page,
    excludes_llcs_or_partnerships (true if the form text excludes LLCs/partnerships/JVs from
    the automatic Named Insured extension — read the form text carefully),
    excludes_note (quote the relevant clause if present).
  This is critical for GAP-01 EXPANDED analysis — a Broad Form NI that excludes LLCs does
  NOT cure a missing-LLC-entity problem on the Dec page.

- `cancellation_notice_days`: Capture the policy's cancellation notice provision:
    for_nonpayment (e.g., 10 days),
    for_other_reasons (e.g., 60 days),
    page_ref.
  Many policies have different notice periods for non-payment vs other cancellation reasons.

- `designated_entity_noc_endorsements[]`: List every Designated Entity Notice of Cancellation
  endorsement (e.g., Hanover 401-1235, ISO IL 02 45, IL 02 95). For each:
    form_number, name, page,
    designated_entities (list of customers/counties listed on the schedule),
    notice_period_days.
  These are distinct from the policy's general cancellation provision — they apply only to
  the listed entities.
"""


# ── Prompt builders ────────────────────────────────────────────────

def build_contract_prompt(filename: str, text_content: str, client_notes: str) -> str:
    """Build the prompt to extract insurance requirements from ONE contract.

    Produces structured per-coverage-line output (by_coverage), designated_entity_noc,
    carrier_rating_minimum, claims-made requirements, indemnification scope, and a
    legacy flat `requirements` array. Each coverage line populated only if explicitly
    addressed in the contract; null otherwise.
    """
    return (
        _methodology_header()
        + f"""TASK: Extract all insurance requirements from this ONE contract document.

CLIENT CONTEXT:
{client_notes}

INSTRUCTIONS:
- This input is a SINGLE contract. Set `source_file` to the exact filename below.
- Read every section. Insurance requirements appear in indemnification, risk allocation,
  general conditions, and insurance sections (often labeled "INSURANCE", "Insurance Requirements",
  or numbered §8 / §10 / §X).
- Set `has_insurance_provisions` to false if the document has no insurance schedule at all
  (e.g., it's a contract amendment that doesn't restate insurance terms). When false, set
  `by_coverage`, `designated_entity_noc`, etc. to null and explain in the legacy `notes` field.
- Otherwise populate `by_coverage` with ONE entry per line of coverage the contract addresses.
  For lines NOT addressed, set the value to null. Common lines:
    general_liability, auto_liability, workers_comp, employers_liability,
    professional_liability, cyber, umbrella, property, crime, inland_marine
- For EACH coverage line, capture:
    minimum primary limits (per occurrence / aggregate / CSL),
    whether umbrella attachment is permitted to satisfy the minimum (umbrella_may_satisfy_minimum: true/false),
    additional insured requirement and scope,
    primary & noncontributory requirement,
    waiver of subrogation requirement,
    section_ref + exact_quote.
  AMBIGUITY-FLAGGING RULE FOR umbrella_may_satisfy_minimum:
  When a contract has BOTH:
    (a) a program-level umbrella permission clause
        (e.g., §X.Y "policies may be combined with Commercial Umbrella Insurance to meet
        the minimum limit requirements" — applies to all required coverages generically)
    AND
    (b) a specific coverage-line clause that does NOT inline-mention umbrella attachment
        for that line
  → the contract is AMBIGUOUS on whether umbrella satisfies the specific line's minimum.
    Two defensible readings:
      Strict reading:    "specific governs general" — umbrella does NOT satisfy this line.
      Permissive reading: program-level (a) cross-applies — umbrella DOES satisfy.

    For any coverage line where this ambiguity exists:
      - Set umbrella_may_satisfy_minimum: false  (strict reading default)
      - Set umbrella_interpretation_ambiguous: true  (NEW field)
      - Add umbrella_satisfaction_note explaining BOTH readings explicitly:
         "Contract has program-level umbrella permission [section ref] but [coverage line]
          clause does not inline-mention umbrella. Strict reading: umbrella does NOT satisfy
          this line's minimum. Permissive reading: umbrella DOES satisfy. Human review
          required to choose which interpretation governs."

  Set umbrella_may_satisfy_minimum: true AND umbrella_interpretation_ambiguous: false ONLY
  when the SPECIFIC coverage-line clause itself explicitly says umbrella attachment is
  permitted for THAT line (e.g., "CGL — and, if necessary, Commercial Umbrella, with a
  limit of not less than $X"). In that case the inline-mention is unambiguous; no human
  review needed for that line.

  Set umbrella_may_satisfy_minimum: false AND umbrella_interpretation_ambiguous: false
  when the contract has NO umbrella permission clause at all (program-level or otherwise).
- Capture `designated_entity_noc` if the contract requires a Designated Entity NOC endorsement
  (e.g., 30-day notice to the County, ACORD 28-style requirement).
- Capture `carrier_rating_minimum` (A.M. Best rating threshold).
- Capture `claims_made_requirements` (retro before contract; ERP minimum years).
- Capture `indemnification` scope (caused-by-negligence / broad form / sole-negligence carve-out).
- Also populate the legacy `requirements` flat array — one entry per discrete obligation.
- Quote EXACT contract language verbatim. Cite pages/sections precisely.
- Return ONLY valid JSON matching the schema below. No prose before or after the JSON.

SOURCE FILE: {filename}

REQUIRED JSON SCHEMA:
{_CONTRACT_SCHEMA}

CONTRACT TEXT:
{text_content}"""
    )


def build_policy_prompt(
    filename: str,
    text_content: str,
    client_notes: str,
    requirements_json: dict,
    policy_type_hint: str = "",
) -> str:
    """Build the prompt to analyze a policy against extracted contract requirements."""
    req_str = json.dumps(requirements_json, indent=2)
    pt_hint = policy_type_hint or _detect_type_from_filename(filename)
    kb_section = _load_kb_for_policy_type(pt_hint)
    return (
        _methodology_header()
        + kb_section
        + _CRITICAL_THINKING_BLOCK
        + _POLICY_STRUCTURED_FIELDS_BLOCK
        + f"""TASK: Analyze this insurance policy against the contract requirements listed below.

CLIENT CONTEXT:
{client_notes}

CONTRACT REQUIREMENTS ALREADY EXTRACTED:
{req_str}

INSTRUCTIONS:
- You have the full extracted text of this policy below. Read every page.
- Auto-detect the policy type from the declarations page. Do not assume.
- Set `policy_type` to EXACTLY one of: "CGL", "Auto", "Umbrella", "Workers Comp",
  "Professional Liability", "Cyber", "Crime", "Property", "Package", "Management Liability",
  "Tech E&O", or "other". This is the canonical type used for matrix iteration.
  For multi-line bundles (D&O+EPLI+Crime+Fiduciary, or Property+GL+IM), set policy_type to
  "Package" or "Management Liability" and use coverage_parts[] to enumerate the actual lines
  (e.g., ["D&O", "EPLI", "Crime", "Fiduciary"]).
- Identify if monoline or package. List all coverage parts if package.
- For Management Liability packages: check for manufacturing/professional services exclusions on entity coverage.
- Note every endorsement — especially Additional Insured forms (CG 20 10, CG 20 33, CG 20 37), Waiver of Subrogation, Primary & Noncontributory, Cross Liability.
- Note every exclusion that could affect coverage for this client's operations.
- Populate all checklist fields accurately.
- Populate the ADDITIONAL STRUCTURED FIELDS block above precisely — entity matrix analysis depends on these.
- Return ONLY valid JSON matching the schema below. No prose before or after the JSON.

SOURCE FILE: {filename}

REQUIRED JSON SCHEMA:
{_POLICY_SCHEMA}

POLICY TEXT (PAGE N OF M notation preserved):
{text_content}"""
    )


def build_standalone_policy_prompt(
    filename: str,
    text_content: str,
    client_notes: str,
) -> str:
    """Build the prompt to analyze a policy on its own merits (no contracts provided)."""
    pt_hint    = _detect_type_from_filename(filename)
    kb_section = _load_kb_for_policy_type(pt_hint)
    return (
        _methodology_header()
        + kb_section
        + _CRITICAL_THINKING_BLOCK
        + _POLICY_STRUCTURED_FIELDS_BLOCK
        + f"""TASK: Analyze this insurance policy on its own merits. No upstream contracts were provided.

CLIENT CONTEXT:
{client_notes}

INSTRUCTIONS:
- You have the full extracted text of this policy below. Read every page.
- Identify the policy type from the declarations page. Do not assume — read the dec page and figure it out.
- Set `policy_type` to EXACTLY one of: "CGL", "Auto", "Umbrella", "Workers Comp",
  "Professional Liability", "Cyber", "Crime", "Property", "Package", "Management Liability",
  "Tech E&O", or "other". For multi-line bundles set "Package" or "Management Liability" and
  enumerate the actual covered lines in coverage_parts[].
- Identify if monoline or package. List all coverage parts if package.
- For Management Liability packages: check for manufacturing/professional services exclusions on entity coverage.
- Use the coverage-specific checklist from the methodology above. Find real issues:
    * Problematic exclusions (absolute, total, or unusually broad)
    * Missing standard endorsements (AI blanket, waiver of subrogation, primary & noncontributory)
    * Poorly constructed terms (narrow definitions of "professional services", "employee", "occurrence")
    * Coverage limitations, sublimits, and sunset clauses
    * Prior acts gaps on claims-made policies
    * Defense cost treatment (inside vs. outside limits)
    * Hammer clauses and consent-to-settle restrictions
- Note every endorsement, especially AI forms (CG 20 10, CG 20 33, CG 20 37).
- Note every exclusion of significance and its potential business impact.
- Populate all checklist fields accurately.
- When you find significant exclusions or gaps, note whether a DIFFERENT policy type would typically cover that exposure. Add this to the exclusion's "impact" field (e.g., "Total pollution exclusion — a Contractors Pollution Liability policy would cover environmental incidents from the client's work." or "Professional services exclusion — a standalone E&O/Professional Liability policy is needed."). This helps flag missing coverage types in the overall program.
- Do NOT generate meta-findings about missing contracts or audit completeness.
- Only report findings that come from actually reading this policy text.
- Return ONLY valid JSON matching the schema below. No prose before or after the JSON.

SOURCE FILE: {filename}

REQUIRED JSON SCHEMA:
{_POLICY_SCHEMA}

POLICY TEXT (PAGE N OF M notation preserved):
{text_content}"""
    )


def build_policy_chunk_prompt(
    filename: str,
    chunk_text: str,
    page_range: str,
    client_notes: str,
    requirements_json: dict | None = None,
) -> str:
    """
    Build a prompt for analyzing one chunk (page range) of a large policy.
    Returns a partial policy analysis for later merging.
    """
    req_section = ""
    if requirements_json and requirements_json.get("requirements"):
        req_str = json.dumps(requirements_json, indent=2)
        req_section = f"\nCONTRACT REQUIREMENTS TO CHECK AGAINST:\n{req_str}\n"

    task = (
        "Analyze this insurance policy — specifically the pages indicated below. "
        "No contracts were provided; analyze on own merits."
        if not requirements_json or not requirements_json.get("requirements")
        else "Analyze this section of the insurance policy against the contract requirements."
    )

    return (
        _methodology_header()
        + _CRITICAL_THINKING_BLOCK
        + _POLICY_STRUCTURED_FIELDS_BLOCK
        + f"""TASK: {task}

CLIENT CONTEXT:
{client_notes}
{req_section}
THIS CHUNK: {page_range} of {filename}

INSTRUCTIONS:
- Read every page in this chunk carefully.
- Extract the policy type, carrier, named insured, policy number, dates, and limits IF they appear in this chunk (dec page is usually early in the policy). If they don't appear in this chunk, leave those fields as null.
- When `policy_type` is determinable from this chunk, set it to EXACTLY one of: "CGL", "Auto",
  "Umbrella", "Workers Comp", "Professional Liability", "Cyber", "Crime", "Property", "Package",
  "Management Liability", "Tech E&O", or "other". Otherwise leave null.
- Note EVERY endorsement found in this chunk — form number, name, page, and what it does.
- Note EVERY exclusion of significance found in this chunk — name, form, page, and impact.
- Populate checklist fields for any items you can confirm from this chunk. Leave uncertain items as false.
- Do NOT invent information. If something doesn't appear in this chunk, don't report it.
- Return ONLY valid JSON matching the schema below. No prose before or after the JSON.

SOURCE FILE: {filename}
PAGE RANGE: {page_range}

REQUIRED JSON SCHEMA:
{_POLICY_SCHEMA}

POLICY TEXT — {page_range}:
{chunk_text}"""
    )


def build_policy_merge_prompt(
    filename: str,
    chunk_analyses: list,
    client_notes: str,
) -> str:
    """
    Merge multiple chunk analyses of the same policy into one unified analysis.
    """
    chunks_str = json.dumps(chunk_analyses, indent=2)
    return (
        _methodology_header()
        + f"""TASK: Merge multiple partial analyses of the same insurance policy into one unified, complete analysis.

CLIENT CONTEXT:
{client_notes}

SOURCE FILE: {filename}
NUMBER OF CHUNKS: {len(chunk_analyses)}

INSTRUCTIONS:
- You are given {len(chunk_analyses)} partial analyses, each covering a different page range of the same policy.
- Merge them into a single unified analysis:
    * Policy type, carrier, named insured, policy number, dates, and limits come from whichever chunk has the dec page data.
    * Combine ALL endorsements from all chunks into one list (deduplicate by form number).
    * Combine ALL exclusions from all chunks into one list (deduplicate by name/form number).
    * For the checklist: a field is true if ANY chunk found it to be true.
    * is_package is true if any chunk found it to be a package policy.
    * coverage_parts: union of all parts found across chunks.
- Do not invent information that wasn't present in any chunk.
- Return ONLY valid JSON matching the schema below. No prose before or after the JSON.

REQUIRED JSON SCHEMA:
{_POLICY_SCHEMA}

CHUNK ANALYSES TO MERGE:
{chunks_str}"""
    )


def build_crossref_prompt(
    client_notes: str,
    client_slug: str,
    requirements_json: dict,
    policy_analyses: list,
) -> str:
    """Build the cross-reference prompt to generate final audit findings."""
    req_str = json.dumps(requirements_json, indent=2)
    pol_str = json.dumps(policy_analyses, indent=2)
    return (
        _methodology_header()
        + _CRITICAL_THINKING_BLOCK
        + _load_rmf_checklists()
        + f"""TASK: Cross-reference all contract requirements against all insurance policies. Generate a complete, detailed set of audit findings.

CLIENT CONTEXT:
{client_notes}

CLIENT SLUG: {client_slug}

CONTRACT REQUIREMENTS:
{req_str}

POLICY ANALYSES:
{pol_str}

INSTRUCTIONS:
- RMF CHECKLIST WALK (PRIMARY AUDIT METHOD):
  For each policy in the program, the RMF checklist for that policy type is
  loaded above in the "RMF CHECKLISTS" section. These checklists define the
  items a competent commercial insurance auditor must evaluate on every audit.

  For EACH RMF item on the checklist for EACH policy:
    1. Determine whether the policy addresses it. Use the per-policy analysis
       JSON (exclusions_of_note, endorsements, checklist, coverage_parts,
       additional_named_insureds, etc.).
    2. If the item is a defect or gap → emit a Bad or Ugly finding.
    3. If the item is correctly addressed in a way worth highlighting (e.g.,
       good endorsements present, blanket AI/WoS in place) → emit a Good finding.
    4. If the policy language is ambiguous, or the determination requires
       information not in the policy/contract → emit a 'Needs Review' finding
       (category exactly: "Needs Review") with explicit explanation of what
       human judgment is required.
    5. Default to emitting a finding for every RMF item. Only omit silently
       when the item has ZERO conceivable applicability to this client based
       on industry / geography / operations (e.g., DBA for a non-government-
       overseas employer; Maritime for a landlocked non-shipping operation).

       When in doubt, emit:
         - A Good finding if the item appears compliant
         - A Needs Review finding if you can't determine applicability from
           the policy / contract data alone

       Do NOT silently skip items that are merely "no obvious gap found" —
       those are Good findings, not omissions. The audit's value comes from
       confirming what's checked AND surfacing what needs review, not from a
       curated list of only-the-obvious-problems.

       Good findings should be substantive and reference-worthy — confirming
       that a meaningful audit point is correctly addressed (e.g., "Blanket
       Waiver of Subrogation across program," "Auto Hired/Non-Owned coverage
       included"). Trivial confirmations (e.g., "Policy has a declarations
       page") are not Good findings.

  The General All Policies checklist applies to EVERY policy regardless of
  type. The coverage-specific checklist (CGL / Commercial Auto / Umbrella /
  Workers Comp) applies only to that policy type.

  The RMF checklist is the floor for audit completeness — a finding list
  missing RMF items is incomplete, regardless of how strong the substantive
  findings are. Quality is measured by RMF coverage first, then by depth of
  substantive findings on top.
- ALWAYS-EMIT ITEMS (no silent omission):

  The following RMF items must ALWAYS produce a finding for each applicable
  policy in the program (Good if compliant, Bad/Ugly if defective, Needs
  Review if ambiguous). Do NOT silently skip these — historical analysis
  shows the AI tends to drop these even though they're broadly applicable.

  Where an item appears in BOTH the CGL bucket and the Auto bucket (e.g.,
  Mental Anguish in BI / Fellow Employee / Notice & Knowledge), emit a
  SEPARATE finding for the CGL policy AND for the Auto policy — do not
  collapse to a single finding that mentions both. Each policy needs its
  own substantive analysis.

  General (cross-program):
    - Unintentional Errors and Omissions giveback (Gen-2)
    - Notice and Knowledge across program (Gen-4)

  CGL:
    - Mental Anguish in BI definition (CGL-23) — CGL-specific finding
    - Care, Custody, and Control exclusion review (CGL-2)
    - Fellow Employee Exclusion deletion (CGL-20) — CGL-specific finding
    - Notice & Knowledge officer-limited endorsement (CGL-25) — CGL-specific
    - Damage to Premises sublimit (CGL-10)
    - Duty to Defend (CGL-13)
    - TRIA / terrorism (CGL-32)

  Auto (Commercial Auto) — emit a SEPARATE Auto-specific finding for each;
  do not rely on a paired CGL finding to satisfy the Auto RMF item:
    - Additional Insured status — Automatic + Waiver of Subrogation +
      Primary & Non-contributory (CA-1)
    - BI definition includes Mental Anguish (CA-2) — Auto-specific finding,
      separate from any CGL-23 finding
    - Broad Named Insured + all Named Insureds listed (CA-3)
    - Employee as Insured CA 9933 + Employee Hired Autos CA 2054 (CA-6)
    - Environmental / limited pollution endorsement CA 99 48 (CA-8)
    - Fellow Employee Exclusion deletion (CA-9) — Auto-specific finding
    - Hired & Non-Owned Auto coverage (CA-10)
    - Mobile Equipment vs Auto definition (CA-12)
    - Notice and Knowledge officer-limited (CA-13) — Auto-specific finding
    - Ownership of Vehicles — owned vs leased vs personally-owned (CA-14)
    - Symbols 1/2 vs 7 analysis (CA-16)
    - Temporary & Leased Workers excluded from "employee" definition (CA-17)
    - Uninsured / Underinsured Motorists (CA-18)

  Umbrella:
    - Defense inside vs outside limits (UMB-5)
    - Maintenance of underlying (UMB-6)
    - Punitive damages exclusion (UMB-10)
    - Right and Duty when underlying exhausted (UMB-11)

  Workers' Compensation:
    - Small indemnity claims & back-to-work program (WC-1)
    - Small medical claims management (WC-2)
    - All States Endorsement — Item 3.A vs 3.C state coverage (WC-3)
    - Alternate Employee Endorsement — emit with "verify staffing
      arrangements" framing if leasing/staffing exposure is unclear (WC-5)
    - Employer's Liability limits adequate to support Umbrella attachment (WC-6)
    - Experience Modification trend & broker management (WC-8)
    - Large claims by name & total incurred review (WC-10)
    - All possible premium credits applied (WC-11)
    - Owners Excluded review (WC-12)
    - Classification codes correct against actual operations (WC-15)
    - Waiver of Subrogation (WC-16)

  These are items where "no finding" is information-destroying for the
  client. Emit at minimum a Good finding ("policy compliant on this point")
  or a Needs Review finding ("requires verification") for each applicable
  policy. If the per-policy analysis JSON doesn't contain enough data to
  determine compliance, that's exactly when a Needs Review finding is
  warranted — not a silent skip.

- CONDITIONAL "N/A" ITEMS (emit brief Good finding confirming non-applicability):

  Coverage-specific items that only apply under certain operations profiles.
  Emit either a full analysis (when trigger fires) OR a brief Good finding
  "N/A — [reason]" — never silent omit.

  Auto (Commercial Auto):
    - CA-4 Lease Gap — trigger: leased vehicles in symbol/schedule; else "N/A — no leased vehicles"
    - CA-5 Drive Other Car — trigger: exec officers as Named Insureds; else "N/A — no exec officer NIs"
    - CA-11 No-fault states — trigger: ops in NY/FL/MI/NJ/PA/KS/KY/ND/MN/MA/HI/UT; else "N/A — no no-fault state ops"
    - CA-15 Parked Vehicles aggregate ded — trigger: fleet parking / vehicle storage; else "N/A — no fleet parking exposure"

  Workers' Compensation:
    - WC-7 Foreign Voluntary / Endemic Disease / Repatriation — trigger: international travel or operations; else "N/A — no foreign exposure"
    - WC-9 Maritime endorsement — trigger: waterfront / vessel / dock-adjacent ops; else "N/A — no maritime exposure"
    - WC-13 DBA — trigger: US gov overseas contracts; else "N/A — no DBA exposure"
    - WC-14 USL&H / MEL — trigger: maritime / harbor / longshore exposure; else "N/A — no MEL exposure"
- AMBIGUOUS UMBRELLA ATTACHMENT (Needs Review trigger):
  If a contract requirement's coverage line has umbrella_interpretation_ambiguous: true
  in the by_coverage data, do NOT emit that line's umbrella-attachment compliance
  finding as a Bad/Ugly violation OR a Good met. Instead emit a 'Needs Review' finding
  for that line, citing both readings and asking for human judgment. Example:
    "Maricopa Auto $2M CSL — Umbrella Attachment Ambiguous (Needs Review). Maricopa
     §8.2.9 has program-level umbrella permission; §8.2.11 Auto clause does not inline-
     mention umbrella. Strict reading: $1M Auto + $10M Umbrella does not satisfy $2M
     Auto minimum (umbrella excluded). Permissive reading: $1M + $10M = $11M, far
     exceeding $2M. Recommend confirming with Maricopa County which interpretation
     they apply before treating this as compliant."

  Note: the Needs Review finding for umbrella ambiguity does NOT replace a separate
  coverage-shortfall finding for the underlying line. If the underlying CGL/Auto/etc
  policy limit is below the contract minimum, emit BOTH findings:
    1. A Bad/Ugly finding for the underlying coverage shortfall
       (e.g., "Auto CSL $1M vs $2M Maricopa minimum")
    2. A Needs Review finding for the umbrella interpretation ambiguity
       (e.g., "Whether $10M Umbrella cures this depends on contract reading")
  The two findings together surface both the raw gap and the interpretive question.
- For every requirement, check EVERY policy in the program. A gap on GL might be covered by the umbrella — always verify before calling something "Ugly."
- If a gap exists across ALL policies and could be addressed by a policy type NOT present in this program, flag it as "Ugly" and call it out explicitly in the recommendation (e.g., "No Cyber Liability policy found in this program — this is an uninsured gap. Recommend adding standalone cyber coverage." or "GL has a total pollution exclusion and no CPL is in the program — recommend Contractors Pollution Liability.").
- Common missing-policy patterns to watch for:
    * GL total pollution exclusion + no CPL → flag missing Contractors Pollution Liability
    * GL professional services exclusion + no E&O → flag missing Professional Liability
    * No Cyber policy in program → flag uninsured cyber exposure
    * No D&O / Management Liability → flag director/officer personal exposure
    * No EPLI → flag employment practices exposure
    * No Crime/Fidelity → flag employee theft and funds transfer exposure
    * Auto HNOA gap → flag hired & non-owned auto exposure
- DO NOT EMIT META-FINDINGS ABOUT THE AUDIT PROCESS ITSELF.

  Forbidden meta-findings — these describe the audit's input scope, not
  the policy's substantive content, and have no place in the findings
  list:
    * "The contract requirements file was empty / not provided"
    * "Audit Scope Limitation — Contract Requirements Not Loaded"
    * "No loss runs were supplied for this audit"
    * "Renewal Certificate provided instead of full policy form"
    * Any finding whose subject is the audit's input scope rather than
      the policy's content.

  When CONTRACT REQUIREMENTS above is empty (requirements: []), treat
  the audit as policy-only. Emit findings about the policy itself; do
  not flag the absence of contracts as a finding. Policy-only scope is
  conveyed in audit metadata and the report cover page, not in the
  findings list.

  When policy text is partial (e.g., a renewal certificate excerpt
  rather than the full form), it's appropriate to emit Needs Review
  findings on SUBSTANTIVE points that can't be confirmed from the
  partial text — but the partial text itself is not a finding.
- Categorize each finding:
  - "Good"  = policy meets or exceeds the requirement. Credit where it's due.
  - "Bad"   = gap, limitation, or problematic exclusion — needs attention but not catastrophic.
  - "Ugly"  = critical: policy expressly excludes something the contract requires, or a serious uninsured exposure that could sink the business.
- CONCRETE CARRIER-CONTROLLED MID-TERM CHANGES → Bad, not Needs Review.

  Provisions where the carrier reserves the right to change premium,
  rates, charges, or coverage terms mid-policy without the insured's
  consent are concrete policy mechanics — not "confirm with carrier"
  items. Their downside is observable directly in the policy text;
  the only uncertainty is when (not whether) the trigger fires.

  Examples (not exhaustive):
    * "Pending Rate Change" endorsements (e.g. WC 00 04 04 in NCCI
      WC forms, or carrier-specific equivalents) that permit the
      carrier to adjust premium mid-term once a state-approved rate
      filing takes effect.
    * Audit Noncompliance Charge endorsements that levy penalties
      (typically 2x premium) based on undisclosed payroll or other
      misreporting.
    * Any clause reserving carrier discretion to change coverage
      terms, rates, deductibles, or charges mid-policy without the
      insured's consent.

  Future-contingent triggers do NOT make these Needs Review. The
  model has historically misclassified Pending Rate Change as
  "needs verification" because the trigger (state filing approval)
  hasn't fired yet. That reasoning is wrong: the provision itself
  is in the policy and its mechanism is observable. Classify Bad.

  Typical scoring:
    * Severity 3 — premium movement, not coverage failure.
    * Likelihood depends on trigger frequency:
        - State rate changes: likelihood 3 (common in active filing
          environments).
        - Audit noncompliance: likelihood 1-2 (rare unless insured
          misreports).
        - Carrier-discretion coverage changes: likelihood 2.
- For Bad and Ugly findings only: score Likelihood (1-5) and Severity (1-5).
  - Likelihood: how likely this gap causes a real claim or coverage denial given this client's operations.
  - Severity: 1=<$10k, 2=$10k-$50k, 3=$50k-$250k, 4=$250k-$1M, 5=>$1M or business-threatening.
  - risk_score = likelihood × severity.
- Good findings: set likelihood, severity, and risk_score to null.
- Quote exact policy language. Cite exact page numbers.
- Write plain_english in CFO language — explain the business impact, no jargon, as if talking to a smart non-insurance person.
- Include ALL findings, Good and Bad/Ugly. Don't omit the Good ones.
- discoveryQuestions: For every Bad and Ugly finding, generate 2-4 leading questions a producer would ask the client during a discovery or pre-proposal meeting to validate and contextualize this specific issue. Requirements:
    * Open-ended and Socratic — designed to surface the client's awareness (or lack of it)
    * Specific to THIS finding, not generic insurance questions
    * Grounded in real scenarios — reference the client's industry, operations, or the contract party where relevant
    * Should naturally set up the producer's recommendation as the obvious solution
    * Written in plain, conversational language — how a trusted advisor talks, not how a policy reads
    * For Good findings: set discoveryQuestions to []
- Return ONLY valid JSON matching the schema below. No prose before or after the JSON.

REQUIRED JSON SCHEMA:
{_FINDINGS_SCHEMA}"""
    )


def build_crosspolicy_prompt(findings: list, policy_analyses: list) -> str:
    """
    Build the cross-policy intelligence prompt.

    After synthesis, review all findings across all policies to:
    - Flag where a gap in one policy is covered by another
    - Adjust covered_by_other_policy and covered_by_which_policy fields
    - Downgrade severity where coverage exists elsewhere
    """
    findings_str = json.dumps(findings, indent=2)
    policies_str = json.dumps(
        [
            {
                "source_file": p.get("source_file") or p.get("_source_file"),
                "policy_type": p.get("policy_type"),
                "policy_number": p.get("policy_number"),
                "coverage_parts": p.get("coverage_parts", []),
                "endorsements": p.get("endorsements", []),
                "checklist": p.get("checklist", {}),
            }
            for p in policy_analyses
        ],
        indent=2,
    )
    return (
        _methodology_header()
        + f"""TASK: Review audit findings across all policies for cross-policy coverage intelligence.

POLICY PROGRAM SUMMARY:
{policies_str}

CURRENT FINDINGS:
{findings_str}

INSTRUCTIONS:
- Review every Bad and Ugly finding. For each one, check ALL other policies in the program.
- If a gap found on one policy is actually covered by another policy (e.g., an exclusion on the GL is picked up by the umbrella, or a missing endorsement on one policy is present on another):
    * Set covered_by_other_policy to true
    * Set covered_by_which_policy to the name/type of the policy that covers it
    * Downgrade Ugly → Bad if fully covered elsewhere. Do not downgrade if partially covered.
    * Reduce severity by 1-2 points if substantially covered elsewhere.
    * Recompute risk_score = likelihood × severity.
- If a finding is truly an absolute gap across ALL policies in the program, leave it as-is.
- Good findings: do not change.
- Return the COMPLETE updated findings list as JSON — all findings, not just the changed ones.
- Return ONLY valid JSON with this structure: {{"findings": [...]}}
- No prose before or after the JSON."""
    )


# ── Strategic Advisor schema ────────────────────────────────────────

_STRATEGIC_ADVISOR_SCHEMA = """{
  "tbv_positioning": {
    "headline": "One sharp sentence that opens the final meeting conversation",
    "provocation_narrative": "3-5 sentence script tailored to this client's specific situation — use the briefcase, airplane, black swan, turkey, or MAG analogy as appropriate",
    "recommended_analogy": "briefcase|airplane|turkey|black_swan|mag|toothpaste",
    "analogy_rationale": "Why this analogy fits this client specifically",
    "two_objections_prep": ["Script for addressing 'we trust our broker'", "Script for addressing 'we've never had a major claim'"]
  },
  "pct_playbook": [
    {
      "finding_id": "finding-001",
      "finding_title": "Technical finding title",
      "laymen_title": "Creative, memorable non-technical title (like 'Pants unbuttoned, fly is open')",
      "severity_framing": "One sentence explaining the danger in plain English — no jargon",
      "worst_case_scenario": "Most realistic catastrophic outcome in dollars or operational impact",
      "cost_of_doing_nothing": "Quantified cost or exposure range if this goes unaddressed",
      "conviction_evidence_type": "Type of supporting evidence to find: IRMI article|court case|carrier denial letter|Hurricane Sandy/similar loss event|industry statistic",
      "our_solution": "What we will do to fix this — specific endorsement, carrier, or program",
      "presentation_sequence": 1
    }
  ],
  "broker_a_vs_b": {
    "incumbent_evidence": "Specific proof from this audit that the incumbent is a Dec-Sheet broker — cite actual findings",
    "our_differentiation": "Concrete things we did that demonstrate TBV: contract analysis, page references, exact language review",
    "transition_script": "2-3 sentence script for the Broker A vs. Broker B contrast at the final meeting"
  },
  "five_principals": {
    "product": "Assessment of our product advantage — which findings give us the clearest superiority",
    "price": "Pricing strategy — should we lead with price or let product carry?",
    "relationship": "Relationship assessment and tactics to strengthen it before the final meeting",
    "qualification": "Is this a qualified prospect? Green lights and any red flags from the findings",
    "strategy": "Overall win strategy in 2-3 sentences"
  },
  "final_meeting_outline": {
    "opening_script": "How to open the meeting — TBV recap in 60 seconds",
    "section_sequence": ["List finding titles in recommended presentation order"],
    "mid_meeting_trial_close": "One Socratic question to ask mid-presentation to test buy-in",
    "closing_statement": "Final close — airplane analogy or equivalent for this client's situation",
    "leave_behind_summary": "What to emphasize in the abbreviated executive summary (one page)"
  },
  "progress_report_agenda": [
    "Item or question to test with client at the middle meeting before the final presentation"
  ]
}"""


def build_strategic_advisor_prompt(state: dict, client_notes: str) -> str:
    """
    Build the CAUA-informed strategic advisor prompt.

    Uses CAUA framework (TBV, PCT playbook, Broker A vs B, 5 organizing principals)
    to generate positioning, PCT playbook, win strategy, and final meeting outline.

    FIX 4: Includes full citation details (policy_file, policy_page, policy_quote,
    contract_page, contract_quote) in every finding so Claude can cite them in the plan.
    """
    findings       = state.get("findings", [])
    display_name   = state.get("display_name", "the client")
    industry       = state.get("industry", "")
    client_context = client_notes or ""

    # Sort: Ugly first by risk score, then Bad — skip Good (not needed for presentation strategy)
    def _sort_key(f):
        cat   = f.get("category", "Good")
        order = {"Ugly": 0, "Bad": 1, "Good": 2}.get(cat, 3)
        score = f.get("risk_score") or 0
        return (order, -score)

    actionable = [f for f in findings if f.get("category") in ("Ugly", "Bad")]
    sorted_findings = sorted(actionable, key=_sort_key)

    # Lean fields only — keeps prompt small enough to complete within timeout
    finding_summaries = []
    for f in sorted_findings:
        finding_summaries.append({
            "id":               f.get("id"),
            "requirement_type": f.get("requirement_type"),
            "category":         f.get("category"),
            "risk_score":       f.get("risk_score"),
            "plain_english":    str(f.get("plain_english")  or ""),
            "recommendation":   str(f.get("recommendation") or ""),
            "policy_file":      f.get("policy_file"),
            "policy_page":      f.get("policy_page"),
        })

    findings_json = json.dumps(finding_summaries, indent=2)

    ugly_ct = sum(1 for f in findings if f.get("category") == "Ugly")
    bad_ct  = sum(1 for f in findings if f.get("category") == "Bad")
    good_ct = sum(1 for f in findings if f.get("category") == "Good")

    caua_context = (
        "=== CAUA STRATEGIC FRAMEWORK ===\n"
        + _CAUA_SUMMARY
        + "\n=== END CAUA FRAMEWORK ===\n\n"
        if _CAUA_SUMMARY else ""
    )

    return (
        caua_context
        + f"""TASK: Generate a complete CAUA-informed strategic advisory plan for a final account presentation.

CLIENT: {display_name}
INDUSTRY: {industry or "Not specified"}
AUDIT RESULTS: {ugly_ct} critical (Ugly), {bad_ct} needs attention (Bad), {good_ct} compliant (Good)

CLIENT CONTEXT:
{client_context}

AUDIT FINDINGS (sorted by priority — includes full citation details):
{findings_json}

INSTRUCTIONS:
You are {_broker_name()}, a Strategic Risk Consultant using the CAUA / TBV methodology to present audit findings and win this account from the incumbent broker.

Using the CAUA framework above, generate a complete strategic advisory plan:

1. TBV POSITIONING: Craft a provocation narrative tailored to THIS client's specific situation. Choose the analogy (briefcase, airplane, turkey, black swan, MAG, toothpaste) that will land best given the client's industry and the findings. Write scripts — not bullet points.

2. PCT PLAYBOOK: For every Ugly and Bad finding, create a presentation-ready entry:
   - Assign a laymen's title (creative, memorable — NOT insurance jargon)
   - Quantify the cost of doing nothing (worst-case scenario in dollars or operational terms)
   - Specify what type of conviction evidence to find (IRMI, court case, etc.)
   - Sequence the findings in optimal presentation order (most compelling Ugly findings first)

3. BROKER A vs. B: Using the ACTUAL findings from this audit as evidence, write the specific script for contrasting our TBV process vs. what the incumbent broker missed. Be specific — cite the actual gaps found.

4. FIVE PRINCIPALS ASSESSMENT: Evaluate this account on all five organizing principals. Give an honest qualification assessment — are there red flags?

5. FINAL MEETING OUTLINE: Write the actual opening script (60-second TBV recap), the recommended section sequence, a mid-presentation trial close question, and the closing statement.

6. PROGRESS REPORT AGENDA: 2-3 items to test with the client before the final meeting.

CRITICAL — CITATION REQUIREMENT (FIX 4):
Every time you reference a finding or policy problem anywhere in the strategic plan — in the PCT Playbook, the TBV Positioning, the Broker A vs. B section, the Final Meeting Outline, or anywhere else — you MUST cite the specific policy filename and page number from the finding data above.

Format citations like this:
  "New Mexico is not listed as a covered state (25-26 WC Berkley RTS Policy.pdf, Page 11 of 87)"
  "Florida crews classified as chimney sweeps (25-26 WC Berkley RTS Policy.pdf, Page 30 of 87, Class 9014)"
  "Blanket AI endorsement missing — only scheduled AI found (Hartford GL Policy.pdf, Page 42 of 89)"

Never reference a finding without telling the reader exactly which policy document and which page to look at. This is how the marked-up policy becomes the exhibit at the presentation table.

Be specific to THIS client's situation. Use the actual findings as evidence throughout.
Return ONLY valid JSON matching the schema below. No prose before or after the JSON.

REQUIRED JSON SCHEMA:
{_STRATEGIC_ADVISOR_SCHEMA}"""
    )


def build_client_research_prompt(company_name: str, website_url: str, industry: str) -> str:
    """
    Build a prompt for Claude to research a prospect company using web search.

    Returns a markdown-formatted research report covering 8 sections.
    """
    return (
        _methodology_header()
        + f"""TASK: Research the following prospect company and produce a structured intelligence report.

COMPANY: {company_name}
WEBSITE: {website_url or "Not provided"}
INDUSTRY: {industry or "Not specified"}

INSTRUCTIONS:
You are {_broker_name()}'s AI research assistant preparing for an initial prospecting meeting.
Search the web for current information about this company and produce a concise intelligence report.

Cover all 8 sections below. For each, provide 2–4 bullet points of specific, factual information.
If you cannot find reliable information for a section, write "Insufficient public data found."

SECTIONS:
1. WHAT THEY DO — Core business, products/services, key markets, value proposition
2. COMPANY SIZE — Revenue range, employee count, growth trajectory, number of locations
3. LEADERSHIP — CEO/owner name, key executives, tenure, any recent leadership changes
4. GEOGRAPHY — HQ location, operating states/countries, any recent expansions
5. RECENT NEWS — Press releases, acquisitions, lawsuits, regulatory actions, awards (last 24 months)
6. RISK FACTORS — Industry-specific risks, any publicized claims/incidents, regulatory exposure, supply chain issues
7. COMPETITIVE LANDSCAPE — Who are their main competitors? What market position do they occupy?
8. INSURANCE OPPORTUNITY — Based on their size, industry, and risk profile, what are the most likely coverage gaps or opportunities? What contract requirements might they face?

FORMAT:
Use markdown with ## headers for each section and bullet points within each section.
Keep it scannable — this is a prep document for a sales call, not an essay.
Be specific. Cite specific facts, not generic statements about the industry.

Start directly with the report content — no preamble.
"""
    )


def extract_json(text: str) -> dict | None:
    """
    Extract the first JSON object from Claude's response text.

    Attempts in order:
      1. Strip a markdown code fence and parse the inner block
      2. Parse the whole text directly
      3. Bracket-counting — walk chars to find the exact balanced end of the
         first { ... } object (handles braces inside strings and escape seqs)
      4. Last resort: first { to last } (original behaviour)

    Steps 1, 2, and 4 try strict json.loads first; on JSONDecodeError they
    fall back to json_repair.loads, which recovers from common model-output
    mistakes like unescaped quotes inside string values. Logs to stderr when
    the fallback fires. Step 3 (bracket-counting) stays strict-only — applying
    json_repair to partial input could give wrong object bounds.

    Returns None if no valid JSON object can be found.
    """
    if not text:
        return None

    def _try(t: str, label: str) -> dict | None:
        """Strict json.loads, with json_repair fallback on JSONDecodeError."""
        try:
            return json.loads(t)
        except json.JSONDecodeError as e_strict:
            try:
                result = json_repair.loads(t)
                if isinstance(result, dict) and result:
                    print(
                        f"[claude_runner] extract_json: json_repair recovered "
                        f"'{label}' (strict failed: {e_strict.msg} at line "
                        f"{e_strict.lineno})",
                        file=sys.stderr,
                    )
                    return result
            except Exception:
                pass
            return None

    # 1. Strip a markdown code fence and parse the inner block
    fence = re.search(r"```(?:json)?\s*(\{[\s\S]*?\})\s*```", text)
    if fence:
        result = _try(fence.group(1), "fence-stripped")
        if result is not None:
            return result

    # 2. Try the whole text directly
    result = _try(text.strip(), "whole-text")
    if result is not None:
        return result

    # 3. Bracket-counting — find the exact balanced end of the first { object
    start = text.find("{")
    if start != -1:
        depth   = 0
        in_str  = False
        escaped = False
        for i, ch in enumerate(text[start:], start):
            if escaped:
                escaped = False
                continue
            if ch == "\\" and in_str:
                escaped = True
                continue
            if ch == '"':
                in_str = not in_str
                continue
            if in_str:
                continue
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    try:
                        return json.loads(text[start : i + 1])
                    except json.JSONDecodeError:
                        break  # found balanced braces but still invalid — fall through

    # 4. Last resort: first { to last }
    start = text.find("{")
    end   = text.rfind("}")
    if start != -1 and end > start:
        result = _try(text[start : end + 1], "first-{-to-last-}")
        if result is not None:
            return result

    return None
