import customtkinter as ctk
from typing import List, Callable, Tuple

from services.account_selector import AccountSelector
from services import MetaAccountDTO

from .styles import (
    BG_COLOR, SURFACE_COLOR, INPUT_COLOR, HOVER_COLOR,
    ACCENT_COLOR, ACCENT_HOVER, TEXT_COLOR, SUB_TEXT_COLOR, ERROR_COLOR,
    DIVIDER_COLOR, CARD_RADIUS, PAD_SM, PAD_MD, PAD_LG, PAD_XL, PAD_2XL, PAD_3XL,
    FONT_2XL, FONT_MD, FONT_SM, FONT_XS,
    heading_font, body_font,
    create_section_header, create_premium_button, create_premium_input,
)

class BulkMessageTab(ctk.CTkFrame):
    """Enterprise Bulk Messaging UI (Premium Redesign)."""
    def __init__(self, master, get_accounts_cb: Callable[[], List[MetaAccountDTO]], bulk_send_cb: Callable, **kwargs):
        super().__init__(master, fg_color=BG_COLOR, corner_radius=0, **kwargs)
        self.get_accounts_cb = get_accounts_cb
        self.bulk_send_cb = bulk_send_cb
        self._build_ui()

    @staticmethod
    def _normalize_recipients(raw_text: str) -> Tuple[List[str], List[str], int]:
        normalized, invalid_lines, seen, duplicate_count = [], [], set(), 0
        for raw_line in raw_text.splitlines():
            line = raw_line.strip()
            if not line: continue
            candidate = line.replace(" ", "").replace("-", "").replace("(", "").replace(")", "")
            if candidate.startswith("+"): candidate = candidate[1:]
            if not candidate.isdigit() or not (8 <= len(candidate) <= 15):
                invalid_lines.append(line); continue
            if candidate in seen: duplicate_count += 1; continue
            seen.add(candidate); normalized.append(candidate)
        return normalized, invalid_lines, duplicate_count

    def _build_ui(self):
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)

        # Header
        self.header_frame = create_section_header(self, "Bulk Campaign", "Send messages safely with anti-spam compliance")
        self.header_frame.grid(row=0, column=0, columnspan=2, sticky="ew", padx=PAD_3XL, pady=(PAD_2XL, 0))

        # Account Selection
        acct_frame = ctk.CTkFrame(self, fg_color=SURFACE_COLOR, corner_radius=CARD_RADIUS)
        acct_frame.grid(row=1, column=0, columnspan=2, sticky="ew", padx=PAD_3XL, pady=(PAD_XL, PAD_MD))
        ctk.CTkLabel(acct_frame, text="1. SENDER META ACCOUNT", font=ctk.CTkFont(size=FONT_SM, weight="bold"), text_color=SUB_TEXT_COLOR).pack(anchor="w", padx=PAD_XL, pady=(PAD_LG, PAD_SM))
        accounts = self.get_accounts_cb()
        self.account_selector = AccountSelector(acct_frame, accounts=accounts)
        self.account_selector.pack(fill="x", padx=PAD_XL, pady=(0, PAD_XL))

        # Recipients
        recipients_frame = ctk.CTkFrame(self, fg_color=SURFACE_COLOR, corner_radius=CARD_RADIUS)
        recipients_frame.grid(row=2, column=0, sticky="nsew", padx=(PAD_3XL, PAD_MD), pady=PAD_MD)
        ctk.CTkLabel(recipients_frame, text="2. RECIPIENTS", font=ctk.CTkFont(size=FONT_SM, weight="bold"), text_color=SUB_TEXT_COLOR).pack(anchor="w", padx=PAD_XL, pady=(PAD_LG, PAD_SM))
        ctk.CTkLabel(recipients_frame, text="Paste phone numbers (one per line, E.164 without +)", font=body_font(FONT_SM), text_color=SUB_TEXT_COLOR).pack(anchor="w", padx=PAD_XL, pady=(0, PAD_MD))
        self.phones_textbox = ctk.CTkTextbox(recipients_frame, fg_color=INPUT_COLOR, text_color=TEXT_COLOR, corner_radius=8, border_width=0)
        self.phones_textbox.pack(fill="both", expand=True, padx=PAD_XL, pady=(0, PAD_XL))

        # Message
        message_frame = ctk.CTkFrame(self, fg_color=SURFACE_COLOR, corner_radius=CARD_RADIUS)
        message_frame.grid(row=2, column=1, sticky="nsew", padx=(PAD_MD, PAD_3XL), pady=PAD_MD)
        ctk.CTkLabel(message_frame, text="3. MESSAGE CONTENT", font=ctk.CTkFont(size=FONT_SM, weight="bold"), text_color=SUB_TEXT_COLOR).pack(anchor="w", padx=PAD_XL, pady=(PAD_LG, PAD_SM))

        type_switch_frame = ctk.CTkFrame(message_frame, fg_color="transparent")
        type_switch_frame.pack(fill="x", padx=PAD_XL, pady=PAD_SM)
        self.message_type_var = ctk.StringVar(value="text")
        ctk.CTkRadioButton(type_switch_frame, text="Plain Text", variable=self.message_type_var, value="text", command=self._toggle_message_inputs, text_color=TEXT_COLOR, border_color=ACCENT_COLOR, hover_color=ACCENT_HOVER).pack(side="left", padx=(0, PAD_XL))
        ctk.CTkRadioButton(type_switch_frame, text="WhatsApp Template", variable=self.message_type_var, value="template", command=self._toggle_message_inputs, text_color=TEXT_COLOR, border_color=ACCENT_COLOR, hover_color=ACCENT_HOVER).pack(side="left")

        self.text_input_frame = ctk.CTkFrame(message_frame, fg_color="transparent")
        self.text_input_frame.pack(fill="both", expand=True, padx=PAD_XL, pady=(PAD_MD, PAD_XL))
        self.message_textbox = ctk.CTkTextbox(self.text_input_frame, fg_color=INPUT_COLOR, text_color=TEXT_COLOR, corner_radius=8, border_width=0)
        self.message_textbox.pack(fill="both", expand=True)

        self.template_input_frame = ctk.CTkFrame(message_frame, fg_color="transparent")
        self.template_name_entry = create_premium_input(self.template_input_frame, "Template Name (e.g., promotional_greeting)", height=45)
        self.template_name_entry.pack(fill="x", pady=(0, PAD_LG))
        self.template_lang_entry = create_premium_input(self.template_input_frame, "Language Code (e.g., en_US)", height=45)
        self.template_lang_entry.pack(fill="x", pady=(0, PAD_LG))
        ctk.CTkLabel(self.template_input_frame, text="Note: Template must be pre-approved in Meta Business Manager.", text_color=SUB_TEXT_COLOR, font=body_font(FONT_SM)).pack(anchor="w")

        # Actions & Progress
        self.grid_rowconfigure(2, weight=1)
        self.grid_rowconfigure(3, weight=0)
        action_frame = ctk.CTkFrame(self, fg_color=SURFACE_COLOR, corner_radius=CARD_RADIUS)
        action_frame.grid(row=3, column=0, columnspan=2, sticky="nsew", padx=PAD_3XL, pady=(PAD_MD, PAD_XL))

        self.progress_bar = ctk.CTkProgressBar(action_frame, progress_color=ACCENT_COLOR, fg_color=INPUT_COLOR, height=10, corner_radius=5)
        self.progress_bar.pack(fill="x", padx=PAD_XL, pady=(PAD_XL, PAD_MD))
        self.progress_bar.set(0)

        status_container = ctk.CTkFrame(action_frame, fg_color="transparent")
        status_container.pack(fill="x", padx=PAD_XL, pady=(0, PAD_XL))
        self.status_label = ctk.CTkLabel(status_container, text="Ready to Dispatch", font=body_font(FONT_SM), text_color=SUB_TEXT_COLOR)
        self.status_label.pack(side="left")
        self.btn_send = create_premium_button(status_container, text="Start Bulk Campaign ▶", variant="primary", command=self._start_bulk_send)
        self.btn_send.pack(side="right")

    def _toggle_message_inputs(self):
        if self.message_type_var.get() == "text":
            self.template_input_frame.pack_forget()
            self.text_input_frame.pack(fill="both", expand=True, padx=PAD_XL, pady=(PAD_MD, PAD_XL))
        else:
            self.text_input_frame.pack_forget()
            self.template_input_frame.pack(fill="both", expand=True, padx=PAD_XL, pady=(PAD_MD, PAD_XL))

    def _start_bulk_send(self):
        account = self.account_selector.get_selected_account()
        if not account:
            self.status_label.configure(text="Error: No account selected.", text_color=ERROR_COLOR); return
        raw_phones_text = self.phones_textbox.get("1.0", "end")
        phones, invalid_lines, duplicate_count = self._normalize_recipients(raw_phones_text)
        if invalid_lines:
            preview = ", ".join(invalid_lines[:3])
            if len(invalid_lines) > 3: preview = f"{preview}, ..."
            self.status_label.configure(text=f"Error: {len(invalid_lines)} invalid recipient(s): {preview}", text_color=ERROR_COLOR); return
        if not phones:
            self.status_label.configure(text="Error: No recipients provided.", text_color=ERROR_COLOR); return

        duplicate_note = f" ({duplicate_count} duplicates removed)" if duplicate_count else ""
        self.phones_textbox.delete("1.0", "end")
        self.phones_textbox.insert("1.0", "\n".join(phones))

        msg_type = self.message_type_var.get()
        message_body, template_name, template_lang = "", "", "en_US"
        if msg_type == "text":
            message_body = self.message_textbox.get("1.0", "end").strip()
            if not message_body:
                self.status_label.configure(text="Error: Message cannot be empty.", text_color=ERROR_COLOR); return
        else:
            template_name = self.template_name_entry.get().strip()
            template_lang = self.template_lang_entry.get().strip() or "en_US"
            if not template_name:
                self.status_label.configure(text="Error: Template name is required.", text_color=ERROR_COLOR); return

        self.btn_send.configure(state="disabled")
        self.phones_textbox.configure(state="disabled")
        self.message_textbox.configure(state="disabled")
        self.template_name_entry.configure(state="disabled")
        self.template_lang_entry.configure(state="disabled")
        self.status_label.configure(text=f"Initializing bulk send to {len(phones)} recipient(s){duplicate_note}...", text_color=TEXT_COLOR)
        self.progress_bar.set(0)
        self.bulk_send_cb(
            account_id=account.id, to_phones=phones, message_type=msg_type,
            text_body=message_body, template_name=template_name, template_language=template_lang,
            progress_callback=lambda current, total, phone: self.after(0, lambda: self._update_progress_ui(current, total, phone)),
            completion_callback=lambda success, fail: self.after(0, lambda: self._on_complete_ui(success, fail))
        )

    def _update_progress_ui(self, current: int, total: int, phone: str):
        progress = current / total if total > 0 else 0
        self.progress_bar.set(progress)
        self.status_label.configure(text=f"Dispatching {current}/{total} (Last: {phone})", text_color=TEXT_COLOR)

    def _on_complete_ui(self, success_count: int, fail_count: int):
        self.btn_send.configure(state="normal")
        self.phones_textbox.configure(state="normal")
        self.message_textbox.configure(state="normal")
        self.template_name_entry.configure(state="normal")
        self.template_lang_entry.configure(state="normal")
        self.status_label.configure(text=f"Campaign Completed. Success: {success_count}, Failed: {fail_count}", text_color=ACCENT_COLOR)
        self.progress_bar.set(1.0)
