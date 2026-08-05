import os
import customtkinter as ctk
from tkinter import filedialog
from typing import Dict, Any, Callable


class ControlPanel(ctk.CTkFrame):
    """
    Granular Transcoding & Encoding Controls Panel.
    Includes container format selector, CRF quality slider, encoding presets,
    resolution scaling options, audio bitrate options, and destination folder selector.
    """

    FORMATS = ["MP4", "MKV", "AVI", "MP3", "FLAC", "WAV"]
    PRESETS = ["ultrafast", "superfast", "veryfast", "faster", "fast", "medium", "slow", "slower", "veryslow"]
    RESOLUTIONS = ["Original", "3840x2160 (4K)", "1920x1080 (1080p)", "1280x720 (720p)", "854x480 (480p)"]
    AUDIO_BITRATES = ["96k", "128k", "192k", "256k", "320k"]

    def __init__(self, master, **kwargs):
        super().__init__(master, corner_radius=10, **kwargs)

        self.grid_columnconfigure((0, 1), weight=1)

        # Title Header
        self.title_label = ctk.CTkLabel(
            self,
            text="⚙️ Encoding Settings",
            font=ctk.CTkFont(size=15, weight="bold")
        )
        self.title_label.grid(row=0, column=0, columnspan=2, padx=12, pady=(12, 8), sticky="w")

        # Container Format Row
        self.lbl_format = ctk.CTkLabel(self, text="Container Format:", font=ctk.CTkFont(size=12, weight="bold"))
        self.lbl_format.grid(row=1, column=0, padx=12, pady=(4, 2), sticky="w")

        self.format_menu = ctk.CTkOptionMenu(
            self,
            values=self.FORMATS,
            command=self._on_format_change
        )
        self.format_menu.grid(row=2, column=0, padx=12, pady=(0, 8), sticky="ew")
        self.format_menu.set("MP4")

        # Resolution Scaler Row
        self.lbl_res = ctk.CTkLabel(self, text="Resolution Scaler:", font=ctk.CTkFont(size=12, weight="bold"))
        self.lbl_res.grid(row=1, column=1, padx=12, pady=(4, 2), sticky="w")

        self.res_menu = ctk.CTkOptionMenu(
            self,
            values=self.RESOLUTIONS
        )
        self.res_menu.grid(row=2, column=1, padx=12, pady=(0, 8), sticky="ew")
        self.res_menu.set("Original")

        # Video CRF Slider (Quality Control)
        self.crf_header_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.crf_header_frame.grid(row=3, column=0, columnspan=2, padx=12, pady=(4, 2), sticky="ew")

        self.lbl_crf = ctk.CTkLabel(
            self.crf_header_frame,
            text="Video Quality (CRF 18–28):",
            font=ctk.CTkFont(size=12, weight="bold")
        )
        self.lbl_crf.pack(side="left")

        self.lbl_crf_val = ctk.CTkLabel(
            self.crf_header_frame,
            text="22 (Balanced)",
            font=ctk.CTkFont(size=11),
            text_color=("gray40", "gray65")
        )
        self.lbl_crf_val.pack(side="right")

        self.crf_slider = ctk.CTkSlider(
            self,
            from_=18,
            to=28,
            number_of_steps=10,
            command=self._on_crf_slider_change
        )
        self.crf_slider.grid(row=4, column=0, columnspan=2, padx=12, pady=(0, 8), sticky="ew")
        self.crf_slider.set(22)

        # Preset & Audio Bitrate Row
        self.lbl_preset = ctk.CTkLabel(self, text="Encoding Preset:", font=ctk.CTkFont(size=12, weight="bold"))
        self.lbl_preset.grid(row=5, column=0, padx=12, pady=(4, 2), sticky="w")

        self.preset_menu = ctk.CTkOptionMenu(self, values=self.PRESETS)
        self.preset_menu.grid(row=6, column=0, padx=12, pady=(0, 8), sticky="ew")
        self.preset_menu.set("medium")

        self.lbl_audio_bitrate = ctk.CTkLabel(self, text="Audio Bitrate:", font=ctk.CTkFont(size=12, weight="bold"))
        self.lbl_audio_bitrate.grid(row=5, column=1, padx=12, pady=(4, 2), sticky="w")

        self.audio_bitrate_menu = ctk.CTkOptionMenu(self, values=self.AUDIO_BITRATES)
        self.audio_bitrate_menu.grid(row=6, column=1, padx=12, pady=(0, 8), sticky="ew")
        self.audio_bitrate_menu.set("192k")

        # Output Folder Selector
        self.lbl_dest = ctk.CTkLabel(self, text="Output Folder:", font=ctk.CTkFont(size=12, weight="bold"))
        self.lbl_dest.grid(row=7, column=0, columnspan=2, padx=12, pady=(4, 2), sticky="w")

        self.dest_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.dest_frame.grid(row=8, column=0, columnspan=2, padx=12, pady=(0, 12), sticky="ew")
        self.dest_frame.grid_columnconfigure(0, weight=1)

        default_out_dir = os.path.join(os.path.expanduser("~"), "Videos", "OmniConvert_Output")
        self.dest_entry = ctk.CTkEntry(self.dest_frame)
        self.dest_entry.grid(row=0, column=0, padx=(0, 6), sticky="ew")
        self.dest_entry.insert(0, default_out_dir)

        self.btn_dest_browse = ctk.CTkButton(
            self.dest_frame,
            text="Choose...",
            width=90,
            command=self._on_browse_dest
        )
        self.btn_dest_browse.grid(row=0, column=1)

    def _on_crf_slider_change(self, val):
        crf = int(round(val))
        if crf <= 19:
            qual_str = "Near Lossless"
        elif crf <= 23:
            qual_str = "Balanced"
        else:
            qual_str = "High Compression"
        self.lbl_crf_val.configure(text=f"{crf} ({qual_str})")

    def _on_format_change(self, selected_fmt: str):
        is_audio = selected_fmt.lower() in ["mp3", "flac", "wav"]
        state = "disabled" if is_audio else "normal"

        self.res_menu.configure(state=state)
        self.crf_slider.configure(state=state)
        self.preset_menu.configure(state=state)

    def _on_browse_dest(self):
        folder = filedialog.askdirectory(
            title="Select Destination Output Folder",
            initialdir=self.dest_entry.get()
        )
        if folder:
            self.dest_entry.delete(0, "end")
            self.dest_entry.insert(0, os.path.normpath(folder))

    def get_settings(self) -> Dict[str, Any]:
        """Returns dict of current user-selected encoding controls."""
        return {
            "output_format": self.format_menu.get().lower(),
            "resolution": self.res_menu.get(),
            "crf": int(round(self.crf_slider.get())),
            "preset": self.preset_menu.get(),
            "audio_bitrate": self.audio_bitrate_menu.get(),
            "output_dir": os.path.normpath(self.dest_entry.get().strip())
        }
