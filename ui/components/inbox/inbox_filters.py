import customtkinter as ctk
from ui.styles import BG_COLOR, TEXT_COLOR, get_font

class InboxFilters(ctk.CTkFrame):
    def __init__(self, master, on_filter_change, **kwargs):
        super().__init__(master, fg_color=BG_COLOR, height=50, **kwargs)
        self.on_filter_change = on_filter_change
        
        self.status_var = ctk.StringVar(value="All")
        
        filters = ["All", "Unread", "Open", "Closed"]
        for i, f in enumerate(filters):
            rb = ctk.CTkRadioButton(self, text=f, variable=self.status_var, value=f, 
                                    command=self._on_change, font=get_font(size=12))
            rb.pack(side="left", padx=10, pady=10)
            
    def _on_change(self):
        if self.on_filter_change:
            self.on_filter_change(self.status_var.get())
