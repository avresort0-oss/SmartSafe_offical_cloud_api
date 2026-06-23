import customtkinter as ctk
import sys
import os
from typing import Optional, List, Callable, Any

from services.workspace_service import WorkspaceDTO, WorkspaceAnalyticsDTO
from services.meta_account_service import MetaAccountDTO
from .account_health_card import AccountHealthCard

from .styles import (
    BG_COLOR, SURFACE_COLOR, TEXT_COLOR, TEXT_SECONDARY, SUB_TEXT_COLOR,
    DIVIDER_COLOR, ACCENT_COLOR,
    CARD_RADIUS, PAD_SM, PAD_MD, PAD_LG, PAD_XL, PAD_2XL, PAD_3XL,
    FONT_3XL, FONT_XL, FONT_LG, FONT_MD, FONT_XS,
    heading_font, body_font,
    create_section_header, create_analytics_card, create_divider,
)


class DashboardFrame(ctk.CTkFrame):
    """
    System Health & Analytics Dashboard.
    Provides a real-time overview of connected Meta WhatsApp Business Accounts
    and key performance metrics for the selected workspace.
    """
    def __init__(self, master: ctk.CTkFrame,
                 refresh_account_cb: Optional[Callable[[str], None]] = None,
                 view_templates_cb: Optional[Callable[[str], None]] = None,
                 **kwargs):
        super().__init__(master, fg_color=BG_COLOR, corner_radius=0, **kwargs)

        self.refresh_account_cb = refresh_account_cb
        self.view_templates_cb = view_templates_cb
        self.account_cards = []
        self._is_loading = False

        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        # Main scrollable container
        self.main_scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.main_scroll.grid(row=0, column=0, sticky="nsew", padx=PAD_XL, pady=PAD_XL)
        self.main_scroll.grid_columnconfigure(0, weight=1)

        # Header
        self.header_frame = create_section_header(self.main_scroll, "Workspace Dashboard", "Health & Activity Overview")
        self.header_frame.grid(row=0, column=0, sticky="ew", pady=(PAD_MD, PAD_3XL), padx=PAD_MD)
        # keep reference to the title label for refresh_data
        self.header_label = self.header_frame.winfo_children()[0]

        # Analytics cards row
        self.analytics_frame = ctk.CTkFrame(self.main_scroll, fg_color="transparent")
        self.analytics_frame.grid(row=1, column=0, sticky="ew", pady=(0, PAD_3XL))
        self.analytics_frame.grid_columnconfigure((0, 1, 2, 3), weight=1)

        self.sent_widget = create_analytics_card(self.analytics_frame, "Messages Sent", "0", "outbound")
        self.sent_widget.grid(row=0, column=0, padx=PAD_MD, sticky="ew")

        self.received_widget = create_analytics_card(self.analytics_frame, "Messages Received", "0", "inbound")
        self.received_widget.grid(row=0, column=1, padx=PAD_MD, sticky="ew")

        self.conversations_widget = create_analytics_card(self.analytics_frame, "Active Conv.", "0", "active")
        self.conversations_widget.grid(row=0, column=2, padx=PAD_MD, sticky="ew")

        self.contacts_widget = create_analytics_card(self.analytics_frame, "New Contacts", "0", "contacts")
        self.contacts_widget.grid(row=0, column=3, padx=PAD_MD, sticky="ew")

        # Divider
        create_divider(self.main_scroll).grid(row=2, column=0, sticky="ew", padx=PAD_MD, pady=(0, PAD_XL))

        # Account Health header
        account_header_frame = ctk.CTkFrame(self.main_scroll, fg_color="transparent")
        account_header_frame.grid(row=3, column=0, sticky="ew", padx=PAD_MD, pady=(0, PAD_LG))
        ctk.CTkLabel(
            account_header_frame, text="Meta Account Health",
            font=heading_font(FONT_XL), text_color=TEXT_COLOR,
        ).pack(side="left")

        self.accounts_container = ctk.CTkFrame(self.main_scroll, fg_color="transparent")
        self.accounts_container.grid(row=4, column=0, sticky="nsew", padx=PAD_SM)
        self.accounts_container.grid_columnconfigure(0, weight=1)

        # Loading Overlay (Simple version)
        self._loading_label = ctk.CTkLabel(
            self.main_scroll, text="Loading dashboard analytics...",
            font=heading_font(FONT_LG), text_color=ACCENT_COLOR
        )
        # Initially hidden

    def show_loading(self):
        """Shows the loading indicator and hides content."""
        self._is_loading = True
        self.analytics_frame.grid_remove()
        self.accounts_container.grid_remove()
        self._loading_label.grid(row=1, column=0, rowspan=4, pady=100)

    def hide_loading(self):
        """Hides the loading indicator and shows content."""
        self._is_loading = False
        self._loading_label.grid_remove()
        self.analytics_frame.grid()
        self.accounts_container.grid()

    def refresh_data(self, stats: WorkspaceAnalyticsDTO, accounts: List[MetaAccountDTO], workspace: WorkspaceDTO):
        """Rewrites the dashboard with fresh data."""
        self.hide_loading()
        self.header_label.configure(text=f"{workspace.name}")

        sent = getattr(stats, "total_messages_sent", getattr(stats, "total_messages", 0))
        received = getattr(stats, "total_messages_received", 0)
        conversations = getattr(stats, "active_conversations", 0)
        contacts = getattr(stats, "new_contacts", 0)

        self.sent_widget.value_label.configure(text=str(sent))
        self.received_widget.value_label.configure(text=str(received))
        self.conversations_widget.value_label.configure(text=str(conversations))
        self.contacts_widget.value_label.configure(text=str(contacts))

        # Clear existing cards efficiently
        for card in self.account_cards:
            if card.winfo_exists():
                card.destroy()
        self.account_cards.clear()

        if not accounts:
            no_accounts_label = ctk.CTkLabel(
                self.accounts_container,
                text="No Meta Accounts linked to this workspace.\nGo to 'Meta Accounts' to bind a new WABA.",
                text_color=SUB_TEXT_COLOR, font=ctk.CTkFont(size=FONT_LG),
            )
            no_accounts_label.pack(pady=40)
            self.account_cards.append(no_accounts_label)
        else:
            # Batch card creation to avoid UI locking if there are many accounts
            for account_dto in accounts:
                card = AccountHealthCard(
                    self.accounts_container,
                    account=account_dto,
                    refresh_callback=self.refresh_account_cb,
                    view_templates_callback=lambda acc_id=account_dto.id: self.view_templates_cb(acc_id) if self.view_templates_cb else None
                )
                card.pack(fill="x", pady=PAD_SM)
                self.account_cards.append(card)
