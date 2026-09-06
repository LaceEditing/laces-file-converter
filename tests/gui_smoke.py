"""Exercise the actual Tk event loop and worker on an X11/XWayland display."""

import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

from converter import Progress
from main import FileConverterApp


def main():
    with tempfile.TemporaryDirectory(prefix="lace-gui-") as folder:
        source = Path(folder) / "demo with spaces ü.mp4"
        broken = Path(folder) / "broken.mp4"
        broken.write_bytes(b"not media")
        subprocess.run(["ffmpeg", "-v", "error", "-f", "lavfi", "-i", "testsrc2=size=1280x720:rate=30",
                        "-t", "12", "-c:v", "libx264", "-preset", "ultrafast", "-y", str(source)], check=True)
        with patch.dict(os.environ, {"XDG_CONFIG_HOME": folder}):
            app = FileConverterApp()
            app.geometry("980x980")
            app.update()
            callback_errors = []
            app.report_callback_exception = lambda *exc: callback_errors.append(exc)
            try:
                app.output_folder.set(folder)
                app.add_files([str(source), str(broken)])
                app.start_conversion()
                assert app.browse_input_btn.cget("state") == "disabled"
                # Drag-and-drop cannot replace an active batch.
                app.add_files([str(broken)])
                assert len(app.input_files) == 2
                started = time.monotonic()
                saw_progress = False
                captured = False
                while app.is_converting:
                    app.update()
                    if app.progress_bar.get() > 0:
                        saw_progress = True
                        if not captured and os.environ.get("LACE_GUI_SCREENSHOT"):
                            subprocess.run(["import", "-window", str(app.winfo_id()), os.environ["LACE_GUI_SCREENSHOT"]], check=True)
                            captured = True
                    assert time.monotonic() - started < 30, "GUI job did not finish"
                    time.sleep(0.01)
                assert saw_progress
                assert "1/2 converted, 1 failed" in app.status_label.cget("text")
                assert len(app.details) == 2
                assert app.browse_input_btn.cget("state") == "normal"
                assert list(Path(folder).glob("*converted.mp4"))
                assert not list(Path(folder).glob(".lace-converting-*"))

                app._display_progress(0, 1, source.name, Progress("Converting", 2))
                assert app.indeterminate
                assert "Duration unavailable" in app.file_progress_label.cget("text")
                app._display_progress(0, 1, source.name, Progress("Converting", 2, 12, 6, 2))
                assert not app.indeterminate
                assert "50%" in app.file_progress_label.cget("text")
                assert "0:03" in app.metrics_label.cget("text")
                app.add_files([str(source)])
                app.start_conversion()
                app.after(150, app.on_close)
                app.mainloop()
                assert not list(Path(folder).glob(".lace-converting-*"))
                assert not callback_errors, callback_errors
                print("GUI smoke passed: progress, mixed success/failure, frozen selection, unknown duration, close/cancel cleanup.")
            finally:
                try:
                    app.destroy()
                except Exception:
                    pass

    # CustomTkinter keeps interpreter-level timers. Use a fresh process for a
    # second root, just as a real second launch would, to avoid stale Tk timers.
    subprocess.run([sys.executable, __file__, "--fallback"], check=True)


def check_fallback():
    # A missing native tkdnd extension must not prevent launching the app.
    with patch("main.tkdnd.TkinterDnD._require", side_effect=RuntimeError("test unavailable extension")):
        app = FileConverterApp()
        app.update()
        assert not app.dnd_available
        assert app.browse_input_btn.cget("state") == "normal"
        app.destroy()
    print("GUI fallback passed: Browse works without drag-and-drop.")


if __name__ == "__main__":
    check_fallback() if "--fallback" in sys.argv else main()
