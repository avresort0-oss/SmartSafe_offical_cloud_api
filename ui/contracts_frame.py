import customtkinter as ctk
from tkinter import filedialog
from typing import Any, Callable, Dict, List, Optional
import os
import subprocess
import sys

from services.workspace_service import WorkspaceDTO

from .styles import (
    BG_COLOR, SURFACE_COLOR, INPUT_COLOR, HOVER_COLOR, ACTIVE_COLOR,
    ACCENT_COLOR, ACCENT_HOVER, TEXT_COLOR, SUB_TEXT_COLOR, ERROR_COLOR, DIVIDER_COLOR,
    CARD_RADIUS, CARD_RADIUS_SM, INPUT_RADIUS,
    PAD_XS, PAD_SM, PAD_MD, PAD_LG, PAD_XL, PAD_2XL, PAD_3XL,
    FONT_2XL, FONT_XL, FONT_LG, FONT_MD, FONT_SM, FONT_XS,
    heading_font, body_font,
    create_section_header, create_premium_button, create_premium_input,
)

class ContractsFrame(ctk.CTkFrame):
    def __init__(self, master: ctk.CTkFrame,
                 load_contracts_cb: Optional[Callable[[], List[Any]]] = None,
                 load_contacts_cb: Optional[Callable[[], List[Any]]] = None,
                 create_contract_cb: Optional[Callable[[Dict[str, Any]], Any]] = None,
                 update_contract_status_cb: Optional[Callable[[str, str], Any]] = None,
                 **kwargs):
        super().__init__(master, fg_color=BG_COLOR, corner_radius=0, **kwargs)
        self.load_contracts_cb = load_contracts_cb
        self.load_contacts_cb = load_contacts_cb
        self.create_contract_cb = create_contract_cb
        self.update_contract_status_cb = update_contract_status_cb
        self.current_workspace: Optional[WorkspaceDTO] = None
        self._contacts: List[Any] = []
        self._contact_label_to_id: Dict[str, str] = {}
        self._selected_doc_path: Optional[str] = None

        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=3)
        self.grid_columnconfigure(1, weight=7)

        self._build_header()
        self._build_list_panel()
        self._build_form_panel()
        self.load_initial_data()

    def configure_callbacks(self, load_contracts_cb, load_contacts_cb, create_contract_cb, update_contract_status_cb):
        self.load_contracts_cb = load_contracts_cb
        self.load_contacts_cb = load_contacts_cb
        self.create_contract_cb = create_contract_cb
        self.update_contract_status_cb = update_contract_status_cb

    def refresh_workspace(self, workspace: WorkspaceDTO):
        self.current_workspace = workspace
        self.load_initial_data()

    def _build_header(self):
        self.header_frame = create_section_header(self, "Contracts", "Manage legal documents and SLAs")
        self.header_frame.grid(row=0, column=0, columnspan=2, sticky="ew", padx=PAD_3XL, pady=(PAD_2XL, PAD_MD))

    def _build_list_panel(self):
        self.list_panel = ctk.CTkFrame(self, fg_color=SURFACE_COLOR, corner_radius=CARD_RADIUS)
        self.list_panel.grid(row=1, column=0, sticky="nsew", padx=(PAD_3XL, PAD_SM), pady=(0, PAD_2XL))
        self.list_panel.grid_rowconfigure(1, weight=1)
        self.list_panel.grid_columnconfigure(0, weight=1)

        search_row = ctk.CTkFrame(self.list_panel, fg_color="transparent")
        search_row.grid(row=0, column=0, sticky="ew", padx=PAD_LG, pady=PAD_LG)
        ctk.CTkLabel(search_row, text="All Contracts", font=heading_font(FONT_LG), text_color=TEXT_COLOR).pack(side="left")
        ctk.CTkButton(search_row, text="↻", width=36, height=36, corner_radius=CARD_RADIUS_SM, command=self.refresh_list, fg_color=INPUT_COLOR, hover_color=HOVER_COLOR).pack(side="right")

        self.list_scroll = ctk.CTkScrollableFrame(self.list_panel, fg_color="transparent")
        self.list_scroll.grid(row=1, column=0, sticky="nsew", padx=PAD_SM, pady=(0, PAD_MD))

    def _build_form_panel(self):
        self.form_panel = ctk.CTkFrame(self, fg_color=SURFACE_COLOR, corner_radius=CARD_RADIUS)
        self.form_panel.grid(row=1, column=1, sticky="nsew", padx=(PAD_SM, PAD_3XL), pady=(0, PAD_2XL))
        self.form_panel.grid_columnconfigure(0, weight=1)
        self.form_panel.grid_rowconfigure(0, weight=1)

        self.form_scroll = ctk.CTkScrollableFrame(self.form_panel, fg_color="transparent")
        self.form_scroll.grid(row=0, column=0, sticky="nsew", padx=PAD_2XL, pady=PAD_2XL)
        self.form_scroll.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(self.form_scroll, text="Log New Contract", font=heading_font(FONT_XL), text_color=TEXT_COLOR).pack(anchor="w", pady=(0, PAD_XL))

        ctk.CTkLabel(self.form_scroll, text="Associated Client", text_color=SUB_TEXT_COLOR, font=ctk.CTkFont(weight="bold")).pack(anchor="w", pady=(0, PAD_SM))
        self.contact_menu = ctk.CTkOptionMenu(self.form_scroll, values=["No Contacts"], fg_color=INPUT_COLOR, button_color=INPUT_COLOR, corner_radius=INPUT_RADIUS, height=40, dropdown_fg_color=SURFACE_COLOR, dropdown_text_color=TEXT_COLOR, dropdown_hover_color=HOVER_COLOR)
        self.contact_menu.pack(fill="x", pady=(0, PAD_LG))

        self._build_input_field("Contract Title", self.form_scroll, "title_entry", "e.g. Master Service Agreement")
        self._build_input_field("Contract Number", self.form_scroll, "number_entry", "e.g. MSA-2026-001")

        ctk.CTkLabel(self.form_scroll, text="Contract Type", text_color=SUB_TEXT_COLOR, font=ctk.CTkFont(weight="bold")).pack(anchor="w", pady=(0, PAD_SM))
        self.type_menu = ctk.CTkOptionMenu(self.form_scroll, values=["SERVICE", "NDA", "MSA", "OTHER"], fg_color=INPUT_COLOR, button_color=INPUT_COLOR, corner_radius=INPUT_RADIUS, height=40, dropdown_fg_color=SURFACE_COLOR, dropdown_text_color=TEXT_COLOR, dropdown_hover_color=HOVER_COLOR)
        self.type_menu.pack(fill="x", pady=(0, PAD_LG))

        ctk.CTkLabel(self.form_scroll, text="Document Attachment", text_color=SUB_TEXT_COLOR, font=ctk.CTkFont(weight="bold")).pack(anchor="w", pady=(0, PAD_SM))
        doc_row = ctk.CTkFrame(self.form_scroll, fg_color="transparent")
        doc_row.pack(fill="x", pady=(0, PAD_XL))
        self.doc_btn = ctk.CTkButton(doc_row, text="📎 Select File", command=self._select_doc, fg_color=INPUT_COLOR, hover_color=HOVER_COLOR, corner_radius=INPUT_RADIUS, height=40, width=120)
        self.doc_btn.pack(side="left")
        self.doc_status_lbl = ctk.CTkLabel(doc_row, text="No file selected", text_color=SUB_TEXT_COLOR)
        self.doc_status_lbl.pack(side="left", padx=PAD_MD)

        self.create_btn = create_premium_button(self.form_scroll, text="Create Contract", variant="primary", command=self._create_contract, height=45)
        self.create_btn.pack(fill="x", pady=(PAD_XL, PAD_MD))
        self.status_label = ctk.CTkLabel(self.form_scroll, text="", text_color=SUB_TEXT_COLOR)
        self.status_label.pack()

    def _build_input_field(self, label_text, parent, attr_name, placeholder):
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", pady=(0, PAD_LG))
        ctk.CTkLabel(row, text=label_text, text_color=SUB_TEXT_COLOR, font=ctk.CTkFont(weight="bold")).pack(anchor="w", pady=(0, 2))
        entry = create_premium_input(row, placeholder)
        entry.pack(fill="x")
        setattr(self, attr_name, entry)

    def _read(self, item, key, default=None):
        if hasattr(item, key): return getattr(item, key)
        if isinstance(item, dict): return item.get(key, default)
        return default

    def load_initial_data(self):
        self._contacts = self.load_contacts_cb() if self.load_contacts_cb else []
        self._contact_label_to_id.clear()
        labels = []
        for c in self._contacts:
            cid = self._read(c, "id")
            name = self._read(c, "display_name", "Unknown")
            phone = self._read(c, "phone_e164", "")
            label = f"{name} ({phone})"
            labels.append(label)
            self._contact_label_to_id[label] = cid
        if not labels: labels = ["No Contacts"]
        self.contact_menu.configure(values=labels)
        self.contact_menu.set(labels[0])
        self.refresh_list()

    def refresh_list(self):
        for child in self.list_scroll.winfo_children(): child.destroy()
        rows = self.load_contracts_cb() if self.load_contracts_cb else []
        if not rows:
            ctk.CTkLabel(self.list_scroll, text="No contracts found.", text_color=SUB_TEXT_COLOR).pack(pady=PAD_2XL)
            return
        for row in rows: self._render_contract(row)

    def _render_contract(self, row):
        card = ctk.CTkFrame(self.list_scroll, fg_color=INPUT_COLOR, corner_radius=CARD_RADIUS_SM)
        card.pack(fill="x", padx=PAD_XS, pady=PAD_XS)
        cid = self._read(row, "id")
        title = self._read(row, "title", "Untitled")
        number = self._read(row, "contract_number", "-")
        status = self._read(row, "status", "DRAFT")
        doc_path = self._read(row, "document_path", "")
        status_colors = {"ACTIVE": ACCENT_COLOR, "DRAFT": SUB_TEXT_COLOR, "EXPIRED": ERROR_COLOR, "PAUSED": "#e9c46a", "CANCELLED": ERROR_COLOR}
        border_color = status_colors.get(status, SUB_TEXT_COLOR)

        accent = ctk.CTkFrame(card, fg_color=border_color, width=4, corner_radius=2)
        accent.pack(side="left", fill="y", padx=(4, 0), pady=PAD_SM)
        info = ctk.CTkFrame(card, fg_color="transparent")
        info.pack(side="left", fill="both", expand=True, padx=PAD_MD, pady=PAD_MD)

        top_row = ctk.CTkFrame(info, fg_color="transparent")
        top_row.pack(fill="x")
        ctk.CTkLabel(top_row, text=title, text_color=TEXT_COLOR, font=ctk.CTkFont(size=FONT_MD, weight="bold")).pack(side="left")
        status_menu = ctk.CTkOptionMenu(top_row, values=["DRAFT", "ACTIVE", "PAUSED", "EXPIRED", "CANCELLED"], fg_color="transparent", button_color="transparent", button_hover_color=HOVER_COLOR, text_color=border_color, font=ctk.CTkFont(size=FONT_XS, weight="bold"), command=lambda s, contract_id=cid: self._change_status(contract_id, s), width=100, height=24, corner_radius=4)
        status_menu.set(status)
        status_menu.pack(side="right")

        bottom_row = ctk.CTkFrame(info, fg_color="transparent")
        bottom_row.pack(fill="x", pady=(PAD_XS, 0))
        ctk.CTkLabel(bottom_row, text=f"#{number}", text_color=SUB_TEXT_COLOR, font=body_font(FONT_SM)).pack(side="left")
        if doc_path:
            ctk.CTkButton(bottom_row, text="📄 Open", width=60, height=24, corner_radius=4, fg_color="transparent", hover_color=HOVER_COLOR, text_color=TEXT_COLOR, command=lambda p=doc_path: self._open_doc(p)).pack(side="right")

    def _select_doc(self):
        selected = filedialog.askopenfilename(title="Select Contract Document")
        if selected:
            self._selected_doc_path = selected
            self.doc_status_lbl.configure(text=os.path.basename(selected), text_color=TEXT_COLOR)

    def _create_contract(self):
        if not self.create_contract_cb: return
        contact_label = self.contact_menu.get()
        contact_id = self._contact_label_to_id.get(contact_label)
        if not contact_id:
            self.status_label.configure(text="Error: valid contact required.", text_color=ERROR_COLOR); return
        title = self.title_entry.get().strip()
        if not title:
            self.status_label.configure(text="Error: title required.", text_color=ERROR_COLOR); return
        payload = {"contact_id": contact_id, "title": title, "contract_number": self.number_entry.get().strip() or None, "contract_type": self.type_menu.get(), "document_path": self._selected_doc_path}
        try:
            self.create_contract_cb(payload)
            self.title_entry.delete(0, "end"); self.number_entry.delete(0, "end")
            self._selected_doc_path = None
            self.doc_status_lbl.configure(text="No file selected", text_color=SUB_TEXT_COLOR)
            self.status_label.configure(text="✓ Contract created successfully.", text_color=ACCENT_COLOR)
            self.refresh_list()
        except Exception as e:
            self.status_label.configure(text=f"Error: {e}", text_color=ERROR_COLOR)

    def _change_status(self, contract_id, status):
        if not self.update_contract_status_cb or not contract_id: return
        try:
            self.update_contract_status_cb(contract_id, status)
            self.status_label.configure(text=f"✓ Status updated: {status}", text_color=ACCENT_COLOR)
            self.refresh_list()
        except Exception as e:
            self.status_label.configure(text=f"Status update failed: {e}", text_color=ERROR_COLOR)

    def _open_doc(self, path):
        if not path or not os.path.exists(path):
            self.status_label.configure(text="Document path invalid or file missing.", text_color=ERROR_COLOR); return
        if sys.platform == "win32": os.startfile(path)
        elif sys.platform == "darwin": subprocess.Popen(["open", path])
        else: subprocess.Popen(["xdg-open", path])
