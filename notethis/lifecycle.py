from __future__ import annotations

import tkinter as tk
from tkinter import messagebox
from typing import Callable


def schedule_autosave(window: tk.Tk, interval_ms: int, autosave_fn: Callable[[], None]) -> None:
    autosave_fn()
    window.after(interval_ms, lambda: schedule_autosave(window, interval_ms, autosave_fn))


def handle_save_shortcut(save_fn: Callable[[], None]):
    def _handler(_event=None) -> str:
        save_fn()
        return "break"

    return _handler


def confirm_close(window: tk.Tk, is_dirty_fn: Callable[[], bool], save_fn: Callable[[], bool]) -> None:
    if not is_dirty_fn():
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
        if save_fn():
            window.destroy()
        else:
            return
    else:
        window.destroy()
