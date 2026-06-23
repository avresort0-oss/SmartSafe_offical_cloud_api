import customtkinter as ctk
from ui.styles import HEADER_FOOTER_COLOR, ACCENT_COLOR, TEXT_COLOR, get_font, HOVER_COLOR

class ChatHeader(ctk.CTkFrame):
    def __init__(self, master, on_add_label_click=None, on_create_contract_click=None, **kwargs):
        super().__init__(master, fg_color=HEADER_FOOTER_COLOR, corner_radius=0, height=62, **kwargs)
        self.grid_propagate(False)
        self.on_add_label_click = on_add_label_click
        self.on_create_contract_click = on_create_contract_click
        
        # Profile Circle
        self.avatar_label = ctk.CTkLabel(self, text="W", width=42, height=42, corner_radius=21, 
                                         fg_color=ACCENT_COLOR, text_color="#ffffff", font=get_font(size=15, weight="bold"))
        self.avatar_label.pack(side="left", padx=(15, 12), pady=9)
        
        # Contact Info Container
        info_container = ctk.CTkFrame(self, fg_color="transparent")
        info_container.pack(side="left", fill="y", pady=9)
        self.title_label = ctk.CTkLabel(info_container, text="Select a conversation", font=get_font(size=16, weight="bold"), text_color=TEXT_COLOR)
        self.title_label.pack(anchor="w")
        self.status_label = ctk.CTkLabel(info_container, text="offline", font=get_font(size=13), text_color=ACCENT_COLOR)
        self.status_label.pack(anchor="w")

        # Advanced Header Components
        self.header_actions = ctk.CTkFrame(self, fg_color="transparent")
        self.header_actions.pack(side="right", padx=15, pady=9)

        self.timer_badge = ctk.CTkLabel(self.header_actions, text="24h Window: --:--", font=get_font(size=11, weight="bold"),
                                        fg_color="#343f46", text_color="#e9edef", corner_radius=12, height=24, padx=10)
        self.timer_badge.pack(side="right", padx=(10, 0))
        self.timer_badge.pack_forget() 

        self.header_labels_frame = ctk.CTkFrame(self.header_actions, fg_color="transparent")
        self.header_labels_frame.pack(side="right", padx=(10, 0))

        if self.on_add_label_click:
            self.add_label_btn = ctk.CTkButton(self.header_actions, text="+ Label", width=70, height=24, fg_color="transparent", 
                                               hover_color=HOVER_COLOR, text_color=ACCENT_COLOR, border_width=1, border_color=ACCENT_COLOR,
                                               corner_radius=12, font=get_font(size=11, weight="bold"), command=self.on_add_label_click)
            self.add_label_btn.pack(side="right", padx=(10, 0))
            
        if self.on_create_contract_click:
            self.add_contract_btn = ctk.CTkButton(self.header_actions, text="📝 Contract", width=80, height=24, fg_color="transparent", 
                                               hover_color=HOVER_COLOR, text_color="#10b981", border_width=1, border_color="#10b981",
                                               corner_radius=12, font=get_font(size=11, weight="bold"), command=self.on_create_contract_click)
            self.add_contract_btn.pack(side="right", padx=(10, 0))
            
    def set_conversation(self, title: str, status_text: str = "online"):
        self.title_label.configure(text=title)
        self.status_label.configure(text=status_text)
