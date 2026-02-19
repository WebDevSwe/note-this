from pathlib import Path
from datetime import datetime
import re
import sys
import tkinter as tk
import tkinter.font as tkfont
from tkinter import messagebox

from . import exporting
from . import settings_store
from . import storage
from . import tokens
from .paths import (
    ABOUT_MARKDOWN_PATH,
    AUTOSAVE_INTERVAL_MINUTES,
    AUTOSAVE_INTERVAL_MS,
    FILE_PREFIX,
    TOKENS_CONFIG_PATH,
)

current_note_file = None
current_note_created_at = None
last_saved_text = ""
text_area = None
document_label = None
status_label = None
stats_label = None
search_entry = None
divider_widget = None
tooltip_objects = []
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


def tooltip_text(key: str, fallback: str) -> str:
    config = settings_store.load_tooltips_config()
    button_texts = config.get("buttons", {})
    value = button_texts.get(key, fallback)
    return str(value).strip()


class ToolTip:
    def __init__(self, widget: tk.Widget, text: str) -> None:
        self.widget = widget
        self.text = text
        self.tip_window = None
        self.after_id = None

        self.widget.bind("<Enter>", self.on_enter, add="+")
        self.widget.bind("<Leave>", self.on_leave, add="+")
        self.widget.bind("<ButtonPress>", self.on_leave, add="+")

    def on_enter(self, _event=None) -> None:
        if self.after_id is None:
            self.after_id = self.widget.after(500, self.show_tip)

    def on_leave(self, _event=None) -> None:
        if self.after_id is not None:
            self.widget.after_cancel(self.after_id)
            self.after_id = None
        self.hide_tip()

    def show_tip(self) -> None:
        self.after_id = None
        if self.tip_window is not None or not self.text:
            return

        x = self.widget.winfo_rootx() + 16
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 6

        self.tip_window = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f"+{x}+{y}")

        label = tk.Label(
            tw,
            text=self.text,
            justify="left",
            relief="solid",
            borderwidth=1,
            background=current_theme()["tooltip_bg"],
            fg=current_theme()["tooltip_fg"],
            highlightbackground=current_theme()["tooltip_border"],
            padx=6,
            pady=3,
        )
        label.pack()

    def hide_tip(self) -> None:
        if self.tip_window is not None:
            self.tip_window.destroy()
            self.tip_window = None


def attach_tooltip(widget: tk.Widget, key: str, fallback: str = "") -> None:
    config = settings_store.load_tooltips_config()
    if not config.get("enabled", True):
        return

    text = tooltip_text(key, fallback)
    if not text:
        return

    tooltip_objects.append(ToolTip(widget, text))


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
    if divider_widget is not None:
        divider_widget.config(bg=current_theme()["divider"])
    if text_area is not None:
        text_area.tag_configure("search_match", background=current_theme()["search_match"])

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


def open_about_dialog(window: tk.Tk) -> None:
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

    render_about_markdown(text_widget, markdown_text)

    close_button = tk.Button(dialog, text="Stäng", command=dialog.destroy, width=10)
    close_button.pack(pady=(0, 12))
    attach_tooltip(close_button, "about.close", "Stäng informationsfönstret.")
    apply_theme(dialog)


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


def editor_text() -> str:
    return text_area.get("1.0", tk.END).rstrip()


def is_dirty() -> bool:
    return editor_text() != last_saved_text


def update_document_label() -> None:
    name = current_note_file.name if current_note_file is not None else "Nytt"
    dirty_marker = " *" if is_dirty() else ""
    document_label.config(text=f"Dokument: {name}{dirty_marker}")


def update_document_stats() -> None:
    raw_text = text_area.get("1.0", "end-1c")
    words = len(raw_text.split())
    characters = len(raw_text)
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

    if text_area is not None:
        text_area.tag_configure("md_h1", font=heading_fonts["h1"])
        text_area.tag_configure("md_h2", font=heading_fonts["h2"])
        text_area.tag_configure("md_h3", font=heading_fonts["h3"])
        text_area.tag_configure("md_h4", font=heading_fonts["h4"])


def apply_markdown_heading_styles() -> None:
    if text_area is None:
        return

    for tag_name in ("md_h1", "md_h2", "md_h3", "md_h4"):
        text_area.tag_remove(tag_name, "1.0", tk.END)

    end_line = int(text_area.index("end-1c").split(".")[0])
    for line_number in range(1, end_line + 1):
        line_start = f"{line_number}.0"
        line_end = f"{line_number}.end"
        line_text = text_area.get(line_start, line_end)

        match = re.match(r"^(#{1,4})\s+", line_text)
        if not match:
            continue

        level = len(match.group(1))
        text_area.tag_add(f"md_h{level}", line_start, line_end)


def render_status_line() -> None:
    parts = [base_status_message]
    if search_status_message:
        parts.append(search_status_message)
    status_label.config(text=" | ".join(part for part in parts if part))


def update_search_matches() -> int:
    global search_status_message

    text_area.tag_remove("search_match", "1.0", tk.END)
    query = search_entry.get().strip()
    if not query:
        search_status_message = ""
        return 0

    start_index = "1.0"
    matches = 0
    while True:
        match_index = text_area.search(query, start_index, stopindex=tk.END, nocase=True)
        if not match_index:
            break

        match_end = f"{match_index}+{len(query)}c"
        text_area.tag_add("search_match", match_index, match_end)
        start_index = match_end
        matches += 1

    if matches == 0:
        search_status_message = "Sök: 0 träffar (tips: kontrollera stavning)"
    elif matches == 1:
        search_status_message = "Sök: 1 träff"
    else:
        search_status_message = f"Sök: {matches} träffar"

    return matches


def refresh_editor_state() -> None:
    apply_markdown_heading_styles()
    update_document_label()
    update_document_stats()
    update_search_matches()
    render_status_line()


def set_status(message: str) -> None:
    global base_status_message
    base_status_message = message
    refresh_editor_state()


def undo_last_change(_event=None) -> str:
    try:
        text_area.edit_undo()
        refresh_editor_state()
    except tk.TclError:
        set_status("Inget att ångra")
    return "break"


def save_note(show_empty_warning: bool = True, autosave: bool = False) -> bool:
    global current_note_file, current_note_created_at, last_saved_text

    text = editor_text()
    if not text:
        if show_empty_warning:
            messagebox.showwarning("Tom anteckning", "Skriv något innan du sparar.")
        return False

    if current_note_created_at is None:
        current_note_created_at = datetime.now()

    if current_note_file is None:
        current_note_file = storage.next_note_file()

    resolved_text = tokens.apply_tokens(
        text=text,
        config_path=TOKENS_CONFIG_PATH,
        file_path=current_note_file,
        created_at=current_note_created_at,
        updated_at=datetime.now(),
        file_prefix=FILE_PREFIX,
    )

    if resolved_text == last_saved_text:
        return False

    storage.write_note_file(current_note_file, resolved_text, create_backup=autosave)
    last_saved_text = resolved_text

    if resolved_text != text:
        text_area.delete("1.0", tk.END)
        text_area.insert("1.0", resolved_text)

    status = "Autosparad" if autosave else "Sparad"
    set_status(f"{status}: {current_note_file.name}")
    return True


def save_note_as_copy() -> bool:
    global current_note_file, current_note_created_at, last_saved_text

    text = editor_text()
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
    current_note_file = new_file_path
    current_note_created_at = new_created_at
    last_saved_text = resolved_text

    if resolved_text != text:
        text_area.delete("1.0", tk.END)
        text_area.insert("1.0", resolved_text)

    set_status(f"Sparad som: {current_note_file.name}")
    text_area.focus_set()
    return True


def open_note_file(file_path: Path) -> None:
    global current_note_file, current_note_created_at, last_saved_text

    text = file_path.read_text(encoding="utf-8")
    text_area.delete("1.0", tk.END)
    text_area.insert("1.0", text.rstrip("\n"))

    current_note_file = file_path
    try:
        current_note_created_at = datetime.fromtimestamp(file_path.stat().st_ctime)
    except OSError:
        current_note_created_at = datetime.now()
    last_saved_text = editor_text()
    set_status(f"Öppnad: {file_path.name}")
    text_area.focus_set()


def insert_timestamp() -> None:
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    text_area.insert(tk.INSERT, timestamp)
    refresh_editor_state()
    text_area.focus_set()


def insert_token_placeholder(token_name: str) -> None:
    placeholder = f"[{token_name}]"
    text_area.insert(tk.INSERT, placeholder)
    refresh_editor_state()
    text_area.focus_set()


def handle_return_key(_event) -> str | None:
    line_start = text_area.index("insert linestart")
    line_end = text_area.index("insert lineend")
    line_text = text_area.get(line_start, line_end)

    checkbox_match = re.match(r"^(\s*)-\s+\[(?: |x|X)\]\s+", line_text)
    if checkbox_match:
        prefix = f"\n{checkbox_match.group(1)}- [ ] "
        text_area.insert(tk.INSERT, prefix)
        refresh_editor_state()
        return "break"

    numbered_match = re.match(r"^(\s*)(\d+)\.\s+", line_text)
    if numbered_match:
        next_number = int(numbered_match.group(2)) + 1
        prefix = f"\n{numbered_match.group(1)}{next_number}. "
        text_area.insert(tk.INSERT, prefix)
        refresh_editor_state()
        return "break"

    bullet_match = re.match(r"^(\s*)-\s+", line_text)
    if bullet_match:
        prefix = f"\n{bullet_match.group(1)}- "
        text_area.insert(tk.INSERT, prefix)
        refresh_editor_state()
        return "break"

    return None


def template_list_label(file_path: Path) -> str:
    stem = file_path.stem
    if "_" in stem:
        return stem.split("_", 1)[1]
    return stem


def create_note_from_template(template_path: Path) -> None:
    global current_note_file, current_note_created_at, last_saved_text

    template_text = template_path.read_text(encoding="utf-8")
    text_area.delete("1.0", tk.END)
    text_area.insert("1.0", template_text.rstrip("\n"))
    current_note_file = None
    current_note_created_at = None
    last_saved_text = ""
    set_status(f"Ny från mall: {template_path.name}")
    text_area.focus_set()


def open_template_dialog(window: tk.Tk) -> None:
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
        listbox.insert(tk.END, template_list_label(file_path))

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


def start_new_note_from_template(window: tk.Tk) -> None:
    if is_dirty():
        save_note(show_empty_warning=False, autosave=True)
    open_template_dialog(window)


def open_notes_dialog(window: tk.Tk) -> None:
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
            created = file_path.stat().st_ctime
            updated = file_path.stat().st_mtime
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
        open_note_file(file_path)
        dialog.destroy()

    def delete_selected() -> None:
        global current_note_file, current_note_created_at, last_saved_text

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

        file_path.unlink(missing_ok=True)

        if current_note_file == file_path:
            current_note_file = None
            current_note_created_at = None
            last_saved_text = ""
            text_area.delete("1.0", tk.END)
            set_status("Raderade öppen anteckning")

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


def schedule_autosave(window: tk.Tk) -> None:
    save_note(show_empty_warning=False, autosave=True)
    window.after(AUTOSAVE_INTERVAL_MS, lambda: schedule_autosave(window))


def handle_save_shortcut(_event=None) -> str:
    save_note()
    return "break"


def confirm_close(window: tk.Tk) -> None:
    if not is_dirty():
        window.destroy()
        return

    choice = messagebox.askyesnocancel(
        "Spara ändringar",
        "Du har osparade ändringar. Vill du spara innan du stänger?",
        parent=window,
    )
    if choice is None:
        return
    if choice:
        if save_note():
            window.destroy()
        else:
            return
    else:
        window.destroy()


def main() -> None:
    window = tk.Tk()
    window.title("NoteThis")
    window.geometry("700x450")

    global text_area, document_label, status_label, stats_label, search_entry, divider_widget
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

    file_menu = tk.Menu(menubar, tearoff=0)
    menubar.add_cascade(label="Arkiv", menu=file_menu)
    file_menu.add_command(label="Ny anteckning", command=lambda: start_new_note_from_template(window))
    file_menu.add_command(label="Hantera anteckningar", command=lambda: open_notes_dialog(window))
    file_menu.add_separator()
    file_menu.add_command(label="Spara", command=save_note, accelerator="Ctrl+S")
    file_menu.add_command(label="Spara som..", command=save_note_as_copy)
    export_menu = tk.Menu(file_menu, tearoff=0)
    export_menu.add_command(
        label="Markdown (.md)",
        command=lambda: exporting.export_note(text_area.get("1.0", "end-1c"), set_status, "md"),
    )
    export_menu.add_command(
        label="Text (.txt)",
        command=lambda: exporting.export_note(text_area.get("1.0", "end-1c"), set_status, "txt"),
    )
    export_menu.add_command(
        label="PDF (.pdf)",
        command=lambda: exporting.export_note(text_area.get("1.0", "end-1c"), set_status, "pdf"),
    )
    file_menu.add_cascade(label="Exportera", menu=export_menu)
    file_menu.add_separator()
    file_menu.add_command(label="Avsluta", command=lambda: confirm_close(window))

    edit_menu = tk.Menu(menubar, tearoff=0)
    menubar.add_cascade(label="Redigera", menu=edit_menu)
    edit_menu.add_command(label="Ångra", command=undo_last_change, accelerator="Ctrl+Z")

    insert_menu = tk.Menu(menubar, tearoff=0)
    menubar.add_cascade(label="Infoga", menu=insert_menu)
    insert_menu.add_command(label="Tidsstämpel", command=insert_timestamp)
    insert_menu.add_separator()

    token_config_local = tokens.load_token_config(TOKENS_CONFIG_PATH)
    globals_config = token_config_local.get("globals", {})
    if isinstance(globals_config, dict) and globals_config:
        globals_menu = tk.Menu(insert_menu, tearoff=0)
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
            for token_name in sorted(token_group.keys()):
                group_menu.add_command(
                    label=token_name,
                    command=lambda name=token_name: insert_token_placeholder(name),
                )
            insert_menu.add_cascade(label=group_name.title(), menu=group_menu)

    settings_menu = tk.Menu(menubar, tearoff=0)
    menubar.add_cascade(label="Inställningar", menu=settings_menu)

    theme_menu = tk.Menu(settings_menu, tearoff=0)
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
    menubar.add_cascade(label="Hjälp", menu=help_menu)
    help_menu.add_command(label="Om NoteThis", command=lambda: open_about_dialog(window))

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

    text_area = tk.Text(window, wrap="word", font="TkTextFont", undo=True, maxundo=10, autoseparators=True)
    text_area.pack(fill="both", expand=True, padx=12, pady=(0, 12))
    text_area.tag_configure("search_match", background=current_theme()["search_match"])
    configure_heading_fonts()
    text_area.bind("<KeyRelease>", lambda _event: refresh_editor_state())
    text_area.bind("<Return>", handle_return_key)
    text_area.bind("<Control-z>", undo_last_change)
    text_area.bind("<Control-Z>", undo_last_change)
    text_area.bind("<Control-s>", handle_save_shortcut)
    text_area.bind("<Control-S>", handle_save_shortcut)
    window.bind("<Control-s>", handle_save_shortcut)
    window.bind("<Control-S>", handle_save_shortcut)
    search_entry.bind("<KeyRelease>", lambda _event: refresh_editor_state())
    apply_theme_mode(window)
    set_ui_scale(ui_scale_index)
    set_status(f"Autosparning: var {AUTOSAVE_INTERVAL_MINUTES} min")

    window.after(AUTOSAVE_INTERVAL_MS, lambda: schedule_autosave(window))
    window.protocol("WM_DELETE_WINDOW", lambda: confirm_close(window))
    window.mainloop()


if __name__ == "__main__":
    main()
