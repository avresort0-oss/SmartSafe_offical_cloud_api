import customtkinter as ctk

class Tooltip:
    """
    A simple tooltip implementation for CustomTkinter widgets.
    It creates a small popup window when the user hovers over the associated widget.
    """
    def __init__(self, widget, text: str):
        self.widget = widget
        self.text = text
        self.tooltip_window = None
        self.widget.bind("<Enter>", self.show_tooltip)
        self.widget.bind("<Leave>", self.hide_tooltip)

    def show_tooltip(self, event=None):
        if self.tooltip_window or not self.text:
            return
        
        # Calculate position below the widget
        x = self.widget.winfo_rootx()
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 5

        self.tooltip_window = ctk.CTkToplevel(self.widget)
        self.tooltip_window.wm_overrideredirect(True) # Remove window decorations
        self.tooltip_window.wm_geometry(f"+{x}+{y}")
        self.tooltip_window.attributes("-topmost", True)

        label = ctk.CTkLabel(self.tooltip_window, text=self.text, justify='left',
                             fg_color="#2A2D2E", corner_radius=6, text_color="#DCE4E6",
                             font=ctk.CTkFont(size=11), wraplength=250)
        label.pack(ipadx=8, ipady=5)

    def hide_tooltip(self, event=None):
        if self.tooltip_window:
            self.tooltip_window.destroy()
        self.tooltip_window = None