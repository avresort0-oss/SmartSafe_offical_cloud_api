import sys
from typing import Any, Callable, Optional

import customtkinter as ctk

from ui.styles import (
    ACCENT_COLOR, CHAT_BG_COLOR, SENT_BUBBLE_COLOR, RECEIVED_BUBBLE_COLOR,
    SUB_TEXT_COLOR, TEXT_COLOR, get_font,
)


class MessageList(ctk.CTkScrollableFrame):
    """Message timeline: renders bubbles and owns per-message render state.

    Purely a passive render target invoked synchronously from ChatFrame's already
    main-thread-guaranteed callbacks (_finalize_history_load/_process_polled_messages).
    It never spawns a thread and never calls self.after(), so it introduces no new
    thread-safety surface beyond what ChatFrame already guarantees.
    """

    def __init__(
        self,
        master,
        on_reply: Callable[[str, str], None],
        on_context_menu: Callable[[Any, Optional[str], str, "ctk.CTkFrame"], None],
        on_attachment_open: Callable[[str], None],
        **kwargs,
    ):
        super().__init__(master, fg_color=CHAT_BG_COLOR, corner_radius=0, **kwargs)
        self.grid_columnconfigure(0, weight=1)
        self.on_reply = on_reply
        self.on_context_menu = on_context_menu
        self.on_attachment_open = on_attachment_open

        # State tracking to prevent re-rendering existing messages
        self.rendered_msg_ids = set()
        self.message_labels = {}
        self.message_sync_states = {}
        self.message_star_states = {}
        self.message_timestamps = {}

        # Loading Indicator
        self._loading_label = ctk.CTkLabel(
            self, text="Loading messages...",
            font=get_font(size=14, weight="bold"),
            text_color=ACCENT_COLOR,
        )

    def add_message(self, text: str, is_sent: bool = True, timestamp: str = "12:00 PM", msg_id: Optional[str] = None, is_synced: bool = False, parent_id: Optional[str] = None, sender_name: str = "Unknown", attachment_path: Optional[str] = None, is_starred: bool = False):
        """
        Dynamically injects a new message bubble into the timeline.
        Respects layout alignment (Sent = Right, Received = Left).
        """
        bubble_color = SENT_BUBBLE_COLOR if is_sent else RECEIVED_BUBBLE_COLOR
        anchor = "e" if is_sent else "w"

        # Container to hold the bubble and align it correctly
        msg_container = ctk.CTkFrame(self, fg_color="transparent")
        msg_container.pack(fill="x", pady=5, padx=10)

        # The actual styled message bubble
        bubble = ctk.CTkFrame(msg_container, fg_color=bubble_color, corner_radius=16)
        bubble.pack(anchor=anchor, padx=(60, 25) if not is_sent else (25, 60))

        has_top_element = False

        if parent_id:
            reply_indicator = ctk.CTkLabel(bubble, text="↳ Replied to thread", text_color=ACCENT_COLOR, font=ctk.CTkFont(size=10, slant="italic"))
            reply_indicator.pack(padx=12, pady=(6, 0), anchor="w")
            has_top_element = True

        if not is_sent:
            name_label = ctk.CTkLabel(bubble, text=sender_name, text_color=ACCENT_COLOR, font=ctk.CTkFont(size=13, weight="bold"))
            name_label.pack(padx=14, pady=(2 if has_top_element else 10, 0), anchor="w")
            has_top_element = True

        msg_label = ctk.CTkLabel(bubble, text=text, text_color=TEXT_COLOR, font=get_font(size=14), justify="left", wraplength=420)
        msg_label.pack(padx=14, pady=(4 if has_top_element else 10, 4), anchor="w")

        if attachment_path:
            msg_label.configure(text_color=ACCENT_COLOR, cursor="hand2")
            msg_label.bind("<Button-1>", lambda e, p=attachment_path: self.on_attachment_open(p))

        # Bottom controls (Time + Reply button)
        bottom_frame = ctk.CTkFrame(bubble, fg_color="transparent")
        bottom_frame.pack(fill="x", padx=14, pady=(0, 8))

        star_mark = " ⭐" if is_starred else ""
        sync_mark = " ✓" if is_synced else ""
        display_text = f"{timestamp}{star_mark}{sync_mark}"
        time_label = ctk.CTkLabel(bottom_frame, text=display_text, text_color=SUB_TEXT_COLOR, font=get_font(size=10))
        time_label.pack(side="left" if not is_sent else "right")

        if msg_id:
            self.rendered_msg_ids.add(msg_id)
            self.message_labels[msg_id] = time_label
            self.message_sync_states[msg_id] = is_synced
            self.message_star_states[msg_id] = is_starred
            self.message_timestamps[msg_id] = timestamp

            reply_btn = ctk.CTkButton(bottom_frame, text="Reply", width=30, height=15, font=get_font(size=10), fg_color="transparent", hover_color="#1f2a33", text_color=SUB_TEXT_COLOR, command=lambda m=msg_id, t=text: self.on_reply(m, t))
            reply_btn.pack(side="right" if not is_sent else "left", padx=10)

        # Context Menu Bindings
        def do_popup(event):
            self.on_context_menu(event, msg_id, text, msg_container)

        bubble.bind("<Button-3>", do_popup)
        msg_label.bind("<Button-3>", do_popup)
        if sys.platform == "darwin":
            bubble.bind("<Button-2>", do_popup)
            msg_label.bind("<Button-2>", do_popup)

        # Scroll to bottom whenever a new message is added
        self._parent_canvas.yview_moveto(1.0)

    def is_rendered(self, msg_id: str) -> bool:
        return msg_id in self.rendered_msg_ids

    def get_star_state(self, msg_id: str) -> bool:
        return self.message_star_states.get(msg_id, False)

    def update_message_status(self, msg_id: str, is_synced: Optional[bool] = None, is_starred: Optional[bool] = None) -> None:
        """Updates sync/star state for an already-rendered message and refreshes its
        time label. No-ops if the message isn't rendered or nothing actually changed."""
        if msg_id not in self.message_labels:
            return

        changed = False
        if is_synced is not None and self.message_sync_states.get(msg_id) != is_synced:
            self.message_sync_states[msg_id] = is_synced
            changed = True
        if is_starred is not None and self.message_star_states.get(msg_id) != is_starred:
            self.message_star_states[msg_id] = is_starred
            changed = True

        if not changed:
            return

        timestamp = self.message_timestamps.get(msg_id, "Unknown")
        star_mark = " ⭐" if self.message_star_states.get(msg_id, False) else ""
        sync_mark = " ✓" if self.message_sync_states.get(msg_id, False) else ""
        self.message_labels[msg_id].configure(text=f"{timestamp}{star_mark}{sync_mark}")

    def discard(self, msg_id: str) -> None:
        self.rendered_msg_ids.discard(msg_id)
        self.message_labels.pop(msg_id, None)
        self.message_sync_states.pop(msg_id, None)
        self.message_star_states.pop(msg_id, None)
        self.message_timestamps.pop(msg_id, None)

    def clear_widgets_only(self) -> None:
        """Destroys all rendered bubbles and resets the dedup guard, but leaves the
        other 4 state dicts as-is. Matches set_conversation()'s pre-existing
        behavior (as distinct from clear()'s, used by refresh_workspace) verbatim."""
        for child in self.winfo_children():
            if child != self._loading_label:
                child.destroy()
        self.rendered_msg_ids = set()

    def clear(self) -> None:
        """Destroys all rendered bubbles and resets every piece of render state."""
        for child in self.winfo_children():
            if child != self._loading_label:
                child.destroy()
        self.rendered_msg_ids.clear()
        self.message_labels.clear()
        self.message_sync_states.clear()
        self.message_star_states.clear()
        self.message_timestamps.clear()

    def show_loading(self) -> None:
        if self._loading_label and self._loading_label.winfo_exists():
            self._loading_label.pack(pady=40)

    def hide_loading(self) -> None:
        if self._loading_label and self._loading_label.winfo_exists():
            self._loading_label.pack_forget()
