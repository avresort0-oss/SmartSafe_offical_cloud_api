import customtkinter as ctk
import sys
import os
from typing import Callable, Optional

from .styles import (
    BG_COLOR, SURFACE_COLOR, INPUT_COLOR, ACCENT_COLOR, ACCENT_HOVER,
    TEXT_COLOR, TEXT_SECONDARY, ERROR_COLOR, DIVIDER_COLOR,
    CARD_RADIUS, INPUT_RADIUS, BUTTON_RADIUS, INPUT_HEIGHT, BUTTON_HEIGHT,
    FONT_3XL, FONT_XL, FONT_LG, FONT_MD, FONT_SM,
    heading_font, body_font, create_premium_input, create_premium_button,
)

# Premium Login Constants
LOGIN_CARD_COLOR = "#14232d"
LOGIN_CARD_GLOW  = "#0d1b24"


class AuthView(ctk.CTkFrame):
    """
    Premium Authentication View — Login & Registration.
    Glassmorphism-inspired card centered on a deep dark background.
    """
    def __init__(self, master: ctk.CTk, on_login_attempt: Callable, on_register_attempt: Callable, **kwargs):
        super().__init__(master, fg_color=BG_COLOR, **kwargs)

        self.on_login_attempt = on_login_attempt
        self.on_register_attempt = on_register_attempt

        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self._build_login_form()

    def _build_login_form(self):
        # Outer glow layer
        glow_frame = ctk.CTkFrame(self, fg_color=LOGIN_CARD_GLOW, corner_radius=CARD_RADIUS + 4)
        glow_frame.place(relx=0.5, rely=0.5, anchor="center")

        # Main card
        self.form_frame = ctk.CTkFrame(glow_frame, fg_color=LOGIN_CARD_COLOR, corner_radius=CARD_RADIUS)
        self.form_frame.pack(padx=3, pady=3)

        # Logo / Brand area
        brand_frame = ctk.CTkFrame(self.form_frame, fg_color="transparent")
        brand_frame.pack(pady=(32, 8))

        # Accent dot
        ctk.CTkLabel(
            brand_frame, text="●", font=ctk.CTkFont(size=14),
            text_color=ACCENT_COLOR,
        ).pack(side="left", padx=(0, 6))

        ctk.CTkLabel(
            brand_frame, text="SmartSafe",
            font=ctk.CTkFont(size=FONT_3XL, weight="bold"),
            text_color=ACCENT_COLOR,
        ).pack(side="left")

        ctk.CTkLabel(
            brand_frame, text="v28",
            font=ctk.CTkFont(size=FONT_LG, weight="bold"),
            text_color=TEXT_SECONDARY,
        ).pack(side="left", padx=(4, 0), pady=(8, 0))

        ctk.CTkLabel(
            self.form_frame, text="Enterprise Login",
            font=ctk.CTkFont(size=FONT_XL, weight="bold"),
            text_color=TEXT_COLOR,
        ).pack(pady=(0, 24))

        # Subtle divider
        ctk.CTkFrame(self.form_frame, height=1, fg_color=DIVIDER_COLOR).pack(fill="x", padx=32, pady=(0, 24))

        # Username
        ctk.CTkLabel(
            self.form_frame, text="USERNAME",
            font=ctk.CTkFont(size=10, weight="bold"),
            text_color=TEXT_SECONDARY,
        ).pack(anchor="w", padx=32, pady=(0, 4))

        self.username_entry = create_premium_input(self.form_frame, "Enter your username", width=300)
        self.username_entry.pack(padx=32, fill="x")

        # Password
        ctk.CTkLabel(
            self.form_frame, text="PASSWORD",
            font=ctk.CTkFont(size=10, weight="bold"),
            text_color=TEXT_SECONDARY,
        ).pack(anchor="w", padx=32, pady=(16, 4))

        self.password_entry = create_premium_input(self.form_frame, "Enter your password", show="*", width=300)
        self.password_entry.pack(padx=32, fill="x")

        # Error display
        self.error_label = ctk.CTkLabel(
            self.form_frame, text="",
            text_color=ERROR_COLOR,
            font=ctk.CTkFont(size=FONT_SM),
        )
        self.error_label.pack(pady=(12, 8))

        # Login button
        self.login_button = create_premium_button(
            self.form_frame, text="Login", variant="primary",
            command=self._login_action, width=300, height=44,
        )
        self.login_button.pack(padx=32, fill="x")

        # Register button
        self.register_button = create_premium_button(
            self.form_frame, text="Register",
            variant="secondary", command=self._register_action,
            width=300, height=44,
        )
        self.register_button.pack(padx=32, fill="x", pady=(10, 32))

    def _login_action(self):
        username = self.username_entry.get()
        password = self.password_entry.get()
        self.error_label.configure(text="")
        self.on_login_attempt(username, password)

    def _register_action(self):
        username = self.username_entry.get()
        password = self.password_entry.get()
        email = f"{username}@smartsafe.local"
        self.error_label.configure(text="")
        self.on_register_attempt(username, email, password)

    def show_error(self, message: str, is_login: bool = True):
        self.error_label.configure(text=message)
        if is_login:
            self.username_entry.focus_set()
        else:
            self.username_entry.focus_set()