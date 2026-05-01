"""Smoke test for the audit pipeline.

Run this AFTER any system change (Claude CLI update, OS update,
dependency update, runner edit) to verify the pipeline is still healthy
before trusting it on real client work.

What it does (3-5 minutes):
  - Loads contract_extractions_v3c-postpin.json (Stage A baseline)
  - Loads the smallest per-policy analysis (Convex Excess Tech E&O — ~14 KB)
  - Builds a one-policy synthesis prompt via build_crossref_prompt
  - Calls run_claude with a 180s timeout (chunk should run in well under)
  - Verifies: rc=0, JSON parses cleanly, findings count > 0
  - Prints PASS or FAIL with reason
  - Exit code 0 on success, 1 on failure

Document this under "After-change verification" in BINARY_VERSIONING.md.
"""
import json
import sys
import time
from pathlib import Path

REPO = Path(r"C:\Users\Bogdan\Documents\insurance-audits")
sys.path.insert(0, str(REPO / "app"))

from core.claude_runner import (  # noqa: E402
    run_claude, extract_json, build_crossref_prompt,
)

CLIENT      = REPO / "clients" / "run-test-election-services"
EXCHANGE    = CLIENT / "ai-exchange"
SLUG        = "run-test-election-services"
HERE        = Path(__file__).resolve().parent
TIMEOUT_S   = 600  # synthesis on 1 small policy: typically 1-3 min, up to ~10 min under quota pressure

CLIENT_NOTES = (CLIENT / "client-notes.md").read_text(encoding='utf-8', errors='replace')


def fail(msg: str) -> None:
    print(f"SMOKE TEST FAILED: {msg}", flush=True)
    sys.exit(1)


def main() -> None:
    print("=== Audit pipeline smoke test ===", flush=True)
    t0 = time.time()

    # 1. Load contract data (baseline Stage A output)
    contract_path = HERE / "contract_extractions_v3c-postpin.json"
    if not contract_path.exists():
        fail(f"missing baseline: {contract_path}")
    requirements_data = json.load(contract_path.open(encoding='utf-8'))
    n_contracts = len(requirements_data.get("contracts") or {})
    n_reqs      = len(requirements_data.get("requirements") or [])
    print(f"  loaded contract data: {n_contracts} contracts, {n_reqs} flat reqs", flush=True)

    # 2. Pick the smallest per-policy analysis (Convex)
    candidates = sorted(EXCHANGE.glob(f"{SLUG}-policy-*-analysis.json"),
                        key=lambda p: p.stat().st_size)
    if not candidates:
        fail(f"no per-policy analyses found in {EXCHANGE}")
    smallest = candidates[0]
    pa = json.load(smallest.open(encoding='utf-8'))
    pa.setdefault("_source_file", smallest.name)
    print(f"  test policy: {smallest.name}", flush=True)
    print(f"  policy_type: {pa.get('policy_type', '(unknown)')!r}", flush=True)
    print(f"  size: {smallest.stat().st_size:,} bytes", flush=True)

    # 3. Build synthesis prompt for just this one policy
    synthesis_reqs = {
        "client":        requirements_data.get("client"),
        "analysis_date": requirements_data.get("analysis_date"),
        "requirements":  requirements_data.get("requirements") or [],
    }
    prompt = build_crossref_prompt(CLIENT_NOTES, SLUG, synthesis_reqs, [pa])
    print(f"  prompt size: {len(prompt):,} chars", flush=True)

    if len(prompt) > 200_000:
        fail(f"prompt too large for smoke test ({len(prompt):,} > 200,000) — "
             f"build_crossref_prompt may have changed, expected ~120 KB for one policy")

    # 4. Call claude
    print(f"  calling claude (timeout {TIMEOUT_S}s)...", flush=True)
    call_t0 = time.time()
    ok, result = run_claude(prompt, timeout=TIMEOUT_S)
    call_elapsed = time.time() - call_t0
    print(f"  claude returned: ok={ok}, elapsed={call_elapsed:.1f}s, "
          f"response_chars={len(result or ''):,}", flush=True)

    if not ok:
        fail(f"claude call failed: {result[:300] if result else '(empty)'}")
    if not result:
        fail("claude returned empty result despite ok=True")

    # 5. Verify JSON parse
    parsed = extract_json(result)
    if not parsed:
        fail(f"extract_json returned None on {len(result):,}-char response")
    if not isinstance(parsed, dict):
        fail(f"extract_json returned {type(parsed).__name__}, expected dict")
    if "findings" not in parsed:
        fail(f"parsed dict has keys {list(parsed.keys())}, no 'findings' key")

    findings = parsed["findings"]
    if not isinstance(findings, list):
        fail(f"'findings' is {type(findings).__name__}, expected list")
    n = len(findings)
    if n == 0:
        fail("findings list is empty (synthesis produced 0 findings)")

    # Light shape check on the first finding
    f0 = findings[0]
    required = ["category", "requirement_type"]
    for k in required:
        if k not in f0:
            fail(f"first finding missing required key {k!r} (keys present: {list(f0.keys())})")

    elapsed_total = time.time() - t0
    print(flush=True)
    print(f"SMOKE TEST PASSED ({n} findings, {elapsed_total:.1f}s total)", flush=True)
    sys.exit(0)


if __name__ == "__main__":
    main()
