from __future__ import annotations

import re
import tkinter as tk


def insert_markdown_with_bold(text_widget: tk.Text, line: str, line_tag: str | None = None) -> None:
    cursor = 0
    for match in re.finditer(r"\*\*(.+?)\*\*", line):
        if match.start() > cursor:
            text_widget.insert(tk.END, line[cursor:match.start()], line_tag)
        text_widget.insert(tk.END, match.group(1), ("about_bold", line_tag) if line_tag else "about_bold")
        cursor = match.end()

    if cursor < len(line):
        text_widget.insert(tk.END, line[cursor:], line_tag)


def render_about_markdown(text_widget: tk.Text, markdown_text: str) -> None:
    text_widget.delete("1.0", tk.END)

    for raw_line in markdown_text.splitlines():
        heading_match = re.match(r"^(#{1,4})\s+(.*)$", raw_line)
        if heading_match:
            level = len(heading_match.group(1))
            line_text = heading_match.group(2).strip()
            insert_markdown_with_bold(text_widget, line_text, f"about_h{level}")
            text_widget.insert(tk.END, "\n")
            continue

        insert_markdown_with_bold(text_widget, raw_line, "about_body")
        text_widget.insert(tk.END, "\n")

    text_widget.config(state="disabled")
