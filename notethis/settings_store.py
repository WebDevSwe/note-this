from __future__ import annotations

from pathlib import Path
import json

from .paths import TOOLTIPS_CONFIG_PATH, USER_SETTINGS_PATH

_tooltips_cache: dict | None = None
_user_settings_cache: dict | None = None


def _load_json(path: Path, default: dict) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return default


def load_tooltips_config() -> dict:
    global _tooltips_cache
    if _tooltips_cache is None:
        _tooltips_cache = _load_json(TOOLTIPS_CONFIG_PATH, {"enabled": False, "buttons": {}})
    return _tooltips_cache


def load_user_settings() -> dict:
    global _user_settings_cache
    if _user_settings_cache is None:
        _user_settings_cache = _load_json(USER_SETTINGS_PATH, {})
    return _user_settings_cache


def save_user_settings(settings: dict) -> None:
    global _user_settings_cache
    USER_SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
    USER_SETTINGS_PATH.write_text(json.dumps(settings, indent=2), encoding="utf-8")
    _user_settings_cache = settings
