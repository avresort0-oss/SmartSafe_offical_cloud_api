from typing import Callable

import customtkinter as ctk

from ui.styles import (
    ACCENT_COLOR, HEADER_FOOTER_COLOR, HOVER_COLOR, SUB_TEXT_COLOR, TEXT_COLOR, get_font,
)


class ChatInput(ctk.CTkFrame):
    """Chat composer: emoji/attach/contract buttons, pill-style entry, send button."""

    def __init__(
        self,
        master,
        on_send: Callable[[], None],
        on_attach: Callable[[], None],
        on_type: Callable[..., None],
        on_contract_shortcut: Callable[[], None],
        **kwargs,
    ):
        super().__init__(master, fg_color=HEADER_FOOTER_COLOR, corner_radius=0, height=62, **kwargs)
        self.grid_propagate(False)
        self.on_send = on_send
        self.on_attach = on_attach
        self.on_type = on_type
        self.on_contract_shortcut = on_contract_shortcut

        # Emoji Button
        self.emoji_btn = ctk.CTkButton(self, text="😊", width=40, height=40, fg_color="transparent", hover_color=HOVER_COLOR, font=get_font(size=22), corner_radius=20)
        self.emoji_btn.pack(side="left", padx=(15, 5), pady=11)

        # Attachment Button
        self.attach_btn = ctk.CTkButton(
            self, text="＋", width=40, height=40,
            fg_color="transparent", hover_color=HOVER_COLOR,
            text_color=ACCENT_COLOR, font=get_font(size=22),
            command=self.on_attach,
        )
        self.attach_btn.pack(side="left", padx=(5, 5))

        # New Contract Shortcut
        self.contract_btn = ctk.CTkButton(
            self, text="📝 Contract", width=96, height=34,
            fg_color="#2a3942", hover_color="#374045",
            text_color=TEXT_COLOR, font=get_font(size=12, weight="bold"),
            corner_radius=17,
            command=self.on_contract_shortcut,
        )
        self.contract_btn.pack(side="left", padx=(5, 10))

        # Text Entry (Pill Style)
        entry_container = ctk.CTkFrame(self, fg_color="#2a3942", corner_radius=21, height=42)
        entry_container.pack(side="left", fill="x", expand=True, padx=(0, 10), pady=10)
        entry_container.pack_propagate(False)

        self.msg_entry = ctk.CTkEntry(
            entry_container, placeholder_text="Type a message (Type '/' for quick replies)",
            border_width=0, fg_color="transparent", text_color=TEXT_COLOR,
            placeholder_text_color=SUB_TEXT_COLOR, font=get_font(size=15),
        )
        self.msg_entry.pack(fill="both", expand=True, padx=18)
        self.msg_entry.bind("<Return>", lambda e: self.on_send())
        self.msg_entry.bind("<KeyRelease>", self.on_type)

        # Send Button
        self.send_btn = ctk.CTkButton(
            self, text="➤", width=42, height=42, corner_radius=21,
            fg_color="transparent", hover_color=HOVER_COLOR, text_color=ACCENT_COLOR,
            font=get_font(size=24), command=self.on_send,
        )
        self.send_btn.pack(side="right", padx=(5, 10), pady=10)

    def get_text(self) -> str:
        return self.msg_entry.get().strip()

    def clear(self) -> None:
        self.msg_entry.delete(0, "end")
