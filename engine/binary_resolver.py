import sys
import os
import shutil
import subprocess
from typing import Optional, Tuple, Dict
from tkinter import filedialog, messagebox


class BinaryResolver:
    """
    Dynamic External Binary Resolution Engine.
    Implements a 5-stage discovery hierarchy to locate ffmpeg.exe and ffprobe.exe:
    1. PyInstaller frozen runtime root (sys._MEIPASS).
    2. Working script/executable root directory.
    3. Application relative directory (./bin/).
    4. System environment PATH (shutil.which).
    5. Fallback user selection dialog or WinGet package paths.
    """

    def __init__(self, custom_bin_dir: Optional[str] = None):
        self.custom_bin_dir = custom_bin_dir
        self.ffmpeg_path: Optional[str] = None
        self.ffprobe_path: Optional[str] = None
        self.resolve_all()

    @staticmethod
    def get_base_dir() -> str:
        """Returns frozen bundle path if PyInstaller frozen, else current file directory parent."""
        if getattr(sys, 'frozen', False):
            return getattr(sys, '_MEIPASS', os.path.dirname(sys.executable))
        return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    def resolve_binary(self, binary_name: str) -> Optional[str]:
        """
        Resolves a target binary executable using the 5-stage hierarchy.
        """
        exe_name = f"{binary_name}.exe" if sys.platform == "win32" and not binary_name.endswith(".exe") else binary_name
        base_dir = self.get_base_dir()

        # Stage 1: PyInstaller _MEIPASS root
        if getattr(sys, 'frozen', False):
            meipass_path = os.path.join(base_dir, exe_name)
            if os.path.isfile(meipass_path) and os.access(meipass_path, os.X_OK):
                return meipass_path
            meipass_bin_path = os.path.join(base_dir, "bin", exe_name)
            if os.path.isfile(meipass_bin_path) and os.access(meipass_bin_path, os.X_OK):
                return meipass_bin_path

        # Stage 2: Custom / Working Script Root Directory
        script_root = os.path.abspath(os.getcwd())
        root_exe = os.path.join(script_root, exe_name)
        if os.path.isfile(root_exe) and os.access(root_exe, os.X_OK):
            return root_exe

        # Stage 3: Application ./bin/ Directory
        bin_dir = self.custom_bin_dir or os.path.join(base_dir, "bin")
        bin_exe = os.path.join(bin_dir, exe_name)
        if os.path.isfile(bin_exe) and os.access(bin_exe, os.X_OK):
            return bin_exe

        # Stage 4: System PATH via shutil.which
        which_path = shutil.which(binary_name) or shutil.which(exe_name)
        if which_path and os.path.isfile(which_path):
            return which_path

        # Stage 4b: Windows WinGet Known Directory Fallback
        if sys.platform == "win32":
            winget_root = os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\WinGet\Packages")
            if os.path.exists(winget_root):
                for root, _, files in os.walk(winget_root):
                    if exe_name.lower() in [f.lower() for f in files]:
                        candidate = os.path.join(root, exe_name)
                        if os.path.isfile(candidate):
                            return candidate

        return None

    def resolve_all(self) -> Tuple[Optional[str], Optional[str]]:
        """Resolves both ffmpeg and ffprobe."""
        self.ffmpeg_path = self.resolve_binary("ffmpeg")
        self.ffprobe_path = self.resolve_binary("ffprobe")
        return self.ffmpeg_path, self.ffprobe_path

    def prompt_user_for_binary(self, binary_name: str) -> Optional[str]:
        """Interactive GUI fallback asking the user to manually locate missing binary."""
        title = f"Select Location of {binary_name}.exe"
        file_path = filedialog.askopenfilename(
            title=title,
            filetypes=[("Executable Files", "*.exe"), ("All Files", "*.*")]
        )
        if file_path and os.path.isfile(file_path):
            if binary_name.lower() in os.path.basename(file_path).lower():
                return file_path
            else:
                messagebox.showwarning(
                    "Binary Mismatch",
                    f"Selected file does not appear to be {binary_name}.exe"
                )
        return None

    def ensure_binaries(self) -> bool:
        """
        Ensures both binaries are resolved, prompting user interactively if missing.
        Returns True if both binaries are available.
        """
        if not self.ffmpeg_path:
            self.ffmpeg_path = self.prompt_user_for_binary("ffmpeg")
        if not self.ffprobe_path:
            self.ffprobe_path = self.prompt_user_for_binary("ffprobe")

        return bool(self.ffmpeg_path and self.ffprobe_path)

    def validate_binaries(self) -> Dict[str, bool]:
        """
        Validates binary functionality by running `--version`.
        """
        results = {"ffmpeg": False, "ffprobe": False}
        creationflags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0

        if self.ffmpeg_path:
            try:
                res = subprocess.run(
                    [self.ffmpeg_path, "-version"],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    creationflags=creationflags,
                    text=True,
                    timeout=5
                )
                results["ffmpeg"] = res.returncode == 0
            except Exception:
                results["ffmpeg"] = False

        if self.ffprobe_path:
            try:
                res = subprocess.run(
                    [self.ffprobe_path, "-version"],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    creationflags=creationflags,
                    text=True,
                    timeout=5
                )
                results["ffprobe"] = res.returncode == 0
            except Exception:
                results["ffprobe"] = False

        return results
