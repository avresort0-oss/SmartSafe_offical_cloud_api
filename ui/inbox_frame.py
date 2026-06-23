# -*- coding: utf-8 -*-
import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox
import logging
from typing import Any, Callable, List, Optional

from services.user_service import UserResponseDTO
from services.workspace_service import WorkspaceDTO
from ui.chat_frame import ChatFrame
from ui.components.chat.contact_info_panel import ContactInfoPanel


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
        load_conversations_cb: Callable[[str, Optional[str], Optional[str], Optional[str], bool, Optional[str], bool], List[Any]],
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
        archive_conversation_cb: Optional[Callable[[str, Optional[Callable]], Any]] = None,
        unarchive_conversation_cb: Optional[Callable[[str, Optional[Callable]], Any]] = None,
        pin_conversation_cb: Optional[Callable[[str, Optional[Callable]], Any]] = None,
        unpin_conversation_cb: Optional[Callable[[str, Optional[Callable]], Any]] = None,
        mute_conversation_cb: Optional[Callable[[str, Optional[Callable]], Any]] = None,
        unmute_conversation_cb: Optional[Callable[[str, Optional[Callable]], Any]] = None,
        delete_conversation_cb: Optional[Callable[[str, Optional[Callable]], Any]] = None,
        load_contacts_cb: Optional[Callable[[], List[Any]]] = None,
        start_conversation_cb: Optional[Callable[[str, Optional[Callable]], Any]] = None,
        get_contact_for_conversation_cb: Optional[Callable[[str], Any]] = None,
        load_starred_messages_cb: Optional[Callable[[], List[Any]]] = None,
        mark_read_conversation_cb: Optional[Callable[[str, Optional[Callable]], Any]] = None,
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
        self.archive_conversation_cb = archive_conversation_cb
        self.unarchive_conversation_cb = unarchive_conversation_cb
        self.pin_conversation_cb = pin_conversation_cb
        self.unpin_conversation_cb = unpin_conversation_cb
        self.mute_conversation_cb = mute_conversation_cb
        self.unmute_conversation_cb = unmute_conversation_cb
        self.delete_conversation_cb = delete_conversation_cb
        self.load_contacts_cb = load_contacts_cb
        self.start_conversation_cb = start_conversation_cb
        self.get_contact_for_conversation_cb = get_contact_for_conversation_cb
        self.load_starred_messages_cb = load_starred_messages_cb
        self.mark_read_conversation_cb = mark_read_conversation_cb

        self.selected_conversation_id: Optional[str] = None
        self._conversation_cache: List[Any] = []
        self._meta_accounts: List[Any] = []
        self._selected_meta_account_id: Optional[str] = None
        self._conversation_widgets = {}
        self._starred_widgets: List[Any] = []
        self._empty_label = None
        self._is_loading = False
        self._selection_mode: bool = False
        self._bulk_selected_ids: set = set()

        # WhatsApp-style quick filters
        self._active_tab: str = "All"               # "All" | "Unread" | "Archived"
        self._selected_label: Optional[Any] = None   # currently active label chip (DTO/dict)
        self._label_chip_widgets: dict = {}
        self._filters_visible: bool = False

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
        archive_conversation_cb=None,
        unarchive_conversation_cb=None,
        pin_conversation_cb=None,
        unpin_conversation_cb=None,
        mute_conversation_cb=None,
        unmute_conversation_cb=None,
        delete_conversation_cb=None,
        load_contacts_cb=None,
        start_conversation_cb=None,
        get_contact_for_conversation_cb=None,
        load_starred_messages_cb=None,
        mark_read_conversation_cb=None,
    ):
        self.load_conversations_cb = load_conversations_cb
        self.on_conversation_select_cb = on_conversation_select_cb
        self.on_assign_cb = on_assign_cb
        self.on_update_status_cb = on_update_status_cb
        self.load_labels_cb = load_labels_cb
        self.attach_label_cb = attach_label_cb
        self.detach_label_cb = detach_label_cb
        self.create_contract_cb = create_contract_cb
        self.archive_conversation_cb = archive_conversation_cb
        self.unarchive_conversation_cb = unarchive_conversation_cb
        self.pin_conversation_cb = pin_conversation_cb
        self.unpin_conversation_cb = unpin_conversation_cb
        self.mute_conversation_cb = mute_conversation_cb
        self.unmute_conversation_cb = unmute_conversation_cb
        self.delete_conversation_cb = delete_conversation_cb
        self.load_contacts_cb = load_contacts_cb
        self.start_conversation_cb = start_conversation_cb
        self.get_contact_for_conversation_cb = get_contact_for_conversation_cb
        self.load_starred_messages_cb = load_starred_messages_cb
        self.mark_read_conversation_cb = mark_read_conversation_cb

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
        self._hide_contact_info_panel()
        self.chat_frame.refresh_workspace(workspace)
        self.chat_frame.set_conversation(None, "Select a conversation", "idle")
        if self.get_accounts_cb:
            self._meta_accounts = self.get_accounts_cb()
            accounts = ["All Profiles"] + [acc.display_name for acc in self._meta_accounts]
            self.profile_menu.configure(values=accounts)
            self.profile_var.set("All Profiles")
            self._selected_meta_account_id = None
        self._selected_label = None
        self.tab_var.set("All")
        self._active_tab = "All"
        self._refresh_label_chips()
        self.refresh_conversations()

    # ── Left Panel ─────────────────────────────────────────────────────────────

    def _build_left_panel(self):
        self.left_panel = ctk.CTkFrame(self, fg_color=HEADER_FOOTER_COLOR, corner_radius=0, width=340)
        self.left_panel.grid(row=0, column=0, sticky="nsew")
        self.left_panel.grid_propagate(False)
        self.left_panel.grid_rowconfigure(6, weight=1)   # list_frame is row 6
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

        new_chat_btn = ctk.CTkButton(
            header_frame, text="+", width=32, height=32,
            fg_color=SURFACE_COLOR, hover_color="#2a3942",
            corner_radius=8, font=get_font(size=18, weight="bold"),
            command=self._open_new_chat_dialog
        )
        new_chat_btn.grid(row=0, column=1, sticky="e", padx=(0, 6))

        self.filters_toggle_btn = ctk.CTkButton(
            header_frame, text="⚙", width=32, height=32,
            fg_color=SURFACE_COLOR, hover_color="#2a3942",
            corner_radius=8, font=get_font(size=15),
            command=self._toggle_advanced_filters
        )
        self.filters_toggle_btn.grid(row=0, column=2, sticky="e", padx=(0, 6))

        refresh_btn = ctk.CTkButton(
            header_frame, text="↺", width=32, height=32,
            fg_color=SURFACE_COLOR, hover_color="#2a3942",
            corner_radius=8, font=get_font(size=16),
            command=self.refresh_conversations
        )
        refresh_btn.grid(row=0, column=3, sticky="e", padx=(0, 6))

        self.select_toggle_btn = ctk.CTkButton(
            header_frame, text="☑", width=32, height=32,
            fg_color=SURFACE_COLOR, hover_color="#2a3942",
            corner_radius=8, font=get_font(size=15),
            command=self._toggle_selection_mode
        )
        self.select_toggle_btn.grid(row=0, column=4, sticky="e")

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

        # ── Quick-Filter Tabs (All / Unread / Archived) ────────────────────────
        self.tab_var = ctk.StringVar(value="All")
        self.tab_segmented = ctk.CTkSegmentedButton(
            self.left_panel,
            values=["All", "Unread", "Archived", "Starred"],
            variable=self.tab_var,
            command=self._on_tab_change,
            fg_color=INPUT_COLOR,
            selected_color=ACCENT_COLOR,
            selected_hover_color=ACCENT_HOVER,
            unselected_color=INPUT_COLOR,
            unselected_hover_color=HOVER_COLOR,
            text_color=TEXT_COLOR,
            font=get_font(size=12, weight="bold"),
            height=34,
        )
        self.tab_segmented.grid(row=2, column=0, sticky="ew", padx=12, pady=(0, 10))

        # ── Bulk Selection Action Bar (replaces tabs while selecting) ───────────
        self.bulk_action_bar = ctk.CTkFrame(self.left_panel, fg_color=INPUT_COLOR, corner_radius=10, height=34)
        self.bulk_action_bar.grid_propagate(False)

        cancel_btn = ctk.CTkButton(
            self.bulk_action_bar, text="✕", width=26, height=26,
            fg_color="transparent", hover_color=HOVER_COLOR,
            text_color=SUB_TEXT_COLOR, corner_radius=4,
            font=get_font(size=12), command=self._toggle_selection_mode
        )
        cancel_btn.pack(side="left", padx=(6, 4), pady=4)

        self.bulk_count_label = ctk.CTkLabel(
            self.bulk_action_bar, text="0 selected",
            font=get_font(size=12, weight="bold"), text_color=TEXT_COLOR
        )
        self.bulk_count_label.pack(side="left", padx=4)

        ctk.CTkButton(
            self.bulk_action_bar, text="Mark read", width=70, height=26,
            fg_color="transparent", hover_color=HOVER_COLOR,
            text_color=ACCENT_COLOR, corner_radius=4,
            font=get_font(size=11, weight="bold"), command=self._bulk_mark_read
        ).pack(side="right", padx=(0, 6), pady=4)
        ctk.CTkButton(
            self.bulk_action_bar, text="Archive", width=60, height=26,
            fg_color="transparent", hover_color=HOVER_COLOR,
            text_color=ACCENT_COLOR, corner_radius=4,
            font=get_font(size=11, weight="bold"), command=self._bulk_archive
        ).pack(side="right", padx=(0, 4), pady=4)
        ctk.CTkButton(
            self.bulk_action_bar, text="Delete", width=60, height=26,
            fg_color="transparent", hover_color=HOVER_COLOR,
            text_color=ERROR_COLOR, corner_radius=4,
            font=get_font(size=11, weight="bold"), command=self._bulk_delete
        ).pack(side="right", padx=(0, 4), pady=4)

        # ── Label Chips (horizontally scrollable) ──────────────────────────────
        self.label_chip_row = ctk.CTkScrollableFrame(
            self.left_panel, fg_color="transparent", height=40,
            orientation="horizontal",
            scrollbar_button_color=SURFACE_COLOR,
            scrollbar_button_hover_color="#2a3942",
        )
        self.label_chip_row.grid(row=3, column=0, sticky="ew", padx=8, pady=(0, 6))

        # ── Advanced Filters (collapsible — Status / Assignee / Profile) ───────
        self.adv_filters_frame = ctk.CTkFrame(self.left_panel, fg_color="transparent")
        self.adv_filters_frame.grid_columnconfigure(0, weight=1)
        self.adv_filters_frame.grid(row=4, column=0, sticky="ew", padx=12, pady=(0, 10))
        self.adv_filters_frame.grid_remove()  # hidden by default — toggled via ⚙

        adv_row = ctk.CTkFrame(self.adv_filters_frame, fg_color="transparent")
        adv_row.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        adv_row.grid_columnconfigure((0, 1), weight=1)

        self.status_var = ctk.StringVar(value="ALL")
        self.status_menu = ctk.CTkOptionMenu(
            adv_row,
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
        self.status_menu.grid(row=0, column=0, sticky="ew", padx=(0, 4))

        self.assignee_entry = ctk.CTkEntry(
            adv_row, placeholder_text="Assignee",
            fg_color=INPUT_COLOR, border_width=0,
            text_color=TEXT_COLOR, placeholder_text_color=SUB_TEXT_COLOR,
            corner_radius=10, height=34, font=ctk.CTkFont(size=12)
        )
        self.assignee_entry.grid(row=0, column=1, sticky="ew", padx=(4, 0))
        self.assignee_entry.bind("<Return>", lambda _e: self.refresh_conversations())

        # ── Profile Dropdown ──────────────────────────────────────────────────
        self.profile_var = ctk.StringVar(value="All Profiles")
        self.profile_menu = ctk.CTkOptionMenu(
            self.adv_filters_frame,
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
        self.profile_menu.grid(row=1, column=0, sticky="ew")

        # ── Divider ───────────────────────────────────────────────────────────
        divider = ctk.CTkFrame(self.left_panel, fg_color=DIVIDER_COLOR, height=1)
        divider.grid(row=5, column=0, sticky="ew", padx=0, pady=(0, 0))

        # ── Conversation List ─────────────────────────────────────────────────
        self.list_frame = ctk.CTkScrollableFrame(
            self.left_panel, fg_color="transparent",
            scrollbar_button_color=SURFACE_COLOR,
            scrollbar_button_hover_color="#2a3942",
        )
        self.list_frame.grid(row=6, column=0, sticky="nsew", padx=0, pady=0)
        self.list_frame.grid_columnconfigure(0, weight=1)

        # Loading Indicator (Overlay-ish via pack)
        self._loading_label = ctk.CTkLabel(
            self.list_frame, text="Loading conversations...",
            font=get_font(size=13, weight="bold"),
            text_color=ACCENT_COLOR
        )
        # Initially hidden

        self._refresh_label_chips()

    def _toggle_advanced_filters(self):
        self._filters_visible = not self._filters_visible
        if self._filters_visible:
            self.adv_filters_frame.grid()
            self.filters_toggle_btn.configure(fg_color=ACCENT_COLOR)
        else:
            self.adv_filters_frame.grid_remove()
            self.filters_toggle_btn.configure(fg_color=SURFACE_COLOR)

    def _on_tab_change(self, value: str):
        self._active_tab = value
        if value == "Starred":
            for conv_id in list(self._conversation_widgets.keys()):
                self._conversation_widgets[conv_id]["card"].destroy()
            self._conversation_widgets = {}
        else:
            for card in self._starred_widgets:
                if card.winfo_exists():
                    card.destroy()
            self._starred_widgets = []
        if self._empty_label is not None and self._empty_label.winfo_exists():
            self._empty_label.pack_forget()
        self.refresh_conversations()

    # ── Bulk Multi-Select ────────────────────────────────────────────────────────

    def _toggle_selection_mode(self):
        self._selection_mode = not self._selection_mode
        self._bulk_selected_ids = set()
        self._update_bulk_count_label()

        if self._selection_mode:
            self.tab_segmented.grid_remove()
            self.bulk_action_bar.grid(row=2, column=0, sticky="ew", padx=12, pady=(0, 10))
            self.select_toggle_btn.configure(fg_color=ACCENT_COLOR)
        else:
            self.bulk_action_bar.grid_remove()
            self.tab_segmented.grid(row=2, column=0, sticky="ew", padx=12, pady=(0, 10))
            self.select_toggle_btn.configure(fg_color=SURFACE_COLOR)

        # Force a clean rebuild so cards show/hide their checkboxes.
        for conv_id in list(self._conversation_widgets.keys()):
            self._conversation_widgets[conv_id]["card"].destroy()
        self._conversation_widgets = {}
        self.refresh_conversations()

    def _update_bulk_count_label(self):
        count = len(self._bulk_selected_ids)
        self.bulk_count_label.configure(text=f"{count} selected")

    def _on_bulk_checkbox_toggle(self, conv_id: str, var: "ctk.BooleanVar"):
        if var.get():
            self._bulk_selected_ids.add(conv_id)
        else:
            self._bulk_selected_ids.discard(conv_id)
        self._update_bulk_count_label()

    def _run_bulk_action(self, action_cb: Callable):
        ids = list(self._bulk_selected_ids)
        remaining = len(ids)
        finished = False

        def _finish_once():
            nonlocal finished
            if not finished:
                finished = True
                self._toggle_selection_mode()

        if remaining == 0:
            _finish_once()
            return

        def _one_done(_result):
            nonlocal remaining
            remaining -= 1
            if remaining <= 0:
                _finish_once()

        for conv_id in ids:
            try:
                action_cb(conv_id, _one_done)
            except Exception as e:
                logger.error(f"Bulk action failed for {conv_id}: {e}")
                remaining -= 1
        if remaining <= 0:
            _finish_once()

    def _bulk_archive(self):
        if not self._bulk_selected_ids or not self.archive_conversation_cb:
            return
        self._run_bulk_action(self.archive_conversation_cb)

    def _bulk_delete(self):
        if not self._bulk_selected_ids or not self.delete_conversation_cb:
            return
        count = len(self._bulk_selected_ids)
        if not messagebox.askyesno("Delete chats", f"Delete {count} selected chat(s)? This cannot be undone from the app."):
            return
        self._run_bulk_action(self.delete_conversation_cb)

    def _bulk_mark_read(self):
        if not self._bulk_selected_ids or not self.mark_read_conversation_cb:
            return
        self._run_bulk_action(self.mark_read_conversation_cb)

    # ── New Chat / Compose ──────────────────────────────────────────────────────

    def _open_new_chat_dialog(self):
        if not self.load_contacts_cb:
            return

        dialog = ctk.CTkToplevel(self)
        dialog.title("New chat")
        dialog.geometry("360x480")
        dialog.configure(fg_color=HEADER_FOOTER_COLOR)
        dialog.transient(self.winfo_toplevel())
        dialog.grab_set()

        search_entry = ctk.CTkEntry(
            dialog, placeholder_text="🔍   Search contacts…",
            fg_color=INPUT_COLOR, border_width=0,
            text_color=TEXT_COLOR, placeholder_text_color=SUB_TEXT_COLOR,
            corner_radius=10, height=36, font=get_font(size=13)
        )
        search_entry.pack(fill="x", padx=12, pady=(12, 8))

        contact_list_frame = ctk.CTkScrollableFrame(dialog, fg_color="transparent")
        contact_list_frame.pack(fill="both", expand=True, padx=8, pady=(0, 12))

        try:
            contacts = self.load_contacts_cb() or []
        except Exception as e:
            logger.error(f"Error loading contacts: {e}")
            contacts = []

        def _render(filter_text: str = ""):
            for child in contact_list_frame.winfo_children():
                child.destroy()
            term = filter_text.strip().lower()
            visible = 0
            for contact in contacts:
                name = self._read_item(contact, "display_name", "Unknown") or "Unknown"
                phone = self._read_item(contact, "phone_e164", "") or ""
                if term and term not in name.lower() and term not in phone.lower():
                    continue
                visible += 1

                row = ctk.CTkFrame(contact_list_frame, fg_color="transparent")
                row.pack(fill="x", pady=2)

                avatar = ctk.CTkLabel(
                    row, text=(name[0].upper() if name else "?"),
                    width=34, height=34, corner_radius=17,
                    fg_color=get_avatar_color(name), text_color="#ffffff",
                    font=get_font(size=13, weight="bold")
                )
                avatar.pack(side="left", padx=(6, 10), pady=4)

                text_frame = ctk.CTkFrame(row, fg_color="transparent")
                text_frame.pack(side="left", fill="x", expand=True)
                ctk.CTkLabel(text_frame, text=name, font=get_font(size=13, weight="bold"), text_color=TEXT_COLOR, anchor="w").pack(fill="x", anchor="w")
                ctk.CTkLabel(text_frame, text=phone, font=get_font(size=11), text_color=SUB_TEXT_COLOR, anchor="w").pack(fill="x", anchor="w")

                contact_id = self._read_item(contact, "id")
                _click = lambda _e, cid=contact_id: self._start_new_conversation(cid, dialog)
                for w in (row, avatar, text_frame):
                    w.bind("<Button-1>", _click)

            if visible == 0:
                ctk.CTkLabel(contact_list_frame, text="No contacts found.", text_color=SUB_TEXT_COLOR, font=get_font(size=12)).pack(pady=20)

        search_entry.bind("<KeyRelease>", lambda _e: _render(search_entry.get()))
        _render()

    def _start_new_conversation(self, contact_id: Optional[str], dialog: "ctk.CTkToplevel"):
        dialog.destroy()
        if not contact_id or not self.start_conversation_cb:
            return

        def _done(result):
            if not result:
                return
            new_conv_id = self._read_item(result, "id")
            if new_conv_id:
                self.refresh_conversations(on_done=lambda: self._select_conversation(new_conv_id))

        try:
            self.start_conversation_cb(contact_id, _done)
        except Exception as e:
            logger.error(f"Start conversation failed: {e}")

    # ── Label Chips ────────────────────────────────────────────────────────────

    def _refresh_label_chips(self):
        for child in self.label_chip_row.winfo_children():
            child.destroy()
        self._label_chip_widgets = {}

        if not self.load_labels_cb:
            return
        try:
            labels = self.load_labels_cb() or []
        except Exception as e:
            logger.error(f"Error loading labels: {e}")
            return

        for label in labels:
            label_id = self._read_item(label, "id")
            name = self._read_item(label, "name", "Label") or "Label"
            color = self._read_item(label, "color_hex", "#7c3aed") or "#7c3aed"
            if not label_id:
                continue
            is_selected = bool(self._selected_label) and self._read_item(self._selected_label, "id") == label_id
            chip = ctk.CTkButton(
                self.label_chip_row, text=name,
                height=26, corner_radius=13,
                fg_color=color if is_selected else "transparent",
                hover_color=color,
                border_width=1, border_color=color,
                text_color="#ffffff" if is_selected else color,
                font=get_font(size=11, weight="bold"),
                command=lambda l=label: self._on_label_chip_click(l),
            )
            chip.pack(side="left", padx=(0, 6), pady=4)
            self._label_chip_widgets[label_id] = chip

    def _on_label_chip_click(self, label: Any):
        label_id = self._read_item(label, "id")
        current_id = self._read_item(self._selected_label, "id") if self._selected_label else None
        self._selected_label = None if current_id == label_id else label
        self._refresh_label_chips()
        self.refresh_conversations()

    # ── Right Panel ────────────────────────────────────────────────────────────

    def _build_right_panel(self, load_messages_cb, send_message_cb, delete_message_cb, toggle_star_cb, load_quick_replies_cb=None):
        self.right_panel = ctk.CTkFrame(self, fg_color=BG_COLOR, corner_radius=0)
        self.right_panel.grid(row=0, column=1, sticky="nsew")
        self.right_panel.grid_rowconfigure(1, weight=1)
        self.right_panel.grid_columnconfigure(0, weight=1)
        self.right_panel.grid_columnconfigure(1, weight=0)

        # ── Action / Info Bar (Premium Header) ────────────────────────────────
        self.action_bar = ctk.CTkFrame(self.right_panel, fg_color=HEADER_FOOTER_COLOR, corner_radius=0, height=62)
        self.action_bar.grid(row=0, column=0, sticky="ew")
        self.action_bar.grid_propagate(False)
        self.action_bar.grid_columnconfigure(0, weight=1)
        self.action_bar.grid_columnconfigure(1, weight=0)
        self.action_bar.grid_columnconfigure(2, weight=0)
        self.action_bar.grid_columnconfigure(3, weight=0)
        self.action_bar.grid_columnconfigure(4, weight=0)

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
        assign_btn.grid(row=0, column=3, padx=5, pady=13)

        self.more_options_btn = ctk.CTkButton(
            self.action_bar, text="⋮", width=34, height=34,
            fg_color="transparent", hover_color=HOVER_COLOR,
            text_color=TEXT_COLOR,
            corner_radius=17, font=get_font(size=16, weight="bold"),
            command=self._show_action_bar_menu
        )
        self.more_options_btn.grid(row=0, column=4, padx=(0, 20), pady=13)

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

        # ── Contact Info Side Panel (hidden by default) ─────────────────────────
        self.contact_info_panel = ContactInfoPanel(self.right_panel, on_close=self._hide_contact_info_panel)
        self.contact_info_panel.grid(row=0, column=1, rowspan=2, sticky="nsew")
        self.contact_info_panel.grid_remove()
        self._contact_info_visible = False

        for widget in (self.chat_frame.chat_header.avatar_label, self.chat_frame.chat_header.title_label):
            widget.configure(cursor="hand2")
            widget.bind("<Button-1>", lambda _e: self._toggle_contact_info_panel())

    # ── Contact Info Panel ───────────────────────────────────────────────────────

    def _toggle_contact_info_panel(self):
        if self._contact_info_visible:
            self._hide_contact_info_panel()
            return
        if not self.selected_conversation_id or not self.get_contact_for_conversation_cb:
            return

        try:
            contact = self.get_contact_for_conversation_cb(self.selected_conversation_id)
        except Exception as e:
            logger.error(f"Error loading contact info: {e}")
            return
        if not contact:
            return

        row = self._find_conversation(self.selected_conversation_id)
        labels = self._read_item(row, "labels", []) or [] if row else []
        self.contact_info_panel.set_contact(contact, labels=labels, read_item=self._read_item)
        self.contact_info_panel.grid()
        self._contact_info_visible = True

    def _hide_contact_info_panel(self):
        self.contact_info_panel.grid_remove()
        self._contact_info_visible = False

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

    def refresh_conversations(self, on_done: Optional[Callable] = None):
        if self._is_loading:
            return

        self._is_loading = True
        if self._loading_label is not None:
            self._loading_label.pack(pady=20)
        if self._empty_label is not None and self._empty_label.winfo_exists():
            self._empty_label.pack_forget()

        import threading

        if self._active_tab == "Starred":
            def _worker_starred():
                try:
                    rows = self.load_starred_messages_cb() if self.load_starred_messages_cb else []
                    self.after(0, lambda: self._finalize_starred_refresh(rows, on_done))
                except Exception as e:
                    logger.error(f"Error loading starred messages: {e}")
                    self.after(0, lambda: self._finalize_starred_refresh([], on_done))

            threading.Thread(target=_worker_starred, daemon=True).start()
            return

        status = self.status_var.get()
        status_filter = None if status == "ALL" else status
        search_query = self.search_entry.get().strip()
        assignee_filter = self.assignee_entry.get().strip() or None
        label_filter = self._read_item(self._selected_label, "name") if self._selected_label else None
        unread_only = (self._active_tab == "Unread")
        archived = (self._active_tab == "Archived")
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
                    archived,
                )
                self.after(0, lambda: self._finalize_refresh(rows, on_done))
            except Exception as e:
                logger.error(f"Error loading conversations: {e}")
                self.after(0, lambda: self._finalize_refresh([], on_done))

        threading.Thread(target=_worker, daemon=True).start()

    def _finalize_refresh(self, rows, on_done: Optional[Callable] = None):
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
            if on_done:
                on_done()
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

        if on_done:
            on_done()

    # ── Starred Messages View ────────────────────────────────────────────────────

    def _finalize_starred_refresh(self, rows, on_done: Optional[Callable] = None):
        self._is_loading = False
        self._loading_label.pack_forget()

        for card in self._starred_widgets:
            if card.winfo_exists():
                card.destroy()
        self._starred_widgets = []

        self._conversation_cache = rows or []

        if not self._conversation_cache:
            if not (self._empty_label and self._empty_label.winfo_exists()):
                self._empty_label = ctk.CTkLabel(
                    self.list_frame, text="No starred messages.",
                    text_color=SUB_TEXT_COLOR, font=get_font(size=13)
                )
            self._empty_label.pack(pady=32)
        else:
            if self._empty_label and self._empty_label.winfo_exists():
                self._empty_label.pack_forget()
            for item in self._conversation_cache:
                self._create_starred_item(item)

        if on_done:
            on_done()

    def _create_starred_item(self, item: Any) -> None:
        msg_id  = self._read_item(item, "id")
        conv_id = self._read_item(item, "conversation_id")
        name    = self._read_item(item, "contact_name", "Unknown") or "Unknown"
        text    = self._read_item(item, "text", "") or ""
        ts      = self._read_item(item, "created_at", "") or ""
        if ts and "T" in ts:
            ts = ts.split("T")[1][:5]

        card = ctk.CTkFrame(self.list_frame, fg_color="transparent", corner_radius=0)
        card.pack(fill="x", padx=0, pady=0)
        self._starred_widgets.append(card)

        content = ctk.CTkFrame(card, fg_color="transparent")
        content.pack(fill="both", expand=True, padx=(10, 12), pady=10)

        top_row = ctk.CTkFrame(content, fg_color="transparent")
        top_row.pack(fill="x")

        avatar = ctk.CTkLabel(
            top_row, text=(name[0].upper() if name else "?"),
            width=32, height=32, corner_radius=16,
            fg_color=get_avatar_color(name), text_color="#ffffff",
            font=get_font(size=12, weight="bold")
        )
        avatar.pack(side="left", padx=(0, 8))

        name_label = ctk.CTkLabel(top_row, text=name, font=get_font(size=13, weight="bold"), text_color=TEXT_COLOR, anchor="w")
        name_label.pack(side="left", fill="x", expand=True)

        ts_label = ctk.CTkLabel(top_row, text=ts, font=get_font(size=10), text_color=SUB_TEXT_COLOR)
        ts_label.pack(side="right")

        preview = text[:90] + "…" if len(text) > 90 else (text or "")
        preview_label = ctk.CTkLabel(
            content, text=f"⭐ {preview}",
            font=get_font(size=12), text_color=SUB_TEXT_COLOR,
            anchor="w", wraplength=260, justify="left"
        )
        preview_label.pack(fill="x", pady=(4, 0), anchor="w")

        div = ctk.CTkFrame(card, fg_color=DIVIDER_COLOR, height=1)
        div.pack(fill="x", side="bottom")

        _click = lambda _e, cid=conv_id, mid=msg_id: self._open_starred_message(cid, mid)
        for widget in (card, content, top_row, avatar, name_label, preview_label):
            widget.bind("<Button-1>", _click)

    def _open_starred_message(self, conversation_id: Optional[str], msg_id: Optional[str]) -> None:
        if not conversation_id:
            return
        self.tab_var.set("All")
        self._active_tab = "All"
        self._selected_label = None
        self._refresh_label_chips()

        for card in self._starred_widgets:
            if card.winfo_exists():
                card.destroy()
        self._starred_widgets = []

        def _after_refresh():
            self._select_conversation(conversation_id)
            if msg_id:
                self.after(300, lambda: self.chat_frame.message_list.scroll_to(msg_id))
                self.after(300, lambda: self.chat_frame.message_list.highlight_message(msg_id))

        self.refresh_conversations(on_done=_after_refresh)

    def _create_conversation_item(self, item: Any, conv_id: str) -> dict:
        name    = self._read_item(item, "contact_name", "Unknown") or "Unknown"
        phone   = self._read_item(item, "contact_phone", "") or ""
        preview = self._read_item(item, "last_message_preview", "") or ""
        unread  = self._read_item(item, "unread_count", 0) or 0
        status  = self._read_item(item, "status", "OPEN") or "OPEN"
        is_pinned = bool(self._read_item(item, "is_pinned", False))
        is_muted  = bool(self._read_item(item, "is_muted", False))
        ts      = self._read_item(item, "last_message_at", "") or self._read_item(item, "updated_at", "") or ""
        if ts and "T" in ts:
            ts = ts.split("T")[1][:5]  # "14:32"
        display_name = f"📌 {name}" if is_pinned else name

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

        # Bulk-select checkbox (only rendered while selection mode is active)
        checkbox_var = ctk.BooleanVar(value=(conv_id in self._bulk_selected_ids))
        checkbox = ctk.CTkCheckBox(
            top_row, text="", width=20, height=20, checkbox_width=18, checkbox_height=18,
            variable=checkbox_var, fg_color=ACCENT_COLOR, hover_color=ACCENT_HOVER,
            border_color=SUB_TEXT_COLOR,
            command=lambda cid=conv_id, v=checkbox_var: self._on_bulk_checkbox_toggle(cid, v),
        )
        if self._selection_mode:
            checkbox.pack(side="left", padx=(0, 8))

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
            text=display_name,
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

        # "⋮" more-options menu (Pin / Mute / Archive / Delete)
        menu_btn = ctk.CTkButton(
            top_row, text="⋮", width=22, height=22,
            fg_color="transparent", hover_color=HOVER_COLOR,
            text_color=SUB_TEXT_COLOR, corner_radius=4,
            font=get_font(size=14, weight="bold")
        )
        menu_btn.pack(side="right", padx=(4, 0))
        menu_btn.bind("<Button-1>", lambda e, cid=conv_id: self._show_conversation_menu(e, cid))

        # Timestamp (top-right)
        ts_label = ctk.CTkLabel(
            top_row, text=ts,
            font=get_font(size=11),
            text_color=SUB_TEXT_COLOR
        )
        ts_label.pack(side="right", anchor="n", pady=(2, 0))

        # Mute indicator (only visible when muted)
        mute_icon = ctk.CTkLabel(
            top_row, text="🔇",
            font=get_font(size=11),
            text_color=SUB_TEXT_COLOR
        )
        if is_muted:
            mute_icon.pack(side="right", anchor="n", pady=(2, 0), padx=(0, 4))

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
        def _click(_e, cid=conv_id, var=checkbox_var):
            if self._selection_mode:
                var.set(not var.get())
                self._on_bulk_checkbox_toggle(cid, var)
            else:
                self._select_conversation(cid)

        for widget in [card, content, top_row, name_frame, name_label, phone_label,
                        preview_label, bottom_row, status_badge, accent_bar, labels_frame]:
            widget.bind("<Button-1>", _click)
        if unread_label:
            unread_label.bind("<Button-1>", _click)

        return {
            "card":         card,
            "bottom_row":   bottom_row,
            "checkbox":     checkbox,
            "checkbox_var": checkbox_var,
            "accent_bar":   accent_bar,
            "name_label":   name_label,
            "phone_label":  phone_label,
            "preview_label": preview_label,
            "status_badge": status_badge,
            "ts_label":     ts_label,
            "unread_label": unread_label,
            "labels_frame": labels_frame,
            "mute_icon":    mute_icon,
        }

    def _update_conversation_item(self, item: Any, widgets: dict):
        conv_id = self._read_item(item, "id")
        name    = self._read_item(item, "contact_name", "Unknown") or "Unknown"
        phone   = self._read_item(item, "contact_phone", "") or ""
        preview = self._read_item(item, "last_message_preview", "") or ""
        unread  = self._read_item(item, "unread_count", 0) or 0
        status  = self._read_item(item, "status", "OPEN") or "OPEN"
        is_pinned = bool(self._read_item(item, "is_pinned", False))
        is_muted  = bool(self._read_item(item, "is_muted", False))
        ts      = self._read_item(item, "last_message_at", "") or self._read_item(item, "updated_at", "") or ""
        if ts and "T" in ts:
            ts = ts.split("T")[1][:5]

        is_selected = (conv_id == self.selected_conversation_id)
        status_color = get_status_color(status)

        widgets["card"].configure(fg_color=HOVER_COLOR if is_selected else "transparent")
        widgets["accent_bar"].configure(fg_color=ACCENT_COLOR if is_selected else "transparent")
        widgets["name_label"].configure(text=f"📌 {name}" if is_pinned else name)
        widgets["phone_label"].configure(text=phone)
        mute_icon = widgets.get("mute_icon")
        if mute_icon:
            if is_muted:
                mute_icon.pack(side="right", anchor="n", pady=(2, 0), padx=(0, 4))
            else:
                mute_icon.pack_forget()
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
        if conversation_id != self.selected_conversation_id:
            self._hide_contact_info_panel()
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

    # ── Conversation Actions ("Others" ⋮) Menu ─────────────────────────────────

    def _build_conversation_menu(self, conversation_id: str, is_archived: bool, is_pinned: bool, is_muted: bool) -> tk.Menu:
        menu = tk.Menu(
            self, tearoff=0,
            bg=SURFACE_COLOR, fg=TEXT_COLOR,
            activebackground=ACCENT_COLOR, activeforeground="#ffffff",
            borderwidth=0, relief="flat",
        )
        if is_pinned:
            menu.add_command(label="Unpin chat", command=lambda: self._on_unpin(conversation_id))
        else:
            menu.add_command(label="Pin chat", command=lambda: self._on_pin(conversation_id))
        if is_muted:
            menu.add_command(label="Unmute conversation", command=lambda: self._on_unmute(conversation_id))
        else:
            menu.add_command(label="Mute conversation", command=lambda: self._on_mute(conversation_id))
        if is_archived:
            menu.add_command(label="Unarchive chat", command=lambda: self._on_unarchive(conversation_id))
        else:
            menu.add_command(label="Archive chat", command=lambda: self._on_archive(conversation_id))
        menu.add_separator()
        menu.add_command(label="Delete chat", command=lambda: self._on_delete(conversation_id))
        return menu

    def _show_conversation_menu(self, event, conversation_id: str):
        row = self._find_conversation(conversation_id)
        if not row:
            return
        is_archived = bool(self._read_item(row, "is_archived", False))
        is_pinned = bool(self._read_item(row, "is_pinned", False))
        is_muted = bool(self._read_item(row, "is_muted", False))
        menu = self._build_conversation_menu(conversation_id, is_archived, is_pinned, is_muted)
        menu.tk_popup(event.x_root, event.y_root)

    def _show_action_bar_menu(self):
        if not self.selected_conversation_id:
            return
        row = self._find_conversation(self.selected_conversation_id)
        is_archived = bool(self._read_item(row, "is_archived", False)) if row else False
        is_pinned = bool(self._read_item(row, "is_pinned", False)) if row else False
        is_muted = bool(self._read_item(row, "is_muted", False)) if row else False
        menu = self._build_conversation_menu(self.selected_conversation_id, is_archived, is_pinned, is_muted)
        x = self.more_options_btn.winfo_rootx()
        y = self.more_options_btn.winfo_rooty() + self.more_options_btn.winfo_height()
        menu.tk_popup(x, y)

    def _on_archive(self, conversation_id: str):
        if not self.archive_conversation_cb:
            return

        def _done(result):
            self.refresh_conversations()

        try:
            self.archive_conversation_cb(conversation_id, _done)
        except Exception as e:
            logger.error(f"Archive failed: {e}")

    def _on_unarchive(self, conversation_id: str):
        if not self.unarchive_conversation_cb:
            return

        def _done(result):
            self.refresh_conversations()

        try:
            self.unarchive_conversation_cb(conversation_id, _done)
        except Exception as e:
            logger.error(f"Unarchive failed: {e}")

    def _on_pin(self, conversation_id: str):
        if not self.pin_conversation_cb:
            return

        def _done(result):
            self.refresh_conversations()

        try:
            self.pin_conversation_cb(conversation_id, _done)
        except Exception as e:
            logger.error(f"Pin failed: {e}")

    def _on_unpin(self, conversation_id: str):
        if not self.unpin_conversation_cb:
            return

        def _done(result):
            self.refresh_conversations()

        try:
            self.unpin_conversation_cb(conversation_id, _done)
        except Exception as e:
            logger.error(f"Unpin failed: {e}")

    def _on_mute(self, conversation_id: str):
        if not self.mute_conversation_cb:
            return

        def _done(result):
            self.refresh_conversations()

        try:
            self.mute_conversation_cb(conversation_id, _done)
        except Exception as e:
            logger.error(f"Mute failed: {e}")

    def _on_unmute(self, conversation_id: str):
        if not self.unmute_conversation_cb:
            return

        def _done(result):
            self.refresh_conversations()

        try:
            self.unmute_conversation_cb(conversation_id, _done)
        except Exception as e:
            logger.error(f"Unmute failed: {e}")

    def _on_delete(self, conversation_id: str):
        if not self.delete_conversation_cb:
            return
        if not messagebox.askyesno("Delete chat", "Delete this chat? This cannot be undone from the app."):
            return

        def _done(result):
            if conversation_id == self.selected_conversation_id:
                self.selected_conversation_id = None
                self._update_action_bar_placeholder()
                self.chat_frame.set_conversation(None, "Select a conversation", "idle")
            self.refresh_conversations()

        try:
            self.delete_conversation_cb(conversation_id, _done)
        except Exception as e:
            logger.error(f"Delete failed: {e}")
