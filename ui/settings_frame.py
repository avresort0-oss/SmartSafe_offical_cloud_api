import customtkinter as ctk
import sys
import os
import threading
import logging
from typing import Callable, Optional, Dict, Tuple

from .styles import (
    BG_COLOR, SURFACE_COLOR, INPUT_COLOR, HOVER_COLOR, ACTIVE_COLOR,
    ACCENT_COLOR, ACCENT_HOVER, TEXT_COLOR, TEXT_SECONDARY, SUB_TEXT_COLOR,
    ERROR_COLOR, WARNING_COLOR,
    CARD_RADIUS, INPUT_RADIUS, BUTTON_RADIUS, INPUT_HEIGHT, BUTTON_HEIGHT,
    PAD_SM, PAD_MD, PAD_LG, PAD_XL, PAD_2XL, PAD_3XL,
    FONT_3XL, FONT_XL, FONT_LG, FONT_MD, FONT_SM, FONT_XS,
    heading_font, body_font,
    create_section_header, create_premium_input, create_premium_button, create_divider,
)


class SettingsFrame(ctk.CTkFrame):
    """
    Enterprise Settings Component (Premium Redesign).
    Provides the interface for users to configure appearance and application behavior.
    """
    def __init__(
        self,
        master: ctk.CTkFrame,
        on_save_wa_settings: Optional[Callable[[str, str, str], None]] = None,
        load_wa_settings_cb: Optional[Callable[[], Dict[str, str]]] = None,
        check_wa_status_cb: Optional[Callable[[], Tuple[bool, str]]] = None,
        on_save_sync_settings: Optional[Callable[[str], None]] = None,
        load_sync_settings_cb: Optional[Callable[[], Dict[str, str]]] = None,
        on_save_mock_settings: Optional[Callable[[bool], None]] = None,
        load_mock_settings_cb: Optional[Callable[[], Dict[str, bool]]] = None,
        on_save_theme_cb: Optional[Callable[[str], None]] = None,
        load_theme_cb: Optional[Callable[[], str]] = None,
        on_save_feature_flags_cb: Optional[Callable[[bool, bool, bool], None]] = None,
        load_feature_flags_cb: Optional[Callable[[], Dict[str, bool]]] = None,
        **kwargs
    ):
        super().__init__(master, fg_color=BG_COLOR, corner_radius=0, **kwargs)
        self.on_save_wa_settings = on_save_wa_settings
        self.load_wa_settings_cb = load_wa_settings_cb
        self.check_wa_status_cb = check_wa_status_cb
        self.on_save_sync_settings = on_save_sync_settings
        self.load_sync_settings_cb = load_sync_settings_cb
        self.on_save_mock_settings = on_save_mock_settings
        self.load_mock_settings_cb = load_mock_settings_cb
        self.on_save_theme_cb = on_save_theme_cb
        self.load_theme_cb = load_theme_cb
        self.on_save_feature_flags_cb = on_save_feature_flags_cb
        self.load_feature_flags_cb = load_feature_flags_cb

        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        # Main scrollable area
        self.main_scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.main_scroll.grid(row=0, column=0, sticky="nsew", padx=PAD_XL, pady=PAD_XL)
        self.main_scroll.grid_columnconfigure(0, weight=1)

        self._build_header()
        self._build_appearance_section()
        self._build_integrations_section()
        self._build_sync_section()
        self._build_simulation_section()
        self._build_feature_flags_section()

    def _build_header(self):
        self.header_frame = ctk.CTkFrame(self.main_scroll, fg_color="transparent", corner_radius=0)
        self.header_frame.grid(row=0, column=0, sticky="ew", pady=(PAD_MD, PAD_3XL), padx=PAD_MD)

        ctk.CTkLabel(
            self.header_frame, text="Settings", font=heading_font(FONT_3XL), text_color=TEXT_COLOR
        ).pack(anchor="w")

        ctk.CTkLabel(
            self.header_frame, text="Manage your enterprise workspace preferences",
            font=body_font(FONT_MD), text_color=SUB_TEXT_COLOR
        ).pack(anchor="w", pady=(PAD_SM, 0))

    def _create_input(self, parent, placeholder: str, show: str = ""):
        return create_premium_input(parent, placeholder, show=show, width=400)

    # ── Sections ───────────────────────────────────────────────────────────────
    def _build_appearance_section(self):
        card = ctk.CTkFrame(self.main_scroll, fg_color=SURFACE_COLOR, corner_radius=CARD_RADIUS)
        card.grid(row=1, column=0, sticky="ew", padx=PAD_MD, pady=(0, PAD_XL))

        ctk.CTkLabel(card, text="Appearance", font=heading_font(FONT_LG), text_color=TEXT_COLOR).pack(anchor="w", padx=PAD_XL, pady=(PAD_XL, PAD_SM))
        ctk.CTkLabel(card, text="Customize the interface theme.", font=body_font(FONT_SM), text_color=SUB_TEXT_COLOR).pack(anchor="w", padx=PAD_XL, pady=(0, PAD_XL))

        control_frame = ctk.CTkFrame(card, fg_color="transparent")
        control_frame.pack(fill="x", padx=PAD_XL, pady=(0, PAD_XL))

        ctk.CTkLabel(control_frame, text="Theme Mode", font=ctk.CTkFont(size=FONT_MD, weight="bold"), text_color=TEXT_COLOR).pack(side="left")

        self.theme_menu = ctk.CTkOptionMenu(
            control_frame, values=["Dark", "Light", "System"], command=self._change_theme,
            fg_color=INPUT_COLOR, button_color=ACCENT_COLOR, button_hover_color=ACCENT_HOVER, corner_radius=INPUT_RADIUS
        )
        self.theme_menu.pack(side="right")
        self.theme_menu.set("Dark")

    def _change_theme(self, choice: str):
        if self.on_save_theme_cb:
            self.on_save_theme_cb(choice)
        else:
            ctk.set_appearance_mode(choice)

    def _build_integrations_section(self):
        card = ctk.CTkFrame(self.main_scroll, fg_color=SURFACE_COLOR, corner_radius=CARD_RADIUS)
        card.grid(row=2, column=0, sticky="ew", padx=PAD_MD, pady=(0, PAD_XL))

        ctk.CTkLabel(card, text="Integrations", font=heading_font(FONT_LG), text_color=TEXT_COLOR).pack(anchor="w", padx=PAD_XL, pady=(PAD_XL, PAD_SM))
        ctk.CTkLabel(card, text="Configure global external service APIs.", font=body_font(FONT_SM), text_color=SUB_TEXT_COLOR).pack(anchor="w", padx=PAD_XL, pady=(0, PAD_XL))

        wa_token_frame = ctk.CTkFrame(card, fg_color="transparent")
        wa_token_frame.pack(fill="x", padx=PAD_XL, pady=(0, PAD_LG))
        ctk.CTkLabel(wa_token_frame, text="WhatsApp API Token", font=ctk.CTkFont(size=FONT_MD, weight="bold"), text_color=TEXT_COLOR).pack(side="left")
        self.wa_token_entry = self._create_input(wa_token_frame, "Enter graph API access token", show="*")
        self.wa_token_entry.pack(side="right")

        wa_phone_id_frame = ctk.CTkFrame(card, fg_color="transparent")
        wa_phone_id_frame.pack(fill="x", padx=PAD_XL, pady=(0, PAD_LG))
        ctk.CTkLabel(wa_phone_id_frame, text="Default Phone ID", font=ctk.CTkFont(size=FONT_MD, weight="bold"), text_color=TEXT_COLOR).pack(side="left")
        self.wa_phone_id_entry = self._create_input(wa_phone_id_frame, "Enter WhatsApp Phone Number ID")
        self.wa_phone_id_entry.pack(side="right")

        wa_webhook_frame = ctk.CTkFrame(card, fg_color="transparent")
        wa_webhook_frame.pack(fill="x", padx=PAD_XL, pady=(0, PAD_XL))
        ctk.CTkLabel(wa_webhook_frame, text="Webhook Verify Token", font=ctk.CTkFont(size=FONT_MD, weight="bold"), text_color=TEXT_COLOR).pack(side="left")
        self.wa_verify_token_entry = self._create_input(wa_webhook_frame, "Enter Webhook Verify Token", show="*")
        self.wa_verify_token_entry.pack(side="right")

        status_frame = ctk.CTkFrame(card, fg_color="transparent")
        status_frame.pack(fill="x", padx=PAD_XL, pady=(PAD_MD, PAD_XL))

        self.wa_status_label = ctk.CTkLabel(status_frame, text="Status: Unknown", font=body_font(FONT_SM), text_color=SUB_TEXT_COLOR)
        self.wa_status_label.pack(side="left")

        test_btn = create_premium_button(
            status_frame, text="Test Connection", variant="ghost", width=120, height=36,
            command=self._check_wa_status,
        )
        test_btn.configure(border_width=1, border_color=SUB_TEXT_COLOR)
        test_btn.pack(side="right")

        self.save_wa_btn = create_premium_button(
            card, text="Save WhatsApp Settings", variant="primary", command=self._save_wa_settings,
        )
        self.save_wa_btn.pack(anchor="e", padx=PAD_XL, pady=(0, PAD_XL))

    def _build_sync_section(self):
        card = ctk.CTkFrame(self.main_scroll, fg_color=SURFACE_COLOR, corner_radius=CARD_RADIUS)
        card.grid(row=3, column=0, sticky="ew", padx=PAD_MD, pady=(0, PAD_XL))

        ctk.CTkLabel(card, text="Offline Sync", font=heading_font(FONT_LG), text_color=TEXT_COLOR).pack(anchor="w", padx=PAD_XL, pady=(PAD_XL, PAD_SM))
        ctk.CTkLabel(card, text="Background polling rates for messages and analytics.", font=body_font(FONT_SM), text_color=SUB_TEXT_COLOR).pack(anchor="w", padx=PAD_XL, pady=(0, PAD_XL))

        sync_interval_frame = ctk.CTkFrame(card, fg_color="transparent")
        sync_interval_frame.pack(fill="x", padx=PAD_XL, pady=(0, PAD_XL))
        ctk.CTkLabel(sync_interval_frame, text="Sync Interval (seconds)", font=ctk.CTkFont(size=FONT_MD, weight="bold"), text_color=TEXT_COLOR).pack(side="left")
        self.sync_interval_entry = self._create_input(sync_interval_frame, "e.g., 10")
        self.sync_interval_entry.pack(side="right")

        self.save_sync_btn = create_premium_button(
            card, text="Save Sync Settings", variant="primary", command=self._save_sync_settings,
        )
        self.save_sync_btn.pack(anchor="e", padx=PAD_XL, pady=(0, PAD_XL))

    def _build_simulation_section(self):
        card = ctk.CTkFrame(self.main_scroll, fg_color=SURFACE_COLOR, corner_radius=CARD_RADIUS)
        card.grid(row=4, column=0, sticky="ew", padx=PAD_MD, pady=(0, PAD_XL))

        ctk.CTkLabel(card, text="Simulation & Testing", font=heading_font(FONT_LG), text_color=TEXT_COLOR).pack(anchor="w", padx=PAD_XL, pady=(PAD_XL, PAD_SM))
        ctk.CTkLabel(card, text="Manage local mock message ingestion worker for testing capabilities without API costs.", font=body_font(FONT_SM), text_color=SUB_TEXT_COLOR).pack(anchor="w", padx=PAD_XL, pady=(0, PAD_XL))

        toggle_frame = ctk.CTkFrame(card, fg_color="transparent")
        toggle_frame.pack(fill="x", padx=PAD_XL, pady=(0, PAD_XL))
        self.mock_enabled_var = ctk.BooleanVar(value=True)
        self.mock_toggle = ctk.CTkSwitch(toggle_frame, text="Enable Mock Message Worker", variable=self.mock_enabled_var, progress_color=ACCENT_COLOR)
        self.mock_toggle.pack(side="left")

        self.save_mock_btn = create_premium_button(
            card, text="Save Simulation Settings", variant="primary", command=self._save_mock_settings,
        )
        self.save_mock_btn.pack(anchor="e", padx=PAD_XL, pady=(0, PAD_XL))

    def _build_feature_flags_section(self):
        card = ctk.CTkFrame(self.main_scroll, fg_color=SURFACE_COLOR, corner_radius=CARD_RADIUS)
        card.grid(row=5, column=0, sticky="ew", padx=PAD_MD, pady=(0, PAD_3XL))

        ctk.CTkLabel(card, text="Feature Flags", font=heading_font(FONT_LG), text_color=TEXT_COLOR).pack(anchor="w", padx=PAD_XL, pady=(PAD_XL, PAD_SM))
        ctk.CTkLabel(
            card, text="Toggle UI elements and feature visibility across the dashboard workspace.",
            font=body_font(FONT_SM), text_color=SUB_TEXT_COLOR
        ).pack(anchor="w", padx=PAD_XL, pady=(0, PAD_XL))

        toggle_frame = ctk.CTkFrame(card, fg_color="transparent")
        toggle_frame.pack(fill="x", padx=PAD_XL, pady=(0, PAD_XL))
        toggle_frame.grid_columnconfigure((0, 1, 2), weight=1)

        self.enable_inbox_v2_var = ctk.BooleanVar(value=True)
        self.enable_contacts_crm_var = ctk.BooleanVar(value=True)
        self.enable_contracts_var = ctk.BooleanVar(value=True)

        ctk.CTkSwitch(toggle_frame, text="Inbox V2", variable=self.enable_inbox_v2_var, progress_color=ACCENT_COLOR).grid(row=0, column=0, sticky="w")
        ctk.CTkSwitch(toggle_frame, text="Contacts CRM", variable=self.enable_contacts_crm_var, progress_color=ACCENT_COLOR).grid(row=0, column=1, sticky="w")
        ctk.CTkSwitch(toggle_frame, text="Contracts Module", variable=self.enable_contracts_var, progress_color=ACCENT_COLOR).grid(row=0, column=2, sticky="w")

        self.save_flags_btn = create_premium_button(
            card, text="Save Feature Flags", variant="primary", command=self._save_feature_flags,
        )
        self.save_flags_btn.pack(anchor="e", padx=PAD_XL, pady=(0, PAD_XL))

    # ── Backend Operations ─────────────────────────────────────────────────────
    def load_initial_settings(self):
        if not self.load_wa_settings_cb: return
        settings = self.load_wa_settings_cb()
        self.wa_token_entry.delete(0, "end")
        self.wa_phone_id_entry.delete(0, "end")
        self.wa_verify_token_entry.delete(0, "end")
        self.wa_token_entry.insert(0, settings.get("WA_TOKEN", ""))
        self.wa_phone_id_entry.insert(0, settings.get("WA_PHONE_ID", ""))
        self.wa_verify_token_entry.insert(0, settings.get("META_WEBHOOK_VERIFY_TOKEN", ""))

        if self.load_theme_cb:
            current_theme = self.load_theme_cb()
            self.theme_menu.set(current_theme)

        if self.load_sync_settings_cb:
            sync_settings = self.load_sync_settings_cb()
            self.sync_interval_entry.delete(0, "end")
            self.sync_interval_entry.insert(0, sync_settings.get("SYNC_INTERVAL", "10"))

        if self.load_mock_settings_cb:
            mock_settings = self.load_mock_settings_cb()
            self.mock_enabled_var.set(mock_settings.get("MOCK_ENABLED", True))

        if self.load_feature_flags_cb:
            flags = self.load_feature_flags_cb()
            self.enable_inbox_v2_var.set(flags.get("ENABLE_INBOX_V2", True))
            self.enable_contacts_crm_var.set(flags.get("ENABLE_CONTACTS_CRM", True))
            self.enable_contracts_var.set(flags.get("ENABLE_CONTRACTS", True))

        self._check_wa_status()

    def _save_wa_settings(self):
        if self.on_save_wa_settings:
            token = self.wa_token_entry.get()
            phone_id = self.wa_phone_id_entry.get()
            verify_token = self.wa_verify_token_entry.get()
            self.on_save_wa_settings(token, phone_id, verify_token)
            self.save_wa_btn.configure(text="✓ Saved Initializing...")
            self.after(500, self._check_wa_status)
            self.save_wa_btn.after(2000, lambda: self.save_wa_btn.configure(text="Save WhatsApp Settings"))

    def _check_wa_status(self):
        if not self.check_wa_status_cb:
            self.wa_status_label.configure(text="Status: Check function not available", text_color=ERROR_COLOR)
            return

        self.wa_status_label.configure(text="Status: Checking connection...", text_color=WARNING_COLOR)

        def _worker():
            try:
                is_valid, message = self.check_wa_status_cb()
                status_text = f"Status: {message}"
                status_color = ACCENT_COLOR if is_valid else ERROR_COLOR
                self.after(0, lambda: self.wa_status_label.configure(text=status_text, text_color=status_color))
            except Exception as e:
                logging.getLogger(__name__).error("Status check failed: %s", e)
                self.after(0, lambda: self.wa_status_label.configure(text="Status: Error checking status", text_color=ERROR_COLOR))

        threading.Thread(target=_worker, daemon=True).start()

    def _save_sync_settings(self):
        if self.on_save_sync_settings:
            interval = self.sync_interval_entry.get()
            if not interval.isdigit() or int(interval) < 1:
                self.save_sync_btn.configure(text="Invalid Interval", fg_color=ERROR_COLOR)
                self.save_sync_btn.after(2000, lambda: self.save_sync_btn.configure(text="Save Sync Settings", fg_color=ACCENT_COLOR))
                return
            self.on_save_sync_settings(interval)
            self.save_sync_btn.configure(text="✓ Saved")
            self.save_sync_btn.after(2000, lambda: self.save_sync_btn.configure(text="Save Sync Settings"))

    def _save_mock_settings(self):
        if self.on_save_mock_settings:
            is_enabled = self.mock_enabled_var.get()
            self.on_save_mock_settings(is_enabled)
            self.save_mock_btn.configure(text="✓ Saved")
            self.save_mock_btn.after(2000, lambda: self.save_mock_btn.configure(text="Save Simulation Settings"))

    def _save_feature_flags(self):
        if self.on_save_feature_flags_cb:
            self.on_save_feature_flags_cb(
                self.enable_inbox_v2_var.get(),
                self.enable_contacts_crm_var.get(),
                self.enable_contracts_var.get(),
            )
            self.save_flags_btn.configure(text="✓ Saved")
            self.save_flags_btn.after(2000, lambda: self.save_flags_btn.configure(text="Save Feature Flags"))
