"""
GUI Styles and Visual Design System Package
"""
import os
import customtkinter as ctk

THEME_JSON_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "theme.json")

def apply_custom_theme():
    if os.path.exists(THEME_JSON_PATH):
        try:
            ctk.set_default_color_theme(THEME_JSON_PATH)
        except Exception:
            ctk.set_default_color_theme("blue")
    else:
        ctk.set_default_color_theme("blue")
