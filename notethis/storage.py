from __future__ import annotations

from pathlib import Path
import re

from .paths import FILE_PREFIX, FILE_SUFFIX, NOTES_DIR, TEMPLATES_DIR


def list_note_files() -> list[Path]:
    NOTES_DIR.mkdir(parents=True, exist_ok=True)
    return sorted(NOTES_DIR.glob(f"{FILE_PREFIX}*{FILE_SUFFIX}"))


def list_template_files() -> list[Path]:
    TEMPLATES_DIR.mkdir(parents=True, exist_ok=True)
    return sorted(TEMPLATES_DIR.glob(f"*{FILE_SUFFIX}"))


def next_note_file() -> Path:
    max_number = 0
    for file_path in list_note_files():
        name = file_path.stem
        number_part = name.replace(FILE_PREFIX, "", 1)
        if number_part.isdigit():
            max_number = max(max_number, int(number_part))

    next_number = max_number + 1
    return NOTES_DIR / f"{FILE_PREFIX}{next_number:03d}{FILE_SUFFIX}"


def write_note_file(file_path: Path, text: str, create_backup: bool = False) -> None:
    if create_backup and file_path.exists():
        backup_file_path = file_path.with_name(f"{file_path.name}.bak")
        backup_file_path.unlink(missing_ok=True)
        file_path.replace(backup_file_path)

    file_path.write_text(text + "\n", encoding="utf-8")


def extract_note_title(text: str) -> str:
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        heading_match = re.match(r"^#{1,6}\s+(.*)$", line)
        if heading_match:
            return heading_match.group(1).strip()
        return line
    return ""


def note_list_label(file_path: Path, max_chars: int = 60) -> str:
    text = file_path.read_text(encoding="utf-8").strip()
    title = extract_note_title(text) or file_path.stem
    compact_text = " ".join(text.split())

    if len(compact_text) > max_chars:
        preview = compact_text[:max_chars].rstrip() + "..."
    else:
        preview = compact_text

    if not preview:
        preview = "(tom anteckning)"

    return f"{title} ({file_path.name}) - {preview}"
