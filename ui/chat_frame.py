import os
import sys
import subprocess
import tkinter as tk
import customtkinter as ctk
from tkinter import filedialog
import logging
import threading

logger = logging.getLogger(__name__)
from typing import Optional, Callable, List, Any

from .styles import (
    BG_COLOR, SURFACE_COLOR, INPUT_COLOR, HOVER_COLOR,
    ACCENT_COLOR, ACCENT_HOVER, TEXT_COLOR, SUB_TEXT_COLOR,
    HEADER_FOOTER_COLOR, get_font, get_media_icon
)
from .components.chat.chat_header import ChatHeader
from .components.chat.chat_input import ChatInput
from .components.chat.message_list import MessageList
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

        # Per-message render state lives on MessageList; ChatFrame keeps only the
        # orchestration state that spans header/input/callback-dispatch concerns.
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
        self.chat_header = ChatHeader(
            self,
            on_add_label_click=self._on_add_label_click,
            on_remove_label=self._on_remove_label,
        )
        self.chat_header.grid(row=0, column=0, sticky="ew")

    def _build_message_list(self):
        self.message_list = MessageList(
            self,
            on_reply=self._initiate_reply,
            on_context_menu=self._show_context_menu,
            on_attachment_open=self._open_attachment,
        )
        self.message_list.grid(row=1, column=0, sticky="nsew")

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

        current_text = self.chat_input.get_text()
        if current_text:
            text = f"{current_text} {text}" if text else current_text

        send_cb = self.send_message_cb
        if (text or attachment) and send_cb is not None and self.current_user is not None:
            reply_parent_id = self.replying_to_msg_id
            self.chat_input.clear()
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
        text = self.chat_input.msg_entry.get()
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
        self.chat_input.clear()
        self._send_quick_reply(reply)

    def _build_input_area(self):
        self.chat_input = ChatInput(
            self,
            on_send=self._handle_send,
            on_attach=self._handle_attachment,
            on_type=self._on_input_change,
            on_contract_shortcut=self._on_create_contract_shortcut,
        )
        self.chat_input.grid(row=5, column=0, sticky="ew")

    def add_message(self, text: str, is_sent: bool = True, timestamp: str = "12:00 PM", msg_id: Optional[str] = None, is_synced: bool = False, parent_id: Optional[str] = None, sender_name: str = "Unknown", attachment_path: Optional[str] = None, is_starred: bool = False):
        """
        Dynamically injects a new message bubble into the timeline.
        Respects layout alignment (Sent = Right, Received = Left).
        """
        self.message_list.add_message(
            text=text,
            is_sent=is_sent,
            timestamp=timestamp,
            msg_id=msg_id,
            is_synced=is_synced,
            parent_id=parent_id,
            sender_name=sender_name,
            attachment_path=attachment_path,
            is_starred=is_starred,
        )

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
        self.message_list.show_loading()

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
        self.message_list.hide_loading()

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
            if not self.message_list.is_rendered(msg.id):
                is_sent = bool(self.current_user is not None and msg.sender_id == self.current_user.id)
                self.add_message_from_dto(msg, is_sent)
            else:
                self.message_list.update_message_status(msg.id, is_synced=msg.is_synced, is_starred=msg.is_starred)
        
    def _initiate_reply(self, msg_id: str, text: str):
        self.replying_to_msg_id = msg_id
        snippet = text[:40] + "..." if len(text) > 40 else text
        self.reply_label.configure(text=f"Replying to: \"{snippet}\"")
        self.reply_banner.grid(row=2, column=0, sticky="ew")

    def _cancel_reply(self):
        self.replying_to_msg_id = None
        self.reply_banner.grid_forget()

    def _handle_send(self):
        text = self.chat_input.get_text()
        send_cb = self.send_message_cb
        if text and send_cb is not None and self.current_user is not None:
            reply_parent_id = self.replying_to_msg_id
            self.chat_input.clear()
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
            is_starred = self.message_list.get_star_state(msg_id)
            star_label = "Unstar Message" if is_starred else "Star Message"
            menu.add_command(label=star_label, command=lambda: self._toggle_star(msg_id))
            menu.add_command(label="Delete Message", command=lambda: self._delete_message(msg_id, widget_to_destroy))
        menu.tk_popup(event.x_root, event.y_root)

    def _toggle_star(self, msg_id: str):
        if self.toggle_star_cb:
            new_state = self.toggle_star_cb(msg_id)
            self.message_list.update_message_status(msg_id, is_starred=new_state)

    def _copy_message(self, text: str):
        self.clipboard_clear()
        self.clipboard_append(text)
        self.update()

    def _delete_message(self, msg_id: str, widget_to_destroy: ctk.CTkFrame):
        if self.delete_message_cb:
            self.delete_message_cb(msg_id)
        widget_to_destroy.destroy()
        self.message_list.discard(msg_id)

    def refresh_workspace(self, workspace: WorkspaceDTO):
        """Dynamically clears and reloads the chat view for a new workspace."""
        self.current_workspace = workspace
        self.chat_header.set_workspace_identity(workspace.name)

        self.message_list.clear()
        self.last_message_timestamp = None
        self.refresh_quick_replies()
        self._load_history()

    def set_conversation(self, conversation_id: Optional[str], title: str, status_text: str = "online", last_message_at: str = "", labels: Optional[List[Any]] = None):
        self.active_conversation_id = conversation_id
        self.chat_header.set_conversation(title, status_text, has_conversation=bool(conversation_id))

        if conversation_id:
            self.chat_header.update_session_timer(last_message_at)
            self.chat_header.refresh_labels(labels or [])

        self.message_list.clear_widgets_only()
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


    def _on_remove_label(self, label_id: str):
        if self.active_conversation_id and self.detach_label_cb:
            if self.detach_label_cb(label_id, self.active_conversation_id):
                # Robust identification via name or specific attribute
                for child in self.chat_header.header_labels_frame.winfo_children():
                    # Use getattr to avoid lint issues with dynamic attributes
                    if getattr(child, "_label_id", None) == label_id:
                        child.destroy()
                        break
                        
    def destroy(self):
        if hasattr(self, '_poll_timer'):
            self.after_cancel(self._poll_timer)
        super().destroy()
