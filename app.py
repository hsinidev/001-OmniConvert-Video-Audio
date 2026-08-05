"""
OmniConvert Video & Audio Application Entry Point
"""

import sys
import os

# Add root folder to sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from gui.main_window import MainWindow


def main():
    """Application main function."""
    app = MainWindow()
    app.mainloop()


if __name__ == "__main__":
    main()
