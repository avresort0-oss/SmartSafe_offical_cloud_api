import customtkinter as ctk
import sys
import os
from typing import Optional, List, Callable, Dict

from services.meta_account_service import MetaAccountDTO
from .template_card import TemplateCard
from .styles import BG_COLOR, TEXT_COLOR, SUB_TEXT_COLOR

class TemplateViewerFrame(ctk.CTkFrame):
    """
    A view to display all message templates for a given Meta Account.
    """
    def __init__(self, master: ctk.CTkFrame, back_to_dashboard_cb: Callable, **kwargs):
        super().__init__(master, fg_color=BG_COLOR, corner_radius=0, **kwargs)
        self.back_to_dashboard_cb = back_to_dashboard_cb
        self.template_cards = []

        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)

        # --- Header ---
        header_frame = ctk.CTkFrame(self, fg_color="transparent")
        header_frame.grid(row=0, column=0, sticky="ew", padx=20, pady=20)
        header_frame.grid_columnconfigure(1, weight=1)

        back_btn = ctk.CTkButton(header_frame, text="< Back to Dashboard", command=self.back_to_dashboard_cb, fg_color="transparent", hover=False, text_color=SUB_TEXT_COLOR)
        back_btn.grid(row=0, column=0, sticky="w")

        self.header_label = ctk.CTkLabel(header_frame, text="Message Templates", font=ctk.CTkFont(size=24, weight="bold"), text_color=TEXT_COLOR)
        self.header_label.grid(row=0, column=1, sticky="w", padx=20)

        # --- Templates List ---
        self.scrollable_frame = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.scrollable_frame.grid(row=1, column=0, sticky="nsew", padx=20, pady=(0, 20))
        self.scrollable_frame.grid_columnconfigure(0, weight=1)

    def refresh_data(self, templates: List[Dict], account: MetaAccountDTO):
        """
        Clears and repopulates the view with a list of message templates.
        """
        self.header_label.configure(text=f"Message Templates for {account.display_name}")

        for card in self.template_cards:
            card.destroy()
        self.template_cards.clear()

        if not templates:
            no_templates_label = ctk.CTkLabel(self.scrollable_frame, text="No message templates found for this account.", text_color=SUB_TEXT_COLOR, font=ctk.CTkFont(size=14))
            no_templates_label.pack(pady=50)
            self.template_cards.append(no_templates_label)
        else:
            for template_data in templates:
                card = TemplateCard(self.scrollable_frame, template_data=template_data)
                card.pack(fill="x", expand=True, padx=5, pady=5)
                self.template_cards.append(card)
