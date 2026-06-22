from datetime import datetime, timezone
from typing import Any, Callable, List, Optional

import customtkinter as ctk

from ui.styles import (
    ACCENT_COLOR, HEADER_FOOTER_COLOR, HOVER_COLOR, TEXT_COLOR, get_font,
)


class ChatHeader(ctk.CTkFrame):
    """Chat timeline header: avatar/title/status, 24h session timer, label chips."""

    def __init__(
        self,
        master,
        on_add_label_click: Optional[Callable[[], None]] = None,
        on_remove_label: Optional[Callable[[str], None]] = None,
        **kwargs,
    ):
        super().__init__(master, fg_color=HEADER_FOOTER_COLOR, corner_radius=0, height=62, **kwargs)
        self.grid_propagate(False)
        self.on_add_label_click = on_add_label_click
        self.on_remove_label = on_remove_label

        # Profile Circle
        self.avatar_label = ctk.CTkLabel(
            self,
            text="W",
            width=42,
            height=42,
            corner_radius=21,
            fg_color=ACCENT_COLOR,
            text_color="#ffffff",
            font=get_font(size=15, weight="bold"),
        )
        self.avatar_label.pack(side="left", padx=(15, 12), pady=9)

        # Contact Info Container
        info_container = ctk.CTkFrame(self, fg_color="transparent")
        info_container.pack(side="left", fill="y", pady=9)

        self.title_label = ctk.CTkLabel(info_container, text="Select a conversation", font=get_font(size=16, weight="bold"), text_color=TEXT_COLOR)
        self.title_label.pack(anchor="w")

        self.status_label = ctk.CTkLabel(info_container, text="offline", font=get_font(size=13), text_color=ACCENT_COLOR)
        self.status_label.pack(anchor="w")

        # Advanced Header Components
        self.header_actions = ctk.CTkFrame(self, fg_color="transparent")
        self.header_actions.pack(side="right", padx=15, pady=9)

        # 24H Timer Badge
        self.timer_badge = ctk.CTkLabel(
            self.header_actions, text="24h Window: --:--",
            font=get_font(size=11, weight="bold"),
            fg_color="#343f46", text_color="#e9edef",
            corner_radius=12, height=24, padx=10,
        )
        self.timer_badge.pack(side="right", padx=(10, 0))
        self.timer_badge.pack_forget()  # Hidden until conv selected

        # Labels Container
        self.header_labels_frame = ctk.CTkFrame(self.header_actions, fg_color="transparent")
        self.header_labels_frame.pack(side="right", padx=(10, 0))

        self.add_label_btn = ctk.CTkButton(
            self.header_actions, text="+ Label", width=70, height=24,
            fg_color="transparent", hover_color=HOVER_COLOR,
            text_color=ACCENT_COLOR, border_width=1, border_color=ACCENT_COLOR,
            corner_radius=12, font=get_font(size=11, weight="bold"),
            command=self.on_add_label_click,
        )
        self.add_label_btn.pack(side="right", padx=(10, 0))
        self.add_label_btn.pack_forget()

        # Action Buttons
        self.more_btn = ctk.CTkButton(self, text="⋮", width=36, height=36, fg_color="transparent", hover_color=HOVER_COLOR, font=get_font(size=20), corner_radius=18)
        self.more_btn.pack(side="right", padx=(5, 15))

        self.search_btn = ctk.CTkButton(self, text="🔍", width=36, height=36, fg_color="transparent", hover_color=HOVER_COLOR, font=get_font(size=17), corner_radius=18)
        self.search_btn.pack(side="right", padx=5)

    def set_conversation(self, title: str, status_text: str, has_conversation: bool) -> None:
        """Updates title/status/avatar and toggles timer/label-button visibility."""
        self.title_label.configure(text=title)
        self.status_label.configure(text=status_text)
        self.avatar_label.configure(text=title[0].upper() if title else "?")

        if has_conversation:
            self.timer_badge.pack(side="right", padx=(10, 0))
            self.add_label_btn.pack(side="right", padx=(10, 0))
        else:
            self.timer_badge.pack_forget()
            self.add_label_btn.pack_forget()
            for child in self.header_labels_frame.winfo_children():
                child.destroy()

    def set_workspace_identity(self, name: str) -> None:
        """Updates title/avatar to reflect the active workspace (no conversation selected)."""
        self.title_label.configure(text=f"{name}")
        self.avatar_label.configure(text=(name[0].upper() if name else "?"))

    def update_session_timer(self, last_message_at: str) -> None:
        """Renders the 24h WhatsApp session-window countdown, color-coded by time left."""
        if not last_message_at:
            self.timer_badge.configure(text="24h Window: Closed", fg_color="#343f46")
            return

        try:
            ts_str = (last_message_at or "").strip()
            if ts_str.endswith("Z"):
                ts_str = f"{ts_str[:-1]}+00:00"

            last_msg_dt = datetime.fromisoformat(ts_str)
            if last_msg_dt.tzinfo is None:
                last_msg_dt = last_msg_dt.replace(tzinfo=timezone.utc)

            now = datetime.now(timezone.utc)
            diff = now - last_msg_dt.astimezone(timezone.utc)

            seconds_remaining = 24 * 3600 - diff.total_seconds()

            if seconds_remaining <= 0:
                self.timer_badge.configure(text="24h Window: Expired", fg_color="#442222")
            else:
                hours = int(seconds_remaining // 3600)
                minutes = int((seconds_remaining % 3600) // 60)
                self.timer_badge.configure(
                    text=f"24h Window: {hours:02d}:{minutes:02d} left",
                    fg_color="#056162" if hours > 2 else "#664400",
                )
        except Exception:
            self.timer_badge.configure(text="24h Window: Unknown", fg_color="#343f46")

    def refresh_labels(self, labels: List[Any]) -> None:
        """Rebuilds the label-chip row; each chip's remove button calls on_remove_label."""
        for child in self.header_labels_frame.winfo_children():
            child.destroy()

        for label in labels:
            name = label.get("name", "Label") if isinstance(label, dict) else str(label)
            l_color = label.get("color", "#7c3aed") if isinstance(label, dict) else "#7c3aed"
            label_id = label.get("id") if isinstance(label, dict) else label

            chip = ctk.CTkFrame(self.header_labels_frame, fg_color=l_color, corner_radius=12, height=24)
            chip.pack(side="left", padx=(0, 6))
            chip._label_id = label_id

            lbl = ctk.CTkLabel(chip, text=name, font=get_font(size=10, weight="bold"), text_color="#ffffff")
            lbl.pack(side="left", padx=(10, 4), pady=2)

            remove_btn = ctk.CTkButton(
                chip, text="✕", width=16, height=16,
                fg_color="transparent", hover_color="rgba(0,0,0,0.2)",
                text_color="#ffffff", font=get_font(size=8),
                command=lambda lid=label_id: self.on_remove_label(lid) if self.on_remove_label else None,
            )
            remove_btn.pack(side="left", padx=(0, 6), pady=2)
