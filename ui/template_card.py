import customtkinter as ctk
from typing import Dict
import sys
import os

from .styles import (
    SURFACE_COLOR, TEXT_COLOR, SUB_TEXT_COLOR,
    SUCCESS_COLOR, WARNING_COLOR, ERROR_COLOR, BLUE_ACCENT,
)

class TemplateCard(ctk.CTkFrame):
    """
    A UI card component to display details of a single Meta Message Template.
    """
    def __init__(self, master, template_data: Dict, **kwargs):
        super().__init__(master, fg_color=SURFACE_COLOR, corner_radius=8, **kwargs)
        self.template_data = template_data

        self.grid_columnconfigure(1, weight=1)

        status = template_data.get('status', 'UNKNOWN').upper()
        status_color = self._get_status_color(status)

        # --- Left Side: Status Indicator ---
        status_indicator = ctk.CTkFrame(self, width=5, fg_color=status_color, corner_radius=0)
        status_indicator.grid(row=0, column=0, rowspan=4, sticky="ns", padx=(0, 15))

        # --- Right Side: Details ---
        # Row 0: Template Name
        name_label = ctk.CTkLabel(self, text=template_data.get('name', 'Unknown Template'), font=ctk.CTkFont(size=16, weight="bold"), text_color=TEXT_COLOR)
        name_label.grid(row=0, column=1, sticky="w", padx=10, pady=(10, 2))

        # Row 1: Status, Category, Language
        details_frame = ctk.CTkFrame(self, fg_color="transparent")
        details_frame.grid(row=1, column=1, sticky="w", padx=10, pady=0)

        status_label = ctk.CTkLabel(details_frame, text=f"Status: {status}", font=ctk.CTkFont(size=12, weight="bold"), text_color=status_color)
        status_label.pack(side="left", padx=(0, 10))

        category_label = ctk.CTkLabel(details_frame, text=f"Category: {template_data.get('category', 'N/A').title()}", font=ctk.CTkFont(size=12), text_color=SUB_TEXT_COLOR)
        category_label.pack(side="left", padx=(0, 10))

        language_label = ctk.CTkLabel(details_frame, text=f"Lang: {template_data.get('language', 'N/A')}", font=ctk.CTkFont(size=12), text_color=SUB_TEXT_COLOR)
        language_label.pack(side="left")

        # Row 2: Body Preview
        body_preview = self._get_body_preview()
        body_label = ctk.CTkLabel(self, text=body_preview, font=ctk.CTkFont(size=13), text_color=SUB_TEXT_COLOR, justify="left", wraplength=500)
        body_label.grid(row=2, column=1, sticky="w", padx=10, pady=(5, 10))

    def _get_status_color(self, status: str) -> str:
        if status == "APPROVED": return SUCCESS_COLOR
        if status in ("PENDING_DELETION", "PENDING"): return WARNING_COLOR
        if status == "REJECTED": return ERROR_COLOR
        if status == "PAUSED": return BLUE_ACCENT
        return SUB_TEXT_COLOR

    def _get_body_preview(self) -> str:
        components = self.template_data.get('components', [])
        for comp in components:
            if comp.get('type') == 'BODY':
                text = comp.get('text', 'No body text found.')
                return text[:150] + '...' if len(text) > 150 else text
        return "No body component found."