import customtkinter as ctk
from ui.styles import CHAT_BG_COLOR

class MessageList(ctk.CTkScrollableFrame):
    def __init__(self, master, **kwargs):
        super().__init__(master, fg_color=CHAT_BG_COLOR, corner_radius=0, **kwargs)
