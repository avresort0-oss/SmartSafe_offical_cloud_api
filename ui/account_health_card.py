import customtkinter as ctk
from typing import Callable, Optional, Any
from datetime import datetime
import sys
import os
import logging

logger = logging.getLogger(__name__)

from services.meta_account_service import MetaAccountDTO
from .tooltip import Tooltip

from .styles import (
    SURFACE_COLOR, INPUT_COLOR, TEXT_COLOR, TEXT_SECONDARY, SUB_TEXT_COLOR,
    ACCENT_COLOR, ERROR_COLOR, WARNING_COLOR,
    CARD_RADIUS_SM, PAD_SM, PAD_MD, PAD_LG, PAD_XL,
    FONT_LG, FONT_SM, FONT_XS,
)

# Aliases for health-specific colors
GREEN_COLOR  = ACCENT_COLOR
YELLOW_COLOR = WARNING_COLOR
RED_COLOR    = ERROR_COLOR


class AccountHealthCard(ctk.CTkFrame):
    """A UI card component to display the health and status of a single Meta WhatsApp Business Account."""
    def __init__(self, master, account: MetaAccountDTO, refresh_callback: Optional[Callable[[str], None]] = None, view_templates_callback: Optional[Callable[[], Any]] = None, **kwargs):
        super().__init__(master, fg_color=SURFACE_COLOR, corner_radius=CARD_RADIUS_SM, **kwargs)
        self.account = account
        self.refresh_callback = refresh_callback
        self.view_templates_callback = view_templates_callback
        self.grid_columnconfigure(1, weight=1)

        status_color = self._get_status_color(account.api_status)
        status_indicator = ctk.CTkFrame(self, width=5, fg_color=status_color, corner_radius=0)
        status_indicator.grid(row=0, column=0, rowspan=4, sticky="ns", padx=(0, PAD_LG))

        name_frame = ctk.CTkFrame(self, fg_color="transparent")
        name_frame.grid(row=0, column=1, sticky="ew", padx=PAD_MD, pady=(PAD_MD, PAD_SM))
        name_frame.grid_columnconfigure(0, weight=1)
        self.display_name_label = ctk.CTkLabel(name_frame, text=account.display_name, font=ctk.CTkFont(size=FONT_LG, weight="bold"), text_color=TEXT_COLOR)
        self.display_name_label.grid(row=0, column=0, sticky="w")
        self.refresh_btn = ctk.CTkButton(name_frame, text="↻", width=30, height=30, fg_color="transparent", hover_color=INPUT_COLOR, text_color=SUB_TEXT_COLOR, command=self._on_refresh)
        self.refresh_btn.grid(row=0, column=1, sticky="e")

        self.phone_label = ctk.CTkLabel(self, text=f"📞 {account.display_phone or 'N/A'} ({account.verified_name or 'Not Verified'})", font=ctk.CTkFont(size=FONT_SM), text_color=SUB_TEXT_COLOR)
        self.phone_label.grid(row=1, column=1, sticky="w", padx=PAD_MD, pady=0)

        quality_color = self._get_quality_color(account.quality_rating)
        status_frame = ctk.CTkFrame(self, fg_color="transparent")
        status_frame.grid(row=2, column=1, sticky="ew", padx=PAD_MD, pady=(PAD_SM, PAD_MD))
        self.quality_label = ctk.CTkLabel(status_frame, text=f"Quality: {account.quality_rating}", font=ctk.CTkFont(size=FONT_SM, weight="bold"), text_color=quality_color)
        self.quality_label.pack(side="left", padx=(0, PAD_LG))
        Tooltip(self.quality_label, text=self._get_quality_tooltip_text(account.quality_rating))
        self.api_status_label = ctk.CTkLabel(status_frame, text=f"Status: {account.api_status}", font=ctk.CTkFont(size=FONT_SM, weight="bold"), text_color=status_color)
        self.api_status_label.pack(side="left")

        action_frame = ctk.CTkFrame(self, fg_color="transparent")
        action_frame.grid(row=3, column=1, sticky="ew", padx=PAD_MD, pady=(0, PAD_MD))
        action_frame.grid_columnconfigure(0, weight=1)
        sync_time_str = self._format_sync_time(account.last_synced_at)
        self.last_synced_label = ctk.CTkLabel(action_frame, text=sync_time_str, font=ctk.CTkFont(size=FONT_XS), text_color=SUB_TEXT_COLOR)
        self.last_synced_label.grid(row=0, column=0, sticky="w")
        self.templates_btn = ctk.CTkButton(action_frame, text="View Templates", height=28, fg_color=INPUT_COLOR, hover_color="#3b4a54", command=self.view_templates_callback)
        self.templates_btn.grid(row=0, column=1, sticky="e")

    def _get_status_color(self, status): return GREEN_COLOR if status == "CONNECTED" else RED_COLOR
    def _get_quality_color(self, quality):
        q = quality.upper()
        if q == "GREEN": return GREEN_COLOR
        if q == "YELLOW": return YELLOW_COLOR
        if q == "RED": return RED_COLOR
        return SUB_TEXT_COLOR
    def _get_quality_tooltip_text(self, quality):
        q = quality.upper()
        if q == "GREEN": return "High Quality: Your account is healthy and can send messages normally."
        if q == "YELLOW": return "Medium Quality: Your account is at risk of being restricted."
        if q == "RED": return "Low Quality: Your account is restricted or disabled."
        return "Quality rating is unknown or not applicable."
    def _format_sync_time(self, sync_time):
        if not sync_time: return "Last synced: Never"
        return f"Last synced: {sync_time.strftime('%b %d, %H:%M')}"
    def _on_refresh(self):
        if self.refresh_callback and callable(self.refresh_callback):
            self.refresh_btn.configure(state="disabled", text="...")
            try:
                self.refresh_callback(self.account.id)
            except Exception as e:
                logger.error(f"UI refresh trigger failed: {e}")
                self.refresh_btn.configure(state="normal", text="↻")
