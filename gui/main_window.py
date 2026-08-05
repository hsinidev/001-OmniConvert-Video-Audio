import sys
import os
import uuid
import queue
import threading
import subprocess
import customtkinter as ctk
from tkinter import messagebox
from typing import Dict, List, Any, Optional

try:
    from tkinterdnd2 import TkinterDnD, DND_FILES
    DND_AVAILABLE = True
except ImportError:
    DND_AVAILABLE = False

from engine.binary_resolver import BinaryResolver
from engine.hw_accel import HWAccelProber
from engine.ffprobe_parser import FFprobeParser
from engine.transcode_worker import TranscodeWorker, TranscodeJob
from utils.logger import logger

from gui.styles import apply_custom_theme
from gui.components.drop_zone import DropZone
from gui.components.file_card import FileCard
from gui.components.control_panel import ControlPanel
from gui.components.hardware_selector import HardwareSelector
from gui.components.console_log import ConsoleLog


# Base class initialization supporting TkinterDnD2
if DND_AVAILABLE:
    class CTkWithDnD(ctk.CTk, TkinterDnD.DnDWrapper):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.TkdndVersion = TkinterDnD._require(self)
else:
    class CTkWithDnD(ctk.CTk):
        pass


class MainWindow(CTkWithDnD):
    """
    Main Application Window & Event Orchestration Engine.
    Handles 60 FPS UI rendering, 50ms queue event polling loop, theme switching,
    queue reordering, background probing, and batch transcode execution.
    """

    def __init__(self):
        super().__init__()

        # Apply Visual Theme
        apply_custom_theme()
        ctk.set_appearance_mode("Dark")

        # Window Setup
        self.title("OmniConvert Video & Audio  •  v1.0.0-PROD")
        self.geometry("1100x780")
        self.minsize(950, 680)

        # Thread Queue
        self.event_queue = queue.Queue()

        # Engine Modules
        self.resolver = BinaryResolver()
        self.ffmpeg_path = self.resolver.ffmpeg_path
        self.ffprobe_path = self.resolver.ffprobe_path

        self.ffprobe = FFprobeParser(self.ffprobe_path) if self.ffprobe_path else None

        self.hw_prober = HWAccelProber(self.ffmpeg_path) if self.ffmpeg_path else None
        self.available_hw = self.hw_prober.supported_hardware if self.hw_prober else ["CPU Software"]

        # Queue Data State
        # List of item dicts: [{"id": str, "file_path": str, "meta": dict, "card": FileCard, "status": str}]
        self.queue_items: List[Dict[str, Any]] = []

        # Batch Conversion State
        self.is_converting = False
        self.current_worker: Optional[TranscodeWorker] = None
        self.current_job_index = -1
        self.total_batch_count = 0
        self.completed_batch_count = 0

        # Build User Interface Layout
        self.build_ui()

        # Check Binary Status
        self.check_binary_status()

        # Start 50ms Queue Event Polling Loop (20 Hz update frequency)
        self.after(50, self.poll_event_queue)

    def check_binary_status(self):
        """Validates FFmpeg binaries and displays console message or warning dialog."""
        valid_map = self.resolver.validate_binaries()
        if not valid_map.get("ffmpeg") or not valid_map.get("ffprobe"):
            self.log_console("[WARNING] Embedded FFmpeg/FFprobe binaries missing or invalid.")
            self.log_console(f"FFmpeg Path: {self.ffmpeg_path}")
            self.log_console(f"FFprobe Path: {self.ffprobe_path}")
            messagebox.showwarning(
                "Binary Resolution",
                "FFmpeg or FFprobe static binaries were not automatically resolved.\n"
                "You can still add files, but probing and conversion require valid binaries."
            )
        else:
            self.log_console(f"[SYSTEM] FFmpeg binary loaded: {self.ffmpeg_path}")
            self.log_console(f"[SYSTEM] FFprobe binary loaded: {self.ffprobe_path}")
            self.log_console(f"[SYSTEM] Hardware Acceleration: {', '.join(self.available_hw)}")

    def build_ui(self):
        """Constructs responsive layout grids and compound UI components."""
        self.grid_columnconfigure(0, weight=3)  # Left column: DropZone & Queue
        self.grid_columnconfigure(1, weight=2)  # Right column: Settings & Controls
        self.grid_rowconfigure(1, weight=1)     # Center row expands

        # Top Header Bar
        self.header_frame = ctk.CTkFrame(self, corner_radius=0, fg_color=("gray90", "#1E293B"))
        self.header_frame.grid(row=0, column=0, columnspan=2, sticky="ew")
        self.header_frame.grid_columnconfigure(0, weight=1)

        self.title_label = ctk.CTkLabel(
            self.header_frame,
            text="🎬 OmniConvert Video & Audio Engine",
            font=ctk.CTkFont(size=18, weight="bold")
        )
        self.title_label.grid(row=0, column=0, padx=16, pady=10, sticky="w")

        # Top Right Header Controls
        self.header_right_frame = ctk.CTkFrame(self.header_frame, fg_color="transparent")
        self.header_right_frame.grid(row=0, column=1, padx=16, pady=5, sticky="e")

        # Hardware Selector Component
        self.hw_selector = HardwareSelector(
            self.header_right_frame,
            available_hardware=self.available_hw,
            fg_color="transparent"
        )
        self.hw_selector.pack(side="left", padx=(0, 15))

        # Light / Dark Theme Switch
        self.theme_switch = ctk.CTkSwitch(
            self.header_right_frame,
            text="Dark Mode",
            command=self.toggle_theme
        )
        self.theme_switch.pack(side="right")
        self.theme_switch.select()

        # Left Column: DropZone + Queue Container
        self.left_container = ctk.CTkFrame(self, fg_color="transparent")
        self.left_container.grid(row=1, column=0, padx=(12, 6), pady=10, sticky="nsew")
        self.left_container.grid_columnconfigure(0, weight=1)
        self.left_container.grid_rowconfigure(1, weight=1)

        # DropZone Component
        self.drop_zone = DropZone(
            self.left_container,
            on_files_dropped=self.add_files_to_queue,
            height=140
        )
        self.drop_zone.grid(row=0, column=0, sticky="ew", pady=(0, 10))

        # Queue List Frame
        self.queue_frame = ctk.CTkFrame(self.left_container, corner_radius=10)
        self.queue_frame.grid(row=1, column=0, sticky="nsew")
        self.queue_frame.grid_columnconfigure(0, weight=1)
        self.queue_frame.grid_rowconfigure(1, weight=1)

        # Queue Header Row
        self.queue_header = ctk.CTkFrame(self.queue_frame, fg_color="transparent")
        self.queue_header.grid(row=0, column=0, padx=10, pady=(8, 4), sticky="ew")
        self.queue_header.grid_columnconfigure(0, weight=1)

        self.queue_title = ctk.CTkLabel(
            self.queue_header,
            text="Batch Processing Queue (0 items)",
            font=ctk.CTkFont(size=14, weight="bold")
        )
        self.queue_title.grid(row=0, column=0, sticky="w")

        self.btn_clear_queue = ctk.CTkButton(
            self.queue_header,
            text="Clear All",
            width=70,
            height=24,
            font=ctk.CTkFont(size=11),
            fg_color=("gray75", "gray30"),
            hover_color=("#EF4444", "#DC2626"),
            command=self.clear_all_queue
        )
        self.btn_clear_queue.grid(row=0, column=1, padx=(0, 4))

        # Scrollable Queue Items Container
        self.scrollable_queue = ctk.CTkScrollableFrame(self.queue_frame, fg_color="transparent")
        self.scrollable_queue.grid(row=1, column=0, padx=6, pady=(0, 6), sticky="nsew")
        self.scrollable_queue.grid_columnconfigure(0, weight=1)

        # Right Column: Control Panel & Action Buttons
        self.right_container = ctk.CTkFrame(self, fg_color="transparent")
        self.right_container.grid(row=1, column=1, padx=(6, 12), pady=10, sticky="nsew")
        self.right_container.grid_columnconfigure(0, weight=1)

        # Granular Control Panel
        self.control_panel = ControlPanel(self.right_container)
        self.control_panel.grid(row=0, column=0, sticky="ew", pady=(0, 10))

        # Global Batch Progress & Status Section
        self.batch_status_frame = ctk.CTkFrame(self.right_container, corner_radius=10)
        self.batch_status_frame.grid(row=1, column=0, sticky="ew", pady=(0, 10))
        self.batch_status_frame.grid_columnconfigure(0, weight=1)

        self.lbl_batch_stats = ctk.CTkLabel(
            self.batch_status_frame,
            text="Total Progress: Idle",
            font=ctk.CTkFont(size=12, weight="bold")
        )
        self.lbl_batch_stats.grid(row=0, column=0, padx=12, pady=(10, 4), sticky="w")

        self.global_progress_bar = ctk.CTkProgressBar(self.batch_status_frame, height=10)
        self.global_progress_bar.grid(row=1, column=0, padx=12, pady=(0, 10), sticky="ew")
        self.global_progress_bar.set(0.0)

        # Action Buttons Row (Start / Cancel / Open Output)
        self.actions_frame = ctk.CTkFrame(self.right_container, fg_color="transparent")
        self.actions_frame.grid(row=2, column=0, sticky="ew", pady=(0, 10))
        self.actions_frame.grid_columnconfigure((0, 1), weight=1)

        self.btn_start_batch = ctk.CTkButton(
            self.actions_frame,
            text="▶ Start Batch Conversion",
            height=42,
            font=ctk.CTkFont(size=14, weight="bold"),
            fg_color=("#059669", "#10B981"),
            hover_color=("#047857", "#059669"),
            command=self.start_batch_conversion
        )
        self.btn_start_batch.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 6))

        self.btn_cancel_job = ctk.CTkButton(
            self.actions_frame,
            text="⏹ Cancel Job",
            height=34,
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color=("#DC2626", "#EF4444"),
            hover_color=("#B91C1C", "#DC2626"),
            state="disabled",
            command=self.cancel_current_job
        )
        self.btn_cancel_job.grid(row=1, column=0, padx=(0, 4), sticky="ew")

        self.btn_open_folder = ctk.CTkButton(
            self.actions_frame,
            text="📂 Open Output Folder",
            height=34,
            font=ctk.CTkFont(size=12),
            fg_color=("gray75", "gray30"),
            hover_color=("gray65", "gray40"),
            command=self.open_output_folder
        )
        self.btn_open_folder.grid(row=1, column=1, padx=(4, 0), sticky="ew")

        # Bottom Row: Collapsible Console Log
        self.console_log = ConsoleLog(self)
        self.console_log.grid(row=2, column=0, columnspan=2, padx=12, pady=(0, 10), sticky="ew")

    def toggle_theme(self):
        """Toggles visual appearance mode between Dark and Light."""
        if self.theme_switch.get() == 1:
            ctk.set_appearance_mode("Dark")
        else:
            ctk.set_appearance_mode("Light")

    def log_console(self, message: str):
        """Appends log entry to console view."""
        self.console_log.append_log(message)
        logger.info(message)

    def add_files_to_queue(self, file_paths: List[str]):
        """Adds files to queue and launches background FFprobe extraction."""
        for path in file_paths:
            # Avoid duplicate files
            if any(item["file_path"] == path for item in self.queue_items):
                continue

            item_id = str(uuid.uuid4())
            item_data = {
                "id": item_id,
                "file_path": path,
                "meta": {"duration_str": "Probing...", "resolution_str": "Probing..."},
                "card": None,
                "status": "Pending"
            }
            self.queue_items.append(item_data)

            # Spawn Card UI
            card = FileCard(
                self.scrollable_queue,
                item_id=item_id,
                file_path=path,
                meta=item_data["meta"],
                on_remove=self.remove_queue_item,
                on_move_up=self.move_queue_item_up,
                on_move_down=self.move_queue_item_down
            )
            card.pack(fill="x", pady=4)
            item_data["card"] = card

            # Run FFprobe in background thread
            threading.Thread(
                target=self._probe_worker,
                args=(item_id, path),
                daemon=True
            ).start()

        self.update_queue_header()

    def _probe_worker(self, item_id: str, file_path: str):
        """Background thread probing media file properties via FFprobe Parser."""
        if not self.ffprobe:
            return
        meta = self.ffprobe.probe_file(file_path)
        self.event_queue.put({
            "type": "PROBE_COMPLETE",
            "item_id": item_id,
            "data": meta
        })

    def remove_queue_item(self, item_id: str):
        """Removes an item card from the queue."""
        if self.is_converting and self.current_worker:
            # If current item is being converted, cancel first
            current_item = self.queue_items[self.current_job_index] if 0 <= self.current_job_index < len(self.queue_items) else None
            if current_item and current_item["id"] == item_id:
                self.cancel_current_job()

        for idx, item in enumerate(self.queue_items):
            if item["id"] == item_id:
                item["card"].destroy()
                self.queue_items.pop(idx)
                break

        self.update_queue_header()

    def move_queue_item_up(self, item_id: str):
        """Moves queue item up by 1 position."""
        idx = next((i for i, item in enumerate(self.queue_items) if item["id"] == item_id), -1)
        if idx > 0:
            self.queue_items[idx], self.queue_items[idx - 1] = self.queue_items[idx - 1], self.queue_items[idx]
            self.repack_queue_cards()

    def move_queue_item_down(self, item_id: str):
        """Moves queue item down by 1 position."""
        idx = next((i for i, item in enumerate(self.queue_items) if item["id"] == item_id), -1)
        if 0 <= idx < len(self.queue_items) - 1:
            self.queue_items[idx], self.queue_items[idx + 1] = self.queue_items[idx + 1], self.queue_items[idx]
            self.repack_queue_cards()

    def repack_queue_cards(self):
        """Re-packs card widgets according to current queue list order."""
        for item in self.queue_items:
            item["card"].pack_forget()
            item["card"].pack(fill="x", pady=4)

    def clear_all_queue(self):
        """Clears all non-converting queue items."""
        if self.is_converting:
            messagebox.showwarning("Batch Conversion Running", "Cannot clear queue while conversion is in progress. Cancel job first.")
            return

        for item in self.queue_items:
            item["card"].destroy()
        self.queue_items.clear()
        self.update_queue_header()
        self.global_progress_bar.set(0.0)
        self.lbl_batch_stats.configure(text="Total Progress: Idle")

    def update_queue_header(self):
        """Updates queue item count text."""
        count = len(self.queue_items)
        self.queue_title.configure(text=f"Batch Processing Queue ({count} items)")

    def start_batch_conversion(self):
        """Starts batch conversion loop for pending queue items."""
        if not self.queue_items:
            messagebox.showinfo("Queue Empty", "Please drop or add media files to convert.")
            return

        if not self.ffmpeg_path or not os.path.isfile(self.ffmpeg_path):
            messagebox.showerror("Missing FFmpeg", "FFmpeg binary path is invalid or missing.")
            return

        pending_items = [i for i in self.queue_items if i["status"] in ["Pending", "Error", "Cancelled"]]
        if not pending_items:
            messagebox.showinfo("No Pending Items", "All files in queue have already been converted.")
            return

        self.is_converting = True
        self.btn_start_batch.configure(state="disabled")
        self.btn_cancel_job.configure(state="normal")
        self.btn_clear_queue.configure(state="disabled")

        self.total_batch_count = len(self.queue_items)
        self.completed_batch_count = len([i for i in self.queue_items if i["status"] == "Done"])

        self.log_console("Starting batch conversion session...")
        self.process_next_queue_item()

    def process_next_queue_item(self):
        """Finds next pending item and starts TranscodeWorker thread."""
        next_idx = -1
        for idx, item in enumerate(self.queue_items):
            if item["status"] in ["Pending", "Error", "Cancelled"]:
                next_idx = idx
                break

        if next_idx == -1:
            # All items complete!
            self.is_converting = False
            self.btn_start_batch.configure(state="normal")
            self.btn_cancel_job.configure(state="disabled")
            self.btn_clear_queue.configure(state="normal")
            self.lbl_batch_stats.configure(text=f"Batch Conversion Complete! ({self.completed_batch_count}/{self.total_batch_count} Done)")
            self.global_progress_bar.set(1.0)
            self.log_console("Batch conversion finished!")
            messagebox.showinfo("Batch Complete", "All batch media files have been converted successfully!")
            return

        self.current_job_index = next_idx
        item = self.queue_items[next_idx]

        settings = self.control_panel.get_settings()
        hw_accel_choice = self.hw_selector.get_selected()

        job = TranscodeJob(
            job_id=item["id"],
            input_path=item["file_path"],
            output_dir=settings["output_dir"],
            output_format=settings["output_format"],
            hw_accel=hw_accel_choice,
            crf=settings["crf"],
            preset=settings["preset"],
            resolution=settings["resolution"],
            audio_bitrate=settings["audio_bitrate"],
            total_duration=item["meta"].get("duration", 0.0)
        )

        item["status"] = "Converting"
        item["card"].update_status("Converting")

        self.update_global_batch_progress()

        # Instantiate TranscodeWorker thread
        self.current_worker = TranscodeWorker(
            ffmpeg_path=self.ffmpeg_path,
            job=job,
            event_queue=self.event_queue
        )
        self.current_worker.start()

    def cancel_current_job(self):
        """Cancels active transcoding job."""
        if self.current_worker:
            self.log_console("Cancelling current transcode job...")
            self.current_worker.cancel()
            self.current_worker = None

        if 0 <= self.current_job_index < len(self.queue_items):
            item = self.queue_items[self.current_job_index]
            item["status"] = "Cancelled"
            item["card"].update_status("Cancelled")

        self.is_converting = False
        self.btn_start_batch.configure(state="normal")
        self.btn_cancel_job.configure(state="disabled")
        self.btn_clear_queue.configure(state="normal")
        self.lbl_batch_stats.configure(text="Conversion Job Cancelled")

    def open_output_folder(self):
        """Opens destination output directory in Windows Explorer."""
        settings = self.control_panel.get_settings()
        out_dir = settings["output_dir"]
        os.makedirs(out_dir, exist_ok=True)
        if sys.platform == "win32":
            os.startfile(out_dir)
        else:
            subprocess.run(["xdg-open", out_dir])

    def update_global_batch_progress(self, current_item_pct: float = 0.0):
        """Calculates global batch progress bar percentage."""
        if self.total_batch_count <= 0:
            return

        done_count = len([i for i in self.queue_items if i["status"] == "Done"])
        fraction = (done_count + (current_item_pct / 100.0)) / self.total_batch_count
        progress_norm = min(1.0, max(0.0, fraction))

        self.global_progress_bar.set(progress_norm)
        self.lbl_batch_stats.configure(
            text=f"Batch Progress: {done_count + 1}/{self.total_batch_count}  ({progress_norm * 100:.1f}%)"
        )

    def poll_event_queue(self):
        """
        Thread-Safe Queue Event Polling Loop operating at 20 Hz (every 50ms).
        Processes messages emitted by background threads without blocking the 60 FPS UI main loop.
        """
        try:
            while True:
                event = self.event_queue.get_nowait()
                event_type = event.get("type")
                item_id = event.get("job_id") or event.get("item_id")
                data = event.get("data", {})

                if event_type == "PROBE_COMPLETE":
                    # Update card with probed metadata
                    item = next((i for i in self.queue_items if i["id"] == item_id), None)
                    if item:
                        item["meta"] = data
                        item["card"].destroy()
                        # Re-instantiate card with probed meta
                        new_card = FileCard(
                            self.scrollable_queue,
                            item_id=item_id,
                            file_path=item["file_path"],
                            meta=data,
                            on_remove=self.remove_queue_item,
                            on_move_up=self.move_queue_item_up,
                            on_move_down=self.move_queue_item_down
                        )
                        item["card"] = new_card
                        self.repack_queue_cards()

                elif event_type == "PROGRESS":
                    item = next((i for i in self.queue_items if i["id"] == item_id), None)
                    if item and item["card"]:
                        item["card"].update_progress(data)
                        self.update_global_batch_progress(data.get("progress_percent", 0.0))

                elif event_type == "STATUS":
                    item = next((i for i in self.queue_items if i["id"] == item_id), None)
                    status_text = data.get("status", "Pending")
                    if item and item["card"]:
                        item["status"] = status_text
                        item["card"].update_status(status_text)

                elif event_type == "LOG":
                    line = data.get("line", "")
                    if line:
                        self.console_log.append_log(line)

                elif event_type == "COMPLETED":
                    item = next((i for i in self.queue_items if i["id"] == item_id), None)
                    if item:
                        item["status"] = "Done"
                        if item["card"]:
                            item["card"].update_status("Done")
                    self.completed_batch_count += 1
                    self.log_console(f"Completed converting: {item['file_path'] if item else item_id}")
                    # Move to next queue item
                    if self.is_converting:
                        self.after(200, self.process_next_queue_item)

                elif event_type == "ERROR":
                    item = next((i for i in self.queue_items if i["id"] == item_id), None)
                    if item:
                        item["status"] = "Error"
                        if item["card"]:
                            item["card"].update_status("Error")
                    self.log_console(f"[ERROR] {data.get('error')}")
                    if self.is_converting:
                        self.after(200, self.process_next_queue_item)

                self.event_queue.task_done()

        except queue.Empty:
            pass

        # Schedule next poll in 50 milliseconds
        self.after(50, self.poll_event_queue)
