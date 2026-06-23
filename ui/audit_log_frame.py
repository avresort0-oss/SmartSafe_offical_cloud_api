import customtkinter as ctk
from typing import Callable, List
from ui.styles import ACCENT_COLOR, get_font

class AuditLogFrame(ctk.CTkFrame):
    def __init__(self, master, fetch_logs_cb: Callable):
        super().__init__(master, fg_color="transparent")
        self.fetch_logs_cb = fetch_logs_cb
        
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)
        
        # Header
        header_frame = ctk.CTkFrame(self, fg_color="transparent")
        header_frame.grid(row=0, column=0, sticky="ew", pady=(0, 20))
        
        ctk.CTkLabel(header_frame, text="Security & Audit Logs", font=get_font(size=24, weight="bold"), text_color=ACCENT_COLOR).pack(side="left")
        
        refresh_btn = ctk.CTkButton(header_frame, text="Refresh Logs", width=120, command=self.load_data)
        refresh_btn.pack(side="right")
        
        # Table Header
        table_header = ctk.CTkFrame(self, fg_color="#1e293b", corner_radius=8)
        table_header.grid(row=1, column=0, sticky="ew", padx=10, pady=(0, 5))
        
        cols = ["Timestamp", "User ID", "Action", "Target", "IP Address"]
        for i, col in enumerate(cols):
            table_header.grid_columnconfigure(i, weight=1)
            ctk.CTkLabel(table_header, text=col, font=get_font(size=14, weight="bold"), text_color="white").grid(row=0, column=i, pady=10, sticky="w", padx=10)
            
        # Scrollable list
        self.scroll_area = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.scroll_area.grid(row=2, column=0, sticky="nsew", padx=5)

    def load_data(self):
        for widget in self.scroll_area.winfo_children():
            widget.destroy()
            
        logs = self.fetch_logs_cb()
        if not logs:
            ctk.CTkLabel(self.scroll_area, text="No audit logs found.", font=get_font(size=14), text_color="gray").pack(pady=20)
            return
            
        for log in logs:
            row = ctk.CTkFrame(self.scroll_area, fg_color="#334155", corner_radius=4)
            row.pack(fill="x", pady=2)
            
            for i in range(5):
                row.grid_columnconfigure(i, weight=1)
                
            ts = log.created_at.strftime("%Y-%m-%d %H:%M:%S") if log.created_at else "N/A"
            ctk.CTkLabel(row, text=ts, font=get_font(size=12)).grid(row=0, column=0, sticky="w", padx=10, pady=5)
            ctk.CTkLabel(row, text=str(log.user_id)[:8], font=get_font(size=12)).grid(row=0, column=1, sticky="w", padx=10, pady=5)
            ctk.CTkLabel(row, text=log.action, font=get_font(size=12), text_color=ACCENT_COLOR).grid(row=0, column=2, sticky="w", padx=10, pady=5)
            ctk.CTkLabel(row, text=str(log.target_id)[:8] if log.target_id else "-", font=get_font(size=12)).grid(row=0, column=3, sticky="w", padx=10, pady=5)
            ctk.CTkLabel(row, text=log.ip_address or "-", font=get_font(size=12)).grid(row=0, column=4, sticky="w", padx=10, pady=5)
