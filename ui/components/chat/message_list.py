import sys
from typing import Any, Callable, Optional

import customtkinter as ctk

from ui.styles import (
    ACCENT_COLOR, CHAT_BG_COLOR, ERROR_COLOR, SENT_BUBBLE_COLOR, RECEIVED_BUBBLE_COLOR,
    SUB_TEXT_COLOR, TEXT_COLOR, get_font,
)


def _receipt_glyph(status: str):
    """Maps a message's delivery status to a WhatsApp-style tick glyph + color."""
    s = (status or "").upper()
    if s == "SENT":
        return "✓", SUB_TEXT_COLOR
    if s == "DELIVERED":
        return "✓✓", SUB_TEXT_COLOR
    if s == "READ":
        return "✓✓", ACCENT_COLOR
    if s == "FAILED":
        return "⚠", ERROR_COLOR
    return "🕐", SUB_TEXT_COLOR  # PENDING / QUEUED


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
        self.message_status = {}
        self.message_tick_labels = {}
        self.message_star_states = {}
        self.message_timestamps = {}
        self.message_bodies = {}
        self.message_order = []
        self.message_containers = {}
        self.message_bubbles = {}
        self.message_bubble_colors = {}
        self._highlighted_msg_id = None

        # Loading Indicator
        self._loading_label = ctk.CTkLabel(
            self, text="Loading messages...",
            font=get_font(size=14, weight="bold"),
            text_color=ACCENT_COLOR,
        )

    def add_message(self, text: str, is_sent: bool = True, timestamp: str = "12:00 PM", msg_id: Optional[str] = None, status: str = "PENDING", parent_id: Optional[str] = None, sender_name: str = "Unknown", attachment_path: Optional[str] = None, is_starred: bool = False):
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
        display_text = f"{timestamp}{star_mark}"

        # Read-receipt tick (✓ / ✓✓ / blue ✓✓) — outgoing messages only
        tick_label = None
        if is_sent:
            glyph, glyph_color = _receipt_glyph(status)
            tick_label = ctk.CTkLabel(bottom_frame, text=glyph, text_color=glyph_color, font=get_font(size=10))
            tick_label.pack(side="right")

        time_label = ctk.CTkLabel(bottom_frame, text=display_text, text_color=SUB_TEXT_COLOR, font=get_font(size=10))
        time_label.pack(side="left" if not is_sent else "right")

        if msg_id:
            self.rendered_msg_ids.add(msg_id)
            self.message_labels[msg_id] = time_label
            self.message_status[msg_id] = status
            self.message_tick_labels[msg_id] = tick_label
            self.message_star_states[msg_id] = is_starred
            self.message_timestamps[msg_id] = timestamp
            self.message_bodies[msg_id] = text or ""
            if msg_id not in self.message_order:
                self.message_order.append(msg_id)
            self.message_containers[msg_id] = msg_container
            self.message_bubbles[msg_id] = bubble
            self.message_bubble_colors[msg_id] = bubble_color

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

    def update_message_status(self, msg_id: str, status: Optional[str] = None, is_starred: Optional[bool] = None) -> None:
        """Updates status/star state for an already-rendered message and refreshes its
        time label + read-receipt tick. No-ops if the message isn't rendered or nothing
        actually changed."""
        if msg_id not in self.message_labels:
            return

        changed = False
        if status is not None and self.message_status.get(msg_id) != status:
            self.message_status[msg_id] = status
            changed = True
        if is_starred is not None and self.message_star_states.get(msg_id) != is_starred:
            self.message_star_states[msg_id] = is_starred
            changed = True

        if not changed:
            return

        timestamp = self.message_timestamps.get(msg_id, "Unknown")
        star_mark = " ⭐" if self.message_star_states.get(msg_id, False) else ""
        self.message_labels[msg_id].configure(text=f"{timestamp}{star_mark}")

        tick_label = self.message_tick_labels.get(msg_id)
        if tick_label is not None and tick_label.winfo_exists():
            glyph, glyph_color = _receipt_glyph(self.message_status.get(msg_id, "PENDING"))
            tick_label.configure(text=glyph, text_color=glyph_color)

    def discard(self, msg_id: str) -> None:
        self.rendered_msg_ids.discard(msg_id)
        self.message_labels.pop(msg_id, None)
        self.message_status.pop(msg_id, None)
        self.message_tick_labels.pop(msg_id, None)
        self.message_star_states.pop(msg_id, None)
        self.message_timestamps.pop(msg_id, None)
        self.message_bodies.pop(msg_id, None)
        self.message_containers.pop(msg_id, None)
        self.message_bubbles.pop(msg_id, None)
        self.message_bubble_colors.pop(msg_id, None)
        if msg_id in self.message_order:
            self.message_order.remove(msg_id)

    # ── Search within chat ───────────────────────────────────────────────────────

    def find_matches(self, query: str) -> list:
        """Returns msg_ids (oldest → newest) whose body text contains `query`."""
        term = (query or "").strip().lower()
        if not term:
            return []
        return [mid for mid in self.message_order if term in self.message_bodies.get(mid, "").lower()]

    def scroll_to(self, msg_id: str) -> None:
        container = self.message_containers.get(msg_id)
        if not container or not container.winfo_exists():
            return
        self.update_idletasks()
        bbox = self._parent_canvas.bbox("all")
        total_height = bbox[3] if bbox else 0
        if not total_height:
            return
        fraction = max(0.0, min(1.0, container.winfo_y() / total_height))
        self._parent_canvas.yview_moveto(fraction)

    def highlight_message(self, msg_id: Optional[str]) -> None:
        """Highlights one bubble (accent color) and restores any previously highlighted one."""
        if self._highlighted_msg_id and self._highlighted_msg_id != msg_id:
            prev_bubble = self.message_bubbles.get(self._highlighted_msg_id)
            prev_color = self.message_bubble_colors.get(self._highlighted_msg_id)
            if prev_bubble is not None and prev_bubble.winfo_exists() and prev_color is not None:
                prev_bubble.configure(fg_color=prev_color)

        self._highlighted_msg_id = msg_id
        if not msg_id:
            return
        bubble = self.message_bubbles.get(msg_id)
        if bubble is not None and bubble.winfo_exists():
            bubble.configure(fg_color=ACCENT_COLOR)

    def clear_highlight(self) -> None:
        self.highlight_message(None)

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
        self.message_status.clear()
        self.message_tick_labels.clear()
        self.message_star_states.clear()
        self.message_timestamps.clear()
        self.message_bodies.clear()
        self.message_order.clear()
        self.message_containers.clear()
        self.message_bubbles.clear()
        self.message_bubble_colors.clear()
        self._highlighted_msg_id = None

    def show_loading(self) -> None:
        if self._loading_label and self._loading_label.winfo_exists():
            self._loading_label.pack(pady=40)

    def hide_loading(self) -> None:
        if self._loading_label and self._loading_label.winfo_exists():
            self._loading_label.pack_forget()
