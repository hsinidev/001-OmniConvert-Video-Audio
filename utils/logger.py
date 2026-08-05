import sys
import datetime
import threading
from typing import Optional, Callable


class ThreadSafeLogger:
    """
    Thread-Safe Application & Telemetry Logger.
    """

    def __init__(self, callback: Optional[Callable[[str], None]] = None):
        self.lock = threading.Lock()
        self.callback = callback

    def set_callback(self, callback: Callable[[str], None]):
        with self.lock:
            self.callback = callback

    def log(self, message: str, level: str = "INFO"):
        now_str = datetime.datetime.now().strftime("%H:%M:%S.%f")[:-3]
        formatted = f"[{now_str}] [{level.upper()}] {message}"
        with self.lock:
            print(formatted)
            if self.callback:
                try:
                    self.callback(formatted)
                except Exception:
                    pass

    def info(self, message: str):
        self.log(message, "INFO")

    def warning(self, message: str):
        self.log(message, "WARNING")

    def error(self, message: str):
        self.log(message, "ERROR")


# Default global logger instance
logger = ThreadSafeLogger()
