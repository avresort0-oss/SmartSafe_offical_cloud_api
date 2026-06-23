import customtkinter as ctk
from typing import List, Optional
from services.contact_service import ContactDTO
from services.contract_service import ContractDTO
from services.workspace_service import WorkspaceDTO

from .styles import (
    BG_COLOR, SURFACE_COLOR, TEXT_COLOR, SUB_TEXT_COLOR, DIVIDER_COLOR, ACCENT_COLOR,
    CARD_RADIUS, PAD_SM, PAD_MD, PAD_LG, PAD_XL, PAD_3XL,
    FONT_3XL, FONT_XL, FONT_LG, FONT_MD, FONT_XS,
    heading_font,
    create_section_header, create_analytics_card, create_divider,
)


class LeadAnalyticsFrame(ctk.CTkFrame):
    """Lead Analytics Dashboard (Premium Redesign)."""

    def __init__(self, master: ctk.CTkFrame, **kwargs):
        super().__init__(master, fg_color=BG_COLOR, corner_radius=0, **kwargs)
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self.main_scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.main_scroll.grid(row=0, column=0, sticky="nsew", padx=PAD_XL, pady=PAD_XL)
        self.main_scroll.grid_columnconfigure(0, weight=1)

        self._build_header()
        self._build_analytics_section()
        self._build_lists()

        # Loading Indicator
        self._loading_label = ctk.CTkLabel(
            self.main_scroll, text="Loading lead analytics...",
            font=heading_font(FONT_LG), text_color=ACCENT_COLOR
        )

    def show_loading(self):
        self.analytics_frame.grid_remove()
        self._loading_label.grid(row=1, column=0, rowspan=3, pady=100)

    def hide_loading(self):
        self._loading_label.grid_remove()
        self.analytics_frame.grid()

    def _build_header(self):
        self.header_frame = ctk.CTkFrame(self.main_scroll, fg_color="transparent")
        self.header_frame.grid(row=0, column=0, sticky="ew", pady=(PAD_MD, PAD_3XL), padx=PAD_MD)
        self.header_label = ctk.CTkLabel(self.header_frame, text="Lead Analytics Dashboard", font=heading_font(FONT_3XL), text_color=TEXT_COLOR)
        self.header_label.pack(side="left")
        ctk.CTkLabel(self.header_frame, text=" | CRM & Pipelines", font=ctk.CTkFont(size=FONT_MD), text_color=SUB_TEXT_COLOR).pack(side="left", padx=PAD_MD, pady=(6, 0))

    def _build_analytics_section(self):
        self.analytics_frame = ctk.CTkFrame(self.main_scroll, fg_color="transparent")
        self.analytics_frame.grid(row=1, column=0, sticky="ew", pady=(0, PAD_3XL))
        self.analytics_frame.grid_columnconfigure((0, 1, 2, 3), weight=1)

        self.total_contacts_widget = create_analytics_card(self.analytics_frame, "Total Contacts", "0", "contacts")
        self.total_contacts_widget.grid(row=0, column=0, padx=PAD_MD, sticky="ew")
        self.leads_widget = create_analytics_card(self.analytics_frame, "Total Leads", "0", "leads")
        self.leads_widget.grid(row=0, column=1, padx=PAD_MD, sticky="ew")
        self.customers_widget = create_analytics_card(self.analytics_frame, "Total Customers", "0", "customers")
        self.customers_widget.grid(row=0, column=2, padx=PAD_MD, sticky="ew")
        self.contracts_widget = create_analytics_card(self.analytics_frame, "Active Contracts", "0", "contracts")
        self.contracts_widget.grid(row=0, column=3, padx=PAD_MD, sticky="ew")

    def _build_lists(self):
        create_divider(self.main_scroll).grid(row=2, column=0, sticky="ew", padx=PAD_MD, pady=(0, PAD_XL))

        content_row = ctk.CTkFrame(self.main_scroll, fg_color="transparent")
        content_row.grid(row=3, column=0, sticky="nsew", padx=PAD_MD)
        content_row.grid_columnconfigure((0, 1), weight=1)

        recent_leads = ctk.CTkFrame(content_row, fg_color=SURFACE_COLOR, corner_radius=CARD_RADIUS)
        recent_leads.grid(row=0, column=0, sticky="nsew", padx=(0, PAD_MD))
        ctk.CTkLabel(recent_leads, text="Recent Leads", font=heading_font(FONT_LG), text_color=TEXT_COLOR).pack(anchor="w", padx=PAD_XL, pady=(PAD_XL, PAD_MD))
        ctk.CTkLabel(recent_leads, text="No recent leads.", text_color=SUB_TEXT_COLOR).pack(pady=40)

        pipeline_stats = ctk.CTkFrame(content_row, fg_color=SURFACE_COLOR, corner_radius=CARD_RADIUS)
        pipeline_stats.grid(row=0, column=1, sticky="nsew", padx=(PAD_MD, 0))
        ctk.CTkLabel(pipeline_stats, text="Pipeline Overview", font=heading_font(FONT_LG), text_color=TEXT_COLOR).pack(anchor="w", padx=PAD_XL, pady=(PAD_XL, PAD_MD))
        ctk.CTkLabel(pipeline_stats, text="More analytics widgets coming soon.", text_color=SUB_TEXT_COLOR).pack(pady=40)

    def refresh_data(self, workspace: WorkspaceDTO, contacts: List[ContactDTO], contracts: List[ContractDTO]):
        self.hide_loading()
        if workspace:
            self.header_label.configure(text=f"{workspace.name}")
        total_contacts = len(contacts)
        total_leads = sum(1 for c in contacts if c.lifecycle_stage == "LEAD")
        total_customers = sum(1 for c in contacts if c.lifecycle_stage == "CUSTOMER")
        active_contracts = sum(1 for c in contracts if c.status in ("ACTIVE", "SIGNED", "PENDING_SIGNATURE", "DRAFT"))
        self.total_contacts_widget.value_label.configure(text=str(total_contacts))
        self.leads_widget.value_label.configure(text=str(total_leads))
        self.customers_widget.value_label.configure(text=str(total_customers))
        self.contracts_widget.value_label.configure(text=str(active_contracts))
