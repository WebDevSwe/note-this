from datetime import datetime
from pathlib import Path
import json

from notethis import tokens


def write_tokens_config(path: Path) -> None:
    config = {
        "globals": {"APP": "NoteThis"},
        "tokens": {
            "date": {
                "TODAY": {"source": "date", "format": "%Y-%m-%d"},
            },
            "system": {
                "NOTE_ID": {"source": "note_id"},
                "CREATED": {"source": "created_at", "format": "%Y-%m-%d %H:%M"},
            },
        },
    }
    path.write_text(json.dumps(config), encoding="utf-8")


def test_apply_tokens_replaces_known_tokens(tmp_path: Path) -> None:
    config_path = tmp_path / "tokens.json"
    write_tokens_config(config_path)

    file_path = tmp_path / "note_A001.md"
    text = "[APP] [TODAY] [NOTE_ID] [CREATED]"
    created_at = datetime(2026, 2, 18, 9, 30)
    updated_at = datetime(2026, 2, 19, 13, 0)

    result = tokens.apply_tokens(
        text=text,
        config_path=config_path,
        file_path=file_path,
        created_at=created_at,
        updated_at=updated_at,
        file_prefix="note_A",
    )

    assert result == "NoteThis 2026-02-19 001 2026-02-18 09:30"


def test_apply_tokens_keeps_unknown_tokens(tmp_path: Path) -> None:
    config_path = tmp_path / "tokens.json"
    write_tokens_config(config_path)

    result = tokens.apply_tokens(
        text="[UNKNOWN]",
        config_path=config_path,
        file_path=None,
        created_at=None,
        updated_at=datetime(2026, 2, 19, 13, 0),
        file_prefix="note_A",
    )

    assert result == "[UNKNOWN]"


def test_format_with_fallback_supports_day_without_zero() -> None:
    value = datetime(2026, 2, 3, 8, 5)
    assert tokens.format_with_fallback(value, "%-d %b %Y") == "3 Feb 2026"
