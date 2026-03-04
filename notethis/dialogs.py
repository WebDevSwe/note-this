from __future__ import annotations

from datetime import datetime
from pathlib import Path
import tkinter as tk
import tkinter.font as tkfont
from tkinter import messagebox

from . import markdown
from . import storage
from .paths import ABOUT_MARKDOWN_PATH


def open_about_dialog(
    window: tk.Tk,
    apply_theme,
    attach_tooltip,
) -> None:
    dialog = tk.Toplevel(window)
    dialog.title("Om NoteThis")
    dialog.geometry("700x520")
    dialog.transient(window)

    content_frame = tk.Frame(dialog)
    content_frame.pack(fill="both", expand=True, padx=12, pady=12)

    scrollbar = tk.Scrollbar(content_frame)
    scrollbar.pack(side="right", fill="y")

    text_widget = tk.Text(content_frame, wrap="word", yscrollcommand=scrollbar.set, font="TkTextFont")
    text_widget.pack(side="left", fill="both", expand=True)
    scrollbar.config(command=text_widget.yview)

    base_font = tkfont.nametofont("TkTextFont")
    family = base_font.cget("family")
    size = int(base_font.cget("size"))

    heading_size_map = {1: max(size + 6, 14), 2: max(size + 4, 13), 3: max(size + 2, 12), 4: max(size + 1, 11)}
    for level in (1, 2, 3, 4):
        tag_name = f"about_h{level}"
        heading_font = tkfont.Font(family=family, size=heading_size_map[level], weight="bold")
        text_widget.tag_configure(tag_name, font=heading_font, spacing1=8, spacing3=4)

    text_widget.tag_configure("about_body", spacing1=2, spacing3=4)
    text_widget.tag_configure("about_bold", font=tkfont.Font(family=family, size=size, weight="bold"))

    try:
        markdown_text = ABOUT_MARKDOWN_PATH.read_text(encoding="utf-8")
    except FileNotFoundError:
        markdown_text = "# NoteThis\n\nKunde inte läsa infofilen i settings."

    markdown.render_about_markdown(text_widget, markdown_text)

    close_button = tk.Button(dialog, text="Stäng", command=dialog.destroy, width=10)
    close_button.pack(pady=(0, 12))
    attach_tooltip(close_button, "about.close", "Stäng informationsfönstret.")
    apply_theme(dialog)


def open_template_dialog(
    window: tk.Tk,
    create_note_from_template,
    apply_theme,
    attach_tooltip,
) -> None:
    template_files = storage.list_template_files()
    if not template_files:
        messagebox.showinfo("Inga mallar", "Hittade inga mallar i mappen templates.")
        return

    dialog = tk.Toplevel(window)
    dialog.title("Välj mall")
    dialog.geometry("420x340")
    dialog.transient(window)
    dialog.grab_set()

    list_frame = tk.Frame(dialog)
    list_frame.pack(fill="both", expand=True, padx=12, pady=(12, 8))

    scrollbar = tk.Scrollbar(list_frame)
    scrollbar.pack(side="right", fill="y")

    listbox = tk.Listbox(list_frame, yscrollcommand=scrollbar.set)
    listbox.pack(side="left", fill="both", expand=True)
    scrollbar.config(command=listbox.yview)

    for file_path in template_files:
        listbox.insert(tk.END, storage.template_list_label(file_path))

    buttons = tk.Frame(dialog)
    buttons.pack(fill="x", padx=12, pady=(0, 12))

    def selected_template() -> Path | None:
        selection = listbox.curselection()
        if not selection:
            messagebox.showinfo("Ingen vald", "Välj en mall i listan.", parent=dialog)
            return None

        idx = selection[0]
        if idx >= len(template_files):
            return None
        return template_files[idx]

    def create_selected() -> None:
        file_path = selected_template()
        if file_path is None:
            return
        create_note_from_template(file_path)
        dialog.destroy()

    create_button = tk.Button(buttons, text="Skapa", command=create_selected, width=10)
    create_button.pack(side="left")
    attach_tooltip(create_button, "template.create", "Temporär tooltip: Skapa anteckning från vald mall.")

    close_button = tk.Button(buttons, text="Stäng", command=dialog.destroy, width=10)
    close_button.pack(side="right")
    attach_tooltip(close_button, "template.close", "Temporär tooltip: Stäng mallfönstret utan att skapa.")

    listbox.bind("<Double-Button-1>", lambda _event: create_selected())
    apply_theme(dialog)


def open_notes_dialog(
    window: tk.Tk,
    on_open,
    on_delete,
    apply_theme,
    attach_tooltip,
) -> None:
    dialog = tk.Toplevel(window)
    dialog.title("Öppna / Radera anteckning")
    dialog.geometry("420x340")
    dialog.transient(window)
    dialog.grab_set()

    control_bar = tk.Frame(dialog)
    control_bar.pack(fill="x", padx=12, pady=(12, 4))

    filter_var = tk.StringVar()
    filter_entry = tk.Entry(control_bar, textvariable=filter_var)
    filter_entry.pack(side="left", fill="x", expand=True)
    attach_tooltip(filter_entry, "notes.filter", "Filtrera anteckningar efter titel eller text.")

    sort_var = tk.StringVar(value="Senast ändrad")
    sort_menu = tk.OptionMenu(control_bar, sort_var, "Senast ändrad", "Skapad", "Titel", "Filnamn")
    sort_menu.pack(side="right", padx=(8, 0))

    list_frame = tk.Frame(dialog)
    list_frame.pack(fill="both", expand=True, padx=12, pady=(0, 8))

    scrollbar = tk.Scrollbar(list_frame)
    scrollbar.pack(side="right", fill="y")

    listbox = tk.Listbox(list_frame, yscrollcommand=scrollbar.set)
    listbox.pack(side="left", fill="both", expand=True)
    scrollbar.config(command=listbox.yview)

    buttons = tk.Frame(dialog)
    buttons.pack(fill="x", padx=12, pady=(0, 12))

    note_files: list[Path] = []

    def build_note_meta(file_path: Path) -> dict[str, object]:
        text = file_path.read_text(encoding="utf-8").strip()
        title = storage.extract_note_title(text) or file_path.stem
        compact_text = " ".join(text.split())
        preview = compact_text[:60].rstrip() + "..." if len(compact_text) > 60 else compact_text
        if not preview:
            preview = "(tom anteckning)"
        label = f"{title} ({file_path.name}) - {preview}"
        try:
            stat = file_path.stat()
            created = stat.st_ctime
            updated = stat.st_mtime
        except OSError:
            created = 0
            updated = 0
        return {
            "path": file_path,
            "title": title.lower(),
            "name": file_path.name.lower(),
            "preview": preview.lower(),
            "created": created,
            "updated": updated,
            "label": label,
        }

    def refresh_list() -> None:
        nonlocal note_files
        note_files = storage.list_note_files()
        listbox.delete(0, tk.END)
        query = filter_var.get().strip().lower()
        metas = [build_note_meta(file_path) for file_path in note_files]
        if query:
            metas = [
                meta
                for meta in metas
                if query in meta["title"] or query in meta["name"] or query in meta["preview"]
            ]

        sort_key = sort_var.get()
        if sort_key == "Skapad":
            metas.sort(key=lambda meta: meta["created"], reverse=True)
        elif sort_key == "Titel":
            metas.sort(key=lambda meta: meta["title"])
        elif sort_key == "Filnamn":
            metas.sort(key=lambda meta: meta["name"])
        else:
            metas.sort(key=lambda meta: meta["updated"], reverse=True)

        note_files = [meta["path"] for meta in metas]
        for meta in metas:
            listbox.insert(tk.END, meta["label"])

    def selected_file() -> Path | None:
        selection = listbox.curselection()
        if not selection:
            messagebox.showinfo("Ingen vald", "Välj en anteckning i listan.", parent=dialog)
            return None

        idx = selection[0]
        if idx >= len(note_files):
            return None
        return note_files[idx]

    def open_selected() -> None:
        file_path = selected_file()
        if file_path is None:
            return
        on_open(file_path)
        dialog.destroy()

    def delete_selected() -> None:
        file_path = selected_file()
        if file_path is None:
            return

        confirmed = messagebox.askyesno(
            "Radera anteckning",
            f"Vill du radera {file_path.name}?",
            parent=dialog,
        )
        if not confirmed:
            return

        on_delete(file_path)
        refresh_list()

    open_button = tk.Button(buttons, text="Öppna", command=open_selected, width=10)
    open_button.pack(side="left")
    attach_tooltip(open_button, "notes.open", "Temporär tooltip: Öppna vald anteckning.")

    delete_button = tk.Button(buttons, text="Radera", command=delete_selected, width=10)
    delete_button.pack(side="left", padx=(8, 0))
    attach_tooltip(delete_button, "notes.delete", "Temporär tooltip: Radera vald anteckning permanent.")

    close_button = tk.Button(buttons, text="Stäng", command=dialog.destroy, width=10)
    close_button.pack(side="right")
    attach_tooltip(close_button, "notes.close", "Temporär tooltip: Stäng anteckningslistan.")

    listbox.bind("<Double-Button-1>", lambda _event: open_selected())

    refresh_list()
    filter_entry.bind("<KeyRelease>", lambda _event: refresh_list())
    sort_var.trace_add("write", lambda *_args: refresh_list())
    apply_theme(dialog)
