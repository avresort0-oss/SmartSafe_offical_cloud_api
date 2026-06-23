import customtkinter as ctk
from ui.styles import BG_COLOR, TEXT_COLOR, get_font, HOVER_COLOR

class ConversationList(ctk.CTkScrollableFrame):
    def __init__(self, master, on_conversation_select, **kwargs):
        super().__init__(master, fg_color=BG_COLOR, corner_radius=0, **kwargs)
        self.on_conversation_select = on_conversation_select
        self.conversations = []
        
    def populate(self, conversations):
        for widget in self.winfo_children():
            widget.destroy()
            
        self.conversations = conversations
        for conv in conversations:
            self._create_card(conv)
            
    def _create_card(self, conv):
        card = ctk.CTkFrame(self, fg_color="transparent", corner_radius=8, cursor="hand2")
        card.pack(fill="x", pady=2, padx=5)
        
        name = conv.contact.display_name if conv.contact else "Unknown"
        ctk.CTkLabel(card, text=name, font=get_font(size=14, weight="bold"), anchor="w").pack(fill="x", padx=10, pady=(10, 5))
        
        card.bind("<Button-1>", lambda e, c=conv: self.on_conversation_select(c))
        for child in card.winfo_children():
            child.bind("<Button-1>", lambda e, c=conv: self.on_conversation_select(c))
