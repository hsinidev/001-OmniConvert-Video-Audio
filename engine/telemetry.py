import re
from typing import Dict, Any, Optional


class TelemetryParser:
    """
    Real-Time Telemetry Parsing Engine for FFmpeg stderr logs.
    Utilizes compiled regular expressions to extract timestamp, speed, fps, and progress metrics line-by-line.
    """

    RE_DURATION = re.compile(r"Duration:\s*(\d{2}):(\d{2}):(\d{2})\.(\d{2})")
    RE_TIME = re.compile(r"time=(\d{2}):(\d{2}):(\d{2})\.(\d{2})")
    RE_SPEED = re.compile(r"speed=\s*([0-9\.]+)x")
    RE_FPS = re.compile(r"fps=\s*([0-9\.]+)")
    RE_FRAME = re.compile(r"frame=\s*(\d+)")

    def __init__(self, total_duration_seconds: float = 0.0):
        self.total_duration_seconds = total_duration_seconds
        self.current_seconds = 0.0
        self.progress_percent = 0.0
        self.fps = 0.0
        self.speed = 1.0
        self.frame = 0
        self.eta_seconds = 0.0

    def parse_line(self, line: str) -> Optional[Dict[str, Any]]:
        """
        Parses a single stderr line from FFmpeg.
        Returns a dict of metrics if telemetry metrics were updated, else None.
        """
        updated = False

        # Check total duration if not already set
        if self.total_duration_seconds <= 0.0:
            match_dur = self.RE_DURATION.search(line)
            if match_dur:
                h, m, s, ms = map(int, match_dur.groups())
                self.total_duration_seconds = h * 3600 + m * 60 + s + ms / 100.0
                updated = True

        # Parse current encoding timestamp: time=HH:MM:SS.ms
        match_time = self.RE_TIME.search(line)
        if match_time:
            h, m, s, ms = map(int, match_time.groups())
            self.current_seconds = h * 3600 + m * 60 + s + ms / 100.0

            if self.total_duration_seconds > 0.0:
                raw_pct = (self.current_seconds / self.total_duration_seconds) * 100.0
                self.progress_percent = min(100.0, max(0.0, raw_pct))

            updated = True

        # Parse FPS
        match_fps = self.RE_FPS.search(line)
        if match_fps:
            try:
                self.fps = float(match_fps.group(1))
                updated = True
            except ValueError:
                pass

        # Parse speed multiplier (e.g. speed= 2.5x)
        match_speed = self.RE_SPEED.search(line)
        if match_speed:
            try:
                spd = float(match_speed.group(1))
                if spd > 0:
                    self.speed = spd
                updated = True
            except ValueError:
                pass

        # Parse frame count
        match_frame = self.RE_FRAME.search(line)
        if match_frame:
            try:
                self.frame = int(match_frame.group(1))
                updated = True
            except ValueError:
                pass

        # Calculate ETA
        if self.total_duration_seconds > 0 and self.current_seconds < self.total_duration_seconds:
            remaining_seconds = self.total_duration_seconds - self.current_seconds
            self.eta_seconds = remaining_seconds / self.speed if self.speed > 0 else remaining_seconds
        else:
            self.eta_seconds = 0.0

        if updated:
            return {
                "current_seconds": self.current_seconds,
                "total_duration_seconds": self.total_duration_seconds,
                "progress_percent": self.progress_percent,
                "fps": self.fps,
                "speed": self.speed,
                "frame": self.frame,
                "eta_seconds": self.eta_seconds,
                "eta_str": self.format_eta(self.eta_seconds),
                "timestamp_str": self.format_timestamp(self.current_seconds)
            }

        return None

    @staticmethod
    def format_timestamp(seconds: float) -> str:
        total_sec = int(seconds)
        hours = total_sec // 3600
        minutes = (total_sec % 3600) // 60
        secs = total_sec % 60
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"

    @staticmethod
    def format_eta(seconds: float) -> str:
        total_sec = max(0, int(seconds))
        minutes = total_sec // 60
        secs = total_sec % 60
        if minutes > 60:
            hours = minutes // 60
            minutes %= 60
            return f"{hours}h {minutes}m"
        return f"{minutes:02d}:{secs:02d}"
