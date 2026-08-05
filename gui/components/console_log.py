import customtkinter as ctk


class ConsoleLog(ctk.CTkFrame):
    """
    Collapsible Real-Time Terminal Console Log Viewer.
    Features auto-scrolling log text display, clear log button, and collapse/expand toggle.
    """

    def __init__(self, master, **kwargs):
        super().__init__(master, corner_radius=10, **kwargs)
        self.is_expanded = True

        self.grid_columnconfigure(0, weight=1)

        # Header Frame
        self.header_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.header_frame.grid(row=0, column=0, padx=10, pady=(6, 4), sticky="ew")
        self.header_frame.grid_columnconfigure(0, weight=1)

        self.lbl_title = ctk.CTkLabel(
            self.header_frame,
            text="💻 Application & FFmpeg Telemetry Console Log",
            font=ctk.CTkFont(size=12, weight="bold")
        )
        self.lbl_title.grid(row=0, column=0, sticky="w")

        # Controls: Clear Log & Toggle Collapse
        self.btn_clear = ctk.CTkButton(
            self.header_frame,
            text="Clear Log",
            width=70,
            height=24,
            font=ctk.CTkFont(size=11),
            fg_color=("gray75", "gray30"),
            hover_color=("gray65", "gray40"),
            command=self.clear_log
        )
        self.btn_clear.grid(row=0, column=1, padx=(0, 6))

        self.btn_toggle = ctk.CTkButton(
            self.header_frame,
            text="▲ Collapse",
            width=80,
            height=24,
            font=ctk.CTkFont(size=11),
            command=self.toggle_collapse
        )
        self.btn_toggle.grid(row=0, column=2)

        # Log Textbox
        self.textbox = ctk.CTkTextbox(
            self,
            font=ctk.CTkFont(family="Consolas", size=11),
            wrap="none",
            height=120
        )
        self.textbox.grid(row=1, column=0, padx=10, pady=(0, 10), sticky="ew")
        self.textbox.configure(state="disabled")

    def append_log(self, text: str):
        """Appends a new line to the console and auto-scrolls to end."""
        self.textbox.configure(state="normal")
        self.textbox.insert("end", text + "\n")
        self.textbox.see("end")
        self.textbox.configure(state="disabled")

    def clear_log(self):
        """Clears all text from console log."""
        self.textbox.configure(state="normal")
        self.textbox.delete("1.0", "end")
        self.textbox.configure(state="disabled")

    def toggle_collapse(self):
        """Toggles visibility of the log textbox."""
        if self.is_expanded:
            self.textbox.grid_remove()
            self.btn_toggle.configure(text="▼ Expand")
            self.is_expanded = False
        else:
            self.textbox.grid(row=1, column=0, padx=10, pady=(0, 10), sticky="ew")
            self.btn_toggle.configure(text="▲ Collapse")
            self.is_expanded = True
