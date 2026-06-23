import customtkinter as ctk
import hashlib
from typing import Any, Callable, Dict, List, Optional

from services.workspace_service import WorkspaceDTO

from .styles import (
    BG_COLOR, SURFACE_COLOR, INPUT_COLOR, HOVER_COLOR, ACTIVE_COLOR,
    ACCENT_COLOR, ACCENT_HOVER, TEXT_COLOR, SUB_TEXT_COLOR, ERROR_COLOR, DIVIDER_COLOR,
    CARD_RADIUS, CARD_RADIUS_SM, INPUT_RADIUS,
    PAD_XS, PAD_SM, PAD_MD, PAD_LG, PAD_XL, PAD_2XL, PAD_3XL,
    FONT_2XL, FONT_XL, FONT_LG, FONT_MD, FONT_SM, FONT_XS, FONT_2XS,
    heading_font, body_font,
    create_section_header, create_premium_input, create_premium_button,
)


def get_color_from_string(s: str) -> str:
    if not s: return "#6b7280"
    colors = ["#e53935", "#d81b60", "#8e24aa", "#5e35b1", "#3949ab",
              "#1e88e5", "#039be5", "#00acc1", "#00897b", "#43a047",
              "#7cb342", "#c0ca33", "#fdd835", "#ffb300", "#fb8c00", "#f4511e"]
    h = int(hashlib.sha256(s.encode("utf-8")).hexdigest(), 16)
    return colors[h % len(colors)]


class AddressBookFrame(ctk.CTkFrame):
    """Contact CRM view (Premium Redesign)."""

    def __init__(self, master, load_contacts_cb=None, create_contact_cb=None, update_contact_cb=None, load_labels_cb=None, create_label_cb=None, attach_label_cb=None, detach_label_cb=None, **kwargs):
        super().__init__(master, fg_color=BG_COLOR, corner_radius=0, **kwargs)
        self.load_contacts_cb = load_contacts_cb
        self.create_contact_cb = create_contact_cb
        self.update_contact_cb = update_contact_cb
        self.load_labels_cb = load_labels_cb
        self.create_label_cb = create_label_cb
        self.attach_label_cb = attach_label_cb
        self.detach_label_cb = detach_label_cb
        self.current_workspace = None
        self.selected_contact_id = None
        self._contacts = []
        self._labels = []
        self._label_name_to_id = {}

        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=3)
        self.grid_columnconfigure(1, weight=7)
        self._build_header()
        self._build_list_panel()
        self._build_form_panel()

    def _read(self, item, key, default=None):
        if hasattr(item, key): return getattr(item, key)
        if isinstance(item, dict): return item.get(key, default)
        return default

    def _build_header(self):
        self.header_frame = ctk.CTkFrame(self, fg_color="transparent", corner_radius=0)
        self.header_frame.grid(row=0, column=0, columnspan=2, sticky="ew", padx=PAD_3XL, pady=(PAD_2XL, PAD_MD))
        self.title_label = ctk.CTkLabel(self.header_frame, text="Contacts CRM", font=heading_font(FONT_2XL), text_color=TEXT_COLOR)
        self.title_label.pack(side="left")
        ctk.CTkLabel(self.header_frame, text="| Manage leads and customers", font=body_font(FONT_MD), text_color=SUB_TEXT_COLOR).pack(side="left", padx=(PAD_MD, 0), pady=(4, 0))
        self.new_contact_btn = create_premium_button(self.header_frame, text="+ Add Contact", variant="primary", width=120, height=36, command=self._clear_selection_for_new)
        self.new_contact_btn.configure(corner_radius=18)
        self.new_contact_btn.pack(side="right")

    def _build_list_panel(self):
        self.list_panel = ctk.CTkFrame(self, fg_color=SURFACE_COLOR, corner_radius=CARD_RADIUS)
        self.list_panel.grid(row=1, column=0, sticky="nsew", padx=(PAD_3XL, PAD_SM), pady=(0, PAD_2XL))
        self.list_panel.grid_rowconfigure(1, weight=1)
        self.list_panel.grid_columnconfigure(0, weight=1)
        search_row = ctk.CTkFrame(self.list_panel, fg_color="transparent")
        search_row.grid(row=0, column=0, sticky="ew", padx=PAD_LG, pady=PAD_LG)
        self.search_entry = create_premium_input(search_row, "Search contacts...", height=36)
        self.search_entry.pack(side="left", fill="x", expand=True, padx=(0, PAD_MD))
        ctk.CTkButton(search_row, text="↻", width=36, height=36, corner_radius=CARD_RADIUS_SM, command=self.load_initial_data, fg_color=INPUT_COLOR, hover_color=HOVER_COLOR).pack(side="right")
        self.contacts_canvas = ctk.CTkScrollableFrame(self.list_panel, fg_color="transparent")
        self.contacts_canvas.grid(row=1, column=0, sticky="nsew", padx=PAD_SM, pady=(0, PAD_MD))

    def _build_form_panel(self):
        self.form_panel = ctk.CTkFrame(self, fg_color=SURFACE_COLOR, corner_radius=CARD_RADIUS)
        self.form_panel.grid(row=1, column=1, sticky="nsew", padx=(PAD_SM, PAD_3XL), pady=(0, PAD_2XL))
        self.form_panel.grid_columnconfigure(0, weight=1)
        self.form_panel.grid_rowconfigure(0, weight=1)
        self.form_scroll = ctk.CTkScrollableFrame(self.form_panel, fg_color="transparent")
        self.form_scroll.grid(row=0, column=0, sticky="nsew", padx=PAD_LG, pady=PAD_LG)
        self.form_scroll.grid_columnconfigure(0, weight=1)
        self.form_header_label = ctk.CTkLabel(self.form_scroll, text="Contact Details", font=heading_font(FONT_XL), text_color=TEXT_COLOR)
        self.form_header_label.pack(anchor="w", pady=(0, PAD_XL))

        self._build_input_field("Name", self.form_scroll, "display_name", "e.g. John Doe", "name_entry")
        self._build_input_field("Phone (E.164)", self.form_scroll, "phone_e164", "e.g. +15550001234", "phone_entry")
        self._build_input_field("Email", self.form_scroll, "email", "e.g. john@example.com (optional)", "email_entry")
        self._build_input_field("Owner User ID", self.form_scroll, "owner_id", "Assignee user ID (optional)", "owner_entry")

        lifecycle_row = ctk.CTkFrame(self.form_scroll, fg_color="transparent")
        lifecycle_row.pack(fill="x", pady=(PAD_MD, PAD_SM))
        ctk.CTkLabel(lifecycle_row, text="Lifecycle Stage", text_color=SUB_TEXT_COLOR, font=ctk.CTkFont(weight="bold")).pack(side="left")
        self.lifecycle_menu = ctk.CTkOptionMenu(lifecycle_row, values=["LEAD", "ACTIVE", "CUSTOMER", "AT_RISK", "CHURNED"], fg_color=INPUT_COLOR, button_color=ACCENT_COLOR, button_hover_color=ACCENT_HOVER, corner_radius=INPUT_RADIUS, dropdown_fg_color=SURFACE_COLOR, dropdown_text_color=TEXT_COLOR, dropdown_hover_color=HOVER_COLOR)
        self.lifecycle_menu.pack(side="right")

        ctk.CTkLabel(self.form_scroll, text="Internal Notes", text_color=SUB_TEXT_COLOR, font=ctk.CTkFont(weight="bold")).pack(anchor="w", pady=(PAD_LG, PAD_SM))
        self.notes_box = ctk.CTkTextbox(self.form_scroll, height=100, fg_color=INPUT_COLOR, text_color=TEXT_COLOR, corner_radius=INPUT_RADIUS, border_width=0)
        self.notes_box.pack(fill="x", pady=(0, PAD_XL))

        btn_row = ctk.CTkFrame(self.form_scroll, fg_color="transparent")
        btn_row.pack(fill="x", pady=(0, PAD_XL))
        btn_row.grid_columnconfigure(0, weight=1)
        btn_row.grid_columnconfigure(1, weight=1)
        self.create_btn = create_premium_button(btn_row, text="Create Contact", variant="primary", command=self._create_contact)
        self.create_btn.grid(row=0, column=0, sticky="ew", padx=(0, PAD_SM))
        self.update_btn = ctk.CTkButton(btn_row, text="Save Changes", fg_color=INPUT_COLOR, hover_color=HOVER_COLOR, corner_radius=CARD_RADIUS_SM, height=40, font=ctk.CTkFont(weight="bold"), command=self._update_contact)
        self.update_btn.grid(row=0, column=1, sticky="ew")

        self.feedback_label = ctk.CTkLabel(self.form_scroll, text="", text_color=SUB_TEXT_COLOR)
        self.feedback_label.pack(anchor="center", pady=(0, PAD_MD))
        ctk.CTkFrame(self.form_scroll, fg_color=DIVIDER_COLOR, height=1).pack(fill="x", pady=PAD_LG)

        ctk.CTkLabel(self.form_scroll, text="Labels & Tags", font=heading_font(FONT_XL), text_color=TEXT_COLOR).pack(anchor="w", pady=(0, PAD_LG))
        label_create_row = ctk.CTkFrame(self.form_scroll, fg_color="transparent")
        label_create_row.pack(fill="x", pady=(0, PAD_MD))
        self.new_label_entry = create_premium_input(label_create_row, "New label name...", height=36)
        self.new_label_entry.pack(side="left", fill="x", expand=True, padx=(0, PAD_MD))
        self.create_label_btn = ctk.CTkButton(label_create_row, text="+ Create Label", width=110, height=36, corner_radius=CARD_RADIUS_SM, fg_color=INPUT_COLOR, hover_color=HOVER_COLOR, command=self._create_label)
        self.create_label_btn.pack(side="right")

        assign_row = ctk.CTkFrame(self.form_scroll, fg_color="transparent")
        assign_row.pack(fill="x", pady=(0, PAD_MD))
        self.label_menu = ctk.CTkOptionMenu(assign_row, values=["No Labels"], fg_color=INPUT_COLOR, button_color=INPUT_COLOR, corner_radius=INPUT_RADIUS, height=36, dropdown_fg_color=SURFACE_COLOR, dropdown_text_color=TEXT_COLOR, dropdown_hover_color=HOVER_COLOR)
        self.label_menu.pack(side="left", fill="x", expand=True, padx=(0, PAD_MD))
        self.attach_btn = create_premium_button(assign_row, text="Attach", variant="primary", width=90, height=36, command=self._attach_label)
        self.attach_btn.pack(side="left", padx=(0, PAD_SM))
        self.detach_btn = ctk.CTkButton(assign_row, text="Detach", width=90, height=36, corner_radius=CARD_RADIUS_SM, fg_color=INPUT_COLOR, hover_color="#3b2b2b", text_color=ERROR_COLOR, command=self._detach_label)
        self.detach_btn.pack(side="left")

    def _build_input_field(self, label_text, parent, prop_name, placeholder, attr_name):
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", pady=(0, PAD_LG))
        ctk.CTkLabel(row, text=label_text, text_color=SUB_TEXT_COLOR, font=ctk.CTkFont(weight="bold")).pack(anchor="w", pady=(0, 2))
        entry = create_premium_input(row, placeholder)
        entry.pack(fill="x")
        setattr(self, attr_name, entry)

    def configure_callbacks(self, load_contacts_cb, create_contact_cb, update_contact_cb, load_labels_cb, create_label_cb, attach_label_cb, detach_label_cb):
        self.load_contacts_cb = load_contacts_cb
        self.create_contact_cb = create_contact_cb
        self.update_contact_cb = update_contact_cb
        self.load_labels_cb = load_labels_cb
        self.create_label_cb = create_label_cb
        self.attach_label_cb = attach_label_cb
        self.detach_label_cb = detach_label_cb

    def load_initial_data(self):
        self._contacts = self.load_contacts_cb() if self.load_contacts_cb else []
        self._labels = self.load_labels_cb() if self.load_labels_cb else []
        query = self.search_entry.get().strip().lower()
        if query:
            self._contacts = [c for c in self._contacts if query in str(self._read(c, "display_name", "")).lower() or query in str(self._read(c, "phone_e164", "")).lower()]
        self._label_name_to_id.clear()
        label_names = []
        for lb in self._labels:
            lid = self._read(lb, "id")
            name = self._read(lb, "name", "Unnamed")
            self._label_name_to_id[name] = lid
            label_names.append(name)
        if not label_names: label_names = ["No Labels"]
        self.label_menu.configure(values=label_names)
        self.label_menu.set(label_names[0])
        self._render_contacts()

    def refresh_workspace(self, workspace):
        self.current_workspace = workspace
        self.title_label.configure(text=f"{workspace.name[:15]}{'...' if len(workspace.name)>15 else ''} CRM")
        if not self.selected_contact_id: self._clear_form()
        self.load_initial_data()

    def _render_contacts(self):
        for child in self.contacts_canvas.winfo_children(): child.destroy()
        if not self._contacts:
            ctk.CTkLabel(self.contacts_canvas, text="No contacts found.", text_color=SUB_TEXT_COLOR, pady=20).pack()
            return
        for row in self._contacts: self._render_contact_card(row)

    def _render_contact_card(self, row):
        cid = self._read(row, "id")
        name = self._read(row, "display_name", "Unknown Contact")
        phone = self._read(row, "phone_e164", "No Phone")
        stage = self._read(row, "lifecycle_stage", "LEAD")
        labels = self._read(row, "labels", []) or []
        is_selected = (cid == self.selected_contact_id)

        card = ctk.CTkFrame(self.contacts_canvas, fg_color=ACTIVE_COLOR if is_selected else "transparent", corner_radius=CARD_RADIUS_SM, cursor="hand2")
        card.pack(fill="x", padx=PAD_XS, pady=PAD_XS)

        def on_enter(e, w=card, s=is_selected):
            if not s: w.configure(fg_color=HOVER_COLOR)
        def on_leave(e, w=card, s=is_selected):
            if not s: w.configure(fg_color="transparent")
        card.bind("<Enter>", on_enter); card.bind("<Leave>", on_leave)
        card.bind("<Button-1>", lambda _e, c=row: self._select_contact(c))

        if is_selected:
            ctk.CTkFrame(card, fg_color=ACCENT_COLOR, width=4, corner_radius=2).pack(side="left", fill="y", pady=6, padx=(4, 0))

        avatar_color = get_color_from_string(name)
        initial = name[0].upper() if name and name != "Unknown Contact" else "?"
        avatar = ctk.CTkLabel(card, text=initial, width=40, height=40, corner_radius=20, fg_color=avatar_color, text_color="#ffffff", font=ctk.CTkFont(size=FONT_LG, weight="bold"))
        avatar.pack(side="left", padx=PAD_MD, pady=PAD_MD)
        avatar.bind("<Button-1>", lambda _e, c=row: self._select_contact(c))

        info = ctk.CTkFrame(card, fg_color="transparent")
        info.pack(side="left", fill="both", expand=True, pady=PAD_MD, padx=(0, PAD_MD))
        info.bind("<Button-1>", lambda _e, c=row: self._select_contact(c))

        top_row = ctk.CTkFrame(info, fg_color="transparent")
        top_row.pack(fill="x")
        top_row.bind("<Button-1>", lambda _e, c=row: self._select_contact(c))
        name_lbl = ctk.CTkLabel(top_row, text=name, font=ctk.CTkFont(size=FONT_MD, weight="bold"), text_color=TEXT_COLOR, anchor="w")
        name_lbl.pack(side="left")
        name_lbl.bind("<Button-1>", lambda _e, c=row: self._select_contact(c))

        stage_color = ACCENT_COLOR if stage in ("ACTIVE", "CUSTOMER") else (ERROR_COLOR if stage == "CHURNED" else "#e9c46a")
        ctk.CTkLabel(top_row, text=f" {stage} ", font=ctk.CTkFont(size=FONT_2XS, weight="bold"), text_color=BG_COLOR, fg_color=stage_color, corner_radius=4).pack(side="right")

        bottom_row = ctk.CTkFrame(info, fg_color="transparent")
        bottom_row.pack(fill="x")
        bottom_row.bind("<Button-1>", lambda _e, c=row: self._select_contact(c))
        ctk.CTkLabel(bottom_row, text=phone, font=body_font(FONT_SM), text_color=SUB_TEXT_COLOR, anchor="w").pack(side="left")
        if labels:
            ctk.CTkLabel(bottom_row, text=f"{len(labels)} label(s)", font=ctk.CTkFont(size=FONT_2XS), text_color=ACCENT_COLOR).pack(side="right")

    def _clear_selection_for_new(self):
        self.selected_contact_id = None; self._clear_form()
        self.form_header_label.configure(text="New Contact")
        self.create_btn.configure(state="normal", fg_color=ACCENT_COLOR)
        self.update_btn.configure(state="disabled"); self._render_contacts()

    def _clear_form(self):
        self.phone_entry.delete(0, "end"); self.name_entry.delete(0, "end")
        self.email_entry.delete(0, "end"); self.owner_entry.delete(0, "end")
        self.notes_box.delete("1.0", "end"); self.lifecycle_menu.set("LEAD")
        self.feedback_label.configure(text="")

    def _select_contact(self, row):
        self.selected_contact_id = self._read(row, "id")
        self.form_header_label.configure(text=f"Edit: {self._read(row, 'display_name', 'Contact')}")
        self.create_btn.configure(state="disabled", fg_color=INPUT_COLOR, text_color=SUB_TEXT_COLOR)
        self.update_btn.configure(state="normal")
        self.phone_entry.delete(0, "end"); self.phone_entry.insert(0, self._read(row, "phone_e164", ""))
        self.name_entry.delete(0, "end"); self.name_entry.insert(0, self._read(row, "display_name", ""))
        self.email_entry.delete(0, "end"); self.email_entry.insert(0, self._read(row, "email", "") or "")
        self.owner_entry.delete(0, "end"); self.owner_entry.insert(0, self._read(row, "owner_user_id", "") or "")
        self.notes_box.delete("1.0", "end"); self.notes_box.insert("1.0", self._read(row, "notes", "") or "")
        self.lifecycle_menu.set(self._read(row, "lifecycle_stage", "LEAD") or "LEAD")
        self.feedback_label.configure(text=""); self._render_contacts()

    def _create_contact(self):
        if not self.create_contact_cb: return
        payload = {"phone_e164": self.phone_entry.get().strip(), "display_name": self.name_entry.get().strip(), "email": self.email_entry.get().strip() or None, "owner_user_id": self.owner_entry.get().strip() or None, "lifecycle_stage": self.lifecycle_menu.get(), "notes": self.notes_box.get("1.0", "end").strip()}
        if not payload["phone_e164"] or not payload["display_name"]:
            self.feedback_label.configure(text="Name and Phone are required.", text_color=ERROR_COLOR); return
        try:
            self.create_contact_cb(payload); self._clear_selection_for_new()
            self.feedback_label.configure(text="✓ Contact created successfully", text_color=ACCENT_COLOR); self.load_initial_data()
        except Exception as e: self.feedback_label.configure(text=f"Create failed: {str(e)}", text_color=ERROR_COLOR)

    def _update_contact(self):
        if not self.update_contact_cb or not self.selected_contact_id:
            self.feedback_label.configure(text="Select a contact first.", text_color=ERROR_COLOR); return
        payload = {"display_name": self.name_entry.get().strip(), "email": self.email_entry.get().strip() or None, "owner_user_id": self.owner_entry.get().strip() or None, "lifecycle_stage": self.lifecycle_menu.get(), "notes": self.notes_box.get("1.0", "end").strip()}
        try:
            self.update_contact_cb(self.selected_contact_id, payload)
            self.feedback_label.configure(text="✓ Contact updated successfully", text_color=ACCENT_COLOR); self.load_initial_data()
        except Exception as e: self.feedback_label.configure(text=f"Update failed: {e}", text_color=ERROR_COLOR)

    def _create_label(self):
        if not self.create_label_cb: return
        name = self.new_label_entry.get().strip()
        if not name: self.feedback_label.configure(text="Label name required.", text_color=ERROR_COLOR); return
        try:
            self.create_label_cb(name, "#00a884"); self.new_label_entry.delete(0, "end")
            self.feedback_label.configure(text=f"✓ Label '{name}' added", text_color=ACCENT_COLOR); self.load_initial_data()
        except Exception as e: self.feedback_label.configure(text=f"Label create failed: {e}", text_color=ERROR_COLOR)

    def _attach_label(self):
        if not self.selected_contact_id or not self.attach_label_cb:
            self.feedback_label.configure(text="Select a contact first.", text_color=ERROR_COLOR); return
        label_name = self.label_menu.get()
        label_id = self._label_name_to_id.get(label_name)
        if not label_id: self.feedback_label.configure(text="Label not available.", text_color=ERROR_COLOR); return
        ok = self.attach_label_cb(label_id, self.selected_contact_id)
        self.feedback_label.configure(text="✓ Label attached" if ok else "Attach failed.", text_color=ACCENT_COLOR if ok else ERROR_COLOR)
        self.load_initial_data()

    def _detach_label(self):
        if not self.selected_contact_id or not self.detach_label_cb:
            self.feedback_label.configure(text="Select a contact first.", text_color=ERROR_COLOR); return
        label_name = self.label_menu.get()
        label_id = self._label_name_to_id.get(label_name)
        if not label_id: self.feedback_label.configure(text="Label not available.", text_color=ERROR_COLOR); return
        ok = self.detach_label_cb(label_id, self.selected_contact_id)
        self.feedback_label.configure(text="✓ Label detached" if ok else "Detach failed.", text_color=ACCENT_COLOR if ok else ERROR_COLOR)
        self.load_initial_data()
