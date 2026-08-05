import sys
import os
import json
import subprocess
from typing import Dict, Any, Optional


class FFprobeParser:
    """
    FFprobe JSON Metadata Extraction Engine.
    Runs non-blocking ffprobe subprocesses to extract structured stream and format metadata.
    """

    def __init__(self, ffprobe_path: str):
        self.ffprobe_path = ffprobe_path

    def probe_file(self, file_path: str) -> Dict[str, Any]:
        """
        Executes ffprobe -v quiet -print_format json -show_format -show_streams <input_path>
        and returns parsed dictionary of media properties.
        """
        default_meta = {
            "valid": False,
            "filename": os.path.basename(file_path),
            "file_size_bytes": 0,
            "file_size_str": "0 B",
            "duration": 0.0,
            "duration_str": "00:00:00",
            "width": 0,
            "height": 0,
            "resolution_str": "N/A",
            "fps": 0.0,
            "fps_str": "N/A",
            "video_codec": "None",
            "audio_codec": "None",
            "audio_sample_rate": "N/A",
            "channels": 0,
            "has_video": False,
            "has_audio": False,
            "error": None
        }

        if not os.path.exists(file_path):
            default_meta["error"] = "File does not exist"
            return default_meta

        try:
            file_size = os.path.getsize(file_path)
            default_meta["file_size_bytes"] = file_size
            default_meta["file_size_str"] = self.format_file_size(file_size)
        except Exception:
            pass

        if not self.ffprobe_path or not os.path.isfile(self.ffprobe_path):
            default_meta["error"] = "ffprobe.exe binary path not available"
            return default_meta

        cmd = [
            self.ffprobe_path,
            "-v", "quiet",
            "-print_format", "json",
            "-show_format",
            "-show_streams",
            file_path
        ]

        creationflags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0

        try:
            res = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                creationflags=creationflags,
                text=True,
                timeout=10,
                encoding="utf-8",
                errors="replace"
            )

            if res.returncode != 0:
                default_meta["error"] = f"FFprobe failed with returncode {res.returncode}"
                return default_meta

            data = json.loads(res.stdout)
            format_data = data.get("format", {})
            streams_data = data.get("streams", [])

            # Duration
            duration_sec = float(format_data.get("duration", 0.0))
            default_meta["duration"] = duration_sec
            default_meta["duration_str"] = self.format_duration(duration_sec)

            for stream in streams_data:
                codec_type = stream.get("codec_type")
                if codec_type == "video" and not default_meta["has_video"]:
                    default_meta["has_video"] = True
                    default_meta["video_codec"] = stream.get("codec_name", "unknown")
                    default_meta["width"] = int(stream.get("width", 0))
                    default_meta["height"] = int(stream.get("height", 0))
                    if default_meta["width"] > 0 and default_meta["height"] > 0:
                        default_meta["resolution_str"] = f"{default_meta['width']}x{default_meta['height']}"

                    # FPS parsing
                    r_frame_rate = stream.get("r_frame_rate", "0/0")
                    if "/" in r_frame_rate:
                        num, den = r_frame_rate.split("/")
                        if float(den) > 0:
                            fps_val = round(float(num) / float(den), 2)
                            default_meta["fps"] = fps_val
                            default_meta["fps_str"] = f"{fps_val} FPS"
                    elif float(r_frame_rate or 0) > 0:
                        fps_val = round(float(r_frame_rate), 2)
                        default_meta["fps"] = fps_val
                        default_meta["fps_str"] = f"{fps_val} FPS"

                    # Fallback duration if format.duration was missing
                    if default_meta["duration"] == 0.0 and "duration" in stream:
                        try:
                            d_sec = float(stream["duration"])
                            default_meta["duration"] = d_sec
                            default_meta["duration_str"] = self.format_duration(d_sec)
                        except ValueError:
                            pass

                elif codec_type == "audio" and not default_meta["has_audio"]:
                    default_meta["has_audio"] = True
                    default_meta["audio_codec"] = stream.get("codec_name", "unknown")
                    default_meta["audio_sample_rate"] = f"{stream.get('sample_rate', 'N/A')} Hz"
                    default_meta["channels"] = int(stream.get("channels", 0))

            default_meta["valid"] = True

        except subprocess.TimeoutExpired:
            default_meta["error"] = "FFprobe timed out"
        except json.JSONDecodeError:
            default_meta["error"] = "Failed to parse JSON output from ffprobe"
        except Exception as e:
            default_meta["error"] = str(e)

        return default_meta

    @staticmethod
    def format_duration(seconds: float) -> str:
        """Formats fractional seconds into HH:MM:SS."""
        total_sec = int(seconds)
        hours = total_sec // 3600
        minutes = (total_sec % 3600) // 60
        secs = total_sec % 60
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"

    @staticmethod
    def format_file_size(size_bytes: int) -> str:
        """Formats byte count into human readable string (KB, MB, GB)."""
        if size_bytes <= 0:
            return "0 B"
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.1f} PB"
