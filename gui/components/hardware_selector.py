import customtkinter as ctk
from typing import List, Callable


class HardwareSelector(ctk.CTkFrame):
    """
    Hardware Acceleration Dropdown Selector Widget.
    Automatically populates choices based on HWAccelProber scan results.
    """

    def __init__(self, master, available_hardware: List[str], on_change: Callable[[str], None] = None, **kwargs):
        super().__init__(master, corner_radius=10, **kwargs)
        self.available_hardware = available_hardware or ["CPU Software"]
        self.on_change = on_change

        self.grid_columnconfigure(1, weight=1)

        self.lbl_title = ctk.CTkLabel(
            self,
            text="⚡ Acceleration:",
            font=ctk.CTkFont(size=12, weight="bold")
        )
        self.lbl_title.grid(row=0, column=0, padx=(12, 6), pady=10, sticky="w")

        self.menu_hw = ctk.CTkOptionMenu(
            self,
            values=self.available_hardware,
            command=self._handle_change
        )
        self.menu_hw.grid(row=0, column=1, padx=(0, 12), pady=10, sticky="ew")

        # Select first hardware option by default
        default_sel = self.available_hardware[0]
        if "NVIDIA NVENC" in self.available_hardware:
            default_sel = "NVIDIA NVENC"
        self.menu_hw.set(default_sel)

    def _handle_change(self, choice: str):
        if self.on_change:
            self.on_change(choice)

    def get_selected(self) -> str:
        return self.menu_hw.get()

    def update_options(self, hardware_list: List[str]):
        self.available_hardware = hardware_list or ["CPU Software"]
        self.menu_hw.configure(values=self.available_hardware)
        if self.menu_hw.get() not in self.available_hardware:
            self.menu_hw.set(self.available_hardware[0])
