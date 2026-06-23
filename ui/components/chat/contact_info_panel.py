from typing import Any, List, Optional

import customtkinter as ctk

from ui.styles import (
    ACCENT_COLOR, HEADER_FOOTER_COLOR, HOVER_COLOR, SUB_TEXT_COLOR,
    TEXT_COLOR, get_avatar_color, get_font,
)


class ContactInfoPanel(ctk.CTkFrame):
    """Slide-in side panel showing full contact details for the open chat."""

    def __init__(self, master, on_close: Optional[callable] = None, **kwargs):
        super().__init__(master, fg_color=HEADER_FOOTER_COLOR, corner_radius=0, width=280, **kwargs)
        self.grid_propagate(False)
        self.on_close = on_close

        header_row = ctk.CTkFrame(self, fg_color="transparent")
        header_row.pack(fill="x", padx=16, pady=(16, 0))
        ctk.CTkLabel(header_row, text="Contact info", font=get_font(size=14, weight="bold"), text_color=TEXT_COLOR).pack(side="left")
        close_btn = ctk.CTkButton(
            header_row, text="✕", width=24, height=24,
            fg_color="transparent", hover_color=HOVER_COLOR,
            text_color=SUB_TEXT_COLOR, corner_radius=4,
            font=get_font(size=12), command=self._on_close_click
        )
        close_btn.pack(side="right")

        self.avatar_label = ctk.CTkLabel(
            self, text="?", width=72, height=72, corner_radius=36,
            fg_color=ACCENT_COLOR, text_color="#ffffff",
            font=get_font(size=26, weight="bold")
        )
        self.avatar_label.pack(pady=(20, 10))

        self.name_label = ctk.CTkLabel(self, text="Unknown", font=get_font(size=16, weight="bold"), text_color=TEXT_COLOR)
        self.name_label.pack()

        self.phone_label = ctk.CTkLabel(self, text="", font=get_font(size=12), text_color=SUB_TEXT_COLOR)
        self.phone_label.pack(pady=(2, 16))

        self.labels_row = ctk.CTkFrame(self, fg_color="transparent")
        self.labels_row.pack(fill="x", padx=16, pady=(0, 10))

        self._section("Lifecycle stage")
        self.lifecycle_label = self._value_label()

        self._section("Email")
        self.email_label = self._value_label()

        self._section("Notes")
        self.notes_label = self._value_label(wraplength=240)

    def _section(self, title: str):
        ctk.CTkLabel(
            self, text=title.upper(), font=get_font(size=10, weight="bold"),
            text_color=SUB_TEXT_COLOR, anchor="w"
        ).pack(fill="x", padx=16, pady=(8, 0))

    def _value_label(self, wraplength: int = 0) -> ctk.CTkLabel:
        lbl = ctk.CTkLabel(
            self, text="—", font=get_font(size=13),
            text_color=TEXT_COLOR, anchor="w", justify="left",
            wraplength=wraplength
        )
        lbl.pack(fill="x", padx=16, pady=(2, 0))
        return lbl

    def _on_close_click(self):
        if self.on_close:
            self.on_close()

    def set_contact(self, contact: Any, labels: Optional[List[Any]] = None, read_item=None) -> None:
        """Populates the panel. `read_item` is a getattr/dict-aware accessor
        matching InboxFrame._read_item, so this works with DTOs or dicts alike."""
        _get = read_item or (lambda obj, key, default=None: getattr(obj, key, default))
        name = _get(contact, "display_name", "Unknown") or "Unknown"
        phone = _get(contact, "phone_e164", "") or ""
        email = _get(contact, "email", "") or "—"
        lifecycle = _get(contact, "lifecycle_stage", "") or "—"
        notes = _get(contact, "notes", "") or "—"

        self.avatar_label.configure(text=(name[0].upper() if name else "?"), fg_color=get_avatar_color(name))
        self.name_label.configure(text=name)
        self.phone_label.configure(text=phone)
        self.lifecycle_label.configure(text=lifecycle)
        self.email_label.configure(text=email)
        self.notes_label.configure(text=notes)

        for child in self.labels_row.winfo_children():
            child.destroy()
        for label in (labels or []):
            lname = _get(label, "name", "Label") if not isinstance(label, str) else label
            lcolor = _get(label, "color", "#7c3aed") if not isinstance(label, str) else "#7c3aed"
            chip = ctk.CTkLabel(
                self.labels_row, text=f" {lname} ",
                font=get_font(size=9, weight="bold"),
                fg_color=lcolor, text_color="#ffffff",
                corner_radius=4, height=14
            )
            chip.pack(side="left", padx=(0, 4))
