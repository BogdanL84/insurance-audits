"""Chunked synthesis support for the audit pipeline.

Background: a single synthesis call with all 9 policies produces a 350+ KB
prompt. Generations on prompts >170 KB have hit truncation/hangs on the
pinned 2.1.121 binary (and worse regressions on 2.1.123). The v3e validation
established that prompts ≤150 KB run reliably under stream-json mode.

This module provides:
  - partition_policies_into_chunks: classifies policies by coverage cluster
    and bin-packs into chunks of <= max_chars.
  - run_chunked_synthesis: runs synthesis either single-call (small programs)
    or chunked (large programs); auto-selects.
  - merge_chunks: dedupes Bad/Ugly findings across chunks while preserving
    Good and Needs Review per-policy.

Generic across clients — uses policy_type / coverage_type fields plus
filename heuristics, no hardcoded per-client keywords.
"""
import json
import sys
import time
from collections import defaultdict
from pathlib import Path

from core.claude_runner import (
    run_claude,
    extract_json,
    build_crossref_prompt,
    ANALYSIS_TIMEOUT,
)


# Estimated prompt overhead from methodology + RMF + contract requirements +
# instructions (everything except the per-policy data). Measured empirically
# at ~95 KB across v3e chunks. Used to derive per-chunk policy budget.
SHARED_BLOCK_ESTIMATE = 95_000

# Default per-call prompt size budget. At ~140 KB total prompt, generation
# completes reliably in the 5-15 minute range without truncation.
DEFAULT_MAX_CHARS = 140_000

# Threshold for switching from single-call to chunked synthesis. If the
# all-policies prompt would be smaller than this, single-call is fine.
SINGLE_CALL_THRESHOLD = 130_000


# Coverage-type clusters. A policy maps to a cluster based on substring
# matches against (policy_type or coverage_type) + filename. Order matters:
# more specific matches first (e.g., "tech e&o" before generic "e&o").
_CLUSTERS = [
    ("pro-cyber", [
        # Cyber and tech-adjacent professional services first
        "tech e&o", "tech eo", "technology e&o", "technology errors",
        "cyber",
        "professional liability", "errors and omissions", "errors & omissions",
        "e&o", "media liability", "miscellaneous professional",
    ]),
    ("ml-fid-crime", [
        "management liability",
        "directors and officers", "directors & officers", "d&o", "d & o",
        "employment practices", "epli",
        "fiduciary",
        "crime", "fidelity", "social engineering",
    ]),
    ("wc", [
        "workers compensation", "workers' compensation", "workers comp",
        "wc -", " wc ", "usl&h", "longshore",
    ]),
    ("core-liability", [
        "commercial general liability", "general liability", "cgl",
        "package",
        "commercial auto", "business auto", "auto liability", "hanover - auto",
        " auto ",
        "umbrella", "excess liability", "commercial umbrella",
        "security guards",
    ]),
    ("property", [
        "commercial property", "property",
        "inland marine", "im ",
        "builders risk", "equipment breakdown",
    ]),
    ("pollution", [
        "pollution liability", "environmental",
        "contractors pollution",
    ]),
]


def _classify(pa: dict) -> str:
    """Map a per-policy analysis to one of the cluster names. Returns
    'other' if nothing matches (caller will bin-pack 'other' separately)."""
    pt   = (pa.get("policy_type") or pa.get("coverage_type") or "").lower()
    src  = (pa.get("_source_file") or pa.get("policy_file") or "").lower()
    blob = f" {pt} {src} ".lower()
    for cluster_name, keywords in _CLUSTERS:
        for kw in keywords:
            if kw in blob:
                return cluster_name
    return "other"


def _measure(pa: dict) -> int:
    """Estimate the JSON-serialized size a per-policy analysis contributes
    to a synthesis prompt. Used for bin-packing."""
    return len(json.dumps(pa, ensure_ascii=False))


def partition_policies_into_chunks(
    policy_analyses: list,
    max_chars: int = DEFAULT_MAX_CHARS,
) -> list:
    """Partition a list of per-policy analyses into chunks for synthesis.

    Returns a list of (chunk_name, [policies]) tuples. Each chunk's policies
    fit within `max_chars - SHARED_BLOCK_ESTIMATE` chars of JSON-serialized
    policy data, so the resulting synthesis prompt is bounded by max_chars.

    Strategy:
      1. Classify each policy into a coverage cluster (core-liability /
         pro-cyber / ml-fid-crime / wc / property / pollution / other).
      2. Within each cluster, bin-pack policies into chunks of <= the
         per-chunk policy budget. Largest policies first (first-fit
         decreasing) for better packing.
      3. A single policy that exceeds the budget gets its own chunk.
      4. Chunks within a cluster are numbered: 'core-liability-1',
         'core-liability-2' if the cluster needed multiple bins; otherwise
         the cluster name alone.
    """
    per_chunk_budget = max_chars - SHARED_BLOCK_ESTIMATE
    if per_chunk_budget <= 0:
        raise ValueError(
            f"max_chars={max_chars} too small; needs to exceed "
            f"SHARED_BLOCK_ESTIMATE={SHARED_BLOCK_ESTIMATE}"
        )

    # 1. Classify
    by_cluster = defaultdict(list)
    for pa in policy_analyses:
        by_cluster[_classify(pa)].append(pa)

    # 2. Bin-pack within each cluster, preserving cluster ordering for
    #    consistent chunk-name output.
    cluster_order = [c for c, _ in _CLUSTERS] + ["other"]
    chunks: list = []
    for cluster_name in cluster_order:
        policies = by_cluster.get(cluster_name) or []
        if not policies:
            continue
        # First-fit-decreasing
        policies = sorted(policies, key=_measure, reverse=True)
        bins: list[list] = []
        for pa in policies:
            sz = _measure(pa)
            placed = False
            if sz <= per_chunk_budget:
                for bin_ in bins:
                    if sum(_measure(p) for p in bin_) + sz <= per_chunk_budget:
                        bin_.append(pa)
                        placed = True
                        break
            if not placed:
                bins.append([pa])
        for i, bin_policies in enumerate(bins, 1):
            chunk_name = f"{cluster_name}-{i}" if len(bins) > 1 else cluster_name
            chunks.append((chunk_name, bin_policies))

    return chunks


def merge_chunks(chunk_findings_lists: list) -> tuple:
    """Merge synthesis findings across N chunks.

    Bad/Ugly: dedupe by (requirement_type, policy_file or 'MULTI'); keep the
    higher-risk-score entry on collision.
    Good / Needs Review: keep all (per-policy by nature).

    Returns (merged_findings_list, dup_log_list).
    """
    seen_keys: dict = {}
    merged: list = []
    dup_log: list = []
    for findings in chunk_findings_lists:
        for f in findings:
            cat = f.get("category")
            if cat in ("Bad", "Ugly"):
                key = (
                    (f.get("requirement_type") or "").strip(),
                    (f.get("policy_file") or "MULTI").strip(),
                )
                if key in seen_keys:
                    prev = seen_keys[key]
                    prev_score = prev.get("risk_score") or 0
                    cur_score  = f.get("risk_score") or 0
                    keep = f if cur_score > prev_score else prev
                    drop = prev if keep is f else f
                    dup_log.append({
                        "requirement_type":   key[0],
                        "policy_file":        key[1],
                        "kept_chunk":         keep.get("_chunk"),
                        "dropped_chunk":      drop.get("_chunk"),
                        "kept_risk_score":    keep.get("risk_score"),
                        "dropped_risk_score": drop.get("risk_score"),
                    })
                    if keep is f:
                        merged[merged.index(prev)] = f
                        seen_keys[key] = f
                else:
                    seen_keys[key] = f
                    merged.append(f)
            else:
                merged.append(f)
    return merged, dup_log


def _attach_risk_score(f: dict) -> None:
    """Compute risk_score from likelihood × severity if not already set."""
    like = f.get("likelihood")
    sev  = f.get("severity")
    if like and sev and "risk_score" not in f:
        f["risk_score"] = int(like) * int(sev)
    elif "risk_score" not in f:
        f["risk_score"] = None


def run_chunked_synthesis(
    client_notes: str,
    slug: str,
    requirements_data: dict,
    policy_analyses: list,
    *,
    max_chars: int = DEFAULT_MAX_CHARS,
    single_call_threshold: int = SINGLE_CALL_THRESHOLD,
    timeout: int = ANALYSIS_TIMEOUT,
    progress_callback=None,
) -> tuple:
    """Run the synthesis stage with auto-chunking.

    If the all-policies prompt would be smaller than `single_call_threshold`,
    runs a single synthesis call (the legacy path). Otherwise partitions the
    policies into coverage-cluster-coherent chunks and runs synthesis on
    each, then merges the per-chunk findings with cross-chunk dedup.

    Args:
      client_notes: contents of clients/<slug>/client-notes.md
      slug: client slug
      requirements_data: contract extractions (Stage A output)
      policy_analyses: list of per-policy analysis dicts
      max_chars: per-chunk prompt size budget (default 140 KB)
      single_call_threshold: prompts under this size use single-call (130 KB)
      timeout: per-call timeout in seconds
      progress_callback: optional fn(stage_label, fraction) called between
        chunks to update UI progress.

    Returns (findings, metadata) where:
      findings = merged synthesis findings list
      metadata = {
        "mode": "single-call" | "chunked",
        "chunks": [...],          # list of per-chunk metric dicts
        "duplicates_collapsed": [...],
        "errors": [...],          # (chunk_name, error_msg) tuples for any failed chunks
        "ok": bool,               # True if at least one chunk succeeded
      }
    """
    synthesis_reqs = {
        "client":        requirements_data.get("client"),
        "analysis_date": requirements_data.get("analysis_date"),
        "requirements":  requirements_data.get("requirements") or [],
    }

    # Estimate the all-policies prompt size to decide single-call vs chunked
    all_prompt = build_crossref_prompt(client_notes, slug, synthesis_reqs, policy_analyses)
    all_size = len(all_prompt)

    metadata = {
        "mode": "single-call" if all_size < single_call_threshold else "chunked",
        "chunks": [],
        "duplicates_collapsed": [],
        "errors": [],
        "all_policies_prompt_chars": all_size,
        "policy_count": len(policy_analyses),
    }

    if all_size < single_call_threshold:
        # Single-call path — preserves the legacy behavior for small clients
        if progress_callback:
            progress_callback("Synthesizing findings (single call)...", 0.0)
        t0 = time.time()
        ok, result = run_claude(all_prompt, timeout=timeout)
        elapsed = time.time() - t0
        chunk_meta = {
            "name": "single-call",
            "policy_count": len(policy_analyses),
            "prompt_chars": all_size,
            "response_chars": len(result or ""),
            "elapsed_s": round(elapsed, 1),
            "ok": ok,
        }
        if not ok:
            metadata["errors"].append(("single-call", str(result)[:300]))
            metadata["ok"] = False
            metadata["chunks"].append(chunk_meta)
            return [], metadata
        parsed = extract_json(result)
        if not parsed or "findings" not in parsed:
            metadata["errors"].append(("single-call", "JSON parse failed"))
            metadata["ok"] = False
            chunk_meta["parse_failed"] = True
            metadata["chunks"].append(chunk_meta)
            return [], metadata
        findings = parsed["findings"]
        for f in findings:
            f["_chunk"] = "single-call"
            _attach_risk_score(f)
        chunk_meta["findings_total"] = len(findings)
        metadata["chunks"].append(chunk_meta)
        metadata["ok"] = True
        if progress_callback:
            progress_callback("Synthesis complete", 1.0)
        return findings, metadata

    # Chunked path
    chunks = partition_policies_into_chunks(policy_analyses, max_chars=max_chars)
    n_chunks = len(chunks)
    findings_lists: list = []

    for idx, (chunk_name, chunk_policies) in enumerate(chunks, 1):
        if progress_callback:
            progress_callback(
                f"Synthesizing chunk {idx}/{n_chunks} ({chunk_name})...",
                (idx - 1) / n_chunks,
            )
        prompt = build_crossref_prompt(client_notes, slug, synthesis_reqs, chunk_policies)
        t0 = time.time()
        ok, result = run_claude(prompt, timeout=timeout)
        elapsed = time.time() - t0
        chunk_meta = {
            "name": chunk_name,
            "policy_count": len(chunk_policies),
            "prompt_chars": len(prompt),
            "response_chars": len(result or ""),
            "elapsed_s": round(elapsed, 1),
            "ok": ok,
        }
        if not ok:
            metadata["errors"].append((chunk_name, str(result)[:300]))
            findings_lists.append([])
            metadata["chunks"].append(chunk_meta)
            continue
        parsed = extract_json(result)
        if not parsed or "findings" not in parsed:
            metadata["errors"].append((chunk_name, "JSON parse failed"))
            chunk_meta["parse_failed"] = True
            findings_lists.append([])
            metadata["chunks"].append(chunk_meta)
            continue
        chunk_findings = parsed["findings"]
        for f in chunk_findings:
            f["_chunk"] = chunk_name
            _attach_risk_score(f)
        findings_lists.append(chunk_findings)
        chunk_meta["findings_total"] = len(chunk_findings)
        metadata["chunks"].append(chunk_meta)

    # Merge findings across chunks with dedup
    merged, dup_log = merge_chunks(findings_lists)
    metadata["duplicates_collapsed"] = dup_log
    metadata["ok"] = any(c.get("ok") and not c.get("parse_failed") for c in metadata["chunks"])

    if progress_callback:
        progress_callback("Synthesis complete", 1.0)

    return merged, metadata
