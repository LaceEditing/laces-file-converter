"""Check DPI scaling, button fit and real scrollbar transitions on a desktop."""

import os
from pathlib import Path
import subprocess
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import customtkinter as ctk
from main import FileConverterApp


def settle(app):
    deadline = time.monotonic() + 0.3
    while time.monotonic() < deadline:
        app.update()
        time.sleep(0.01)


def check_buttons(app):
    for button in (app.browse_input_btn, app.clear_btn, app.browse_output_btn,
                   app.convert_btn, app.details_btn, app.open_output_btn):
        label = button._text_label
        assert label.winfo_reqwidth() + 12 <= button.winfo_width(), button.cget("text")
        assert label.winfo_reqheight() + 8 <= button.winfo_height(), button.cget("text")
    bottom = app.progress_frame.winfo_rooty() + app.progress_frame.winfo_height()
    assert bottom < app.winfo_rooty() + app.winfo_height(), "Progress clipped below the window"


app = FileConverterApp()
try:
    settle(app)
    assert not app.main_frame.scrollbar_visible, "Scrollbar visible at the default size"
    assert not app.main_frame._scrollbar.winfo_ismapped()
    check_buttons(app)
    for scale in (app.display_scale, 1.0, 1.5, 2.0):
        ctk.set_widget_scaling(scale)
        ctk.set_window_scaling(scale)
        app._set_scaled_min_max()
        app.geometry("920x800")
        settle(app)
        assert not app.main_frame.scrollbar_visible, f"Unnecessary scrollbar at {scale}x"
        assert not app.main_frame._scrollbar.winfo_ismapped()
        check_buttons(app)
        app.geometry("760x620")
        settle(app)
        assert app.main_frame.scrollbar_visible, f"Missing scrollbar when content overflows at {scale}x"
        assert app.main_frame._scrollbar.winfo_ismapped()
        check_buttons(app)
        canvas = app.main_frame._parent_canvas
        before = canvas.yview()[0]
        app.main_frame.event_generate("<Button-5>")
        settle(app)
        assert canvas.yview()[0] > before, "Linux wheel did not scroll overflowing content"
        app.geometry("920x800")
        settle(app)
        assert not app.main_frame.scrollbar_visible, "Scrollbar did not disappear after enlarging"
        assert not app.main_frame._scrollbar.winfo_ismapped()
        assert canvas.yview()[0] == 0, "Hidden scrollbar left content scrolled offscreen"
        app.main_frame.event_generate("<Button-5>")
        settle(app)
        assert canvas.yview()[0] == 0, "Fitting content should not scroll"
        print(f"Layout passed at {scale:.2f}x: button fit, fixed progress, overflow-only scrolling, Linux wheel.")
    if os.environ.get("LACE_GUI_SCREENSHOT"):
        ctk.set_widget_scaling(app.display_scale)
        ctk.set_window_scaling(app.display_scale)
        app._set_scaled_min_max()
        app.geometry("920x800")
        settle(app)
        assert not app.main_frame._scrollbar.winfo_ismapped()
        subprocess.run(["import", "-window", str(app.winfo_id()), os.environ["LACE_GUI_SCREENSHOT"]], check=True)
finally:
    app.destroy()
