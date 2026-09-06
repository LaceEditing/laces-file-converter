"""Small Linux-friendly adaptations for the pinned CustomTkinter release."""

import math
import ctypes
import os
import subprocess
import sys

import customtkinter as ctk


def load_logo_font(path: str) -> bool:
    """Register the bundled wordmark font before Tk builds its font list."""
    try:
        if sys.platform == "linux":
            fontconfig = ctypes.CDLL("libfontconfig.so.1")
            add_font = fontconfig.FcConfigAppFontAddFile
            add_font.argtypes = [ctypes.c_void_p, ctypes.c_char_p]
            add_font.restype = ctypes.c_int
            # NULL means this process's current configuration, without writing
            # a font into the user's personal or system font directories.
            return bool(add_font(None, os.fsencode(path)))
        return ctk.FontManager.load_font(path)
    except (OSError, AttributeError):
        return False


def configure_linux_display(root) -> float:
    """Keep Tk's pixel fonts and CustomTkinter's geometry on the same DPI.

    XWayland may report 96 DPI to Tk while Xft renders fonts at the desktop's
    configured DPI. Sync Tk first, then scale the complete interface together.
    The change is confined to this process; no desktop settings are changed.
    """
    dpi = float(root.tk.call("tk", "scaling")) * 72
    try:
        resources = subprocess.run(["xrdb", "-query"], capture_output=True, text=True,
                                   timeout=2, check=True).stdout
        for line in resources.splitlines():
            key, separator, value = line.partition(":")
            if separator and key.strip().lower() == "xft.dpi":
                configured = float(value.strip())
                if math.isfinite(configured) and 64 <= configured <= 384:
                    dpi = configured
                break
    except (OSError, ValueError, subprocess.SubprocessError):
        pass
    root.tk.call("tk", "scaling", dpi / 72)
    scale = max(0.75, min(4.0, dpi / 96))
    ctk.set_widget_scaling(scale)
    ctk.set_window_scaling(scale)
    # CTk briefly locks the window to its old size when scaling changes. Release
    # that lock before the application chooses its initial geometry.
    root._set_scaled_min_max()
    return scale


class AutoHideScrollableFrame(ctk.CTkScrollableFrame):
    """Scroll only overflowing content, including Linux wheel-button events.

    CustomTkinter 5.2.2 exposes no auto-hide setting. Keep its internal canvas
    and scrollbar access here, so the rest of the app uses a normal frame.
    """

    def __init__(self, master, **kwargs):
        self.scrollbar_visible = False
        super().__init__(master, corner_radius=0, border_width=0, **kwargs)
        self._scrollbar.grid_forget()
        self._parent_canvas.configure(yscrollcommand=self._sync_scrollbar)
        self._top = self.winfo_toplevel()
        self._wheel_bindings = {
            sequence: self._top.bind(sequence, self._linux_wheel, add="+")
            for sequence in ("<Button-4>", "<Button-5>")
        }

    def _sync_scrollbar(self, first, last):
        self._scrollbar.set(first, last)
        needed = self.winfo_reqheight() > self._parent_canvas.winfo_height() + 2
        self.scrollbar_visible = needed
        if needed and not self._scrollbar.winfo_manager():
            self._scrollbar.grid(row=1, column=1, sticky="nsew")
        elif not needed and self._scrollbar.winfo_manager():
            # grid_remove leaves CTk's saved geometry in place, so a DPI change
            # would silently show it again. Forget it and restore explicitly.
            self._scrollbar.grid_forget()
            self._parent_canvas.yview_moveto(0)

    def _mouse_wheel_all(self, event):
        if self.scrollbar_visible:
            super()._mouse_wheel_all(event)

    def _linux_wheel(self, event):
        if not self.scrollbar_visible:
            return
        widget = event.widget
        while widget is not None:
            if widget in (self, self._parent_canvas, self._scrollbar):
                self._parent_canvas.yview_scroll(-3 if event.num == 4 else 3, "units")
                return "break"
            widget = getattr(widget, "master", None)

    def destroy(self):
        for sequence, binding in self._wheel_bindings.items():
            self._top.unbind(sequence, binding)
        super().destroy()
