import customtkinter as ctk
from typing import Callable, List, Optional
import os

from .styles import (
    BG_COLOR, SURFACE_COLOR, TEXT_COLOR, TEXT_SECONDARY, 
    PAD_MD, PAD_LG, PAD_XL, PAD_3XL, FONT_XL, FONT_MD, CARD_RADIUS,
    heading_font, body_font, create_section_header, create_premium_card,
    create_premium_button, create_premium_input, create_divider,
    ACCENT_COLOR, ERROR_COLOR, INPUT_COLOR, SURFACE_LIGHT, PAD_SM, PAD_XS
)

class AutoReplyFrame(ctk.CTkFrame):
    """Auto Reply Bot Configuration UI (Premium Redesign)."""

    def __init__(self, master: ctk.CTkFrame, current_workspace=None, controller=None, **kwargs):
        super().__init__(master, fg_color=BG_COLOR, corner_radius=0, **kwargs)
        self.current_workspace = current_workspace
        self.controller = controller
        
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self.main_scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.main_scroll.grid(row=0, column=0, sticky="nsew", padx=PAD_XL, pady=PAD_XL)
        self.main_scroll.grid_columnconfigure(0, weight=1)

        self._build_ui()
        self.refresh_data()

    def _build_ui(self):
        # Header
        self.header = create_section_header(self.main_scroll, "Auto Reply Bot", "Automation")
        self.header.grid(row=0, column=0, sticky="ew", pady=(0, PAD_3XL))

        # Add Rule Section
        self._build_add_rule_card()

        # Rules List Header
        self.list_header = ctk.CTkLabel(
            self.main_scroll, text="ACTIVE RULES", 
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=TEXT_SECONDARY
        )
        self.list_header.grid(row=2, column=0, sticky="w", pady=(PAD_3XL, PAD_MD), padx=PAD_MD)

        # Rules Container
        self.rules_container = ctk.CTkFrame(self.main_scroll, fg_color="transparent")
        self.rules_container.grid(row=3, column=0, sticky="ew")
        self.rules_container.grid_columnconfigure(0, weight=1)

    def _build_add_rule_card(self):
        self.add_card = create_premium_card(self.main_scroll)
        self.add_card.grid(row=1, column=0, sticky="ew", padx=PAD_MD)
        
        # Title
        ctk.CTkLabel(
            self.add_card, text="CREATE NEW RULE", 
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=TEXT_COLOR
        ).grid(row=0, column=0, columnspan=2, sticky="w", padx=PAD_LG, pady=PAD_LG)

        # Trigger Input
        self.trigger_entry = create_premium_input(self.add_card, "Trigger Keyword (e.g. 'price', 'hello')")
        self.trigger_entry.grid(row=1, column=0, sticky="ew", padx=PAD_LG, pady=(0, PAD_MD))

        # Trigger Type
        self.type_var = ctk.StringVar(value="exact")
        self.type_menu = ctk.CTkOptionMenu(
            self.add_card, 
            values=["exact", "contains", "starts_with"],
            variable=self.type_var,
            fg_color=INPUT_COLOR,
            button_color=INPUT_COLOR,
            button_hover_color=SURFACE_LIGHT,
            dropdown_fg_color=SURFACE_COLOR,
            width=120
        )
        self.type_menu.grid(row=1, column=1, sticky="e", padx=(0, PAD_LG), pady=(0, PAD_MD))

        # Response Input
        self.response_text = ctk.CTkTextbox(
            self.add_card, 
            height=100, 
            fg_color=INPUT_COLOR, 
            text_color=TEXT_COLOR,
            corner_radius=10,
            border_width=0,
            font=body_font(FONT_MD)
        )
        self.response_text.grid(row=2, column=0, columnspan=2, sticky="ew", padx=PAD_LG, pady=(0, PAD_LG))

        # Attachment (Optional)
        self.attach_path = None
        self.attach_btn = create_premium_button(
            self.add_card, "📎 Add Attachment", 
            command=self._handle_attachment,
            variant="ghost", height=32
        )
        self.attach_btn.grid(row=3, column=0, sticky="w", padx=PAD_LG, pady=(0, PAD_LG))

        # Create Button
        self.create_btn = create_premium_button(
            self.add_card, "CREATE RULE", 
            command=self._on_create,
            variant="primary"
        )
        self.create_btn.grid(row=3, column=1, sticky="e", padx=PAD_LG, pady=(0, PAD_LG))

    def _handle_attachment(self):
        file = ctk.filedialog.askopenfilename()
        if file:
            self.attach_path = file
            self.attach_btn.configure(text=f"✅ {os.path.basename(file)}", text_color=ACCENT_COLOR)

    def _on_create(self):
        trigger = self.trigger_entry.get().strip()
        response = self.response_text.get("1.0", "end").strip()
        if not trigger or not response or not self.current_workspace:
            return
        
        if self.controller:
            self.controller.create_auto_reply_rule(
                self.current_workspace.id, 
                trigger, 
                response, 
                self.type_var.get(),
                self.attach_path
            )
            # Reset form
            self.trigger_entry.delete(0, "end")
            self.response_text.delete("1.0", "end")
            self.attach_path = None
            self.attach_btn.configure(text="📎 Add Attachment", text_color=TEXT_SECONDARY)

    def refresh_data(self):
        if not self.current_workspace or not self.controller:
            return
            
        # Clear existing
        for widget in self.rules_container.winfo_children():
            widget.destroy()
            
        rules = self.controller.get_auto_reply_rules(self.current_workspace.id)
        if not rules:
            ctk.CTkLabel(
                self.rules_container, text="No rules configured yet.", 
                text_color=TEXT_SECONDARY, font=body_font(FONT_MD)
            ).pack(pady=PAD_XL)
            return

        for i, rule in enumerate(rules):
            self._render_rule_card(rule, i)

    def _render_rule_card(self, rule, index):
        card = create_premium_card(self.rules_container)
        card.pack(fill="x", pady=(0, PAD_MD), padx=PAD_MD)
        
        # Info side
        info_frame = ctk.CTkFrame(card, fg_color="transparent")
        info_frame.pack(side="left", fill="both", expand=True, padx=PAD_LG, pady=PAD_LG)
        
        trigger_label = ctk.CTkLabel(
            info_frame, text=f"Trigger: {rule.trigger_keyword}", 
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=ACCENT_COLOR
        )
        trigger_label.pack(anchor="w")
        
        type_badge = ctk.CTkLabel(
            info_frame, text=rule.trigger_type.upper(), 
            font=ctk.CTkFont(size=9, weight="bold"),
            fg_color=SURFACE_LIGHT,
            text_color=TEXT_SECONDARY,
            corner_radius=4,
            px=6
        )
        # badge support in ctk is limited, using label as workaround
        
        response_preview = rule.response_text[:80] + "..." if len(rule.response_text) > 80 else rule.response_text
        ctk.CTkLabel(
            info_frame, text=response_preview, 
            text_color=TEXT_COLOR, wraplength=400, justify="left"
        ).pack(anchor="w", pady=(PAD_XS, 0))
        
        if rule.attachment_path:
            ctk.CTkLabel(
                info_frame, text=f"📎 {os.path.basename(rule.attachment_path)}", 
                text_color=ACCENT_COLOR, font=ctk.CTkFont(size=11)
            ).pack(anchor="w")

        # Action side
        actions = ctk.CTkFrame(card, fg_color="transparent")
        actions.pack(side="right", padx=PAD_LG)
        
        toggle_text = "ENABLED" if rule.is_active else "DISABLED"
        toggle_color = ACCENT_COLOR if rule.is_active else TEXT_SECONDARY
        
        create_premium_button(
            actions, toggle_text, 
            command=lambda r=rule.id: self.controller.toggle_auto_reply_rule(r),
            variant="ghost", height=28, text_color=toggle_color
        ).pack(side="left", padx=PAD_XS)
        
        create_premium_button(
            actions, "🗑", 
            command=lambda r=rule.id: self.controller.delete_auto_reply_rule(r),
            variant="danger", width=30, height=28
        ).pack(side="left", padx=PAD_XS)
