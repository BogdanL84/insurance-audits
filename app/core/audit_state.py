"""
audit_state.py — Read/write audit-state.json for each client.

Every client has:
  clients/[slug]/output/audit-state.json  ← master data file
  clients/[slug]/client-notes.md          ← human-readable summary
"""

import json
import re
import shutil
from pathlib import Path
from datetime import datetime


# ── Empty state template ───────────────────────────────────────────
def _empty_state() -> dict:
    return {
        "client":        "",
        "display_name":  "",
        "created":       "",
        "last_modified": "",
        "stage":         "setup",
        "client_info":   {},
        "contracts":     {},
        "policies":      {},
        "references":    {},
        "findings":      [],
        "checklist":     {},
    }


# ── Load / Save ────────────────────────────────────────────────────
def load(client_path: Path) -> dict:
    """Load audit-state.json for a client. Returns empty state if not found."""
    state_file = client_path / "output" / "audit-state.json"
    if not state_file.exists():
        return _empty_state()
    try:
        with open(state_file, encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return _empty_state()


def save(client_path: Path, state: dict) -> None:
    """Atomically save audit-state.json."""
    output_dir = client_path / "output"
    output_dir.mkdir(parents=True, exist_ok=True)
    state["last_modified"] = datetime.now().isoformat()
    state_file = output_dir / "audit-state.json"
    tmp_file   = state_file.with_suffix(".tmp")
    with open(tmp_file, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2, ensure_ascii=False)
    tmp_file.replace(state_file)


# ── Initialize a new client ────────────────────────────────────────
def initialize(client_slug: str, display_name: str, client_info: dict) -> dict:
    state = _empty_state()
    state["client"]       = client_slug
    state["display_name"] = display_name
    state["created"]      = datetime.now().isoformat()
    state["stage"]        = "setup"
    state["client_info"]  = client_info
    return state


# ── Create folder structure for a new client ──────────────────────
def create_client_folders(clients_dir: Path, slug: str) -> Path:
    client_path = clients_dir / slug
    for subdir in ("contracts", "policies", "references", "ai-exchange", "output"):
        (client_path / subdir).mkdir(parents=True, exist_ok=True)
    return client_path


# ── Write human-readable client-notes.md ──────────────────────────
def write_client_notes(client_path: Path, state: dict) -> None:
    info = state.get("client_info", {})
    lines = [
        f"# {state['display_name']}",
        "",
        f"**Industry:** {info.get('industry', '—')}",
        f"**Revenue:** {info.get('revenue', '—')}",
        f"**Employees:** {info.get('employees', '—')}",
        f"**States:** {', '.join(info.get('states', [])) or '—'}",
    ]
    risks = info.get("special_risks", [])
    if risks:
        lines.append(f"**Special Risks:** {', '.join(risks)}")

    parties = info.get("contract_parties", [])
    if parties:
        lines += ["", "## Upstream Contract Parties"]
        for p in parties:
            lines.append(f"- {p}")

    notes = info.get("notes", "").strip()
    if notes:
        lines += ["", "## Notes", notes]

    lines += [
        "",
        "---",
        f"*Last updated: {datetime.now().strftime('%Y-%m-%d')}*",
    ]
    (client_path / "client-notes.md").write_text(
        "\n".join(lines), encoding="utf-8"
    )


# ── Slug helpers ───────────────────────────────────────────────────
def slugify(name: str) -> str:
    """Convert display name to a safe folder slug."""
    slug = name.lower().strip()
    slug = re.sub(r"[^\w\s-]", "", slug)
    slug = re.sub(r"[\s_]+", "-", slug)
    slug = re.sub(r"-+", "-", slug).strip("-")
    return slug or "client"


def slug_exists(clients_dir: Path, slug: str) -> bool:
    return (clients_dir / slug).exists()


# ── Summary for dashboard cards ────────────────────────────────────
def get_summary(state: dict) -> dict:
    findings   = state.get("findings", [])
    contracts  = state.get("contracts", {})
    policies   = state.get("policies", {})
    references = state.get("references", {})

    good = sum(1 for f in findings if f.get("category") == "Good")
    bad  = sum(1 for f in findings if f.get("category") == "Bad")
    ugly = sum(1 for f in findings if f.get("category") == "Ugly")

    return {
        "good":                 good,
        "bad":                  bad,
        "ugly":                 ugly,
        "total_findings":       len(findings),
        "contracts":            len(contracts),
        "policies":             len(policies),
        "references":           len(references),
        "contracts_extracted":  sum(1 for c in contracts.values() if c.get("extracted")),
        "policies_extracted":   sum(1 for p in policies.values() if p.get("extracted")),
    }


# ── Auto-advance stage ─────────────────────────────────────────────
def refresh_stage(state: dict) -> dict:
    contracts = state.get("contracts", {})
    policies  = state.get("policies", {})
    findings  = state.get("findings", [])

    has_docs      = contracts or policies
    has_extracted = (
        any(c.get("extracted") for c in contracts.values()) or
        any(p.get("extracted") for p in policies.values())
    )
    has_findings  = bool(findings)
    all_reviewed  = has_findings and all(f.get("reviewed") for f in findings)

    if state.get("stage") == "output_generated":
        # Don't downgrade if output was already generated
        return state

    if all_reviewed:
        state["stage"] = "findings_reviewed"
    elif has_findings:
        state["stage"] = "findings_imported"
    elif has_extracted:
        state["stage"] = "text_extracted"
    elif has_docs:
        state["stage"] = "docs_uploaded"
    else:
        state["stage"] = "setup"

    return state


# ── List all clients for dashboard ────────────────────────────────
def list_clients(clients_dir: Path) -> list:
    if not clients_dir.exists():
        return []

    clients = []
    for folder in sorted(clients_dir.iterdir()):
        if not folder.is_dir():
            continue
        # Skip hidden/system folders
        if folder.name.startswith("."):
            continue

        state   = load(folder)
        summary = get_summary(state)

        last_mod = state.get("last_modified", "")
        try:
            from datetime import datetime as dt
            last_mod_dt  = dt.fromisoformat(last_mod) if last_mod else None
            last_mod_str = last_mod_dt.strftime("%b %d, %Y") if last_mod_dt else "—"
        except ValueError:
            last_mod_str = "—"

        # Format last_analysis_date for display
        analysis_date = state.get("last_analysis_date", "")
        try:
            from datetime import datetime as dt2
            analysis_dt  = dt2.fromisoformat(analysis_date) if analysis_date else None
            analysis_str = analysis_dt.strftime("%b %d, %Y") if analysis_dt else ""
        except ValueError:
            analysis_str = ""

        clients.append({
            "slug":                folder.name,
            "path":                folder,
            "display_name":        state.get("display_name") or folder.name,
            "industry":            state.get("client_info", {}).get("industry", ""),
            "last_modified":       last_mod_str,
            "stage":               state.get("stage", "setup"),
            "summary":             summary,
            "policy_type_counts":  state.get("policy_type_counts", {}),
            "last_analysis_date":  analysis_str,
        })
    return clients


# ── Register a document upload in state ───────────────────────────
def register_document(state: dict, filename: str, doc_type: str,
                       size_mb: float, page_count: int) -> dict:
    """doc_type: 'contract', 'policy', or 'reference'"""
    if doc_type == "contract":
        key = "contracts"
    elif doc_type == "policy":
        key = "policies"
    else:
        key = "references"
    entry = state.setdefault(key, {})

    if filename not in entry:
        entry[filename] = {
            "uploaded":   datetime.now().isoformat(),
            "extracted":  doc_type == "reference",  # images need no extraction
            "size_mb":    round(size_mb, 2),
            "page_count": page_count,
        }
    return state


def mark_extracted(state: dict, filename: str, doc_type: str,
                   word_count: int) -> dict:
    """Mark a document as extracted and store word count."""
    key = "contracts" if doc_type == "contract" else "policies"
    if filename in state.get(key, {}):
        state[key][filename]["extracted"]    = True
        state[key][filename]["word_count"]   = word_count
        state[key][filename]["extracted_at"] = datetime.now().isoformat()
    return state


# ── Prior run archiving ────────────────────────────────────────────
def archive_run(state: dict) -> None:
    """
    Archive the current findings into prior_runs before overwriting.
    Stores full finding snapshots with timestamp and summary counts.
    Keeps at most 5 prior runs (oldest dropped first).

    Call this BEFORE writing new findings to state["findings"].
    """
    findings = state.get("findings", [])
    if not findings:
        return

    prior_runs = state.setdefault("prior_runs", [])
    prior_runs.append({
        "timestamp":     datetime.now().isoformat(),
        "finding_count": len(findings),
        "ugly_count":    sum(1 for f in findings if f.get("category") == "Ugly"),
        "bad_count":     sum(1 for f in findings if f.get("category") == "Bad"),
        "good_count":    sum(1 for f in findings if f.get("category") == "Good"),
        "findings":      findings,   # full snapshots — needed for diff / What Changed
    })
    state["prior_runs"] = prior_runs[-5:]  # keep last 5


# ── Purge findings by source policy ───────────────────────────────
def purge_policy_findings(state: dict, filename: str) -> int:
    """
    Remove all findings whose policy_file matches filename.
    Returns the number of findings removed.
    """
    before = state.get("findings", [])
    after  = [f for f in before if f.get("policy_file") != filename]
    state["findings"] = after
    return len(before) - len(after)


# ── Finding field defaults ─────────────────────────────────────────
def ensure_finding_defaults(finding: dict) -> dict:
    """
    Ensure optional fields are present on a finding dict.
    Call this when loading findings that may predate a schema addition.
    Currently ensures:
      - discoveryQuestions: list[str] — leading questions for producer discovery meetings
    """
    finding.setdefault("discoveryQuestions", [])
    return finding


# ── Delete a client ────────────────────────────────────────────────
def delete_client(clients_dir: Path, slug: str) -> bool:
    """
    Permanently delete a client folder and all its contents.

    Args:
        clients_dir: Path to the clients/ directory
        slug:        Client folder name (slug)

    Returns:
        True if deleted successfully, False if folder not found.
    """
    client_path = clients_dir / slug
    if not client_path.exists():
        return False
    try:
        shutil.rmtree(client_path)
        return True
    except OSError:
        return False


# ── Get all display names (for duplicate checking) ─────────────────
def get_all_display_names(clients_dir: Path) -> dict:
    """
    Return {slug: display_name} for all existing clients.
    Used to detect duplicate display names before saving.
    """
    result = {}
    if not clients_dir.exists():
        return result
    for folder in clients_dir.iterdir():
        if not folder.is_dir() or folder.name.startswith("."):
            continue
        state = load(folder)
        display = state.get("display_name", "").strip()
        if display:
            result[folder.name] = display
    return result
