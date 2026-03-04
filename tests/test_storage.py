from pathlib import Path

from notethis import storage


def test_extract_note_title_prefers_heading() -> None:
    text = "# Titel\n\nBrödtext"
    assert storage.extract_note_title(text) == "Titel"


def test_extract_note_title_uses_first_line() -> None:
    text = "Första raden\nAndra raden"
    assert storage.extract_note_title(text) == "Första raden"


def test_note_list_label_includes_title_and_filename(tmp_path: Path) -> None:
    file_path = tmp_path / "note_A005.md"
    file_path.write_text("# Min titel\nLite text här", encoding="utf-8")
    label = storage.note_list_label(file_path, max_chars=20)
    assert "Min titel" in label
    assert "note_A005.md" in label


def test_next_note_file_increments(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(storage, "NOTES_DIR", tmp_path)
    monkeypatch.setattr(storage, "FILE_PREFIX", "note_A")
    monkeypatch.setattr(storage, "FILE_SUFFIX", ".md")

    (tmp_path / "note_A001.md").write_text("a", encoding="utf-8")
    (tmp_path / "note_A002.md").write_text("b", encoding="utf-8")

    next_path = storage.next_note_file()
    assert next_path.name == "note_A003.md"


def test_template_list_label_strips_prefix() -> None:
    file_path = Path("01_Mall.md")
    assert storage.template_list_label(file_path) == "Mall"
