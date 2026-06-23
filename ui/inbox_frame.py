# -*- coding: utf-8 -*-
import customtkinter as ctk
import logging
from typing import Any, Callable, List, Optional

from services.user_service import UserResponseDTO
from services.workspace_service import WorkspaceDTO
from ui.chat_frame import ChatFrame


logger = logging.getLogger(__name__)


from .styles import (
    BG_COLOR, SURFACE_COLOR, INPUT_COLOR, HOVER_COLOR,
    ACCENT_COLOR, ACCENT_HOVER, TEXT_COLOR, SUB_TEXT_COLOR,
    DIVIDER_COLOR, ERROR_COLOR, HEADER_FOOTER_COLOR, CHAT_BG_COLOR,
    get_font, get_avatar_color, get_status_color
)


class InboxFrame(ctk.CTkFrame):
    def __init__(
        self,
        master: ctk.CTkFrame,
        current_user: UserResponseDTO,
        current_workspace: WorkspaceDTO,
        load_conversations_cb: Callable[[str, Optional[str], Optional[str], Optional[str], bool, Optional[str]], List[Any]],
        load_messages_cb: Callable[[Optional[str], Optional[str]], List[Any]],
        send_message_cb: Callable[[Optional[str], str, str, Optional[str], bool, Optional[str]], Any],
        delete_message_cb: Callable[[str], Any],
        toggle_star_cb: Callable[[str], bool],
        load_quick_replies_cb: Optional[Callable[[], List[str]]] = None,
        on_conversation_select_cb: Optional[Callable[[str], None]] = None,
        on_assign_cb: Optional[Callable[[str, Optional[str], Optional[Callable]], Any]] = None,
        on_update_status_cb: Optional[Callable[[str, str, Optional[Callable]], Any]] = None,
        get_accounts_cb: Optional[Callable[[], List[Any]]] = None,
        load_labels_cb: Optional[Callable[[], List[Any]]] = None,
        attach_label_cb: Optional[Callable[[str, str], bool]] = None,
        detach_label_cb: Optional[Callable[[str, str], bool]] = None,
        create_contract_cb: Optional[Callable[[dict], Any]] = None,
        **kwargs,
    ):
        super().__init__(master, fg_color=BG_COLOR, corner_radius=0, **kwargs)
        self.current_user = current_user
        self.current_workspace = current_workspace
        self.load_conversations_cb = load_conversations_cb
        self.on_conversation_select_cb = on_conversation_select_cb
        self.on_assign_cb = on_assign_cb
        self.on_update_status_cb = on_update_status_cb
        
        # Advanced Features Callbacks
        self.load_labels_cb = load_labels_cb
        self.attach_label_cb = attach_label_cb
        self.detach_label_cb = detach_label_cb
        self.create_contract_cb = create_contract_cb
        self.get_accounts_cb = get_accounts_cb

        self.selected_conversation_id: Optional[str] = None
        self._conversation_cache: List[Any] = []
        self._meta_accounts: List[Any] = []
        self._selected_meta_account_id: Optional[str] = None
        self._conversation_widgets = {}
        self._empty_label = None
        self._is_loading = False
        
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=0)
        self.grid_columnconfigure(1, weight=1)

        self._build_left_panel()
        self._build_right_panel(
            load_messages_cb, send_message_cb,
            delete_message_cb, toggle_star_cb, load_quick_replies_cb
        )
        self.refresh_conversations()

    # ── Callbacks ──────────────────────────────────────────────────────────────

    def configure_callbacks(
        self,
        load_conversations_cb,
        load_messages_cb,
        send_message_cb,
        delete_message_cb,
        toggle_star_cb,
        load_quick_replies_cb=None,
        on_conversation_select_cb=None,
        on_assign_cb: Optional[Callable[[str, Optional[str], Optional[Callable]], Any]] = None,
        on_update_status_cb: Optional[Callable[[str, str, Optional[Callable]], Any]] = None,
        get_accounts_cb=None,
        load_labels_cb=None,
        attach_label_cb=None,
        detach_label_cb=None,
        create_contract_cb=None,
    ):
        self.load_conversations_cb = load_conversations_cb
        self.on_conversation_select_cb = on_conversation_select_cb
        self.on_assign_cb = on_assign_cb
        self.on_update_status_cb = on_update_status_cb
        self.load_labels_cb = load_labels_cb
        self.attach_label_cb = attach_label_cb
        self.detach_label_cb = detach_label_cb
        self.create_contract_cb = create_contract_cb

        if get_accounts_cb:
            self.get_accounts_cb = get_accounts_cb
            
        self.chat_frame.configure_callbacks(
            send_message_cb=send_message_cb,
            delete_message_cb=delete_message_cb,
            toggle_star_cb=toggle_star_cb,
            load_quick_replies_cb=load_quick_replies_cb,
            # Pass advanced callbacks down to ChatFrame
            load_labels_cb=load_labels_cb,
            attach_label_cb=attach_label_cb,
            detach_label_cb=detach_label_cb,
            create_contract_cb=create_contract_cb
        )
        self.chat_frame.toggle_star_cb = toggle_star_cb
        if load_quick_replies_cb:
            self.chat_frame.load_quick_replies_cb = load_quick_replies_cb
            self.chat_frame.refresh_quick_replies()

    def refresh_workspace(self, workspace: WorkspaceDTO):
        self.current_workspace = workspace
        self.selected_conversation_id = None
        self._update_action_bar_placeholder()
        self.chat_frame.refresh_workspace(workspace)
        self.chat_frame.set_conversation(None, "Select a conversation", "idle")
        if self.get_accounts_cb:
            self._meta_accounts = self.get_accounts_cb()
            accounts = ["All Profiles"] + [acc.display_name for acc in self._meta_accounts]
            self.profile_menu.configure(values=accounts)
            self.profile_var.set("All Profiles")
            self._selected_meta_account_id = None
        self.refresh_conversations()

    # ── Left Panel ─────────────────────────────────────────────────────────────

    def _build_left_panel(self):
        self.left_panel = ctk.CTkFrame(self, fg_color=HEADER_FOOTER_COLOR, corner_radius=0, width=340)
        self.left_panel.grid(row=0, column=0, sticky="nsew")
        self.left_panel.grid_propagate(False)
        self.left_panel.grid_rowconfigure(5, weight=1)   # FIX: list_frame is row 5
        self.left_panel.grid_columnconfigure(0, weight=1)

        # ── Header ────────────────────────────────────────────────────────────
        header_frame = ctk.CTkFrame(self.left_panel, fg_color="transparent")
        header_frame.grid(row=0, column=0, sticky="ew", padx=16, pady=(14, 6))
        header_frame.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            header_frame, text="Inbox",
            font=get_font(size=21, weight="bold"),
            text_color=TEXT_COLOR
        ).grid(row=0, column=0, sticky="w")

        refresh_btn = ctk.CTkButton(
            header_frame, text="↺", width=32, height=32,
            fg_color=SURFACE_COLOR, hover_color="#2a3942",
            corner_radius=8, font=get_font(size=16),
            command=self.refresh_conversations
        )
        refresh_btn.grid(row=0, column=1, sticky="e")

        # ── Search Bar (Premium Rounded Pill) ─────────────────────────────────
        search_frame = ctk.CTkFrame(self.left_panel, fg_color="#2a3942", corner_radius=10, height=36)
        search_frame.grid(row=1, column=0, sticky="ew", padx=12, pady=(0, 10))
        search_frame.grid_propagate(False)
        search_frame.grid_columnconfigure(0, weight=1)

        self.search_entry = ctk.CTkEntry(
            search_frame, placeholder_text="🔍   Search conversations…",
            fg_color="transparent", border_width=0,
            text_color=TEXT_COLOR, placeholder_text_color=SUB_TEXT_COLOR,
            font=get_font(size=14)
        )
        self.search_entry.grid(row=0, column=0, sticky="ew", padx=12, pady=5)
        self.search_entry.bind("<Return>", lambda _e: self.refresh_conversations())

        # ── Filter Row ────────────────────────────────────────────────────────
        filter_row = ctk.CTkFrame(self.left_panel, fg_color="transparent")
        filter_row.grid(row=2, column=0, sticky="ew", padx=12, pady=(0, 10))
        filter_row.grid_columnconfigure(0, weight=1)

        self.status_var = ctk.StringVar(value="ALL")
        self.status_menu = ctk.CTkOptionMenu(
            filter_row,
            values=["ALL", "OPEN", "PENDING", "RESOLVED", "CLOSED"],
            variable=self.status_var,
            command=lambda _c: self.refresh_conversations(),
            fg_color=INPUT_COLOR,
            button_color=INPUT_COLOR,
            button_hover_color=HOVER_COLOR,
            dropdown_fg_color=SURFACE_COLOR,
            text_color=TEXT_COLOR,
            corner_radius=10,
            height=34,
        )
        self.status_menu.grid(row=0, column=0, sticky="ew", padx=(0, 6))

        self.unread_only_var = ctk.BooleanVar(value=False)
        unread_switch = ctk.CTkSwitch(
            filter_row, text="Unread",
            variable=self.unread_only_var,
            command=self.refresh_conversations,
            progress_color=ACCENT_COLOR,
            font=get_font(size=13),
            text_color=SUB_TEXT_COLOR,
        )
        unread_switch.grid(row=0, column=1, sticky="e")

        # ── Advanced Filters ──────────────────────────────────────────────────
        adv_row = ctk.CTkFrame(self.left_panel, fg_color="transparent")
        adv_row.grid(row=3, column=0, sticky="ew", padx=12, pady=(0, 10))
        adv_row.grid_columnconfigure((0, 1), weight=1)

        self.assignee_entry = ctk.CTkEntry(
            adv_row, placeholder_text="Assignee",
            fg_color=INPUT_COLOR, border_width=0,
            text_color=TEXT_COLOR, placeholder_text_color=SUB_TEXT_COLOR,
            corner_radius=10, height=34, font=ctk.CTkFont(size=12)
        )
        self.assignee_entry.grid(row=0, column=0, sticky="ew", padx=(0, 4))
        self.assignee_entry.bind("<Return>", lambda _e: self.refresh_conversations())

        self.label_entry = ctk.CTkEntry(
            adv_row, placeholder_text="Label",
            fg_color=INPUT_COLOR, border_width=0,
            text_color=TEXT_COLOR, placeholder_text_color=SUB_TEXT_COLOR,
            corner_radius=10, height=34, font=ctk.CTkFont(size=12)
        )
        self.label_entry.grid(row=0, column=1, sticky="ew", padx=(4, 0))
        self.label_entry.bind("<Return>", lambda _e: self.refresh_conversations())

        # ── Profile Dropdown ──────────────────────────────────────────────────
        self.profile_var = ctk.StringVar(value="All Profiles")
        self.profile_menu = ctk.CTkOptionMenu(
            self.left_panel,
            values=["All Profiles"],
            variable=self.profile_var,
            command=self._on_profile_change,
            fg_color=INPUT_COLOR,
            button_color=INPUT_COLOR,
            button_hover_color=HOVER_COLOR,
            dropdown_fg_color=SURFACE_COLOR,
            text_color=TEXT_COLOR,
            corner_radius=10,
            height=34,
        )
        self.profile_menu.grid(row=4, column=0, sticky="ew", padx=12, pady=(0, 12))

        # ── Divider ───────────────────────────────────────────────────────────
        divider = ctk.CTkFrame(self.left_panel, fg_color=DIVIDER_COLOR, height=1)
        divider.grid(row=4, column=0, sticky="ew", padx=0, pady=(38, 0)) # Fixed position

        # ── Conversation List ─────────────────────────────────────────────────
        self.list_frame = ctk.CTkScrollableFrame(
            self.left_panel, fg_color="transparent",
            scrollbar_button_color=SURFACE_COLOR,
            scrollbar_button_hover_color="#2a3942",
        )
        self.list_frame.grid(row=5, column=0, sticky="nsew", padx=0, pady=0)
        self.list_frame.grid_columnconfigure(0, weight=1)

        # Loading Indicator (Overlay-ish via pack)
        self._loading_label = ctk.CTkLabel(
            self.list_frame, text="Loading conversations...",
            font=get_font(size=13, weight="bold"),
            text_color=ACCENT_COLOR
        )
        # Initially hidden

    # ── Right Panel ────────────────────────────────────────────────────────────

    def _build_right_panel(self, load_messages_cb, send_message_cb, delete_message_cb, toggle_star_cb, load_quick_replies_cb=None):
        self.right_panel = ctk.CTkFrame(self, fg_color=BG_COLOR, corner_radius=0)
        self.right_panel.grid(row=0, column=1, sticky="nsew")
        self.right_panel.grid_rowconfigure(1, weight=1)
        self.right_panel.grid_columnconfigure(0, weight=1)

        # ── Action / Info Bar (Premium Header) ────────────────────────────────
        self.action_bar = ctk.CTkFrame(self.right_panel, fg_color=HEADER_FOOTER_COLOR, corner_radius=0, height=62)
        self.action_bar.grid(row=0, column=0, sticky="ew")
        self.action_bar.grid_propagate(False)
        self.action_bar.grid_columnconfigure(0, weight=1)
        self.action_bar.grid_columnconfigure(1, weight=0)
        self.action_bar.grid_columnconfigure(2, weight=0)
        self.action_bar.grid_columnconfigure(3, weight=0)

        # Contact name / phone
        self.selection_label = ctk.CTkLabel(
            self.action_bar,
            text="Select a conversation",
            font=get_font(size=15, weight="bold"),
            text_color=SUB_TEXT_COLOR,
            anchor="w"
        )
        self.selection_label.grid(row=0, column=0, sticky="w", padx=20, pady=15)

        # Status Badge (Pill Style)
        self.conv_status_var = ctk.StringVar(value="OPEN")
        self.conv_status_menu = ctk.CTkOptionMenu(
            self.action_bar,
            values=["OPEN", "PENDING", "RESOLVED", "CLOSED"],
            variable=self.conv_status_var,
            command=self._on_status_change,
            width=120, height=34,
            fg_color=ACCENT_COLOR,
            button_color=ACCENT_COLOR,
            button_hover_color=ACCENT_HOVER,
            dropdown_fg_color=SURFACE_COLOR,
            text_color="#ffffff",
            corner_radius=17,
            font=get_font(size=12, weight="bold")
        )
        self.conv_status_menu.grid(row=0, column=1, padx=(10, 5), pady=13)

        self.assign_entry = ctk.CTkEntry(
            self.action_bar,
            placeholder_text="Assign to...",
            width=140, height=34,
            fg_color=INPUT_COLOR, border_width=0,
            text_color=TEXT_COLOR, placeholder_text_color=SUB_TEXT_COLOR,
            corner_radius=17, font=get_font(size=13)
        )
        self.assign_entry.grid(row=0, column=2, padx=5, pady=13)

        assign_btn = ctk.CTkButton(
            self.action_bar, text="Assign", width=80, height=34,
            fg_color="transparent", hover_color=HOVER_COLOR,
            text_color=ACCENT_COLOR,
            border_width=1, border_color=ACCENT_COLOR,
            corner_radius=17, font=get_font(size=13, weight="bold"),
            command=self._on_assign
        )
        assign_btn.grid(row=0, column=3, padx=(5, 20), pady=13)

        # ── Chat Frame ────────────────────────────────────────────────────────
        self.chat_frame = ChatFrame(
            self.right_panel,
            current_user=self.current_user,
            current_workspace=self.current_workspace,
            load_messages_cb=load_messages_cb,
            send_message_cb=send_message_cb,
            delete_message_cb=delete_message_cb,
            toggle_star_cb=toggle_star_cb,
            load_quick_replies_cb=load_quick_replies_cb,
        )
        self.chat_frame.grid(row=1, column=0, sticky="nsew")
        self.chat_frame.set_conversation(None, "Select a conversation", "idle")

    # ── Helpers ────────────────────────────────────────────────────────────────

    def _read_item(self, item: Any, key: str, default=None):
        if hasattr(item, key):
            return getattr(item, key)
        if isinstance(item, dict):
            return item.get(key, default)
        return default

    def _update_action_bar_placeholder(self):
        self.selection_label.configure(
            text="Select a conversation",
            text_color=SUB_TEXT_COLOR
        )
        self.conv_status_var.set("OPEN")
        self._sync_status_badge_color("OPEN")

    def _sync_status_badge_color(self, status: str):
        color = get_status_color(status)
        self.conv_status_menu.configure(fg_color=color, button_color=color)

    def _on_profile_change(self, value: str):
        if value == "All Profiles":
            self._selected_meta_account_id = None
        else:
            for acc in self._meta_accounts:
                if acc.display_name == value:
                    self._selected_meta_account_id = acc.id
                    break
        self.refresh_conversations()

    # ── Conversation List ──────────────────────────────────────────────────────

    def refresh_conversations(self):
        if self._is_loading:
            return
            
        self._is_loading = True
        if self._loading_label is not None:
            self._loading_label.pack(pady=20)
        if self._empty_label is not None and self._empty_label.winfo_exists():
            self._empty_label.pack_forget()

        import threading
        
        status = self.status_var.get()
        status_filter = None if status == "ALL" else status
        search_query = self.search_entry.get().strip()
        assignee_filter = self.assignee_entry.get().strip() or None
        label_filter = self.label_entry.get().strip() or None
        unread_only = self.unread_only_var.get()
        account_id = self._selected_meta_account_id

        def _worker():
            try:
                rows = self.load_conversations_cb(
                    search_query,
                    status_filter,
                    assignee_filter,
                    label_filter,
                    unread_only,
                    account_id,
                )
                self.after(0, lambda: self._finalize_refresh(rows))
            except Exception as e:
                logger.error(f"Error loading conversations: {e}")
                self.after(0, lambda: self._finalize_refresh([]))

        threading.Thread(target=_worker, daemon=True).start()

    def _finalize_refresh(self, rows):
        self._is_loading = False
        self._loading_label.pack_forget()
        
        self._conversation_cache = rows or []

        current_conv_ids = {self._read_item(item, "id") for item in self._conversation_cache if self._read_item(item, "id")}

        for conv_id in list(self._conversation_widgets.keys()):
            if conv_id not in current_conv_ids:
                self._conversation_widgets[conv_id]["card"].destroy()
                self._conversation_widgets.pop(conv_id, None)

        if not self._conversation_cache:
            if not (self._empty_label and self._empty_label.winfo_exists()):
                self._empty_label = ctk.CTkLabel(
                    self.list_frame, text="No conversations found.",
                    text_color=SUB_TEXT_COLOR, font=get_font(size=13)
                )
            self._empty_label.pack(pady=32)
            return
        elif self._empty_label and self._empty_label.winfo_exists():
            self._empty_label.pack_forget()

        for item in self._conversation_cache:
            conv_id = self._read_item(item, "id")
            if not conv_id:
                continue
            if conv_id in self._conversation_widgets:
                widgets = self._conversation_widgets[conv_id]
                self._update_conversation_item(item, widgets)
                card = widgets["card"]
                card.pack_forget()
                card.pack(fill="x", padx=0, pady=0)
            else:
                self._conversation_widgets[conv_id] = self._create_conversation_item(item, conv_id)

    def _create_conversation_item(self, item: Any, conv_id: str) -> dict:
        name    = self._read_item(item, "contact_name", "Unknown") or "Unknown"
        phone   = self._read_item(item, "contact_phone", "") or ""
        preview = self._read_item(item, "last_message_preview", "") or ""
        unread  = self._read_item(item, "unread_count", 0) or 0
        status  = self._read_item(item, "status", "OPEN") or "OPEN"
        ts      = self._read_item(item, "last_message_at", "") or self._read_item(item, "updated_at", "") or ""
        if ts and "T" in ts:
            ts = ts.split("T")[1][:5]  # "14:32"

        is_selected = (conv_id == self.selected_conversation_id)
        bg = HOVER_COLOR if is_selected else "transparent"

        # Outer card — full width, no horizontal margin, thin bottom border
        card = ctk.CTkFrame(self.list_frame, fg_color=bg, corner_radius=0)
        card.pack(fill="x", padx=0, pady=0)

        # Left accent bar (visible when selected)
        accent_bar = ctk.CTkFrame(card, fg_color=ACCENT_COLOR if is_selected else "transparent", width=4, corner_radius=0)
        accent_bar.pack(side="left", fill="y", padx=0)

        # Inner content frame
        content = ctk.CTkFrame(card, fg_color="transparent")
        content.pack(side="left", fill="both", expand=True, padx=(10, 12), pady=10)
        content.grid_columnconfigure(0, weight=1)

        # ── Top row: avatar + name + timestamp ────────────────────────────────
        top_row = ctk.CTkFrame(content, fg_color="transparent")
        top_row.pack(fill="x")

        # Avatar circle
        initial = (name[0].upper() if name else "?")
        avatar = ctk.CTkLabel(
            top_row, text=initial,
            width=38, height=38, corner_radius=19,
            fg_color=get_avatar_color(name),
            text_color="#ffffff",
            font=get_font(size=14, weight="bold")
        )
        avatar.pack(side="left", padx=(0, 10))

        # Name + phone
        name_frame = ctk.CTkFrame(top_row, fg_color="transparent")
        name_frame.pack(side="left", fill="x", expand=True)

        name_label = ctk.CTkLabel(
            name_frame,
            text=name,
            font=get_font(size=14, weight="bold"),
            text_color=TEXT_COLOR, anchor="w"
        )
        name_label.pack(fill="x", anchor="w")

        phone_label = ctk.CTkLabel(
            name_frame, text=phone,
            font=get_font(size=11),
            text_color=SUB_TEXT_COLOR, anchor="w"
        )
        phone_label.pack(fill="x", anchor="w")

        # Timestamp (top-right)
        ts_label = ctk.CTkLabel(
            top_row, text=ts,
            font=get_font(size=11),
            text_color=SUB_TEXT_COLOR
        )
        ts_label.pack(side="right", anchor="n", pady=(2, 0))

        # ── Preview row ───────────────────────────────────────────────────────
        preview_text = preview[:72] + "…" if len(preview) > 72 else (preview or "No messages yet")
        preview_label = ctk.CTkLabel(
            content, text=preview_text,
            font=get_font(size=12),
            text_color=SUB_TEXT_COLOR, anchor="w",
            wraplength=240
        )
        preview_label.pack(fill="x", pady=(4, 0))

        # ── Bottom row: status badge + unread bubble ───────────────────────────
        bottom_row = ctk.CTkFrame(content, fg_color="transparent")
        bottom_row.pack(fill="x", pady=(6, 0))

        status_color = get_status_color(status)
        status_badge = ctk.CTkLabel(
            bottom_row, text=f"  {status}  ",
            font=get_font(size=10, weight="bold"),
            fg_color="transparent",
            text_color=status_color,
            corner_radius=4, height=18
        )
        status_badge.pack(side="left")

        unread_label = None
        if unread and unread > 0:
            unread_label = ctk.CTkLabel(
                bottom_row, text=str(unread),
                font=get_font(size=10, weight="bold"),
                fg_color=ACCENT_COLOR,
                text_color="#ffffff",
                corner_radius=10, width=20, height=20
            )
            unread_label.pack(side="right")

        # Label chips container
        labels_frame = ctk.CTkFrame(content, fg_color="transparent")
        labels_frame.pack(fill="x", pady=(4, 0))

        # Divider line at bottom
        div = ctk.CTkFrame(card, fg_color=DIVIDER_COLOR, height=1)
        div.pack(fill="x", side="bottom")

        # ── Click bindings ────────────────────────────────────────────────────
        _click = lambda _e, cid=conv_id: self._select_conversation(cid)
        for widget in [card, content, top_row, name_frame, name_label, phone_label,
                        preview_label, bottom_row, status_badge, accent_bar, labels_frame]:
            widget.bind("<Button-1>", _click)
        if unread_label:
            unread_label.bind("<Button-1>", _click)

        return {
            "card":         card,
            "bottom_row":   bottom_row,
            "accent_bar":   accent_bar,
            "name_label":   name_label,
            "phone_label":  phone_label,
            "preview_label": preview_label,
            "status_badge": status_badge,
            "ts_label":     ts_label,
            "unread_label": unread_label,
            "labels_frame": labels_frame,
        }

    def _update_conversation_item(self, item: Any, widgets: dict):
        conv_id = self._read_item(item, "id")
        name    = self._read_item(item, "contact_name", "Unknown") or "Unknown"
        phone   = self._read_item(item, "contact_phone", "") or ""
        preview = self._read_item(item, "last_message_preview", "") or ""
        unread  = self._read_item(item, "unread_count", 0) or 0
        status  = self._read_item(item, "status", "OPEN") or "OPEN"
        ts      = self._read_item(item, "last_message_at", "") or self._read_item(item, "updated_at", "") or ""
        if ts and "T" in ts:
            ts = ts.split("T")[1][:5]

        is_selected = (conv_id == self.selected_conversation_id)
        status_color = get_status_color(status)

        widgets["card"].configure(fg_color=HOVER_COLOR if is_selected else "transparent")
        widgets["accent_bar"].configure(fg_color=ACCENT_COLOR if is_selected else "transparent")
        widgets["name_label"].configure(text=name)
        widgets["phone_label"].configure(text=phone)
        preview_text = preview[:72] + "…" if len(preview) > 72 else (preview or "No messages yet")
        widgets["preview_label"].configure(text=preview_text)
        widgets["ts_label"].configure(text=ts)
        widgets["status_badge"].configure(
            text=f"  {status}  ",
            fg_color="transparent",
            text_color=status_color
        )

        # Render Labels
        labels = self._read_item(item, "labels", []) or []
        label_frame = widgets.get("labels_frame")
        if label_frame:
            for child in label_frame.winfo_children():
                child.destroy()
            
            for label in labels:
                name = label.get("name", "Label") if isinstance(label, dict) else str(label)
                l_color = label.get("color", "#7c3aed") if isinstance(label, dict) else "#7c3aed"
                
                chip = ctk.CTkLabel(
                    label_frame, text=f" {name} ",
                    font=get_font(size=9, weight="bold"),
                    fg_color=l_color, text_color="#ffffff",
                    corner_radius=4, height=14
                )
                chip.pack(side="left", padx=(0, 4))

        unread_widget = widgets.get("unread_label")
        if unread_widget:
            if unread and unread > 0:
                unread_widget.configure(text=str(unread))
                unread_widget.pack(side="right")
            else:
                unread_widget.pack_forget()
        elif unread and unread > 0:
            bottom_row = widgets.get("bottom_row")
            if bottom_row:
                unread_widget = ctk.CTkLabel(
                    bottom_row,
                    text=str(unread),
                    font=get_font(size=10, weight="bold"),
                    fg_color=ACCENT_COLOR,
                    text_color="#ffffff",
                    corner_radius=10,
                    width=20,
                    height=20,
                )
                unread_widget.pack(side="right")
                unread_widget.bind("<Button-1>", lambda _e, cid=conv_id: self._select_conversation(cid))
                widgets["unread_label"] = unread_widget

    # ── Conversation Selection ─────────────────────────────────────────────────

    def _find_conversation(self, conversation_id: str) -> Optional[Any]:
        for row in self._conversation_cache:
            if self._read_item(row, "id") == conversation_id:
                return row
        return None

    def _select_conversation(self, conversation_id: str):
        row = self._find_conversation(conversation_id)
        if not row:
            return
        self.selected_conversation_id = conversation_id
        self.refresh_conversations()
        name     = self._read_item(row, "contact_name", "Unknown") or "Unknown"
        phone    = self._read_item(row, "contact_phone", "") or ""
        status   = self._read_item(row, "status", "OPEN") or "OPEN"
        assignee = self._read_item(row, "assigned_user_id", None) or ""

        # Update action bar
        self.selection_label.configure(
            text=f"{name}  |  {phone}",
            text_color=TEXT_COLOR
        )
        self.conv_status_var.set(status)
        self._sync_status_badge_color(status)
        self.assign_entry.delete(0, "end")
        if assignee:
            self.assign_entry.insert(0, assignee)

        last_ts  = self._read_item(row, "last_message_at", "") or self._read_item(row, "updated_at", "") or ""
        labels   = self._read_item(row, "labels", []) or []

        self.chat_frame.set_conversation(
            conversation_id,
            f"{name}  ({phone})",
            f"{status}",
            last_message_at=last_ts,
            labels=labels
        )
        if self.on_conversation_select_cb:
            self.on_conversation_select_cb(conversation_id)

    def _on_assign(self):
        if not self.selected_conversation_id or not self.on_assign_cb:
            return
        target = self.assign_entry.get().strip() or None
        self.selection_label.configure(text="Assigning...", text_color=ACCENT_COLOR)
        
        def _done(result):
            self.selection_label.configure(text=f"Assigned to {target or 'nobody'}", text_color=TEXT_COLOR)
            self.refresh_conversations()

        try:
            self.on_assign_cb(self.selected_conversation_id, target, _done)
        except Exception as e:
            self.selection_label.configure(text=f"Assign failed: {e}", text_color=ERROR_COLOR)

    def _on_status_change(self, new_status: str):
        if not self.selected_conversation_id or not self.on_update_status_cb:
            return
        self._sync_status_badge_color(new_status)
        self.selection_label.configure(text=f"Updating status to {new_status}...", text_color=ACCENT_COLOR)
        
        def _done(result):
            self.selection_label.configure(text=f"Status: {new_status}", text_color=TEXT_COLOR)
            self.refresh_conversations()

        try:
            self.on_update_status_cb(self.selected_conversation_id, new_status, _done)
        except Exception as e:
            self.selection_label.configure(text=f"Status failed: {e}", text_color=ERROR_COLOR)
