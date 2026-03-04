from pathlib import Path
from datetime import datetime
from dataclasses import dataclass
import re
import sys
import tkinter as tk
import tkinter.font as tkfont
from tkinter import messagebox
from tkinter import ttk

from . import dialogs
from . import editor_ops
from . import exporting
from . import lifecycle
from . import settings_store
from . import storage
from . import tokens
from . import ui_tooltips
from . import text_tools
from .paths import AUTOSAVE_INTERVAL_MINUTES, AUTOSAVE_INTERVAL_MS, FILE_PREFIX, TOKENS_CONFIG_PATH

@dataclass
class DocumentState:
    file_path: Path | None
    created_at: datetime | None
    last_saved_text: str
    text_widget: tk.Text


notebook = None
doc_states: dict[str, DocumentState] = {}
native_menubar = None
menu_widgets: list[tk.Menu] = []
custom_menubar = None

document_label = None
status_label = None
stats_label = None
search_entry = None
divider_widget = None
tooltip_objects: list[ui_tooltips.ToolTip] = []
base_status_message = ""
search_status_message = ""
UI_SCALE_FACTORS = (1, 1.5, 2)
ui_scale_index = 0
base_font_sizes = {}
heading_fonts = {}
current_theme_name = "light"
theme_mode = "light"
user_settings = {}

THEMES = {
    "light": {
        "bg": "#f3f3f3",
        "surface_bg": "#f3f3f3",
        "text_bg": "#ffffff",
        "text_fg": "#1f1f1f",
        "fg": "#1f1f1f",
        "muted_fg": "#4b4b4b",
        "button_bg": "#e9e9e9",
        "button_active_bg": "#d9d9d9",
        "entry_bg": "#ffffff",
        "selection_bg": "#cfe3ff",
        "selection_fg": "#1f1f1f",
        "divider": "#c8c8c8",
        "search_match": "#fff2a8",
        "tooltip_bg": "#ffffe0",
        "tooltip_fg": "#1f1f1f",
        "tooltip_border": "#b9b9b9",
    },
    "dark": {
        "bg": "#1b1f24",
        "surface_bg": "#1b1f24",
        "text_bg": "#15191e",
        "text_fg": "#e7edf5",
        "fg": "#e7edf5",
        "muted_fg": "#9aa8b8",
        "button_bg": "#2a313a",
        "button_active_bg": "#36404b",
        "entry_bg": "#15191e",
        "selection_bg": "#3d5f86",
        "selection_fg": "#e7edf5",
        "divider": "#45515f",
        "search_match": "#665200",
        "tooltip_bg": "#2c333c",
        "tooltip_fg": "#e7edf5",
        "tooltip_border": "#4f5a67",
    },
}


def attach_tooltip(widget: tk.Widget, key: str, fallback: str = "") -> None:
    ui_tooltips.attach_tooltip(widget, key, fallback, current_theme, tooltip_objects)


def current_theme() -> dict[str, str]:
    return THEMES[current_theme_name]


def style_widget_tree(widget: tk.Widget) -> None:
    theme = current_theme()

    try:
        if isinstance(widget, (tk.Tk, tk.Toplevel, tk.Frame)):
            widget.config(bg=theme["surface_bg"])
        elif isinstance(widget, tk.Label):
            widget.config(bg=theme["surface_bg"], fg=theme["fg"])
        elif isinstance(widget, tk.Button):
            widget.config(
                bg=theme["button_bg"],
                fg=theme["fg"],
                activebackground=theme["button_active_bg"],
                activeforeground=theme["fg"],
            )
        elif isinstance(widget, tk.Menubutton):
            widget.config(
                bg=theme["button_bg"],
                fg=theme["fg"],
                activebackground=theme["button_active_bg"],
                activeforeground=theme["fg"],
            )
        elif isinstance(widget, tk.Entry):
            widget.config(
                bg=theme["entry_bg"],
                fg=theme["text_fg"],
                insertbackground=theme["text_fg"],
                readonlybackground=theme["entry_bg"],
            )
        elif isinstance(widget, tk.Text):
            widget.config(
                bg=theme["text_bg"],
                fg=theme["text_fg"],
                insertbackground=theme["text_fg"],
                selectbackground=theme["selection_bg"],
                selectforeground=theme["selection_fg"],
            )
        elif isinstance(widget, tk.Listbox):
            widget.config(
                bg=theme["text_bg"],
                fg=theme["text_fg"],
                selectbackground=theme["selection_bg"],
                selectforeground=theme["selection_fg"],
            )
        elif isinstance(widget, tk.Scrollbar):
            widget.config(bg=theme["button_bg"], activebackground=theme["button_active_bg"])
    except tk.TclError:
        pass

    for child in widget.winfo_children():
        style_widget_tree(child)


def apply_theme(window: tk.Widget) -> None:
    style_widget_tree(window)
    try:
        style = ttk.Style()
        style.theme_use("default")
        theme = current_theme()
        style.configure(
            "NoteThis.TNotebook",
            background=theme["surface_bg"],
            borderwidth=0,
        )
        style.configure(
            "NoteThis.TNotebook.Tab",
            background=theme["button_bg"],
            foreground=theme["fg"],
            padding=(8, 4),
        )
        style.map(
            "NoteThis.TNotebook.Tab",
            background=[("selected", theme["text_bg"]), ("active", theme["button_active_bg"])],
            foreground=[("selected", theme["text_fg"]), ("active", theme["fg"])],
        )
        if notebook is not None:
            notebook.configure(style="NoteThis.TNotebook")
    except tk.TclError:
        pass
    theme = current_theme()
    for menu in menu_widgets:
        try:
            menu.config(
                bg=theme["surface_bg"],
                fg=theme["fg"],
                activebackground=theme["button_active_bg"],
                activeforeground=theme["fg"],
                borderwidth=0,
            )
        except tk.TclError:
            pass
    if custom_menubar is not None:
        try:
            custom_menubar.config(bg=theme["surface_bg"])
        except tk.TclError:
            pass
    if divider_widget is not None:
        divider_widget.config(bg=current_theme()["divider"])
    for state in doc_states.values():
        state.text_widget.tag_configure("search_match", background=current_theme()["search_match"])


def current_tab_id() -> str:
    if notebook is None:
        return ""
    return notebook.select()


def current_state() -> DocumentState:
    tab_id = current_tab_id()
    if not tab_id or tab_id not in doc_states:
        raise RuntimeError("Ingen aktiv flik.")
    return doc_states[tab_id]


def current_text_area() -> tk.Text:
    return current_state().text_widget


def update_tab_title(tab_id: str, state: DocumentState) -> None:
    name = state.file_path.name if state.file_path is not None else "Nytt"
    dirty_marker = " *" if editor_ops.is_dirty(state.text_widget, state.last_saved_text) else ""
    notebook.tab(tab_id, text=f"{name}{dirty_marker}")


def bind_editor_events(text_widget: tk.Text) -> None:
    text_widget.bind("<KeyRelease>", lambda _event: refresh_editor_state())
    text_widget.bind("<Return>", handle_return_key)
    text_widget.bind("<Control-z>", undo_last_change)
    text_widget.bind("<Control-Z>", undo_last_change)


def create_tab(title: str = "Nytt", text: str = "") -> str:
    frame = tk.Frame(notebook)
    text_widget = tk.Text(frame, wrap="word", font="TkTextFont", undo=True, maxundo=10, autoseparators=True)
    text_widget.pack(fill="both", expand=True, padx=12, pady=(0, 12))
    text_widget.insert("1.0", text)
    text_widget.tag_configure("search_match", background=current_theme()["search_match"])
    bind_editor_events(text_widget)

    state = DocumentState(
        file_path=None,
        created_at=None,
        last_saved_text="",
        text_widget=text_widget,
    )
    notebook.add(frame, text=title)
    tab_id = str(frame)
    doc_states[tab_id] = state
    notebook.select(tab_id)
    text_widget.focus_set()
    configure_heading_fonts()
    apply_theme(frame)
    return tab_id


def close_current_tab() -> None:
    if not doc_states:
        return

    tab_id = current_tab_id()
    state = doc_states[tab_id]
    if editor_ops.is_dirty(state.text_widget, state.last_saved_text):
        choice = messagebox.askyesnocancel(
            "Spara ändringar",
            "Du har osparade ändringar i fliken. Vill du spara innan du stänger?",
        )
        if choice is None:
            return
        if choice:
            if not save_note(state=state):
                return

    notebook.forget(tab_id)
    doc_states.pop(tab_id, None)

    if not doc_states:
        create_tab()
    refresh_editor_state()

def get_system_theme_name() -> str:
    if sys.platform.startswith("win"):
        try:
            import winreg  # type: ignore
        except ImportError:
            return "light"

        try:
            with winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize",
            ) as key:
                value, _ = winreg.QueryValueEx(key, "AppsUseLightTheme")
                return "light" if int(value) == 1 else "dark"
        except OSError:
            return "light"

    return "light"


def apply_theme_mode(window: tk.Widget) -> None:
    global current_theme_name
    resolved_theme = get_system_theme_name() if theme_mode == "system" else theme_mode
    current_theme_name = resolved_theme
    apply_theme(window)


def open_about_dialog(window: tk.Tk) -> None:
    dialogs.open_about_dialog(window, apply_theme, attach_tooltip)


def set_theme_mode(window: tk.Widget, mode: str) -> None:
    global theme_mode
    if mode not in {"light", "dark", "system"}:
        return
    theme_mode = mode
    user_settings["theme_mode"] = theme_mode
    settings_store.save_user_settings(user_settings)
    apply_theme_mode(window)
    if theme_mode == "system":
        set_status("Tema: Följ system")
    else:
        set_status(f"Tema: {'Mörkt' if theme_mode == 'dark' else 'Ljust'}")


def is_dirty() -> bool:
    state = current_state()
    return editor_ops.is_dirty(state.text_widget, state.last_saved_text)


def update_document_label() -> None:
    state = current_state()
    name = state.file_path.name if state.file_path is not None else "Nytt"
    dirty_marker = " *" if editor_ops.is_dirty(state.text_widget, state.last_saved_text) else ""
    document_label.config(text=f"Dokument: {name}{dirty_marker}")
    update_tab_title(current_tab_id(), state)


def update_document_stats() -> None:
    words, characters = editor_ops.update_document_stats(current_text_area())
    stats_label.config(text=f"Ord: {words}  Tecken: {characters}")


def init_ui_scale() -> None:
    global base_font_sizes

    for font_name in ("TkDefaultFont", "TkTextFont", "TkMenuFont", "TkHeadingFont", "TkCaptionFont", "TkIconFont"):
        try:
            font_obj = tkfont.nametofont(font_name)
            base_font_sizes[font_name] = abs(int(font_obj.cget("size")))
        except tk.TclError:
            continue


def set_ui_scale(index: int) -> None:
    global ui_scale_index

    if index < 0 or index >= len(UI_SCALE_FACTORS):
        return

    ui_scale_index = index
    user_settings["ui_scale_index"] = ui_scale_index
    settings_store.save_user_settings(user_settings)
    scale = UI_SCALE_FACTORS[ui_scale_index]

    for font_name, base_size in base_font_sizes.items():
        try:
            tkfont.nametofont(font_name).configure(size=max(1, int(base_size * scale)))
        except tk.TclError:
            continue

    configure_heading_fonts()
    set_status(f"Zoom: {scale * 100}%")


def cycle_ui_scale() -> None:
    set_ui_scale((ui_scale_index + 1) % len(UI_SCALE_FACTORS))


def configure_heading_fonts() -> None:
    base_text_font = tkfont.nametofont("TkTextFont")
    family = base_text_font.cget("family")
    size = int(base_text_font.cget("size"))

    for level in (1, 2, 3, 4):
        font_key = f"h{level}"
        if font_key not in heading_fonts:
            heading_fonts[font_key] = tkfont.Font(
                family=family,
                size=size,
                weight="bold",
            )
        else:
            heading_fonts[font_key].configure(family=family, size=size, weight="bold")

    for state in doc_states.values():
        state.text_widget.tag_configure("md_h1", font=heading_fonts["h1"])
        state.text_widget.tag_configure("md_h2", font=heading_fonts["h2"])
        state.text_widget.tag_configure("md_h3", font=heading_fonts["h3"])
        state.text_widget.tag_configure("md_h4", font=heading_fonts["h4"])


def apply_markdown_heading_styles() -> None:
    editor_ops.apply_markdown_heading_styles(current_text_area())


def render_status_line() -> None:
    parts = [base_status_message]
    if search_status_message:
        parts.append(search_status_message)
    status_label.config(text=" | ".join(part for part in parts if part))


def update_search_matches() -> int:
    global search_status_message

    query = search_entry.get().strip()
    matches = editor_ops.update_search_matches(current_text_area(), query, tag="search_match")
    if matches == 0:
        search_status_message = "" if not query else "Sök: 0 träffar (tips: kontrollera stavning)"
    elif matches == 1:
        search_status_message = "Sök: 1 träff"
    else:
        search_status_message = f"Sök: {matches} träffar"

    return matches


def refresh_editor_state() -> None:
    if notebook is None or not doc_states:
        if status_label is not None:
            status_label.config(text=base_status_message)
        return
    apply_markdown_heading_styles()
    update_document_label()
    update_document_stats()
    update_search_matches()
    render_status_line()


def handle_tab_changed(_event=None) -> None:
    refresh_editor_state()
    current_text_area().focus_set()


def set_status(message: str) -> None:
    global base_status_message
    base_status_message = message
    refresh_editor_state()


def undo_last_change(_event=None) -> str:
    try:
        widget = _event.widget if _event is not None else current_text_area()
        widget.edit_undo()
        refresh_editor_state()
    except tk.TclError:
        set_status("Inget att ångra")
    return "break"


def save_note(show_empty_warning: bool = True, autosave: bool = False, state: DocumentState | None = None) -> bool:
    if state is None:
        state = current_state()

    text = editor_ops.editor_text(state.text_widget)
    if not text:
        if show_empty_warning:
            messagebox.showwarning("Tom anteckning", "Skriv något innan du sparar.")
        return False

    if state.created_at is None:
        state.created_at = datetime.now()

    if state.file_path is None:
        state.file_path = storage.next_note_file()

    resolved_text = tokens.apply_tokens(
        text=text,
        config_path=TOKENS_CONFIG_PATH,
        file_path=state.file_path,
        created_at=state.created_at,
        updated_at=datetime.now(),
        file_prefix=FILE_PREFIX,
    )

    if resolved_text == state.last_saved_text:
        return False

    storage.write_note_file(state.file_path, resolved_text, create_backup=autosave)
    state.last_saved_text = resolved_text

    if resolved_text != text:
        state.text_widget.delete("1.0", tk.END)
        state.text_widget.insert("1.0", resolved_text)

    status = "Autosparad" if autosave else "Sparad"
    set_status(f"{status}: {state.file_path.name}")
    return True


def save_note_as_copy() -> bool:
    state = current_state()

    text = editor_ops.editor_text(state.text_widget)
    if not text:
        messagebox.showwarning("Tom anteckning", "Skriv något innan du sparar.")
        return False

    new_file_path = storage.next_note_file()
    new_created_at = datetime.now()
    resolved_text = tokens.apply_tokens(
        text=text,
        config_path=TOKENS_CONFIG_PATH,
        file_path=new_file_path,
        created_at=new_created_at,
        updated_at=new_created_at,
        file_prefix=FILE_PREFIX,
    )

    new_file_path.write_text(resolved_text + "\n", encoding="utf-8")
    state.file_path = new_file_path
    state.created_at = new_created_at
    state.last_saved_text = resolved_text

    if resolved_text != text:
        state.text_widget.delete("1.0", tk.END)
        state.text_widget.insert("1.0", resolved_text)

    set_status(f"Sparad som: {state.file_path.name}")
    state.text_widget.focus_set()
    return True


def open_note_file(file_path: Path, state: DocumentState | None = None) -> None:
    if state is None:
        state = current_state()

    text = file_path.read_text(encoding="utf-8")
    state.text_widget.delete("1.0", tk.END)
    state.text_widget.insert("1.0", text.rstrip("\n"))

    state.file_path = file_path
    try:
        state.created_at = datetime.fromtimestamp(file_path.stat().st_ctime)
    except OSError:
        state.created_at = datetime.now()
    state.last_saved_text = editor_ops.editor_text(state.text_widget)
    set_status(f"Öppnad: {file_path.name}")
    state.text_widget.focus_set()


def insert_timestamp() -> None:
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    current_text_area().insert(tk.INSERT, timestamp)
    refresh_editor_state()
    current_text_area().focus_set()


def insert_token_placeholder(token_name: str) -> None:
    placeholder = f"[{token_name}]"
    current_text_area().insert(tk.INSERT, placeholder)
    refresh_editor_state()
    current_text_area().focus_set()


def insert_participant_list() -> None:
    try:
        selected_text = current_text_area().get("sel.first", "sel.last")
    except tk.TclError:
        messagebox.showinfo("Ingen markering", "Markera text som ska göras om till en deltagarlista.")
        return

    names = text_tools.parse_participant_list(selected_text)
    if not names:
        messagebox.showinfo("Inga namn hittades", "Kunde inte hitta några namn i markeringen.")
        return

    result = "\n".join(f"- {name}" for name in names)
    current_text_area().delete("sel.first", "sel.last")
    current_text_area().insert(tk.INSERT, result)
    refresh_editor_state()
    current_text_area().focus_set()


def handle_return_key(_event) -> str | None:
    widget = _event.widget if _event is not None else current_text_area()
    line_start = widget.index("insert linestart")
    line_end = widget.index("insert lineend")
    line_text = widget.get(line_start, line_end)

    checkbox_match = re.match(r"^(\s*)-\s+\[(?: |x|X)\]\s+", line_text)
    if checkbox_match:
        prefix = f"\n{checkbox_match.group(1)}- [ ] "
        widget.insert(tk.INSERT, prefix)
        refresh_editor_state()
        return "break"

    numbered_match = re.match(r"^(\s*)(\d+)\.\s+", line_text)
    if numbered_match:
        next_number = int(numbered_match.group(2)) + 1
        prefix = f"\n{numbered_match.group(1)}{next_number}. "
        widget.insert(tk.INSERT, prefix)
        refresh_editor_state()
        return "break"

    bullet_match = re.match(r"^(\s*)-\s+", line_text)
    if bullet_match:
        prefix = f"\n{bullet_match.group(1)}- "
        widget.insert(tk.INSERT, prefix)
        refresh_editor_state()
        return "break"

    return None


def create_note_from_template(template_path: Path, state: DocumentState | None = None) -> None:
    if state is None:
        state = current_state()

    template_text = template_path.read_text(encoding="utf-8")
    state.text_widget.delete("1.0", tk.END)
    state.text_widget.insert("1.0", template_text.rstrip("\n"))
    state.file_path = None
    state.created_at = None
    state.last_saved_text = ""
    set_status(f"Ny från mall: {template_path.name}")
    state.text_widget.focus_set()


def start_new_note_from_template(window: tk.Tk) -> None:
    if is_dirty():
        save_note(show_empty_warning=False, autosave=True)

    def create_in_new_tab(template_path: Path) -> None:
        tab_id = create_tab()
        state = doc_states[tab_id]
        create_note_from_template(template_path, state)

    dialogs.open_template_dialog(window, create_in_new_tab, apply_theme, attach_tooltip)


def open_notes_dialog(window: tk.Tk) -> None:
    def handle_delete(file_path: Path) -> None:
        for tab_id, state in list(doc_states.items()):
            if state.file_path == file_path:
                notebook.forget(tab_id)
                doc_states.pop(tab_id, None)

        file_path.unlink(missing_ok=True)

        if not doc_states:
            create_tab()
        set_status("Raderade anteckning")

    def handle_open(file_path: Path) -> None:
        tab_id = create_tab()
        state = doc_states[tab_id]
        open_note_file(file_path, state)

    dialogs.open_notes_dialog(window, handle_open, handle_delete, apply_theme, attach_tooltip)


def schedule_autosave(window: tk.Tk) -> None:
    def autosave_all() -> None:
        for state in doc_states.values():
            save_note(show_empty_warning=False, autosave=True, state=state)

    lifecycle.schedule_autosave(window, AUTOSAVE_INTERVAL_MS, autosave_all)


def handle_save_shortcut():
    return lifecycle.handle_save_shortcut(save_note)


def confirm_close(window: tk.Tk) -> None:
    def any_dirty() -> bool:
        return any(editor_ops.is_dirty(state.text_widget, state.last_saved_text) for state in doc_states.values())

    def save_all() -> bool:
        success = True
        for state in doc_states.values():
            if editor_ops.is_dirty(state.text_widget, state.last_saved_text):
                if not save_note(state=state):
                    success = False
        return success

    lifecycle.confirm_close(window, any_dirty, save_all)


def main() -> None:
    window = tk.Tk()
    window.title("NoteThis")
    window.geometry("700x450")

    global notebook, document_label, status_label, stats_label, search_entry, divider_widget
    global native_menubar, menu_widgets, custom_menubar
    global theme_mode, ui_scale_index
    user_settings.update(settings_store.load_user_settings())
    theme_mode = str(user_settings.get("theme_mode", "light")).lower()
    if theme_mode not in {"light", "dark", "system"}:
        theme_mode = "light"
        user_settings["theme_mode"] = theme_mode
        settings_store.save_user_settings(user_settings)
    saved_scale = user_settings.get("ui_scale_index", 0)
    if isinstance(saved_scale, int) and 0 <= saved_scale < len(UI_SCALE_FACTORS):
        ui_scale_index = saved_scale
    else:
        ui_scale_index = 0
    tokens.load_token_config(TOKENS_CONFIG_PATH)
    settings_store.load_tooltips_config()
    init_ui_scale()
    configure_heading_fonts()

    menubar = tk.Menu(window)
    window.config(menu=menubar)
    native_menubar = menubar
    menu_widgets = [menubar]

    file_menu = tk.Menu(menubar, tearoff=0)
    menu_widgets.append(file_menu)
    menubar.add_cascade(label="Arkiv", menu=file_menu)
    file_menu.add_command(label="Ny flik", command=lambda: create_tab())
    file_menu.add_command(label="Stäng flik", command=close_current_tab)
    file_menu.add_command(label="Ny anteckning", command=lambda: start_new_note_from_template(window))
    file_menu.add_command(label="Hantera anteckningar", command=lambda: open_notes_dialog(window))
    file_menu.add_separator()
    file_menu.add_command(label="Spara", command=save_note, accelerator="Ctrl+S")
    file_menu.add_command(label="Spara som..", command=save_note_as_copy)
    export_menu = tk.Menu(file_menu, tearoff=0)
    menu_widgets.append(export_menu)
    export_menu.add_command(
        label="Markdown (.md)",
        command=lambda: exporting.export_note(current_text_area().get("1.0", "end-1c"), set_status, "md"),
    )
    export_menu.add_command(
        label="Text (.txt)",
        command=lambda: exporting.export_note(current_text_area().get("1.0", "end-1c"), set_status, "txt"),
    )
    export_menu.add_command(
        label="PDF (.pdf)",
        command=lambda: exporting.export_note(current_text_area().get("1.0", "end-1c"), set_status, "pdf"),
    )
    file_menu.add_cascade(label="Exportera", menu=export_menu)
    file_menu.add_separator()
    file_menu.add_command(label="Avsluta", command=lambda: confirm_close(window))

    edit_menu = tk.Menu(menubar, tearoff=0)
    menu_widgets.append(edit_menu)
    menubar.add_cascade(label="Redigera", menu=edit_menu)
    edit_menu.add_command(label="Ångra", command=undo_last_change, accelerator="Ctrl+Z")

    insert_menu = tk.Menu(menubar, tearoff=0)
    menu_widgets.append(insert_menu)
    menubar.add_cascade(label="Infoga", menu=insert_menu)
    insert_menu.add_command(label="Tidsstämpel", command=insert_timestamp)
    insert_menu.add_command(label="Deltagarlista", command=insert_participant_list)
    insert_menu.add_separator()

    token_config_local = tokens.load_token_config(TOKENS_CONFIG_PATH)
    globals_config = token_config_local.get("globals", {})
    if isinstance(globals_config, dict) and globals_config:
        globals_menu = tk.Menu(insert_menu, tearoff=0)
        menu_widgets.append(globals_menu)
        for token_name in sorted(globals_config.keys()):
            globals_menu.add_command(
                label=token_name,
                command=lambda name=token_name: insert_token_placeholder(name),
            )
        insert_menu.add_cascade(label="Globala", menu=globals_menu)

    tokens_config_local = token_config_local.get("tokens", {})
    if isinstance(tokens_config_local, dict):
        for group_name, token_group in tokens_config_local.items():
            if not isinstance(token_group, dict) or not token_group:
                continue
            group_menu = tk.Menu(insert_menu, tearoff=0)
            menu_widgets.append(group_menu)
            for token_name in sorted(token_group.keys()):
                group_menu.add_command(
                    label=token_name,
                    command=lambda name=token_name: insert_token_placeholder(name),
                )
            insert_menu.add_cascade(label=group_name.title(), menu=group_menu)

    settings_menu = tk.Menu(menubar, tearoff=0)
    menu_widgets.append(settings_menu)
    menubar.add_cascade(label="Inställningar", menu=settings_menu)

    theme_menu = tk.Menu(settings_menu, tearoff=0)
    menu_widgets.append(theme_menu)
    settings_menu.add_cascade(label="Tema", menu=theme_menu)
    theme_var = tk.StringVar(value=theme_mode if theme_mode in {"light", "dark", "system"} else "light")
    theme_menu.add_radiobutton(
        label="Följ system",
        value="system",
        variable=theme_var,
        command=lambda: set_theme_mode(window, theme_var.get()),
    )
    theme_menu.add_radiobutton(
        label="Ljust",
        value="light",
        variable=theme_var,
        command=lambda: set_theme_mode(window, theme_var.get()),
    )
    theme_menu.add_radiobutton(
        label="Mörkt",
        value="dark",
        variable=theme_var,
        command=lambda: set_theme_mode(window, theme_var.get()),
    )

    zoom_menu = tk.Menu(settings_menu, tearoff=0)
    menu_widgets.append(zoom_menu)
    settings_menu.add_cascade(label="Zoom", menu=zoom_menu)
    zoom_var = tk.IntVar(value=ui_scale_index)
    zoom_menu.add_radiobutton(
        label="100%",
        value=0,
        variable=zoom_var,
        command=lambda: set_ui_scale(zoom_var.get()),
    )
    zoom_menu.add_radiobutton(
        label="150%",
        value=1,
        variable=zoom_var,
        command=lambda: set_ui_scale(zoom_var.get()),
    )
    zoom_menu.add_radiobutton(
        label="200%",
        value=2,
        variable=zoom_var,
        command=lambda: set_ui_scale(zoom_var.get()),
    )

    help_menu = tk.Menu(menubar, tearoff=0)
    menu_widgets.append(help_menu)
    menubar.add_cascade(label="Hjälp", menu=help_menu)
    help_menu.add_command(label="Om NoteThis", command=lambda: open_about_dialog(window))

    custom_menubar = tk.Frame(window)
    custom_menubar.pack(fill="x", padx=8, pady=(8, 0))
    menu_buttons = [
        ("Arkiv", file_menu),
        ("Redigera", edit_menu),
        ("Infoga", insert_menu),
        ("Inställningar", settings_menu),
        ("Hjälp", help_menu),
    ]
    for label, menu in menu_buttons:
        btn = tk.Menubutton(custom_menubar, text=label, menu=menu, relief="flat")
        btn.pack(side="left", padx=(0, 6))
        attach_tooltip(btn, f"menu.{label.lower()}", f"Öppna menyn {label}.")

    controls = tk.Frame(window)
    controls.pack(fill="x", padx=12, pady=(12, 8))

    new_button = tk.Button(controls, text="Ny anteckning", command=lambda: start_new_note_from_template(window), width=12)
    new_button.pack(side="left")
    attach_tooltip(new_button, "main.new_note", "Temporär tooltip: Skapa ny anteckning från mall.")

    open_button = tk.Button(
        controls,
        text="Hantera anteckningar",
        command=lambda: open_notes_dialog(window),
        width=18,
    )
    open_button.pack(side="left", padx=(8, 0))
    attach_tooltip(open_button, "main.manage_notes", "Temporär tooltip: Öppna, bläddra och radera anteckningar.")

    spacer = tk.Frame(controls)
    spacer.pack(side="left", fill="x", expand=True)

    right_actions = tk.Frame(controls)
    right_actions.pack(side="right")

    save_button = tk.Button(right_actions, text="💾", command=save_note, width=3)
    save_button.pack(side="right", padx=(0, 6))
    attach_tooltip(save_button, "main.save", "Temporär tooltip: Spara aktuell anteckning.")

    divider = tk.Frame(controls, width=1, height=28)
    divider.pack(side="right", padx=(0, 10), pady=2)
    divider_widget = divider

    search_entry = tk.Entry(controls, width=22)
    search_entry.pack(side="right", padx=(0, 8))
    attach_tooltip(search_entry, "main.search", "Temporär tooltip: Sök i anteckningen och markera träffar.")

    info_bar = tk.Frame(window)
    info_bar.pack(fill="x", padx=12, pady=(0, 8))

    document_label = tk.Label(info_bar, text="Dokument: Nytt", anchor="w")
    document_label.pack(side="left")

    status_label = tk.Label(info_bar, text=f"Autosparning: var {AUTOSAVE_INTERVAL_MINUTES} min", anchor="w")
    status_label.pack(side="left", padx=(12, 0))

    stats_label = tk.Label(info_bar, text="Ord: 0  Tecken: 0", anchor="e")
    stats_label.pack(side="right")

    notebook = ttk.Notebook(window)
    notebook.pack(fill="both", expand=True, padx=12, pady=(0, 12))
    create_tab()

    configure_heading_fonts()

    save_shortcut = handle_save_shortcut()
    window.bind("<Control-s>", save_shortcut)
    window.bind("<Control-S>", save_shortcut)
    search_entry.bind("<KeyRelease>", lambda _event: refresh_editor_state())
    notebook.bind("<<NotebookTabChanged>>", handle_tab_changed)
    apply_theme_mode(window)
    set_ui_scale(ui_scale_index)
    set_status(f"Autosparning: var {AUTOSAVE_INTERVAL_MINUTES} min")

    window.after(AUTOSAVE_INTERVAL_MS, lambda: schedule_autosave(window))
    window.protocol("WM_DELETE_WINDOW", lambda: confirm_close(window))
    window.mainloop()


if __name__ == "__main__":
    main()
