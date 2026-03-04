from __future__ import annotations

import re
import tkinter as tk


def editor_text(text_widget: tk.Text) -> str:
    return text_widget.get("1.0", tk.END).rstrip()


def is_dirty(text_widget: tk.Text, last_saved_text: str) -> bool:
    return editor_text(text_widget) != last_saved_text


def update_document_stats(text_widget: tk.Text) -> tuple[int, int]:
    raw_text = text_widget.get("1.0", "end-1c")
    words = len(raw_text.split())
    characters = len(raw_text)
    return words, characters


def apply_markdown_heading_styles(text_widget: tk.Text) -> None:
    for tag_name in ("md_h1", "md_h2", "md_h3", "md_h4"):
        text_widget.tag_remove(tag_name, "1.0", tk.END)

    end_line = int(text_widget.index("end-1c").split(".")[0])
    for line_number in range(1, end_line + 1):
        line_start = f"{line_number}.0"
        line_end = f"{line_number}.end"
        line_text = text_widget.get(line_start, line_end)

        match = re.match(r"^(#{1,4})\s+", line_text)
        if not match:
            continue

        level = len(match.group(1))
        text_widget.tag_add(f"md_h{level}", line_start, line_end)


def update_search_matches(text_widget: tk.Text, query: str, tag: str = "search_match") -> int:
    text_widget.tag_remove(tag, "1.0", tk.END)
    query = query.strip()
    if not query:
        return 0

    start_index = "1.0"
    matches = 0
    while True:
        match_index = text_widget.search(query, start_index, stopindex=tk.END, nocase=True)
        if not match_index:
            break

        match_end = f"{match_index}+{len(query)}c"
        text_widget.tag_add(tag, match_index, match_end)
        start_index = match_end
        matches += 1

    return matches
