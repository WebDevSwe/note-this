from __future__ import annotations

from datetime import datetime
from pathlib import Path
import json
import re
import socket
from typing import Dict, Tuple

_token_config_cache: Dict[Path, dict] = {}


def load_token_config(config_path: Path) -> dict:
    cached = _token_config_cache.get(config_path)
    if cached is not None:
        return cached

    try:
        config = json.loads(config_path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        config = {}

    _token_config_cache[config_path] = config
    return config


def format_with_fallback(value: datetime, fmt: str) -> str:
    if "%-d" in fmt:
        marker = "__DAY_NO_ZERO__"
        return value.strftime(fmt.replace("%-d", marker)).replace(marker, str(value.day))
    return value.strftime(fmt)


def extract_note_id(file_path: Path | None, file_prefix: str) -> str:
    if file_path is None:
        return ""
    stem = file_path.stem
    if stem.startswith(file_prefix):
        return stem.replace(file_prefix, "", 1)
    return stem


def build_token_values(
    config_path: Path,
    file_path: Path | None,
    created_at: datetime | None,
    updated_at: datetime,
    file_prefix: str,
) -> dict[str, str]:
    config = load_token_config(config_path)
    values: dict[str, str] = {}
    now = updated_at
    note_created_at = created_at or updated_at

    globals_config = config.get("globals", {})
    for key, value in globals_config.items():
        values[str(key)] = str(value)

    tokens_config = config.get("tokens", {})
    for token_group in tokens_config.values():
        if not isinstance(token_group, dict):
            continue
        for token_name, token_spec in token_group.items():
            if not isinstance(token_spec, dict):
                continue

            source = token_spec.get("source", "")
            fmt = token_spec.get("format", "%Y-%m-%d")

            if source in {"date", "time", "datetime"}:
                values[token_name] = format_with_fallback(now, fmt)
            elif source == "hostname":
                values[token_name] = socket.gethostname()
            elif source == "note_id":
                values[token_name] = extract_note_id(file_path, file_prefix)
            elif source == "created_at":
                values[token_name] = format_with_fallback(note_created_at, fmt)
            elif source == "updated_at":
                values[token_name] = format_with_fallback(updated_at, fmt)

    return values


def apply_tokens(
    text: str,
    config_path: Path,
    file_path: Path | None,
    created_at: datetime | None,
    updated_at: datetime,
    file_prefix: str,
) -> str:
    token_values = build_token_values(
        config_path=config_path,
        file_path=file_path,
        created_at=created_at,
        updated_at=updated_at,
        file_prefix=file_prefix,
    )

    def replace_token(match: re.Match) -> str:
        token_name = match.group(1)
        return token_values.get(token_name, match.group(0))

    return re.sub(r"\[([A-Z0-9_]+)\]", replace_token, text)
