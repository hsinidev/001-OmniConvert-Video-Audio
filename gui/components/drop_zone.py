import os
import re
import customtkinter as ctk
from tkinter import filedialog
from typing import Callable, List


class DropZone(ctk.CTkFrame):
    """
    Drag and Drop File Target supporting native OS drop events (<<Drop>>) via TkinterDnD2
    and interactive click-to-browse file selector fallback.
    """

    SUPPORTED_EXTENSIONS = {
        ".mp4", ".mkv", ".avi", ".mov", ".flv", ".wmv", ".webm", ".m4v", ".3gp",
        ".mp3", ".wav", ".flac", ".aac", ".ogg", ".m4a", ".wma"
    }

    def __init__(self, master, on_files_dropped: Callable[[List[str]], None], **kwargs):
        super().__init__(master, **kwargs)
        self.on_files_dropped = on_files_dropped

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Container Frame
        self.inner_frame = ctk.CTkFrame(
            self,
            corner_radius=12,
            border_width=2,
            border_color=("#3B82F6", "#2563EB"),
            fg_color="transparent"
        )
        self.inner_frame.grid(row=0, column=0, padx=12, pady=12, sticky="nsew")
        self.inner_frame.grid_columnconfigure(0, weight=1)

        # Icon / Header
        self.icon_label = ctk.CTkLabel(
            self.inner_frame,
            text="📁 Drop Media Files Here",
            font=ctk.CTkFont(size=18, weight="bold")
        )
        self.icon_label.grid(row=0, column=0, pady=(20, 5))

        # Subtitle
        self.sub_label = ctk.CTkLabel(
            self.inner_frame,
            text="Drag and drop video & audio files or click below to select",
            font=ctk.CTkFont(size=12),
            text_color=("gray60", "gray70")
        )
        self.sub_label.grid(row=1, column=0, pady=(0, 15))

        # Browse Button
        self.browse_button = ctk.CTkButton(
            self.inner_frame,
            text="Browse Files",
            width=140,
            height=36,
            corner_radius=8,
            command=self.open_file_dialog
        )
        self.browse_button.grid(row=2, column=0, pady=(0, 20))

        # Register Drop Target if TkinterDnD2 is available
        self.setup_dnd()

    def setup_dnd(self):
        """Attempts to register TkinterDnD2 drop target events."""
        try:
            self.inner_frame.drop_target_register("*")
            self.inner_frame.dnd_bind('<<Drop>>', self.handle_drop)
            self.drop_target_register("*")
            self.dnd_bind('<<Drop>>', self.handle_drop)
        except Exception:
            # Fallback if dnd_bind isn't directly bound to subwidget
            pass

    def handle_drop(self, event):
        """Parses dropped payload paths."""
        raw_data = getattr(event, 'data', '')
        files = self.parse_drop_payload(raw_data)
        valid_files = [f for f in files if os.path.isfile(f)]
        if valid_files and self.on_files_dropped:
            self.on_files_dropped(valid_files)

    @staticmethod
    def parse_drop_payload(payload: str) -> List[str]:
        """
        Parses single or multiple Windows file path strings from drop payload
        handling curly braces `{C:/path with spaces/file.mp4}` and plain paths.
        """
        if not payload:
            return []

        paths = []
        # Pattern to match {path with spaces} or non-space sequences
        pattern = r'\{([^}]+)\}|(\S+)'
        matches = re.findall(pattern, payload)
        for match in matches:
            path = match[0] if match[0] else match[1]
            path = os.path.normpath(path.strip())
            paths.append(path)

        return paths

    def open_file_dialog(self):
        """Opens native file selector dialog."""
        file_types = [
            ("All Supported Media", "*.mp4 *.mkv *.avi *.mov *.flv *.wmv *.webm *.m4v *.mp3 *.wav *.flac *.aac *.ogg *.m4a"),
            ("Video Files", "*.mp4 *.mkv *.avi *.mov *.flv *.wmv *.webm *.m4v"),
            ("Audio Files", "*.mp3 *.wav *.flac *.aac *.ogg *.m4a"),
            ("All Files", "*.*")
        ]
        selected_files = filedialog.askopenfilenames(
            title="Select Video / Audio Files to Convert",
            filetypes=file_types
        )
        if selected_files and self.on_files_dropped:
            self.on_files_dropped(list(selected_files))
