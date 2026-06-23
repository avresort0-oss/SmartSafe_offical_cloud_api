import threading
import customtkinter as ctk
from typing import List, Callable, Tuple, Optional

from services import MetaAccountDTO, MetaAccountCreateDTO

from .styles import (
    BG_COLOR, SURFACE_COLOR, INPUT_COLOR, HOVER_COLOR, ACTIVE_COLOR,
    ACCENT_COLOR, ACCENT_HOVER, TEXT_COLOR, TEXT_SECONDARY, SUB_TEXT_COLOR,
    ERROR_COLOR, WARNING_COLOR,
    CARD_RADIUS, CARD_RADIUS_SM, INPUT_RADIUS, BUTTON_RADIUS,
    INPUT_HEIGHT, BUTTON_HEIGHT, BUTTON_HEIGHT_SM,
    PAD_XS, PAD_SM, PAD_MD, PAD_LG, PAD_XL, PAD_2XL, PAD_3XL,
    FONT_2XL, FONT_XL, FONT_LG, FONT_MD, FONT_SM, FONT_XS,
    heading_font, body_font,
    create_section_header, create_premium_input, create_premium_button,
)


class AccountsTab(ctk.CTkFrame):
    """
    Enterprise Meta Accounts Management UI (Premium Redesign).
    Handles adding, deleting, and monitoring multiple WhatsApp Business API accounts.
    """
    def __init__(
        self,
        master,
        current_workspace_id: str,
        get_accounts_cb: Callable[[], List[MetaAccountDTO]],
        add_account_cb: Callable[[MetaAccountCreateDTO], Tuple[Optional[MetaAccountDTO], Optional[str]]],
        remove_account_cb: Callable[[str], bool],
        refresh_account_cb: Callable[[str], Optional[MetaAccountDTO]],
        **kwargs
    ):
        super().__init__(master, fg_color=BG_COLOR, corner_radius=0, **kwargs)
        self.current_workspace_id = current_workspace_id
        self.get_accounts_cb = get_accounts_cb
        self.add_account_cb = add_account_cb
        self.remove_account_cb = remove_account_cb
        self.refresh_account_cb = refresh_account_cb

        self._build_ui()
        self.load_accounts()
        self._start_auto_refresh()

    def _build_ui(self):
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=35)
        self.grid_columnconfigure(1, weight=65)

        self._build_header()
        self._build_form_panel()
        self._build_list_panel()

    def _create_input(self, parent: ctk.CTkFrame, placeholder: str, show: str = "") -> ctk.CTkEntry:
        """Helper to generate premium rounded input fields."""
        entry = create_premium_input(parent, placeholder, show=show)
        entry.pack(fill="x", padx=PAD_XL, pady=(0, PAD_LG))
        return entry

    # ── Header ─────────────────────────────────────────────────────────────────
    def _build_header(self):
        self.header_frame = create_section_header(self, "Meta Accounts", "Connect WhatsApp Business API instances")
        self.header_frame.grid(row=0, column=0, columnspan=2, sticky="ew", padx=PAD_3XL, pady=(PAD_2XL, PAD_MD))

    # ── Left Panel (Form) ──────────────────────────────────────────────────────
    def _build_form_panel(self):
        form_frame = ctk.CTkFrame(self, fg_color=SURFACE_COLOR, corner_radius=CARD_RADIUS)
        form_frame.grid(row=1, column=0, sticky="nsew", padx=(PAD_3XL, PAD_SM), pady=(0, PAD_2XL))

        ctk.CTkLabel(
            form_frame, text="Add Meta Account", font=heading_font(FONT_XL), text_color=TEXT_COLOR
        ).pack(pady=(PAD_XL, PAD_SM), anchor="w", padx=PAD_XL)

        ctk.CTkLabel(
            form_frame, text="Bind a new WABA to this workspace.", font=body_font(FONT_SM), text_color=SUB_TEXT_COLOR
        ).pack(pady=(0, PAD_XL), anchor="w", padx=PAD_XL)

        ctk.CTkLabel(form_frame, text="Display Name", text_color=SUB_TEXT_COLOR, font=ctk.CTkFont(weight="bold")).pack(anchor="w", padx=PAD_XL, pady=(0, 2))
        self.entry_name = self._create_input(form_frame, "e.g. Sales US")

        ctk.CTkLabel(form_frame, text="Phone Number ID", text_color=SUB_TEXT_COLOR, font=ctk.CTkFont(weight="bold")).pack(anchor="w", padx=PAD_XL, pady=(0, 2))
        self.entry_phone_id = self._create_input(form_frame, "Found in Meta App Settings")

        ctk.CTkLabel(form_frame, text="WhatsApp Business Account ID", text_color=SUB_TEXT_COLOR, font=ctk.CTkFont(weight="bold")).pack(anchor="w", padx=PAD_XL, pady=(0, 2))
        self.entry_waba_id = self._create_input(form_frame, "Found in Meta App Settings")

        ctk.CTkLabel(form_frame, text="System User Access Token", text_color=SUB_TEXT_COLOR, font=ctk.CTkFont(weight="bold")).pack(anchor="w", padx=PAD_XL, pady=(0, 2))
        self.entry_token = self._create_input(form_frame, "Graph API permanent token", show="*")

        self.lbl_error = ctk.CTkLabel(form_frame, text="", text_color=ERROR_COLOR, font=ctk.CTkFont(size=FONT_SM))
        self.lbl_error.pack(pady=PAD_SM, padx=PAD_XL, anchor="w")

        self.btn_submit = create_premium_button(
            form_frame, text="Connect Account", variant="primary", command=self._on_add_submit, height=45,
        )
        self.btn_submit.pack(pady=PAD_MD, fill="x", padx=PAD_XL)

    # ── Right Panel (Accounts List) ────────────────────────────────────────────
    def _build_list_panel(self):
        list_container = ctk.CTkFrame(self, fg_color=SURFACE_COLOR, corner_radius=CARD_RADIUS)
        list_container.grid(row=1, column=1, sticky="nsew", padx=(PAD_SM, PAD_3XL), pady=(0, PAD_2XL))
        list_container.grid_rowconfigure(1, weight=1)
        list_container.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            list_container, text="Active Accounts", font=heading_font(FONT_XL), text_color=TEXT_COLOR
        ).grid(row=0, column=0, sticky="w", pady=PAD_XL, padx=PAD_2XL)

        self.scroll_list = ctk.CTkScrollableFrame(list_container, fg_color="transparent")
        self.scroll_list.grid(row=1, column=0, sticky="nsew", padx=PAD_MD, pady=(0, PAD_MD))

    def load_accounts(self):
        """Refreshes the right-side account list."""
        for widget in self.scroll_list.winfo_children():
            widget.destroy()

        accounts = self.get_accounts_cb()
        if not accounts:
            ctk.CTkLabel(
                self.scroll_list, text="No accounts connected. Add one from the panel.", text_color=SUB_TEXT_COLOR, pady=40
            ).pack()
            return

        for acc in accounts:
            self._create_account_card(acc)

    def _create_account_card(self, acc: MetaAccountDTO):
        card = ctk.CTkFrame(self.scroll_list, fg_color=INPUT_COLOR, corner_radius=CARD_RADIUS_SM)
        card.pack(fill="x", pady=PAD_SM, padx=PAD_MD)

        dots = {"GREEN": ACCENT_COLOR, "YELLOW": WARNING_COLOR, "RED": ERROR_COLOR}
        quality_color = dots.get(acc.quality_rating.upper(), SUB_TEXT_COLOR)

        # Color accent strip on left
        accent = ctk.CTkFrame(card, fg_color=quality_color, width=4, corner_radius=2)
        accent.pack(side="left", fill="y", padx=(4, 0), pady=PAD_MD)

        info_frame = ctk.CTkFrame(card, fg_color="transparent")
        info_frame.pack(side="left", padx=PAD_LG, pady=PAD_LG, fill="both", expand=True)

        top_row = ctk.CTkFrame(info_frame, fg_color="transparent")
        top_row.pack(fill="x")

        ctk.CTkLabel(top_row, text=acc.display_name, font=ctk.CTkFont(size=FONT_LG, weight="bold"), text_color=TEXT_COLOR).pack(side="left")
        ctk.CTkLabel(
            top_row, text=f" • {acc.api_status} ", font=ctk.CTkFont(size=FONT_SM, weight="bold"),
            text_color=ACCENT_COLOR if acc.api_status == "CONNECTED" else ERROR_COLOR
        ).pack(side="left", padx=PAD_MD)

        ctk.CTkLabel(info_frame, text=f"📞 {acc.display_phone or acc.phone_number_id}", font=ctk.CTkFont(size=FONT_SM), text_color=SUB_TEXT_COLOR).pack(anchor="w", pady=(PAD_XS, 0))

        btn_frame = ctk.CTkFrame(card, fg_color="transparent")
        btn_frame.pack(side="right", padx=PAD_LG)

        refresh_btn = create_premium_button(
            btn_frame, text="↻ Refresh", variant="ghost", width=90, height=BUTTON_HEIGHT_SM,
            command=lambda a=acc.id: self._on_refresh(a),
        )
        refresh_btn.configure(border_width=1, border_color=SUB_TEXT_COLOR)
        refresh_btn.pack(side="left", padx=PAD_SM)

        del_btn = create_premium_button(
            btn_frame, text="Delete", variant="danger", width=80, height=BUTTON_HEIGHT_SM,
            command=lambda a=acc.id: self._on_delete(a),
        )
        del_btn.pack(side="left", padx=PAD_SM)

    def _on_add_submit(self):
        """Handles account creation form submission gracefully using a background thread."""
        name = self.entry_name.get().strip()
        phone_id = self.entry_phone_id.get().strip()
        waba_id = self.entry_waba_id.get().strip()
        token = self.entry_token.get().strip()

        if not all([name, phone_id, waba_id, token]):
            self.lbl_error.configure(text="All fields are required.", text_color=ERROR_COLOR)
            return

        self.lbl_error.configure(text="Verifying with Meta API...", text_color=ACCENT_COLOR)
        self.btn_submit.configure(state="disabled")

        def _worker():
            dto = MetaAccountCreateDTO(display_name=name, phone_number_id=phone_id, access_token=token, waba_id=waba_id, workspace_id=self.current_workspace_id)
            acc, error = self.add_account_cb(dto)
            self.after(0, lambda: self._on_add_complete(acc, error))

        threading.Thread(target=_worker, daemon=True).start()

    def _on_add_complete(self, acc: Optional[MetaAccountDTO], error: Optional[str]):
        self.btn_submit.configure(state="normal")
        if error:
            self.lbl_error.configure(text=error, text_color=ERROR_COLOR)
        else:
            self.lbl_error.configure(text="✓ Account linked successfully.", text_color=ACCENT_COLOR)
            self.entry_name.delete(0, "end")
            self.entry_phone_id.delete(0, "end")
            self.entry_waba_id.delete(0, "end")
            self.entry_token.delete(0, "end")
            self.load_accounts()

    def _on_delete(self, account_id: str):
        if self.remove_account_cb(account_id):
            self.load_accounts()

    def _on_refresh(self, account_id: str):
        """Forces a manual sync of the account status via a background thread."""
        def _worker():
            self.refresh_account_cb(account_id)
            self.after(0, self.load_accounts)
        threading.Thread(target=_worker, daemon=True).start()

    def _start_auto_refresh(self):
        """Polls the Meta API for account health every 5 minutes (300,000ms)."""
        self.after(300_000, self._auto_refresh_tick)

    def _auto_refresh_tick(self):
        def _worker():
            accounts = self.get_accounts_cb()
            for acc in accounts:
                self.refresh_account_cb(acc.id)
            self.after(0, self.load_accounts)

        threading.Thread(target=_worker, daemon=True).start()
        self._start_auto_refresh()