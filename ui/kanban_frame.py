import customtkinter as ctk
from typing import Callable, List, Optional
from ui.styles import ACCENT_COLOR, get_font

class KanbanFrame(ctk.CTkFrame):
    def __init__(self, master, fetch_contacts_cb: Callable, update_stage_cb: Callable):
        super().__init__(master, fg_color="transparent")
        self.fetch_contacts_cb = fetch_contacts_cb
        self.update_stage_cb = update_stage_cb
        
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure((0, 1, 2, 3), weight=1, uniform="col")
        
        # Header
        header_frame = ctk.CTkFrame(self, fg_color="transparent")
        header_frame.grid(row=0, column=0, columnspan=4, sticky="ew", pady=(0, 20))
        
        ctk.CTkLabel(header_frame, text="Leads Pipeline", font=get_font(size=24, weight="bold"), text_color=ACCENT_COLOR).pack(side="left")
        
        refresh_btn = ctk.CTkButton(header_frame, text="Refresh", width=100, command=self.load_data)
        refresh_btn.pack(side="right")
        
        self.stages = ["LEAD", "INTERESTED", "NEGOTIATING", "CLOSED"]
        self.columns = {}
        
        for i, stage in enumerate(self.stages):
            col_frame = ctk.CTkFrame(self, fg_color="#1e293b", corner_radius=10)
            col_frame.grid(row=1, column=i, sticky="nsew", padx=10)
            col_frame.grid_rowconfigure(1, weight=1)
            col_frame.grid_columnconfigure(0, weight=1)
            
            # Column header
            ctk.CTkLabel(col_frame, text=stage, font=get_font(size=16, weight="bold"), text_color="white").grid(row=0, column=0, pady=10)
            
            # Scrollable area for cards
            scroll_area = ctk.CTkScrollableFrame(col_frame, fg_color="transparent")
            scroll_area.grid(row=1, column=0, sticky="nsew", padx=5, pady=5)
            
            self.columns[stage] = scroll_area

    def load_data(self):
        # Clear existing cards
        for stage, scroll_area in self.columns.items():
            for widget in scroll_area.winfo_children():
                widget.destroy()
                
        contacts = self.fetch_contacts_cb()
        if not contacts:
            return
            
        for contact in contacts:
            stage = contact.lifecycle_stage.upper() if contact.lifecycle_stage else "LEAD"
            if stage not in self.stages:
                stage = "LEAD"
            
            self._create_card(self.columns[stage], contact)

    def _create_card(self, parent, contact):
        card = ctk.CTkFrame(parent, fg_color="#334155", corner_radius=8)
        card.pack(fill="x", pady=5, padx=5)
        
        name = contact.display_name or "Unknown"
        phone = contact.phone_e164 or ""
        
        ctk.CTkLabel(card, text=name, font=get_font(size=14, weight="bold"), anchor="w").pack(fill="x", padx=10, pady=(10, 0))
        ctk.CTkLabel(card, text=phone, font=get_font(size=12), text_color="gray", anchor="w").pack(fill="x", padx=10, pady=(0, 10))
        
        # Action buttons to move stages (simulating drag and drop for simple UI)
        btn_frame = ctk.CTkFrame(card, fg_color="transparent")
        btn_frame.pack(fill="x", padx=10, pady=(0, 10))
        
        stages = ["LEAD", "INTERESTED", "NEGOTIATING", "CLOSED"]
        current_idx = stages.index(contact.lifecycle_stage.upper()) if contact.lifecycle_stage.upper() in stages else 0
        
        if current_idx > 0:
            btn_prev = ctk.CTkButton(btn_frame, text="<", width=30, height=24, fg_color="#475569", hover_color="#64748b",
                                     command=lambda c=contact, s=stages[current_idx-1]: self._move_card(c, s))
            btn_prev.pack(side="left")
            
        if current_idx < len(stages) - 1:
            btn_next = ctk.CTkButton(btn_frame, text=">", width=30, height=24, fg_color="#475569", hover_color="#64748b",
                                     command=lambda c=contact, s=stages[current_idx+1]: self._move_card(c, s))
            btn_next.pack(side="right")

    def _move_card(self, contact, new_stage):
        success = self.update_stage_cb(contact.id, new_stage)
        if success:
            self.load_data()
