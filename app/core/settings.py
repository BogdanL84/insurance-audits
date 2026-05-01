"""
settings.py — Load and save broker/branding settings from settings.json.

Settings file lives at: insurance-audits/settings.json
Falls back to hardcoded defaults if the file doesn't exist.
"""

import json
from pathlib import Path

_SETTINGS_PATH = Path(__file__).parent.parent.parent / "settings.json"

_DEFAULTS = {
    "broker_name":    "",
    "broker_title":   "",
    "broker_company": "",
    "broker_email":   "",
    "broker_phone":   "",
    "logo_filename":  None,
}


def load() -> dict:
    """Load settings from disk, merging with defaults for any missing keys."""
    if not _SETTINGS_PATH.exists():
        return dict(_DEFAULTS)
    try:
        data = json.loads(_SETTINGS_PATH.read_text(encoding="utf-8"))
        merged = dict(_DEFAULTS)
        merged.update({k: v for k, v in data.items() if k in _DEFAULTS})
        return merged
    except (json.JSONDecodeError, OSError):
        return dict(_DEFAULTS)


def save(settings: dict) -> None:
    """Persist settings to disk."""
    try:
        _SETTINGS_PATH.write_text(
            json.dumps(settings, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
    except OSError as e:
        raise RuntimeError(f"Could not save settings: {e}") from e


def get(key: str, default=None):
    """Get a single setting value (reads from disk each call — use load() for bulk access)."""
    s = load()
    return s.get(key, _DEFAULTS.get(key, default))
