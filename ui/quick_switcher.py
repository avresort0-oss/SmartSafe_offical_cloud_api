import customtkinter as ctk
from typing import List, Callable, Optional
from services.workspace_service import WorkspaceDTO

class QuickSwitcher(ctk.CTkToplevel):
    """
    A premium Ctrl+K Quick Switcher for rapid workspace navigation.
    """
    def __init__(self, master, workspaces: List[WorkspaceDTO], on_select: Callable[[WorkspaceDTO], None]):
        super().__init__(master)
        self.title("Quick Switcher")
        self.geometry("500x400")
        self.attributes("-topmost", True)
        self.overrideredirect(True) # Borderless for premium feel
        
        # Center on screen
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        x = (screen_width // 2) - (500 // 2)
        y = (screen_height // 2) - (400 // 2)
        self.geometry(f"500x400+{x}+{y}")
        
        self.workspaces = workspaces
        self.on_select = on_select
        self.filtered_workspaces = workspaces
        
        self.configure(fg_color="#1f2c34")
        
        # UI Elements
        self.search_entry = ctk.CTkEntry(self, placeholder_text="Search workspace...", height=50, font=ctk.CTkFont(size=16), fg_color="#2a3942", border_width=0)
        self.search_entry.pack(fill="x", padx=10, pady=10)
        self.search_entry.bind("<KeyRelease>", self._filter_list)
        self.search_entry.bind("<Return>", self._select_first)
        self.search_entry.bind("<Escape>", lambda e: self.destroy())
        self.search_entry.focus_set()
        
        self.results_frame = ctk.CTkScrollableFrame(self, fg_color="transparent", height=300)
        self.results_frame.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        
        self._render_results()

    def _filter_list(self, event=None):
        query = self.search_entry.get().lower()
        self.filtered_workspaces = [ws for ws in self.workspaces if query in ws.name.lower()]
        self._clear_results()
        self._render_results()

    def _clear_results(self):
        for child in self.results_frame.winfo_children():
            child.destroy()

    def _render_results(self):
        for ws in self.filtered_workspaces:
            btn = ctk.CTkButton(
                self.results_frame, 
                text=ws.name, 
                anchor="w", 
                fg_color="transparent", 
                hover_color="#2b2b2b", 
                text_color="#ffffff",
                height=40,
                command=lambda w=ws: self._handle_selection(w)
            )
            btn.pack(fill="x", pady=2)

    def _handle_selection(self, workspace: WorkspaceDTO):
        self.on_select(workspace)
        self.destroy()

    def _select_first(self, event=None):
        if self.filtered_workspaces:
            self._handle_selection(self.filtered_workspaces[0])
