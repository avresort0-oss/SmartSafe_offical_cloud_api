import customtkinter as ctk
from typing import List, Callable, Optional
from services import MetaAccountDTO

BG_COLOR = "#0c1317"
CARD_COLOR = "#202c33"
ACCENT_COLOR = "#00a884"
TEXT_COLOR = "#ffffff"
SUB_TEXT_COLOR = "#8696a0"

class AccountSelector(ctk.CTkFrame):
    """
    Reusable dropdown component for selecting a Meta WhatsApp Business account.
    Displays the account's display name, phone number, and a colored health indicator.
    """
    def __init__(
        self, 
        master: any, 
        accounts: List[MetaAccountDTO], 
        on_select: Optional[Callable[[Optional[MetaAccountDTO]], None]] = None, 
        **kwargs
    ):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.accounts = accounts
        self.on_select = on_select
        self.account_map = {}
        self.selected_account: Optional[MetaAccountDTO] = None

        self._build_ui()

    def _format_label(self, acc: MetaAccountDTO) -> str:
        """Formats the dropdown label with a Unicode health indicator."""
        dots = {"GREEN": "🟢", "YELLOW": "🟡", "RED": "🔴"}
        dot = dots.get(acc.quality_rating.upper(), "⚪")
        phone = acc.display_phone or acc.phone_number_id
        return f"{dot} {acc.display_name} ({phone})"

    def _build_ui(self):
        if not self.accounts:
            self.dropdown = ctk.CTkOptionMenu(
                self, 
                values=["No Accounts Available"], 
                state="disabled",
                fg_color=CARD_COLOR,
                button_color=CARD_COLOR,
                text_color=SUB_TEXT_COLOR
            )
            self.dropdown.pack(fill="x", expand=True)
            return

        labels = []
        for acc in self.accounts:
            label = self._format_label(acc)
            self.account_map[label] = acc
            labels.append(label)

        self.dropdown = ctk.CTkOptionMenu(
            self,
            values=labels,
            command=self._handle_selection,
            fg_color=CARD_COLOR,
            button_color=ACCENT_COLOR,
            button_hover_color="#056162",
            text_color=TEXT_COLOR,
            dynamic_resizing=False
        )
        self.dropdown.pack(fill="x", expand=True)
        
        # Do not auto-select the first account; force explicit choice
        if labels:
            self.dropdown.set("Select Account...")

    def _handle_selection(self, selected_label: str):
        self.selected_account = self.account_map.get(selected_label)
        if self.on_select:
            self.on_select(self.selected_account)

    def get_selected_account(self) -> Optional[MetaAccountDTO]:
        """Returns the currently selected MetaAccountDTO."""
        return self.selected_account

    def refresh_accounts(self, new_accounts: List[MetaAccountDTO]):
        """Updates the dropdown list dynamically without recreating the parent frame components."""
        self.accounts = new_accounts
        self.account_map.clear()
        
        if not self.accounts:
            self.dropdown.configure(
                values=["No Accounts Available"],
                state="disabled",
                text_color=SUB_TEXT_COLOR,
                fg_color=CARD_COLOR,
                button_color=CARD_COLOR
            )
            self.dropdown.set("No Accounts Available")
            return

        labels = []
        for acc in self.accounts:
            label = self._format_label(acc)
            self.account_map[label] = acc
            labels.append(label)

        # Update existing dropdown instead of destroying it
        self.dropdown.configure(
            values=labels,
            state="normal",
            text_color=TEXT_COLOR,
            fg_color=CARD_COLOR,
            button_color=ACCENT_COLOR
        )
        
        # Keep current if valid, else prompt
        if labels:
            current = self.dropdown.get()
            if current in labels:
                self.dropdown.set(current)
                self._handle_selection(current)
            else:
                self.dropdown.set("Select Account...")
                self.selected_account = None