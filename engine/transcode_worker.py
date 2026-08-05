import sys
import os
import re
import queue
import threading
import subprocess
from typing import Dict, Any, Optional

from .telemetry import TelemetryParser


class TranscodeJob:
    """
    Data holder for transcode job parameters.
    """
    def __init__(
        self,
        job_id: str,
        input_path: str,
        output_dir: str,
        output_format: str = "mp4",
        hw_accel: str = "CPU Software",
        crf: int = 22,
        preset: str = "medium",
        resolution: str = "Original",
        audio_bitrate: str = "192k",
        total_duration: float = 0.0
    ):
        self.job_id = job_id
        self.input_path = input_path
        self.output_dir = output_dir
        self.output_format = output_format.lower().strip(".")
        self.hw_accel = hw_accel
        self.crf = crf
        self.preset = preset
        self.resolution = resolution
        self.audio_bitrate = audio_bitrate
        self.total_duration = total_duration

        # Compute output filename
        base_name = os.path.splitext(os.path.basename(input_path))[0]
        self.output_filename = f"{base_name}_converted.{self.output_format}"
        self.output_path = os.path.join(output_dir, self.output_filename)
        self.temp_output_path = os.path.join(output_dir, f".tmp_{self.output_filename}")


class TranscodeWorker(threading.Thread):
    """
    Worker Thread managing FFmpeg transcode execution and telemetry streaming.
    """

    def __init__(self, ffmpeg_path: str, job: TranscodeJob, event_queue: queue.Queue):
        super().__init__(daemon=True)
        self.ffmpeg_path = ffmpeg_path
        self.job = job
        self.event_queue = event_queue
        self.process: Optional[subprocess.Popen] = None
        self.cancelled = False
        self.telemetry = TelemetryParser(total_duration_seconds=job.total_duration)

    def run(self):
        """Main thread entry point."""
        self.post_event("STATUS", {"status": "Converting", "message": "Starting conversion..."})
        self.post_event("LOG", {"line": f"[ENGINE] Target Output: {self.job.output_path}"})

        # Ensure output directory exists
        try:
            os.makedirs(self.job.output_dir, exist_ok=True)
        except Exception as e:
            self.post_event("ERROR", {"error": f"Failed to create output directory: {str(e)}"})
            self.post_event("STATUS", {"status": "Error", "message": "Output Directory Error"})
            return

        cmd = self.build_ffmpeg_cmd()
        cmd_str = " ".join([f'"{arg}"' if " " in arg else arg for arg in cmd])
        self.post_event("LOG", {"line": f"[ENGINE] Command: {cmd_str}"})

        creationflags = 0
        if sys.platform == "win32":
            creationflags = subprocess.CREATE_NO_WINDOW | subprocess.CREATE_NEW_PROCESS_GROUP

        try:
            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                creationflags=creationflags,
                text=True,
                encoding="utf-8",
                errors="replace",
                bufsize=1
            )

            # Read stderr line by line in real-time
            if self.process.stderr:
                for raw_line in iter(self.process.stderr.readline, ''):
                    if self.cancelled:
                        break

                    line = raw_line.strip()
                    if not line:
                        continue

                    # Log output
                    self.post_event("LOG", {"line": f"[FFmpeg] {line}"})

                    # Parse telemetry metrics
                    metrics = self.telemetry.parse_line(line)
                    if metrics:
                        self.post_event("PROGRESS", metrics)

            self.process.wait()

            if self.cancelled:
                self.post_event("STATUS", {"status": "Cancelled", "message": "Job cancelled by user"})
                self.cleanup_temp_files()
                return

            if self.process.returncode == 0:
                # Rename temp output file to target output path
                if os.path.exists(self.job.temp_output_path):
                    if os.path.exists(self.job.output_path):
                        os.remove(self.job.output_path)
                    os.rename(self.job.temp_output_path, self.job.output_path)

                self.post_event("PROGRESS", {
                    "progress_percent": 100.0,
                    "eta_str": "00:00",
                    "speed": 1.0,
                    "fps": 0.0
                })
                self.post_event("STATUS", {"status": "Done", "message": "Conversion completed successfully"})
                self.post_event("COMPLETED", {"output_path": self.job.output_path})
            else:
                err_msg = f"FFmpeg exited with non-zero code ({self.process.returncode})"
                self.post_event("ERROR", {"error": err_msg})
                self.post_event("STATUS", {"status": "Error", "message": err_msg})
                self.cleanup_temp_files()

        except Exception as e:
            if not self.cancelled:
                self.post_event("ERROR", {"error": str(e)})
                self.post_event("STATUS", {"status": "Error", "message": str(e)})
                self.cleanup_temp_files()

    def build_ffmpeg_cmd(self) -> list:
        """Constructs FFmpeg CLI argument array based on container and settings."""
        cmd = [
            self.ffmpeg_path,
            "-y",  # Overwrite output without prompting
            "-hide_banner",
            "-i", self.job.input_path
        ]

        fmt = self.job.output_format.lower()
        is_audio_only = fmt in ["mp3", "flac", "wav"]

        # Container format mapping for -f
        fmt_map = {
            "mp4": "mp4",
            "mkv": "matroska",
            "avi": "avi",
            "mp3": "mp3",
            "flac": "flac",
            "wav": "wav"
        }
        target_fmt = fmt_map.get(fmt, fmt)
        cmd.extend(["-f", target_fmt])

        if is_audio_only:
            cmd.append("-vn")  # Disable video
            if fmt == "mp3":
                cmd.extend(["-c:a", "libmp3lame", "-b:a", self.job.audio_bitrate])
            elif fmt == "flac":
                cmd.extend(["-c:a", "flac"])
            elif fmt == "wav":
                cmd.extend(["-c:a", "pcm_s16le"])
        else:
            # Video Container (MP4, MKV, AVI)
            # Select Video Codec based on Hardware Acceleration
            hw = self.job.hw_accel
            if hw == "NVIDIA NVENC":
                cmd.extend(["-c:v", "h264_nvenc"])
            elif hw == "AMD AMF":
                cmd.extend(["-c:v", "h264_amf"])
            elif hw == "Intel QuickSync (QSV)":
                cmd.extend(["-c:v", "h264_qsv"])
            else:
                # CPU Software Encoder
                cmd.extend(["-c:v", "libx264", "-crf", str(self.job.crf), "-preset", self.job.preset])

            # Resolution scaling filter (-vf scale)
            res = self.job.resolution
            if res == "3840x2160 (4K)":
                cmd.extend(["-vf", "scale=3840:-2"])
            elif res == "1920x1080 (1080p)":
                cmd.extend(["-vf", "scale=1920:-2"])
            elif res == "1280x720 (720p)":
                cmd.extend(["-vf", "scale=1280:-2"])
            elif res == "854x480 (480p)":
                cmd.extend(["-vf", "scale=854:-2"])

            # Audio Codec & Bitrate
            cmd.extend(["-c:a", "aac", "-b:a", self.job.audio_bitrate])

        # Write to temporary output path
        cmd.append(self.job.temp_output_path)
        return cmd

    def cancel(self):
        """
        Clean Job Cancellation using targeted taskkill process group termination.
        Ensures zero orphan ffmpeg.exe instances remain.
        """
        self.cancelled = True
        if self.process and self.process.poll() is None:
            pid = self.process.pid
            if sys.platform == "win32":
                try:
                    subprocess.run(
                        ["taskkill", "/F", "/PID", str(pid), "/T"],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                        creationflags=subprocess.CREATE_NO_WINDOW
                    )
                except Exception:
                    pass
            try:
                self.process.kill()
            except Exception:
                pass

        self.cleanup_temp_files()

    def cleanup_temp_files(self):
        """Removes incomplete temporary output file."""
        if os.path.exists(self.job.temp_output_path):
            try:
                os.remove(self.job.temp_output_path)
            except Exception:
                pass

    def post_event(self, event_type: str, data: Dict[str, Any]):
        """Posts structured payload dictionary to thread-safe Queue."""
        payload = {
            "type": event_type,
            "job_id": self.job.job_id,
            "data": data
        }
        self.event_queue.put(payload)
