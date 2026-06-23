import customtkinter as ctk
from ui.styles import HEADER_FOOTER_COLOR, INPUT_COLOR, TEXT_COLOR, get_font, HOVER_COLOR

class ChatInput(ctk.CTkFrame):
    def __init__(self, master, on_send, on_attach, on_type, **kwargs):
        super().__init__(master, fg_color=HEADER_FOOTER_COLOR, corner_radius=0, height=60, **kwargs)
        self.on_send = on_send
        self.on_attach = on_attach
        self.on_type = on_type
        
        self.grid_columnconfigure(1, weight=1)
        
        self.attach_btn = ctk.CTkButton(self, text="📎", width=40, height=40, fg_color="transparent", 
                                        hover_color=HOVER_COLOR, text_color=TEXT_COLOR, font=get_font(size=18), command=self.on_attach)
        self.attach_btn.grid(row=0, column=0, padx=(15, 5), pady=10)
        
        self.input_entry = ctk.CTkEntry(self, placeholder_text="Type a message...", height=40, corner_radius=20, 
                                        fg_color=INPUT_COLOR, border_width=0, font=get_font(size=14))
        self.input_entry.grid(row=0, column=1, sticky="ew", padx=5, pady=10)
        self.input_entry.bind("<Return>", lambda e: self.on_send())
        self.input_entry.bind("<KeyRelease>", self.on_type)
        
        self.send_btn = ctk.CTkButton(self, text="▶", width=40, height=40, corner_radius=20, font=get_font(size=16), command=self.on_send)
        self.send_btn.grid(row=0, column=2, padx=(5, 15), pady=10)
        
    def get_text(self):
        return self.input_entry.get().strip()
        
    def clear(self):
        self.input_entry.delete(0, 'end')
