import sys
import subprocess
from typing import Dict, List, Optional


class HWAccelProber:
    """
    Hardware Acceleration Detection & Encoder Probing Engine.
    Queries FFmpeg encoder capabilities at runtime to detect NVIDIA NVENC, AMD AMF, Intel QSV,
    and fallback CPU software encoders.
    """

    ACCEL_PROBES = {
        "NVIDIA NVENC": {
            "h264": "h264_nvenc",
            "hevc": "hevc_nvenc",
            "probe_keyword": "nvenc"
        },
        "AMD AMF": {
            "h264": "h264_amf",
            "hevc": "hevc_amf",
            "probe_keyword": "amf"
        },
        "Intel QuickSync (QSV)": {
            "h264": "h264_qsv",
            "hevc": "hevc_qsv",
            "probe_keyword": "qsv"
        }
    }

    SOFTWARE_CODECS = {
        "h264": "libx264",
        "hevc": "libx265",
        "vp9": "libvpx-vp9",
        "mp3": "libmp3lame",
        "aac": "aac",
        "flac": "flac"
    }

    def __init__(self, ffmpeg_path: str):
        self.ffmpeg_path = ffmpeg_path
        self.available_encoders: Dict[str, bool] = {}
        self.supported_hardware: List[str] = ["CPU Software"]
        self.probe()

    def probe(self) -> List[str]:
        """
        Executes `ffmpeg -hide_banner -encoders` and parses output for encoder keywords.
        Returns list of available hardware acceleration names.
        """
        self.supported_hardware = ["CPU Software"]
        if not self.ffmpeg_path:
            return self.supported_hardware

        creationflags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
        try:
            res = subprocess.run(
                [self.ffmpeg_path, "-hide_banner", "-encoders"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                creationflags=creationflags,
                text=True,
                timeout=5
            )
            output = (res.stdout or "") + (res.stderr or "")
            output_lower = output.lower()

            for hw_name, config in self.ACCEL_PROBES.items():
                keyword = config["probe_keyword"]
                if keyword in output_lower:
                    self.supported_hardware.append(hw_name)
                    self.available_encoders[hw_name] = True
                else:
                    self.available_encoders[hw_name] = False

        except Exception:
            pass

        return self.supported_hardware

    def get_video_encoder(self, hw_accel_choice: str, target_codec: str = "h264") -> str:
        """
        Returns the appropriate video encoder string based on hardware choice and target codec.
        Falls back gracefully to CPU software encoders if specified hardware is unavailable.
        """
        target_codec = target_codec.lower()
        if hw_accel_choice in self.ACCEL_PROBES and hw_accel_choice in self.supported_hardware:
            hw_config = self.ACCEL_PROBES[hw_accel_choice]
            if target_codec in hw_config:
                return hw_config[target_codec]

        # CPU Fallback
        return self.SOFTWARE_CODECS.get(target_codec, "libx264")
