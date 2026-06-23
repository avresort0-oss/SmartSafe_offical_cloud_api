# -*- coding: utf-8 -*-
import customtkinter as ctk
from typing import Callable, List, Optional

from services.user_service import UserResponseDTO
from services.workspace_service import WorkspaceDTO

from .styles import (
    BG_COLOR, SURFACE_COLOR, HOVER_COLOR, ACTIVE_COLOR,
    ACCENT_COLOR, ACCENT_HOVER, TEXT_COLOR, TEXT_SECONDARY, SUB_TEXT_COLOR,
    ERROR_COLOR, DIVIDER_COLOR, INPUT_COLOR,
    SIDEBAR_WIDTH, FONT_LG, FONT_MD, FONT_SM, FONT_XS, FONT_2XS,
    CARD_RADIUS_SM, PAD_XS, PAD_SM, PAD_MD, PAD_LG, PAD_XL,
    heading_font, body_font, caption_font,
)

SIDEBAR_BG = "#0d171e"


class CollapsibleSidebar(ctk.CTkFrame):
    """
    Premium navigation sidebar for workspace and module selection.
    """

    def __init__(
        self,
        master: ctk.CTkFrame,
        current_user: UserResponseDTO,
        workspaces: List[WorkspaceDTO],
        on_logout: Callable,
        on_workspace_select: Callable[[WorkspaceDTO], None],
        on_dashboard_select: Callable,
        on_settings_select: Callable,
        on_global_search: Callable[[str], None],
        on_kanban_select: Optional[Callable] = None,
        on_audit_log_select: Optional[Callable] = None,
        on_inbox_select: Optional[Callable] = None,
        on_contacts_select: Optional[Callable] = None,
        on_contracts_select: Optional[Callable] = None,
        on_members_select: Optional[Callable] = None,
        on_accounts_select: Optional[Callable] = None,
        on_bulk_message_select: Optional[Callable] = None,
        on_lead_analytics_select: Optional[Callable] = None,
        on_quick_replies_select: Optional[Callable] = None,
        on_auto_reply_select: Optional[Callable] = None,
        enable_inbox_v2: bool = True,
        enable_contacts_crm: bool = True,
        enable_contracts: bool = True,
        current_role: str = 'ADMIN',
        **kwargs,
    ):
        super().__init__(master, fg_color=SIDEBAR_BG, corner_radius=0, width=SIDEBAR_WIDTH, **kwargs)
        self.grid_propagate(False)

        self.current_user = current_user
        self.workspaces = workspaces
        self.current_role = current_role
        self.on_logout = on_logout
        self.on_workspace_select = on_workspace_select
        self.on_dashboard_select = on_dashboard_select
        self.on_kanban_select = on_kanban_select
        self.on_audit_log_select = on_audit_log_select
        self.on_settings_select = on_settings_select
        self.on_global_search = on_global_search
        self.on_inbox_select = on_inbox_select
        self.on_contacts_select = on_contacts_select
        self.on_contracts_select = on_contracts_select
        self.on_members_select = on_members_select
        self.on_accounts_select = on_accounts_select
        self.on_bulk_message_select = on_bulk_message_select
        self.on_lead_analytics_select = on_lead_analytics_select
        self.on_quick_replies_select = on_quick_replies_select
        self.on_auto_reply_select = on_auto_reply_select
        self.enable_inbox_v2 = enable_inbox_v2
        self.enable_contacts_crm = enable_contacts_crm
        self.enable_contracts = enable_contracts

        self._active_btn = None

        self.grid_rowconfigure(0, weight=0)   # header
        self.grid_rowconfigure(1, weight=1)   # nav scroll
        self.grid_rowconfigure(2, weight=0)   # footer
        self.grid_columnconfigure(0, weight=1)

        self._build_header()
        self._build_main_nav()
        self._build_footer()

    # ── Feature flag update ────────────────────────────────────────────────────

    def update_feature_flags(self, enable_inbox_v2: bool, enable_contacts_crm: bool, enable_contracts: bool, current_role: str = "ADMIN"):
        self.enable_inbox_v2 = enable_inbox_v2
        self.enable_contacts_crm = enable_contacts_crm
        self.enable_contracts = enable_contracts
        self.current_role = current_role
        self._build_main_nav()

    # ── Header ─────────────────────────────────────────────────────────────────

    def _build_header(self):
        self.header_frame = ctk.CTkFrame(self, fg_color="transparent", height=72)
        self.header_frame.grid(row=0, column=0, sticky="ew", padx=PAD_MD, pady=(PAD_LG, PAD_XS))
        self.header_frame.pack_propagate(False)

        # Avatar circle with accent glow
        initial = self.current_user.username[0].upper() if self.current_user.username else "?"
        self.profile_btn = ctk.CTkLabel(
            self.header_frame,
            text=initial,
            width=44, height=44,
            corner_radius=22,
            fg_color=ACCENT_COLOR,
            text_color="#ffffff",
            font=ctk.CTkFont(size=18, weight="bold"),
        )
        self.profile_btn.pack(side="left")

        # User info
        info = ctk.CTkFrame(self.header_frame, fg_color="transparent")
        info.pack(side="left", fill="x", expand=True, padx=(PAD_MD, 0))

        ctk.CTkLabel(
            info,
            text=self.current_user.username,
            font=ctk.CTkFont(size=FONT_MD, weight="bold"),
            text_color=TEXT_COLOR,
            anchor="w",
        ).pack(fill="x")

        ctk.CTkLabel(
            info,
            text="● Online",
            font=ctk.CTkFont(size=FONT_XS),
            text_color=ACCENT_COLOR,
            anchor="w",
        ).pack(fill="x")

        # Divider below header
        ctk.CTkFrame(self, fg_color=DIVIDER_COLOR, height=1).grid(
            row=0, column=0, sticky="sew", padx=0
        )

    # ── Main Navigation ────────────────────────────────────────────────────────

    def _build_main_nav(self):
        if hasattr(self, "main_nav_frame") and self.main_nav_frame.winfo_exists():
            self.main_nav_frame.destroy()

        self.main_nav_frame = ctk.CTkScrollableFrame(
            self, fg_color="transparent",
            scrollbar_button_color=SURFACE_COLOR,
            scrollbar_button_hover_color=HOVER_COLOR,
        )
        self.main_nav_frame.grid(row=1, column=0, sticky="nsew", padx=0, pady=0)

        # Search bar
        search_wrapper = ctk.CTkFrame(self.main_nav_frame, fg_color=INPUT_COLOR, corner_radius=CARD_RADIUS_SM)
        search_wrapper.pack(fill="x", padx=PAD_MD, pady=(PAD_MD, PAD_SM))

        self.search_entry = ctk.CTkEntry(
            search_wrapper,
            placeholder_text="🔍  Search messages...",
            fg_color="transparent",
            border_width=0,
            corner_radius=CARD_RADIUS_SM,
            height=36,
            text_color=TEXT_COLOR,
            placeholder_text_color=TEXT_SECONDARY,
            font=ctk.CTkFont(size=FONT_SM),
        )
        self.search_entry.pack(fill="x", padx=PAD_SM, pady=PAD_XS)
        self.search_entry.bind("<Return>", lambda _e: self.on_global_search(self.search_entry.get()))

        # Section label
        self._section_label("NAVIGATION")

        # Nav buttons — premium pill style with emoji icons
        nav_defs = [
            ("💬", "Inbox",         self.on_inbox_select,         self.enable_inbox_v2),
            ("👥", "Contacts",      self.on_contacts_select,      self.enable_contacts_crm),
            ("📋", "Pipeline",      self.on_kanban_select,      True),
            ("📝", "Contracts",     self.on_contracts_select,     self.enable_contracts),
            ("📊", "Dashboard",     self.on_dashboard_select,     True),
            ("🔗", "Meta Accounts", self.on_accounts_select,      True),
            ("📤", "Bulk Messages", self.on_bulk_message_select,  True),
            ("📈", "Analytics",     self.on_lead_analytics_select,True),
            ("⚡", "Quick Replies", self.on_quick_replies_select, True),
            ("🤖", "Auto Reply",   self.on_auto_reply_select,    True),
            ("⚙️", "Settings",      self.on_settings_select,      True),
            ("🛡️", "Audit Logs",    self.on_audit_log_select,    True),

        ]

        for icon, label, cb, enabled in nav_defs:
            if label == "Contacts" and not self.enable_contacts_crm:
                continue
            if label == "Contracts" and not self.enable_contracts:
                continue
            if label == "Inbox" and not self.enable_inbox_v2:
                continue
                
            # RBAC Enforcement
            if self.current_role.upper() == "AGENT" and label in ["Settings", "Meta Accounts", "Bulk Messages", "Audit Logs", "Quick Replies", "Auto Reply"]:
                continue
            if self.current_role.upper() == "MANAGER" and label in ["Settings", "Meta Accounts", "Audit Logs"]:
                continue

            if cb is None:
                continue
            self._add_nav_button(icon, label, cb)

        if self.on_members_select and not self.enable_contacts_crm:
            self._add_nav_button("👥", "Members", self.on_members_select)

        # Workspaces section
        self._section_label("WORKSPACES")

        for ws in self.workspaces:
            self._add_workspace_button(ws)

    def _section_label(self, text: str):
        ctk.CTkLabel(
            self.main_nav_frame,
            text=text,
            font=ctk.CTkFont(size=FONT_2XS, weight="bold"),
            text_color=TEXT_SECONDARY,
            anchor="w",
        ).pack(fill="x", padx=PAD_LG, pady=(PAD_LG, PAD_XS))

    def _add_nav_button(self, icon: str, label: str, command: Callable):
        """Renders a premium pill-style nav tab with emoji icon + label."""
        row = ctk.CTkFrame(self.main_nav_frame, fg_color="transparent", cursor="hand2")
        row.pack(fill="x", padx=PAD_SM, pady=2)

        btn = ctk.CTkButton(
            row,
            text=f" {icon}  {label}",
            image=None,
            anchor="w",
            fg_color="transparent",
            hover_color=HOVER_COLOR,
            text_color=TEXT_SECONDARY,
            font=ctk.CTkFont(size=FONT_MD),
            height=40,
            corner_radius=CARD_RADIUS_SM,
            command=lambda c=command, b=row: self._on_nav_click(c, b),
        )
        btn.pack(fill="x")

        row._nav_btn = btn
        return row

    def _on_nav_click(self, command: Callable, row_frame: ctk.CTkFrame):
        """Activates clicked tab with accent styling, deactivates previous."""
        if self._active_btn and self._active_btn.winfo_exists():
            self._active_btn._nav_btn.configure(
                fg_color="transparent",
                text_color=TEXT_SECONDARY,
            )
        self._active_btn = row_frame
        row_frame._nav_btn.configure(
            fg_color=ACTIVE_COLOR,
            text_color=TEXT_COLOR,
        )
        if command:
            command()

    # ── Workspace Button ───────────────────────────────────────────────────────

    def _add_workspace_button(self, workspace: WorkspaceDTO):
        row = ctk.CTkFrame(self.main_nav_frame, fg_color="transparent", corner_radius=CARD_RADIUS_SM, height=60, cursor="hand2")
        row.pack(fill="x", padx=PAD_SM, pady=2)
        row.pack_propagate(False)

        def on_enter(_e): row.configure(fg_color=HOVER_COLOR)
        def on_leave(_e): row.configure(fg_color="transparent")
        row.bind("<Enter>", on_enter)
        row.bind("<Leave>", on_leave)
        row.bind("<Button-1>", lambda _e: self.on_workspace_select(workspace))

        # Workspace avatar
        initial = (workspace.name[0].upper() if workspace.name else "?")
        avatar = ctk.CTkLabel(
            row,
            text=initial,
            width=38, height=38,
            corner_radius=CARD_RADIUS_SM,
            fg_color=SURFACE_COLOR,
            text_color=ACCENT_COLOR,
            font=ctk.CTkFont(size=FONT_MD, weight="bold"),
        )
        avatar.pack(side="left", padx=(PAD_MD, PAD_SM), pady=PAD_MD)
        avatar.bind("<Button-1>", lambda _e: self.on_workspace_select(workspace))

        info = ctk.CTkFrame(row, fg_color="transparent")
        info.pack(side="left", fill="both", expand=True, pady=PAD_MD)
        info.bind("<Button-1>", lambda _e: self.on_workspace_select(workspace))

        name_lbl = ctk.CTkLabel(
            info, text=workspace.name,
            font=ctk.CTkFont(size=FONT_SM, weight="bold"),
            text_color=TEXT_COLOR, anchor="w",
        )
        name_lbl.pack(fill="x")
        name_lbl.bind("<Button-1>", lambda _e: self.on_workspace_select(workspace))

        role_lbl = ctk.CTkLabel(
            info,
            text=getattr(workspace, "role", "Member"),
            font=ctk.CTkFont(size=FONT_XS),
            text_color=TEXT_SECONDARY, anchor="w",
        )
        role_lbl.pack(fill="x")
        role_lbl.bind("<Button-1>", lambda _e: self.on_workspace_select(workspace))

    # ── Footer ─────────────────────────────────────────────────────────────────

    def _build_footer(self):
        # Top divider
        ctk.CTkFrame(self, fg_color=DIVIDER_COLOR, height=1).grid(
            row=2, column=0, sticky="new", padx=0
        )

        self.footer_frame = ctk.CTkFrame(self, fg_color="transparent", height=56)
        self.footer_frame.grid(row=2, column=0, sticky="ew", padx=PAD_MD, pady=PAD_SM)
        self.footer_frame.grid_propagate(False)
        self.footer_frame.grid_columnconfigure(0, weight=1)
        self.footer_frame.grid_columnconfigure(1, weight=0)

        # Version label
        ctk.CTkLabel(
            self.footer_frame,
            text="SmartSafe v28 Enterprise",
            font=ctk.CTkFont(size=FONT_2XS),
            text_color=TEXT_SECONDARY,
            anchor="w",
        ).grid(row=0, column=0, sticky="w", padx=PAD_SM)

        # Logout button
        self.logout_button = ctk.CTkButton(
            self.footer_frame,
            text="Logout",
            width=72, height=30,
            fg_color="transparent",
            hover_color="#2a1a1a",
            text_color=ERROR_COLOR,
            border_width=1,
            border_color=ERROR_COLOR,
            corner_radius=6,
            font=ctk.CTkFont(size=FONT_SM, weight="bold"),
            command=self.on_logout,
        )
        self.logout_button.grid(row=0, column=1, sticky="e", padx=PAD_XS)

    # ── Global search dialog ───────────────────────────────────────────────────

    def _handle_global_search_input(self):
        dialog = ctk.CTkInputDialog(text="Enter search query:", title="Global Search")
        query = dialog.get_input()
        if query:
            self.on_global_search(query)
