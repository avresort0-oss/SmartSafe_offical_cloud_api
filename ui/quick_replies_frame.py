import os
import json
from tkinter import filedialog
import customtkinter as ctk
from typing import Callable, List, Dict, Any, Optional

from .styles import (
    BG_COLOR, SURFACE_COLOR, INPUT_COLOR, HOVER_COLOR,
    ACCENT_COLOR, ACCENT_HOVER, TEXT_COLOR, TEXT_SECONDARY, SUB_TEXT_COLOR,
    ERROR_COLOR, DIVIDER_COLOR, PILL_RADIUS,
    CARD_RADIUS, CARD_RADIUS_SM, INPUT_RADIUS, BUTTON_RADIUS,
    INPUT_HEIGHT, BUTTON_HEIGHT, BUTTON_HEIGHT_SM,
    PAD_2XS, PAD_SM, PAD_MD, PAD_LG, PAD_XL, PAD_2XL, PAD_3XL,
    FONT_3XL, FONT_XL, FONT_LG, FONT_MD, FONT_SM, FONT_XS, FONT_2XS,
    heading_font, body_font,
    get_media_icon,
    create_section_header, create_premium_button, create_premium_input,
)


class QuickRepliesFrame(ctk.CTkFrame):
    """
    Quick Replies Management UI (Premium Redesign).
    Allows creating, editing, attaching media, and deleting quick reply templates.
    """
    def __init__(
        self,
        master,
        load_quick_replies_cb: Optional[Callable[[], List[Dict[str, Any]]]] = None,
        save_quick_replies_cb: Optional[Callable[[List[Dict[str, Any]]], None]] = None,
        **kwargs
    ):
        super().__init__(master, fg_color=BG_COLOR, corner_radius=0, **kwargs)
        self.load_quick_replies_cb = load_quick_replies_cb
        self.save_quick_replies_cb = save_quick_replies_cb
        self.replies: List[Dict[str, Any]] = []
        self.editing_idx: Optional[int] = None
        self.selected_attachment: Optional[str] = None
        self._reply_widgets: List[Dict[str, Any]] = []
        self._empty_label = None
        self.search_query = ""

        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        # Main scrollable container
        self.main_scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.main_scroll.grid(row=0, column=0, sticky="nsew", padx=PAD_XL, pady=PAD_XL)
        self.main_scroll.grid_columnconfigure(0, weight=1)

        self._build_header()
        self._build_form()
        self._build_list()

    # ── Header ─────────────────────────────────────────────────────────────────
    def _build_header(self):
        self.header_frame = create_section_header(self.main_scroll, "Quick Replies", "Manage canned responses")
        self.header_frame.grid(row=0, column=0, sticky="ew", pady=(PAD_MD, PAD_3XL), padx=PAD_MD)

    # ── Add/Edit Form ──────────────────────────────────────────────────────────
    def _build_form(self):
        self.add_frame = ctk.CTkFrame(self.main_scroll, fg_color=SURFACE_COLOR, corner_radius=CARD_RADIUS)
        self.add_frame.grid(row=1, column=0, sticky="ew", padx=PAD_MD, pady=(0, PAD_XL))
        self.add_frame.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            self.add_frame, text="Create or Edit Reply",
            font=ctk.CTkFont(size=FONT_MD, weight="bold"), text_color=SUB_TEXT_COLOR
        ).grid(row=0, column=0, columnspan=2, sticky="w", padx=PAD_XL, pady=(PAD_LG, PAD_MD))

        self.title_entry = create_premium_input(
            self.add_frame, "Reply Title (e.g. Greeting)", height=45,
        )
        self.title_entry.grid(row=1, column=0, columnspan=2, sticky="ew", padx=PAD_XL, pady=(0, PAD_MD))

        input_row = ctk.CTkFrame(self.add_frame, fg_color="transparent")
        input_row.grid(row=2, column=0, sticky="ew", padx=PAD_XL, pady=(0, PAD_XL))
        input_row.grid_columnconfigure(0, weight=1)

        self.new_reply_entry = create_premium_input(
            input_row, "Type message content...", height=45,
        )
        self.new_reply_entry.grid(row=0, column=0, sticky="ew", padx=(0, PAD_LG))
        self.new_reply_entry.bind("<Return>", lambda e: self._add_reply())

        # Buttons Right Side
        btn_container = ctk.CTkFrame(input_row, fg_color="transparent")
        btn_container.grid(row=0, column=1)

        self.attach_btn = ctk.CTkButton(
            btn_container, text="📎 Attach Media", width=120, height=45, corner_radius=INPUT_RADIUS,
            fg_color=INPUT_COLOR, hover_color=HOVER_COLOR, command=self._handle_attachment
        )
        self.attach_btn.pack(side="left")

        self.clear_attach_btn = ctk.CTkButton(
            btn_container, text="✕", width=45, height=45, corner_radius=INPUT_RADIUS,
            fg_color=INPUT_COLOR, text_color=ERROR_COLOR, hover_color="#3b1515", command=self._clear_attachment
        )

        self.cancel_edit_btn = create_premium_button(
            btn_container, text="Cancel", variant="ghost", width=80, height=45,
            command=self._cancel_edit,
        )
        self.cancel_edit_btn.configure(border_width=1, border_color=SUB_TEXT_COLOR)

        self.add_btn = create_premium_button(
            btn_container, text="Save Reply", variant="primary", width=120, height=45,
            command=self._add_reply,
        )
        self.add_btn.pack(side="left", padx=(PAD_LG, 0))

    # ── Replies List ───────────────────────────────────────────────────────────
    def _build_list(self):
        self.list_container = ctk.CTkFrame(self.main_scroll, fg_color="transparent")
        self.list_container.grid(row=2, column=0, sticky="nsew", padx=PAD_MD)
        self.list_container.grid_columnconfigure(0, weight=1)

        header_row = ctk.CTkFrame(self.list_container, fg_color="transparent")
        header_row.pack(fill="x", padx=PAD_MD, pady=(0, PAD_MD))

        ctk.CTkLabel(
            header_row, text="Saved Replies",
            font=ctk.CTkFont(size=FONT_MD, weight="bold"), text_color=SUB_TEXT_COLOR
        ).pack(side="left")

        self.search_entry = ctk.CTkEntry(
            header_row, placeholder_text="Search...", width=200, height=BUTTON_HEIGHT_SM,
            border_width=1, border_color=SUB_TEXT_COLOR, fg_color="transparent", corner_radius=PILL_RADIUS
        )
        self.search_entry.pack(side="right")
        self.search_entry.bind("<KeyRelease>", self._on_search)

    def _on_search(self, event=None):
        self.search_query = self.search_entry.get().strip().lower()
        self._render_replies()

    def refresh_data(self):
        if self.load_quick_replies_cb:
            self.replies = self.load_quick_replies_cb()
        self._render_replies()

    def _render_replies(self):
        filtered_replies = []
        for idx, r in enumerate(self.replies):
            t = r.get("title", "")
            c = r.get("text", "") or r.get("content", "")
            if self.search_query in t.lower() or self.search_query in c.lower():
                filtered_replies.append((idx, r))

        if not filtered_replies:
            for w in self._reply_widgets:
                w["card"].pack_forget()
            if not self._empty_label:
                self._empty_label = ctk.CTkLabel(self.list_container, text="No matching quick replies found.", text_color=SUB_TEXT_COLOR)
            self._empty_label.pack(pady=40)
            return

        if self._empty_label:
            self._empty_label.pack_forget()

        for i, (orig_idx, reply) in enumerate(filtered_replies):
            if i < len(self._reply_widgets):
                widgets = self._reply_widgets[i]
                widgets["card"].pack_forget()
            else:
                widgets = self._create_reply_widget()
                self._reply_widgets.append(widgets)

        for i, (orig_idx, reply) in enumerate(filtered_replies):
            widgets = self._reply_widgets[i]
            self._update_reply_widget(widgets, reply, orig_idx)
            widgets["card"].pack(fill="x", pady=PAD_SM)

        for i in range(len(filtered_replies), len(self._reply_widgets)):
            self._reply_widgets[i]["card"].pack_forget()

    def _create_reply_widget(self) -> dict:
        card = ctk.CTkFrame(self.list_container, fg_color=SURFACE_COLOR, corner_radius=CARD_RADIUS_SM)
        card.grid_columnconfigure(0, weight=1)

        # Color strip accent
        accent = ctk.CTkFrame(card, width=4, corner_radius=2, fg_color=ACCENT_COLOR)
        accent.grid(row=0, column=0, sticky="ns", padx=(4, 0), pady=PAD_MD)

        text_container = ctk.CTkFrame(card, fg_color="transparent")
        text_container.grid(row=0, column=1, sticky="w", padx=PAD_LG, pady=PAD_MD)
        text_container.grid_columnconfigure(0, weight=1)

        title_lbl = ctk.CTkLabel(text_container, text="", text_color=TEXT_COLOR, anchor="w", font=ctk.CTkFont(size=FONT_LG, weight="bold"))
        title_lbl.pack(anchor="w")

        desc_lbl = ctk.CTkLabel(text_container, text="", text_color=SUB_TEXT_COLOR, anchor="w", font=body_font(FONT_SM))
        desc_lbl.pack(anchor="w", pady=(PAD_2XS, 0))

        edit_btn = create_premium_button(card, text="✏️ Edit", variant="ghost", width=80, height=BUTTON_HEIGHT_SM)
        edit_btn.configure(border_width=1, border_color=SUB_TEXT_COLOR)
        edit_btn.grid(row=0, column=2, padx=(PAD_LG, PAD_SM), pady=PAD_LG)

        del_btn = create_premium_button(card, text="🗑 Delete", variant="danger", width=80, height=BUTTON_HEIGHT_SM)
        del_btn.grid(row=0, column=3, padx=(PAD_SM, PAD_LG), pady=PAD_LG)

        return {"card": card, "title_lbl": title_lbl, "desc_lbl": desc_lbl, "edit_btn": edit_btn, "del_btn": del_btn}

    def _update_reply_widget(self, widgets: dict, reply: dict, idx: int):
        title = reply.get("title", "")
        text = reply.get("text", "") or reply.get("content", "")
        has_attachment = bool(reply.get("attachment_path"))
        icon = get_media_icon(reply.get("attachment_path")) if has_attachment else ""

        display_title = title if title else "Untitled"
        display_text = f"{icon} {text}".strip() if has_attachment else text

        is_editing = self.editing_idx == idx
        bg_color = INPUT_COLOR if is_editing else SURFACE_COLOR

        widgets["card"].configure(fg_color=bg_color)
        widgets["title_lbl"].configure(text=display_title)
        widgets["desc_lbl"].configure(text=display_text[:120] + ("..." if len(display_text) > 120 else ""))
        widgets["edit_btn"].configure(command=lambda i=idx: self._edit_reply(i))
        widgets["del_btn"].configure(command=lambda i=idx: self._delete_reply(i))

    # ── Actions ────────────────────────────────────────────────────────────────
    def _cancel_edit(self):
        self.editing_idx = None
        self.title_entry.delete(0, "end")
        self.new_reply_entry.delete(0, "end")
        self._clear_attachment()
        self.add_btn.configure(text="Add Reply")
        self.cancel_edit_btn.pack_forget()
        self._render_replies()

    def _handle_attachment(self):
        filetypes = [
            ("All Supported", "*.png;*.jpg;*.jpeg;*.gif;*.mp4;*.avi;*.mp3;*.wav;*.pdf;*.txt;*.docx"),
            ("Images", "*.png;*.jpg;*.jpeg;*.gif"),
            ("Videos", "*.mp4;*.avi;*.mov"),
            ("Audio", "*.mp3;*.wav;*.ogg"),
            ("Documents", "*.pdf;*.txt;*.docx;*.csv")
        ]
        file_path = filedialog.askopenfilename(title="Select attachment for Quick Reply", filetypes=filetypes)
        if file_path:
            self.selected_attachment = file_path
            icon = get_media_icon(file_path)
            self.attach_btn.configure(text=f"{icon} Attached")
            self.clear_attach_btn.pack(side="left", padx=PAD_MD)

    def _clear_attachment(self):
        self.selected_attachment = None
        self.attach_btn.configure(text="📎 Attach Media")
        self.clear_attach_btn.pack_forget()

    def _edit_reply(self, idx: int):
        if 0 <= idx < len(self.replies):
            self.editing_idx = idx
            reply = self.replies[idx]
            self.title_entry.delete(0, "end")
            self.title_entry.insert("end", reply.get("title", ""))
            self.new_reply_entry.delete(0, "end")
            self.new_reply_entry.insert("end", reply.get("text", "") or reply.get("content", ""))

            self.selected_attachment = reply.get("attachment_path")
            if self.selected_attachment:
                icon = get_media_icon(self.selected_attachment)
                self.attach_btn.configure(text=f"{icon} Attached")
                self.clear_attach_btn.pack(side="left", padx=PAD_MD)
            else:
                self.attach_btn.configure(text="📎 Attach Media")
                self.clear_attach_btn.pack_forget()

            self.cancel_edit_btn.pack(side="left", padx=(PAD_LG, 0))
            self.add_btn.configure(text="Save Reply")
            self._render_replies()

    def _add_reply(self):
        title = self.title_entry.get().strip()
        text = self.new_reply_entry.get().strip()
        if text or self.selected_attachment:
            new_reply = {"title": title, "text": text, "content": text, "attachment_path": self.selected_attachment}
            if self.editing_idx is not None:
                self.replies[self.editing_idx] = new_reply
                self.editing_idx = None
                self.add_btn.configure(text="Add Reply")
                self.cancel_edit_btn.pack_forget()
            else:
                if new_reply not in self.replies:
                    self.replies.append(new_reply)

            if self.save_quick_replies_cb:
                self.save_quick_replies_cb(self.replies)

            self.title_entry.delete(0, "end")
            self.new_reply_entry.delete(0, "end")
            self._clear_attachment()
            self._render_replies()

    def _delete_reply(self, idx: int):
        if 0 <= idx < len(self.replies):
            e_idx = self.editing_idx
            if e_idx == idx:
                self._cancel_edit()
            elif e_idx is not None and e_idx > idx:
                self.editing_idx = e_idx - 1

            self.replies.pop(idx)
            if self.save_quick_replies_cb:
                self.save_quick_replies_cb(self.replies)
            self._render_replies()
