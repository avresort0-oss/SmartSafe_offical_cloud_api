import os
import sys
import subprocess
import tkinter as tk
import customtkinter as ctk
from tkinter import filedialog
import logging
import threading
from datetime import datetime, timezone

logger = logging.getLogger(__name__)
from typing import Optional, Callable, List, Any

from .styles import (
    BG_COLOR, SURFACE_COLOR, INPUT_COLOR, HOVER_COLOR,
    ACCENT_COLOR, ACCENT_HOVER, TEXT_COLOR, SUB_TEXT_COLOR,
    SENT_BUBBLE_COLOR, RECEIVED_BUBBLE_COLOR, HEADER_FOOTER_COLOR, 
    CHAT_BG_COLOR, get_font, get_media_icon
)
from services.user_service import UserResponseDTO
from services.workspace_service import WorkspaceDTO


class ChatFrame(ctk.CTkFrame):
    """
    Enterprise Chat Layout Component.
    Handles the message timeline, header context, and input actions.
    Designed for future pagination and lazy-loading integration.
    """
    
    def __init__(
        self, 
        master: ctk.CTkFrame, 
        current_user: Optional[UserResponseDTO] = None,
        current_workspace: Optional[WorkspaceDTO] = None,
        load_messages_cb: Optional[Callable] = None,
        send_message_cb: Optional[Callable] = None,
        delete_message_cb: Optional[Callable] = None,
        toggle_star_cb: Optional[Callable] = None,
        load_quick_replies_cb: Optional[Callable] = None,
        load_labels_cb: Optional[Callable] = None,
        attach_label_cb: Optional[Callable] = None,
        detach_label_cb: Optional[Callable] = None,
        create_contract_cb: Optional[Callable] = None,
        **kwargs
    ):
        super().__init__(master, fg_color=BG_COLOR, corner_radius=0, **kwargs)
        
        self.current_user = current_user
        self.current_workspace = current_workspace
        if load_messages_cb:
            self.load_messages_cb = load_messages_cb
        self.send_message_cb = send_message_cb
        self.delete_message_cb = delete_message_cb
        self.toggle_star_cb = toggle_star_cb
        self.load_quick_replies_cb = load_quick_replies_cb
        
        # Advanced Features Callbacks
        self.load_labels_cb = load_labels_cb
        self.attach_label_cb = attach_label_cb
        self.detach_label_cb = detach_label_cb
        self.create_contract_cb = create_contract_cb

        # State tracking to prevent re-rendering existing messages
        self.rendered_msg_ids = set()
        self.message_labels = {}
        self.message_sync_states = {}
        self.message_star_states = {}
        self.message_timestamps = {}
        self.last_message_timestamp: Optional[str] = None
        self.active_conversation_id: Optional[str] = None
        self.replying_to_msg_id = None
        self._is_loading = False

        # Configure 6-row layout
        self.grid_rowconfigure(0, weight=0)  # Header
        self.grid_rowconfigure(1, weight=1)  # Message Timeline (Expands)
        self.grid_rowconfigure(2, weight=0)  # Reply Banner
        self.grid_rowconfigure(3, weight=0)  # Quick Reply Banner
        self.grid_rowconfigure(4, weight=0)  # Suggest Menu
        self.grid_rowconfigure(5, weight=0)  # Input Area
        self.grid_columnconfigure(0, weight=1)
        
        self._build_header()
        self._build_message_list()
        self._build_reply_banner()
        self._build_quick_replies_banner()
        self._build_suggest_menu()
        self._build_input_area()
        
        # Load persisted messages
        self._load_history()
        
        # Start real-time simulation polling
        self._poll_messages()

    def _build_header(self):
        self.header_frame = ctk.CTkFrame(self, fg_color=HEADER_FOOTER_COLOR, corner_radius=0, height=62)
        self.header_frame.grid(row=0, column=0, sticky="ew")
        self.header_frame.grid_propagate(False)
        
        # Profile Circle
        self.avatar_label = ctk.CTkLabel(
            self.header_frame, 
            text="W", 
            width=42, 
            height=42, 
            corner_radius=21, 
            fg_color=ACCENT_COLOR, 
            text_color="#ffffff",
            font=get_font(size=15, weight="bold")
        )
        self.avatar_label.pack(side="left", padx=(15, 12), pady=9)
        
        # Contact Info Container
        info_container = ctk.CTkFrame(self.header_frame, fg_color="transparent")
        info_container.pack(side="left", fill="y", pady=9)
        
        self.title_label = ctk.CTkLabel(info_container, text="Select a conversation", font=get_font(size=16, weight="bold"), text_color=TEXT_COLOR)
        self.title_label.pack(anchor="w")
        
        self.status_label = ctk.CTkLabel(info_container, text="offline", font=get_font(size=13), text_color=ACCENT_COLOR)
        self.status_label.pack(anchor="w")

        # ── Advanced Header Components ───────────────────────────────────────
        self.header_actions = ctk.CTkFrame(self.header_frame, fg_color="transparent")
        self.header_actions.pack(side="right", padx=15, pady=9)

        # 24H Timer Badge
        self.timer_badge = ctk.CTkLabel(
            self.header_actions, text="24h Window: --:--",
            font=get_font(size=11, weight="bold"),
            fg_color="#343f46", text_color="#e9edef",
            corner_radius=12, height=24, padx=10
        )
        self.timer_badge.pack(side="right", padx=(10, 0))
        self.timer_badge.pack_forget() # Hidden until conv selected

        # Labels Container
        self.header_labels_frame = ctk.CTkFrame(self.header_actions, fg_color="transparent")
        self.header_labels_frame.pack(side="right", padx=(10, 0))

        self.add_label_btn = ctk.CTkButton(
            self.header_actions, text="+ Label", width=70, height=24,
            fg_color="transparent", hover_color=HOVER_COLOR,
            text_color=ACCENT_COLOR, border_width=1, border_color=ACCENT_COLOR,
            corner_radius=12, font=get_font(size=11, weight="bold"),
            command=self._on_add_label_click
        )
        self.add_label_btn.pack(side="right", padx=(10, 0))
        self.add_label_btn.pack_forget()
        
        # Action Buttons
        self.more_btn = ctk.CTkButton(self.header_frame, text="⋮", width=36, height=36, fg_color="transparent", hover_color=HOVER_COLOR, font=get_font(size=20), corner_radius=18)
        self.more_btn.pack(side="right", padx=(5, 15))
        
        self.search_btn = ctk.CTkButton(self.header_frame, text="🔍", width=36, height=36, fg_color="transparent", hover_color=HOVER_COLOR, font=get_font(size=17), corner_radius=18)
        self.search_btn.pack(side="right", padx=5)

    def _build_message_list(self):
        self.message_canvas = ctk.CTkScrollableFrame(self, fg_color=CHAT_BG_COLOR, corner_radius=0)
        self.message_canvas.grid(row=1, column=0, sticky="nsew")
        self.message_canvas.grid_columnconfigure(0, weight=1)

        # Loading Indicator
        self._loading_label = ctk.CTkLabel(
            self.message_canvas, text="Loading messages...",
            font=get_font(size=14, weight="bold"),
            text_color=ACCENT_COLOR
        )

    def _build_reply_banner(self):
        self.reply_banner = ctk.CTkFrame(self, fg_color=INPUT_COLOR, corner_radius=0, height=40)
        self.reply_banner.grid_propagate(False)
        
        self.reply_label = ctk.CTkLabel(self.reply_banner, text="Replying to...", font=get_font(size=13), text_color=ACCENT_COLOR)
        self.reply_label.pack(side="left", padx=20, pady=8)
        
        self.cancel_reply_btn = ctk.CTkButton(self.reply_banner, text="✕", width=24, height=24, fg_color="transparent", hover_color=HOVER_COLOR, text_color=SUB_TEXT_COLOR, command=self._cancel_reply)
        self.cancel_reply_btn.pack(side="right", padx=15, pady=8)

    def configure_callbacks(
        self,
        send_message_cb=None,
        delete_message_cb=None,
        toggle_star_cb=None,
        load_quick_replies_cb=None,
        load_labels_cb=None,
        attach_label_cb=None,
        detach_label_cb=None,
        create_contract_cb=None
    ):
        if send_message_cb: self.send_message_cb = send_message_cb
        if delete_message_cb: self.delete_message_cb = delete_message_cb
        if toggle_star_cb: self.toggle_star_cb = toggle_star_cb
        if load_quick_replies_cb: 
            self.load_quick_replies_cb = load_quick_replies_cb
            self.refresh_quick_replies()
        
        self.load_labels_cb = load_labels_cb
        self.attach_label_cb = attach_label_cb
        self.detach_label_cb = detach_label_cb
        self.create_contract_cb = create_contract_cb

    def _build_quick_replies_banner(self):
        self.quick_replies_banner = ctk.CTkScrollableFrame(self, fg_color=BG_COLOR, corner_radius=0, height=45, orientation="horizontal")
        self.quick_replies_banner.grid(row=3, column=0, sticky="ew", padx=10, pady=0)
        self.quick_replies_banner.grid_remove() # Hidden by default
        self.refresh_quick_replies()

    def refresh_quick_replies(self):
        if hasattr(self, "quick_replies_banner") and self.quick_replies_banner.winfo_exists():
            for child in self.quick_replies_banner.winfo_children():
                child.destroy()
            
            replies = self.load_quick_replies_cb() if self.load_quick_replies_cb else []
            if replies:
                self.quick_replies_banner.grid(row=3, column=0, sticky="ew", padx=10, pady=(5,0))
                for reply in replies:
                    text = reply.get("text", "") or reply.get("content", "") if isinstance(reply, dict) else str(reply)
                    title = reply.get("title", "") if isinstance(reply, dict) else ""
                    attachment_path = reply.get("attachment_path") if isinstance(reply, dict) else None
                    has_attachment = bool(attachment_path)
                    
                    display_text = title if title else (text[:30] + "..." if len(text) > 30 else text)
                    if has_attachment:
                        icon = get_media_icon(attachment_path)
                        display_text = f"{icon} {display_text}".strip()
                        
                    btn = ctk.CTkButton(
                        self.quick_replies_banner,
                        text=display_text,
                        fg_color=HEADER_FOOTER_COLOR,
                        hover_color="#2b3b44",
                        text_color=TEXT_COLOR,
                        corner_radius=15,
                        height=28,
                        command=lambda r=reply: self._send_quick_reply(r)
                    )
                    btn.pack(side="left", padx=(0, 8), pady=2)
            else:
                self.quick_replies_banner.grid_remove()

    def _send_quick_reply(self, reply: Any):
        if isinstance(reply, str):
            text = reply
            attachment = None
        else:
            text = reply.get("text", "") or reply.get("content", "")
            attachment = reply.get("attachment_path")

        current_text = self.msg_entry.get().strip()
        if current_text:
            text = f"{current_text} {text}" if text else current_text
            
        send_cb = self.send_message_cb
        if (text or attachment) and send_cb is not None and self.current_user is not None:
            reply_parent_id = self.replying_to_msg_id
            self.msg_entry.delete(0, "end")
            self._cancel_reply()
            if hasattr(self, "suggest_frame"):
                self.suggest_frame.grid_remove()
                
            route_wa = getattr(self, "wa_toggle_var", ctk.BooleanVar(value=False)).get()
            
            def _callback(new_msg):
                if new_msg:
                    self.add_message_from_dto(new_msg, is_sent=True)
            
            send_cb(self.active_conversation_id, text, self.current_user.id, reply_parent_id, route_wa, attachment, callback=_callback)

    def _build_suggest_menu(self):
        self.suggest_frame = ctk.CTkScrollableFrame(self, fg_color="#182229", corner_radius=10, height=130)
        self.suggest_frame.grid_columnconfigure(0, weight=1)

    def _on_input_change(self, event):
        text = self.msg_entry.get()
        if text.startswith("/"):
            query = text[1:].lower().strip()
            self._show_suggestions(query)
        else:
            self.suggest_frame.grid_remove()

    def _show_suggestions(self, query: str):
        replies = self.load_quick_replies_cb() if self.load_quick_replies_cb else []
        filtered: List[Any] = []
        for r in replies:
            title = r.get("title", "").lower() if isinstance(r, dict) else ""
            content = (r.get("text", "") or r.get("content", "")).lower() if isinstance(r, dict) else str(r).lower()
            if query in title or query in content:
                filtered.append(r)
        
        for child in self.suggest_frame.winfo_children():
            child.destroy()
            
        if not isinstance(filtered, list) or not filtered:
            self.suggest_frame.grid_remove()
            return
            
        self.suggest_frame.grid(row=4, column=0, sticky="ew", padx=10, pady=(0, 5))
        
        # Show top 5
        for idx in range(min(5, len(filtered))):
            reply = filtered[idx]
            title_text = reply.get("title", "") if isinstance(reply, dict) else ""
            content_text = (reply.get("text", "") or reply.get("content", "")) if isinstance(reply, dict) else str(reply)
            title_display = title_text if title_text else "Quick Reply"
            snippet = content_text[:50] + "..." if len(content_text) > 50 else content_text
            
            btn = ctk.CTkButton(
                self.suggest_frame,
                text=f"{title_display} - {snippet}",
                fg_color="transparent",
                hover_color="#2b3b44",
                text_color=TEXT_COLOR,
                anchor="w",
                font=get_font(size=14),
                command=lambda r=reply: self._select_suggestion(r)
            )
            btn.pack(fill="x", padx=5, pady=2)

    def _select_suggestion(self, reply):
        # Insert the text into the input box instead of sending immediately, or just clear and send.
        # Sending immediately is faster. Let's send immediately.
        self.msg_entry.delete(0, "end")
        self._send_quick_reply(reply)

    def _build_input_area(self):
        self.input_frame = ctk.CTkFrame(self, fg_color=HEADER_FOOTER_COLOR, corner_radius=0, height=62)
        self.input_frame.grid(row=5, column=0, sticky="ew")
        self.input_frame.grid_propagate(False)
        
        # Emoji Button
        self.emoji_btn = ctk.CTkButton(self.input_frame, text="😊", width=40, height=40, fg_color="transparent", hover_color=HOVER_COLOR, font=get_font(size=22), corner_radius=20)
        self.emoji_btn.pack(side="left", padx=(15, 5), pady=11)
        
        # Attachment Button
        self.attach_btn = ctk.CTkButton(
            self.input_frame, text="＋", width=40, height=40,
            fg_color="transparent", hover_color=HOVER_COLOR,
            text_color=ACCENT_COLOR, font=get_font(size=22),
            command=self._handle_attachment
        )
        self.attach_btn.pack(side="left", padx=(5, 5))

        # New Contract Shortcut
        self.contract_btn = ctk.CTkButton(
            self.input_frame, text="📝 Contract", width=96, height=34,
            fg_color="#2a3942", hover_color="#374045",
            text_color=TEXT_COLOR, font=get_font(size=12, weight="bold"),
            corner_radius=17,
            command=self._on_create_contract_shortcut
        )
        self.contract_btn.pack(side="left", padx=(5, 10))
        
        # Text Entry (Pill Style)
        entry_container = ctk.CTkFrame(self.input_frame, fg_color="#2a3942", corner_radius=21, height=42)
        entry_container.pack(side="left", fill="x", expand=True, padx=(0, 10), pady=10)
        entry_container.pack_propagate(False)

        self.msg_entry = ctk.CTkEntry(
            entry_container, placeholder_text="Type a message (Type '/' for quick replies)", 
            border_width=0, fg_color="transparent", text_color=TEXT_COLOR, 
            placeholder_text_color=SUB_TEXT_COLOR, font=get_font(size=15)
        )
        self.msg_entry.pack(fill="both", expand=True, padx=18)
        self.msg_entry.bind("<Return>", lambda e: self._handle_send())
        self.msg_entry.bind("<KeyRelease>", self._on_input_change)
        
        # Send Button
        self.send_btn = ctk.CTkButton(
            self.input_frame, text="➤", width=42, height=42, corner_radius=21, 
            fg_color="transparent", hover_color=HOVER_COLOR, text_color=ACCENT_COLOR, 
            font=get_font(size=24), command=self._handle_send
        )
        self.send_btn.pack(side="right", padx=(5, 10), pady=10)

    def add_message(self, text: str, is_sent: bool = True, timestamp: str = "12:00 PM", msg_id: Optional[str] = None, is_synced: bool = False, parent_id: Optional[str] = None, sender_name: str = "Unknown", attachment_path: Optional[str] = None, is_starred: bool = False):
        """
        Dynamically injects a new message bubble into the timeline.
        Respects layout alignment (Sent = Right, Received = Left).
        """
        bubble_color = SENT_BUBBLE_COLOR if is_sent else RECEIVED_BUBBLE_COLOR
        anchor = "e" if is_sent else "w"
        
        # Container to hold the bubble and align it correctly
        msg_container = ctk.CTkFrame(self.message_canvas, fg_color="transparent")
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
            msg_label.bind("<Button-1>", lambda e, p=attachment_path: self._open_attachment(p))
        
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
            
            reply_btn = ctk.CTkButton(bottom_frame, text="Reply", width=30, height=15, font=get_font(size=10), fg_color="transparent", hover_color="#1f2a33", text_color=SUB_TEXT_COLOR, command=lambda m=msg_id, t=text: self._initiate_reply(m, t))
            reply_btn.pack(side="right" if not is_sent else "left", padx=10)

        # Context Menu Bindings
        def do_popup(event):
            self._show_context_menu(event, msg_id, text, msg_container)
            
        bubble.bind("<Button-3>", do_popup)
        msg_label.bind("<Button-3>", do_popup)
        if sys.platform == "darwin":
            bubble.bind("<Button-2>", do_popup)
            msg_label.bind("<Button-2>", do_popup)

        # Scroll to bottom whenever a new message is added
        self.message_canvas._parent_canvas.yview_moveto(1.0)

    def add_message_from_dto(self, msg_dto: Any, is_sent: bool):
        """Helper method to add a message from a DTO to avoid repetition."""
        self.add_message(
            text=msg_dto.content,
            is_sent=is_sent,
            timestamp=msg_dto.timestamp,
            msg_id=msg_dto.id,
            is_synced=msg_dto.is_synced,
            parent_id=msg_dto.parent_id,
            sender_name=msg_dto.sender_name,
            attachment_path=msg_dto.attachment_path,
            is_starred=msg_dto.is_starred
        )
        # Cursor uses updated_at so status updates are captured in incremental polling.
        updated_cursor = getattr(msg_dto, "updated_at", None) or getattr(msg_dto, "created_at", None)
        if updated_cursor and (not self.last_message_timestamp or updated_cursor > self.last_message_timestamp):
            self.last_message_timestamp = updated_cursor

    def _load_history(self):
        """Loads the initial batch of historical messages asynchronously."""
        if self._is_loading:
            return
            
        self._is_loading = True
        if self._loading_label and self._loading_label.winfo_exists():
            self._loading_label.pack(pady=40)
        
        def _worker():
            messages = []
            if self.load_messages_cb:
                try:
                    messages = self.load_messages_cb(self.active_conversation_id, None)
                except Exception as e:
                    logger.error(f"Error loading history: {e}")
            
            self.after(0, lambda: self._finalize_history_load(messages))

        threading.Thread(target=_worker, daemon=True).start()

    def _finalize_history_load(self, messages):
        self._is_loading = False
        if hasattr(self, "_loading_label") and self._loading_label and self._loading_label.winfo_exists():
            self._loading_label.pack_forget()
        if hasattr(self, "_empty_label") and self._empty_label and self._empty_label.winfo_exists():
            self._empty_label.pack_forget()
        
        for msg in messages:
            is_sent = False
            if self.current_user is not None:
                is_sent = bool(msg.sender_id == getattr(self.current_user, 'id', None))
            self.add_message_from_dto(msg, is_sent)

    def _poll_messages(self):
        """
        Efficiently polls for new messages since the last one was received.
        Uses a daemon thread to prevent UI freezing during synchronous database/API calls.
        """
        def _worker():
            new_messages = []
            if self.load_messages_cb:
                try:
                    new_messages = self.load_messages_cb(self.active_conversation_id, self.last_message_timestamp)
                except Exception as e:
                    logger.error(f"Error polling messages: {e}", exc_info=True)
                    
            def _update_and_schedule():
                if new_messages:
                    self._process_polled_messages(new_messages)
                self._poll_timer = self.after(2000, self._poll_messages)
                
            self.after(0, _update_and_schedule)
            
        threading.Thread(target=_worker, daemon=True).start()

    def _process_polled_messages(self, new_messages):
        for msg in new_messages:
            if msg.id not in self.rendered_msg_ids:
                is_sent = bool(self.current_user is not None and msg.sender_id == self.current_user.id)
                self.add_message_from_dto(msg, is_sent)
            elif msg.id in self.message_labels:
                if self.message_sync_states.get(msg.id) != msg.is_synced or self.message_star_states.get(msg.id) != msg.is_starred:
                    self.message_sync_states[msg.id] = msg.is_synced
                    self.message_star_states[msg.id] = msg.is_starred
                    self._update_message_time_label(msg.id)
        
    def _initiate_reply(self, msg_id: str, text: str):
        self.replying_to_msg_id = msg_id
        snippet = text[:40] + "..." if len(text) > 40 else text
        self.reply_label.configure(text=f"Replying to: \"{snippet}\"")
        self.reply_banner.grid(row=2, column=0, sticky="ew")

    def _cancel_reply(self):
        self.replying_to_msg_id = None
        self.reply_banner.grid_forget()

    def _handle_send(self):
        text = self.msg_entry.get().strip()
        send_cb = self.send_message_cb
        if text and send_cb is not None and self.current_user is not None:
            reply_parent_id = self.replying_to_msg_id
            self.msg_entry.delete(0, "end")
            self._cancel_reply()
            
            route_wa = getattr(self, "wa_toggle_var", ctk.BooleanVar(value=False)).get()
            
            def _callback(new_msg):
                if new_msg:
                    self.add_message_from_dto(new_msg, is_sent=True)
            
            send_cb(self.active_conversation_id, text, self.current_user.id, reply_parent_id, route_wa, None, callback=_callback)

    def _handle_attachment(self):
        """File attachment handling."""
        filetypes = [
            ("All Supported", "*.png;*.jpg;*.jpeg;*.gif;*.mp4;*.avi;*.mp3;*.wav;*.pdf;*.txt;*.docx"),
            ("Images", "*.png;*.jpg;*.jpeg;*.gif"),
            ("Videos", "*.mp4;*.avi;*.mov"),
            ("Audio", "*.mp3;*.wav;*.ogg"),
            ("Documents", "*.pdf;*.txt;*.docx;*.csv")
        ]
        file_path = filedialog.askopenfilename(title="Select a file to attach", filetypes=filetypes)
        send_cb = self.send_message_cb
        if file_path and send_cb is not None and self.current_user is not None:
            reply_parent_id = self.replying_to_msg_id
            file_name = os.path.basename(file_path)
            icon = get_media_icon(file_path)
            type_label = "File"
            if icon == "📷": type_label = "Image"
            elif icon == "🎬": type_label = "Video"
            elif icon == "🎵": type_label = "Audio"
            elif icon == "📄": type_label = "Document"
            
            text = f"{icon} [{type_label}]: {file_name}"
            route_wa = getattr(self, "wa_toggle_var", ctk.BooleanVar(value=False)).get()
            def _callback(new_msg):
                if new_msg:
                    self.add_message_from_dto(new_msg, is_sent=True)

            send_cb(self.active_conversation_id, text, self.current_user.id, reply_parent_id, route_wa, file_path, callback=_callback)
            self._cancel_reply()

    def _open_attachment(self, path: str):
        """Opens the attachment using the native OS file viewer."""
        if not path or not os.path.exists(path) or not os.path.isfile(path):
            logger.warning(f"Attempted to open invalid or non-existent attachment path: {path}")
            return
        if sys.platform == "win32":
            os.startfile(path)
        elif sys.platform == "darwin":
            subprocess.Popen(["open", path])
        else:
            subprocess.Popen(["xdg-open", path]) # For Linux
        logger.info(f"Opened attachment: {path}")

    def _show_context_menu(self, event, msg_id: Optional[str], text: str, widget_to_destroy: ctk.CTkFrame):
        """Renders the dark-themed Right-Click context menu."""
        menu = tk.Menu(self, tearoff=0, bg="#111b21", fg="#ffffff", activebackground=ACCENT_COLOR, activeforeground="#ffffff", borderwidth=0, relief="flat") # Added relief for consistency
        menu.add_command(label="Copy Text", command=lambda: self._copy_message(text))
        if msg_id:
            is_starred = self.message_star_states.get(msg_id, False)
            star_label = "Unstar Message" if is_starred else "Star Message"
            menu.add_command(label=star_label, command=lambda: self._toggle_star(msg_id))
            menu.add_command(label="Delete Message", command=lambda: self._delete_message(msg_id, widget_to_destroy))
        menu.tk_popup(event.x_root, event.y_root)

    def _toggle_star(self, msg_id: str):
        if self.toggle_star_cb:
            new_state = self.toggle_star_cb(msg_id)
            self.message_star_states[msg_id] = new_state
            self._update_message_time_label(msg_id)

    def _copy_message(self, text: str):
        self.clipboard_clear()
        self.clipboard_append(text)
        self.update()

    def _delete_message(self, msg_id: str, widget_to_destroy: ctk.CTkFrame):
        if self.delete_message_cb:
            self.delete_message_cb(msg_id)
        widget_to_destroy.destroy()
        self.rendered_msg_ids.discard(msg_id)
        self.message_labels.pop(msg_id, None)
        self.message_sync_states.pop(msg_id, None)
        self.message_star_states.pop(msg_id, None)
        self.message_timestamps.pop(msg_id, None)

    def refresh_workspace(self, workspace: WorkspaceDTO):
        """Dynamically clears and reloads the chat view for a new workspace."""
        self.current_workspace = workspace
        self.title_label.configure(text=f"{workspace.name}")
        self.avatar_label.configure(text=(workspace.name[0].upper() if workspace.name else "?"))
        
        for child in self.message_canvas.winfo_children():
            if child != self._loading_label:
                child.destroy()
        self.rendered_msg_ids.clear()
        self.message_labels.clear()
        self.message_sync_states.clear()
        self.message_star_states.clear()
        self.message_timestamps.clear()
        self.last_message_timestamp = None
        self.refresh_quick_replies()
        self._load_history()

    def set_conversation(self, conversation_id: Optional[str], title: str, status_text: str = "online", last_message_at: str = "", labels: Optional[List[Any]] = None):
        self.active_conversation_id = conversation_id
        self.title_label.configure(text=title)
        self.status_label.configure(text=status_text)
        self.avatar_label.configure(text=title[0].upper() if title else "?")
        
        if conversation_id:
            self.timer_badge.pack(side="right", padx=(10, 0))
            self.add_label_btn.pack(side="right", padx=(10, 0))
            self._update_session_timer(last_message_at)
            self._refresh_header_labels(labels or [])
        else:
            self.timer_badge.pack_forget()
            self.add_label_btn.pack_forget()
            for child in self.header_labels_frame.winfo_children():
                child.destroy()

        self.rendered_msg_ids = set()
        for child in self.message_canvas.winfo_children():
            if child != self._loading_label:
                child.destroy()
        self._load_history()

    def _on_add_label_click(self):
        if not self.active_conversation_id or not self.load_labels_cb or not self.attach_label_cb:
            return
            
        all_labels = self.load_labels_cb()
        if not all_labels:
            return
            
        label_names = [L.get("name") if isinstance(L, dict) else str(L) for L in all_labels]
        
        # Simple selection dialog
        dialog = ctk.CTkInputDialog(text="Select a label to add:", title="Add Label")
        selected_name = dialog.get_input()
        if selected_name:
            # Find the label ID
            label_id = None
            if all_labels:
                for L in all_labels:
                    lname = L.get("name") if isinstance(L, dict) else str(L)
                    if lname == selected_name:
                        label_id = L.get("id") if isinstance(L, dict) else L
                        break
            
            if label_id and self.attach_label_cb:
                if self.attach_label_cb(label_id, self.active_conversation_id):
                    # Request a refresh from the controller or just append locally if we had the list
                    pass

    def _on_create_contract_shortcut(self):
        if not self.active_conversation_id or not self.create_contract_cb:
            return
        # Basic implementation: trigger contract creation for this contact
        self.create_contract_cb({"conversation_id": self.active_conversation_id})


    def _update_session_timer(self, last_message_at: str):
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
                    fg_color="#056162" if hours > 2 else "#664400"
                )
        except Exception as e:
            self.timer_badge.configure(text="24h Window: Unknown", fg_color="#343f46")

    def _refresh_header_labels(self, labels: list):
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
                command=lambda lid=label_id: self._on_remove_label(lid)
            )
            remove_btn.pack(side="left", padx=(0, 6), pady=2)

    def _on_remove_label(self, label_id: str):
        if self.active_conversation_id and self.detach_label_cb:
            if self.detach_label_cb(label_id, self.active_conversation_id):
                # Robust identification via name or specific attribute
                for child in self.header_labels_frame.winfo_children():
                    # Use getattr to avoid lint issues with dynamic attributes
                    if getattr(child, "_label_id", None) == label_id:
                        child.destroy()
                        break
                        
    def _update_message_time_label(self, msg_id: str):
        if msg_id in self.message_labels:
            timestamp = self.message_timestamps.get(msg_id, "Unknown")
            is_starred = self.message_star_states.get(msg_id, False)
            is_synced = self.message_sync_states.get(msg_id, False)
            
            star_mark = " ⭐" if is_starred else ""
            sync_mark = " ✓" if is_synced else ""
            self.message_labels[msg_id].configure(text=f"{timestamp}{star_mark}{sync_mark}")

    def destroy(self):
        if hasattr(self, '_poll_timer'):
            self.after_cancel(self._poll_timer)
        super().destroy()
