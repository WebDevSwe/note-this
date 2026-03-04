from __future__ import annotations

from typing import Callable
import tkinter as tk

from . import settings_store


class ToolTip:
    def __init__(self, widget: tk.Widget, text: str, theme_getter: Callable[[], dict]) -> None:
        self.widget = widget
        self.text = text
        self.theme_getter = theme_getter
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

        theme = self.theme_getter()
        label = tk.Label(
            tw,
            text=self.text,
            justify="left",
            relief="solid",
            borderwidth=1,
            background=theme["tooltip_bg"],
            fg=theme["tooltip_fg"],
            highlightbackground=theme["tooltip_border"],
            padx=6,
            pady=3,
        )
        label.pack()

    def hide_tip(self) -> None:
        if self.tip_window is not None:
            self.tip_window.destroy()
            self.tip_window = None


def tooltip_text(key: str, fallback: str) -> str:
    config = settings_store.load_tooltips_config()
    button_texts = config.get("buttons", {})
    value = button_texts.get(key, fallback)
    return str(value).strip()


def attach_tooltip(
    widget: tk.Widget,
    key: str,
    fallback: str,
    theme_getter: Callable[[], dict],
    tooltip_objects: list[ToolTip],
) -> None:
    config = settings_store.load_tooltips_config()
    if not config.get("enabled", True):
        return

    text = tooltip_text(key, fallback)
    if not text:
        return

    tooltip_objects.append(ToolTip(widget, text, theme_getter))
