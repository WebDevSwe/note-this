from __future__ import annotations

from pathlib import Path
from typing import Callable
from tkinter import messagebox, filedialog


def export_note(text: str, set_status: Callable[[str], None], preferred_format: str | None = None) -> None:
    if not text.strip():
        messagebox.showinfo("Ingen text", "Det finns ingen text att exportera.")
        return

    path, file_format = _ask_export_path(preferred_format)
    if not path or not file_format:
        return

    if file_format in {"md", "txt"}:
        Path(path).write_text(text + "\n", encoding="utf-8")
        set_status(f"Exporterad: {Path(path).name}")
        return

    if file_format == "pdf":
        export_to_pdf(text, Path(path), set_status=set_status)


def _ask_export_path(preferred_format: str | None) -> tuple[str, str]:
    order = ["md", "txt", "pdf"]
    if preferred_format in order:
        order.remove(preferred_format)
        order.insert(0, preferred_format)

    labels = {"md": "Markdown", "txt": "Text", "pdf": "PDF"}
    filetypes = [(labels[ext], f"*.{ext}") for ext in order]
    default_ext = f".{order[0]}"
    path = filedialog.asksaveasfilename(
        title="Exportera anteckning",
        defaultextension=default_ext,
        filetypes=filetypes,
    )
    if not path:
        return "", ""

    ext = Path(path).suffix.lower().lstrip(".")
    if ext not in {"md", "txt", "pdf"}:
        messagebox.showerror("Okänt format", "Kan inte exportera till valt format.")
        return "", ""
    return path, ext


def export_to_pdf(text: str, path: Path, set_status: Callable[[str], None]) -> None:
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.pdfgen import canvas
    except Exception:
        messagebox.showwarning(
            "PDF-stöd saknas",
            "PDF-export kräver paketet reportlab. Installera med: pip install reportlab",
        )
        return

    width, height = A4
    margin = 48
    line_height = 14
    y = height - margin
    c = canvas.Canvas(str(path), pagesize=A4)

    for raw_line in text.splitlines() or [""]:
        line = raw_line.rstrip()
        while line:
            chunk = line[:120]
            line = line[120:]
            if y <= margin:
                c.showPage()
                y = height - margin
            c.drawString(margin, y, chunk)
            y -= line_height

        if not raw_line:
            if y <= margin:
                c.showPage()
                y = height - margin
            y -= line_height

    c.save()
    set_status(f"Exporterad: {path.name}")
