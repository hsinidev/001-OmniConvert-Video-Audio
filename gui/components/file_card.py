import os
import customtkinter as ctk
from typing import Callable, Dict, Any, Optional


class FileCard(ctk.CTkFrame):
    """
    Individual Queue File Item Card widget.
    Renders file metadata, real-time conversion progress bar, status badges, and item control buttons.
    """

    STATUS_COLORS = {
        "Pending": ("#D97706", "#F59E0B"),
        "Converting": ("#2563EB", "#3B82F6"),
        "Done": ("#059669", "#10B981"),
        "Error": ("#DC2626", "#EF4444"),
        "Cancelled": ("#4B5563", "#6B7280")
    }

    def __init__(
        self,
        master,
        item_id: str,
        file_path: str,
        meta: Dict[str, Any],
        on_remove: Callable[[str], None],
        on_move_up: Callable[[str], None],
        on_move_down: Callable[[str], None],
        **kwargs
    ):
        super().__init__(master, corner_radius=8, **kwargs)
        self.item_id = item_id
        self.file_path = file_path
        self.meta = meta
        self.on_remove = on_remove
        self.on_move_up = on_move_up
        self.on_move_down = on_move_down
        self.status = "Pending"

        self.grid_columnconfigure(1, weight=1)

        # Left Column: Reorder Controls (Up / Down)
        self.reorder_frame = ctk.CTkFrame(self, fg_color="transparent", width=24)
        self.reorder_frame.grid(row=0, column=0, rowspan=2, padx=(6, 2), pady=6, sticky="ns")

        self.btn_up = ctk.CTkButton(
            self.reorder_frame,
            text="▲",
            width=20,
            height=18,
            fg_color="transparent",
            hover_color=("gray80", "gray30"),
            font=ctk.CTkFont(size=9),
            command=lambda: self.on_move_up(self.item_id)
        )
        self.btn_up.pack(pady=(2, 1))

        self.btn_down = ctk.CTkButton(
            self.reorder_frame,
            text="▼",
            width=20,
            height=18,
            fg_color="transparent",
            hover_color=("gray80", "gray30"),
            font=ctk.CTkFont(size=9),
            command=lambda: self.on_move_down(self.item_id)
        )
        self.btn_down.pack(pady=(1, 2))

        # Main Info Frame
        self.info_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.info_frame.grid(row=0, column=1, padx=6, pady=(6, 2), sticky="ew")
        self.info_frame.grid_columnconfigure(0, weight=1)

        # File Name & Size
        filename = os.path.basename(file_path)
        self.name_label = ctk.CTkLabel(
            self.info_frame,
            text=filename,
            font=ctk.CTkFont(size=13, weight="bold"),
            anchor="w"
        )
        self.name_label.grid(row=0, column=0, sticky="w")

        # Format Metadata Subtitle String
        dur_str = meta.get("duration_str", "00:00:00")
        res_str = meta.get("resolution_str", "Audio Only") if meta.get("has_video") else "Audio"
        fps_str = meta.get("fps_str", "")
        codec_str = meta.get("video_codec", "") if meta.get("has_video") else meta.get("audio_codec", "")
        size_str = meta.get("file_size_str", "")

        meta_info = f"{size_str}  •  {dur_str}  •  {res_str}"
        if fps_str and fps_str != "N/A":
            meta_info += f" @ {fps_str}"
        if codec_str:
            meta_info += f" ({codec_str})"

        self.meta_label = ctk.CTkLabel(
            self.info_frame,
            text=meta_info,
            font=ctk.CTkFont(size=11),
            text_color=("gray50", "gray65"),
            anchor="w"
        )
        self.meta_label.grid(row=1, column=0, sticky="w")

        # Right Side: Status Badge & Remove Button
        self.control_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.control_frame.grid(row=0, column=2, padx=(4, 8), pady=6, sticky="e")

        self.status_badge = ctk.CTkLabel(
            self.control_frame,
            text="Pending",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color="#FFFFFF",
            fg_color=self.STATUS_COLORS["Pending"][1],
            corner_radius=6,
            width=75,
            height=24
        )
        self.status_badge.pack(side="left", padx=(0, 6))

        self.btn_remove = ctk.CTkButton(
            self.control_frame,
            text="✕",
            width=24,
            height=24,
            fg_color="transparent",
            hover_color=("#EF4444", "#DC2626"),
            text_color=("gray40", "gray70"),
            font=ctk.CTkFont(size=12, weight="bold"),
            command=lambda: self.on_remove(self.item_id)
        )
        self.btn_remove.pack(side="right")

        # Progress Bar & Metrics Row
        self.progress_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.progress_frame.grid(row=1, column=1, columnspan=2, padx=6, pady=(0, 6), sticky="ew")
        self.progress_frame.grid_columnconfigure(0, weight=1)

        self.progress_bar = ctk.CTkProgressBar(self.progress_frame, height=8)
        self.progress_bar.grid(row=0, column=0, sticky="ew", padx=(0, 10))
        self.progress_bar.set(0.0)

        self.telemetry_label = ctk.CTkLabel(
            self.progress_frame,
            text="0%",
            font=ctk.CTkFont(size=11),
            text_color=("gray50", "gray65"),
            width=120,
            anchor="e"
        )
        self.telemetry_label.grid(row=0, column=1, sticky="e")

    def update_status(self, status: str, message: Optional[str] = None):
        """Updates status badge color and text."""
        self.status = status
        color = self.STATUS_COLORS.get(status, ("#4B5563", "#6B7280"))[1]
        self.status_badge.configure(text=status, fg_color=color)

    def update_progress(self, metrics: Dict[str, Any]):
        """Updates item progress bar and live telemetry text."""
        pct = metrics.get("progress_percent", 0.0)
        self.progress_bar.set(pct / 100.0)

        speed = metrics.get("speed", 1.0)
        fps = metrics.get("fps", 0.0)
        eta = metrics.get("eta_str", "00:00")

        text = f"{pct:.1f}%"
        if speed > 0 and self.status == "Converting":
            text = f"{pct:.1f}%  ({speed:.1f}x | ETA {eta})"

        self.telemetry_label.configure(text=text)
