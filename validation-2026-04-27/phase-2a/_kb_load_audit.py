"""KB load-audit — walk every file in knowledge-base/, label which are
loaded by the pipeline vs orphaned.

Pipeline rules (from app/core/claude_runner.py:_load_kb_for_policy_type):
  - knowledge-base/by-coverage/[type]/  *.md + *.pdf, top 6 by sort key (00_ first)
  - knowledge-base/universal/            *.md + *.pdf, top 6
  - knowledge-base/methodology/          *.md + *.pdf, top 3
  - knowledge-base/contracts/            *.md + *.pdf, top 2
  - Sort key: (0 if 00_ else 1, name.lower())
  - .docx, .doc, .pptx are NEVER loaded
  - Subdirectories (archive/) are NEVER walked

Plus dedicated reads:
  - app/core/claude_runner.py loads CLAUDE.md (project root) once for methodology header
  - app/core/claude_runner.py loads methodology/CAUA-framework-summary.md for strategic advisor
  - app/core/cross_policy.py loads universal/GAP-01, GAP-17, GAP-20, GAP-21 (specific 4 files)
"""
import sys
from pathlib import Path
from collections import defaultdict
sys.stdout.reconfigure(encoding='utf-8')

KB = Path(r"C:\Users\Bogdan\Documents\insurance-audits\knowledge-base")

LOAD_FOLDERS = {
    "by-coverage/auto":                 ("per-policy KB injection (auto)", 6),
    "by-coverage/cyber":                ("per-policy KB injection (cyber)", 6),
    "by-coverage/do-epli":              ("per-policy KB injection (do-epli)", 6),
    "by-coverage/gl":                   ("per-policy KB injection (gl)", 6),
    "by-coverage/inland-marine":        ("per-policy KB injection (inland-marine)", 6),
    "by-coverage/pollution":            ("per-policy KB injection (pollution)", 6),
    "by-coverage/professional-liability": ("per-policy KB injection (professional-liability)", 6),
    "by-coverage/property":             ("per-policy KB injection (property)", 6),
    "by-coverage/umbrella-excess":      ("per-policy KB injection (umbrella-excess)", 6),
    "by-coverage/workers-comp":         ("per-policy KB injection (workers-comp)", 6),
    "universal":                        ("per-policy KB injection (universal block)", 6),
    "methodology":                      ("per-policy KB injection (methodology block)", 3),
    "contracts":                        ("per-policy KB injection (contracts block)", 2),
}

SPECIFIC_FILES = {
    "methodology/CAUA-framework-summary.md": "loaded by claude_runner._load_caua_summary() for Strategic Advisor prompt",
    "universal/GAP-01-named-insured-verification.md": "loaded by cross_policy.load_universal_kb_block()",
    "universal/GAP-17-contract-specific-coverage-satisfaction.md": "loaded by cross_policy.load_universal_kb_block()",
    "universal/GAP-20-cross-policy-named-insured-inconsistency.md": "loaded by cross_policy.load_universal_kb_block()",
    "universal/GAP-21-designated-entity-cancellation-notice.md": "loaded by cross_policy.load_universal_kb_block()",
}


def sort_key(p):
    return (0 if p.name.startswith("00_") else 1, p.name.lower())


def loaded_set_for_folder(folder_path: Path, max_files: int) -> set:
    if not folder_path.exists():
        return set()
    candidates = sorted(
        list(folder_path.glob("*.md")) + list(folder_path.glob("*.pdf")),
        key=sort_key,
    )[:max_files]
    return {p.name for p in candidates}


# Build the master list of "loaded" files
loaded_files = {}  # rel_path -> (load_path, sort_position_within_folder)
for rel_folder, (label, max_files) in LOAD_FOLDERS.items():
    folder = KB / rel_folder
    if not folder.exists():
        continue
    candidates = sorted(
        list(folder.glob("*.md")) + list(folder.glob("*.pdf")),
        key=sort_key,
    )
    in_top_n = candidates[:max_files]
    for i, p in enumerate(in_top_n, 1):
        rel = (rel_folder + "/" + p.name).replace("\\", "/")
        loaded_files[rel] = f"{label}, slot {i}/{max_files}"
    # NOTE: bumped (top-N+1 and beyond) NOT added to loaded_files —
    # they fall through to the "ORPHANED (bumped)" branch below.

# Add specific-file overrides
for k, v in SPECIFIC_FILES.items():
    if k in loaded_files:
        loaded_files[k] = loaded_files[k] + "; ALSO " + v
    else:
        loaded_files[k] = v


# Walk every file in KB
all_files = []
for p in sorted(KB.rglob("*")):
    if not p.is_file():
        continue
    rel = str(p.relative_to(KB)).replace("\\", "/")
    if "__pycache__" in rel:
        continue
    size_kb = p.stat().st_size / 1024
    all_files.append((rel, size_kb))


# Categorize
categorized = []
for rel, size_kb in all_files:
    ext = Path(rel).suffix.lower()
    parts = rel.split("/")

    # In a subfolder of a load-folder? (archive/, etc.)
    in_archive_subfolder = (
        len(parts) >= 3 and
        any(rel.startswith(lf + "/") and parts[1] != Path(rel).name for lf in LOAD_FOLDERS)
    )
    # More precise: if the file is in a SUBDIRECTORY of a load folder (not directly inside)
    in_subdir_of_load_folder = False
    for lf in LOAD_FOLDERS:
        if rel.startswith(lf + "/"):
            remainder = rel[len(lf)+1:]
            if "/" in remainder:
                in_subdir_of_load_folder = True
                break

    if rel in loaded_files:
        status = "LOADED"
        detail = loaded_files[rel]
    elif rel in SPECIFIC_FILES:
        status = "LOADED (specific)"
        detail = SPECIFIC_FILES[rel]
    elif in_subdir_of_load_folder:
        status = "ORPHANED (in subfolder, loader doesn't recurse)"
        detail = f"subdir of a load-folder; pipeline globs only top-level *.md/*.pdf"
    elif ext in (".docx", ".doc", ".pptx", ".xlsx", ".png", ".jpg", ".gif", ".html"):
        status = "ORPHANED (non-loadable extension)"
        detail = f"loader only reads .md and .pdf; {ext} files are skipped"
    elif "/" not in rel:
        # KB root file
        status = "ORPHANED (KB root)"
        detail = "KB root files are not part of any load path"
    elif rel.startswith("strategic/") or rel.startswith("presentations/"):
        status = "ORPHANED (folder not in load paths)"
        detail = "strategic/ and presentations/ are reference-only folders"
    else:
        # Should be a .md/.pdf in a load folder but bumped from top-N
        status = "ORPHANED (bumped from top-N)"
        detail = "in a load folder but didn't sort into the top-N slots"

    categorized.append((rel, size_kb, status, detail))


# Print to RMF-LOAD-AUDIT
output = Path(r"C:\Users\Bogdan\Documents\insurance-audits\knowledge-base\methodology\KB-LOAD-AUDIT.md")

n_total = len(categorized)
n_loaded = sum(1 for _, _, s, _ in categorized if s.startswith("LOADED"))
n_orphan = sum(1 for _, _, s, _ in categorized if s.startswith("ORPHAN"))
size_total = sum(sz for _, sz, _, _ in categorized)
size_loaded = sum(sz for _, sz, s, _ in categorized if s.startswith("LOADED"))

with output.open("w", encoding="utf-8") as f:
    f.write("# KB Load Audit — Which Files Does the Pipeline Actually Read?\n\n")
    f.write(f"**Audit date:** 2026-04-29 · **Total files in `knowledge-base/`:** {n_total} · "
            f"**Loaded by pipeline:** {n_loaded} ({100*n_loaded//n_total}%) · "
            f"**Orphaned:** {n_orphan} ({100*n_orphan//n_total}%)\n\n")
    f.write(f"**Total size on disk:** {size_total:,.0f} KB · "
            f"**Loaded size:** {size_loaded:,.0f} KB ({100*size_loaded/size_total:.0f}%)\n\n")

    f.write("## Pipeline load rules (for reference)\n\n")
    f.write("From `app/core/claude_runner.py:_load_kb_for_policy_type`:\n\n")
    f.write("```\n")
    f.write("Per per-policy analysis prompt, four sources concatenated:\n")
    f.write("  1. by-coverage/[detected-type]/  → top 6 .md/.pdf, sorted (00_ first, then alphabetical)\n")
    f.write("  2. universal/                     → top 6 .md/.pdf\n")
    f.write("  3. methodology/                   → top 3 .md/.pdf\n")
    f.write("  4. contracts/                     → top 2 .md/.pdf\n")
    f.write("Per-file cap: 7,500 chars. Total budget: 50,000 chars.\n\n")
    f.write("Plus specific reads:\n")
    f.write("  - methodology/CAUA-framework-summary.md → Strategic Advisor prompt\n")
    f.write("  - universal/GAP-01, GAP-17, GAP-20, GAP-21 → cross-policy matrix prompt\n\n")
    f.write("NEVER loaded:\n")
    f.write("  - .docx, .doc, .pptx, .xlsx, .png, .jpg, .html files\n")
    f.write("  - Files in archive/ or any other subfolder of a load folder\n")
    f.write("  - knowledge-base/ root files\n")
    f.write("  - knowledge-base/strategic/ and knowledge-base/presentations/\n")
    f.write("```\n\n")

    # Group by status
    by_status = defaultdict(list)
    for row in categorized:
        rel, size_kb, status, detail = row
        by_status[status].append(row)

    for status in sorted(by_status, key=lambda s: (0 if s.startswith("LOADED") else 1, s)):
        rows = by_status[status]
        total_kb = sum(sz for _, sz, _, _ in rows)
        f.write(f"\n## {status} — {len(rows)} files ({total_kb:,.0f} KB)\n\n")
        f.write("| File | Size (KB) | Why |\n|---|---:|---|\n")
        for rel, size_kb, _, detail in rows:
            f.write(f"| `{rel}` | {size_kb:.0f} | {detail} |\n")

    # Per-folder summary
    f.write("\n\n## Per-folder summary\n\n")
    f.write("| Folder | Total files | Loaded | Orphaned (bumped) | Orphaned (subdir) | Orphaned (other) |\n")
    f.write("|---|---:|---:|---:|---:|---:|\n")
    folders = defaultdict(lambda: {"total": 0, "loaded": 0, "bumped": 0, "subdir": 0, "other": 0})
    for rel, size_kb, status, detail in categorized:
        folder = rel.split("/")[0] if "/" in rel else "(root)"
        # Treat by-coverage/* as separate folders
        if folder == "by-coverage" and "/" in rel:
            sub = rel.split("/")[1]
            folder = f"by-coverage/{sub}"
        folders[folder]["total"] += 1
        if status.startswith("LOADED"):
            folders[folder]["loaded"] += 1
        elif "bumped" in status:
            folders[folder]["bumped"] += 1
        elif "subfolder" in status:
            folders[folder]["subdir"] += 1
        else:
            folders[folder]["other"] += 1
    for folder in sorted(folders):
        d = folders[folder]
        f.write(f"| `{folder}/` | {d['total']} | {d['loaded']} | {d['bumped']} | {d['subdir']} | {d['other']} |\n")

print(f"KB-LOAD-AUDIT.md written: {n_total} files total, {n_loaded} loaded, {n_orphan} orphaned")
