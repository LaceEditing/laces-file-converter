"""Startup diagnostics usable even when the GUI dependencies are missing."""

import importlib
import os
from pathlib import Path
import sys

from converter import find_binary


def config_path() -> Path:
    if sys.platform == "linux":
        return Path(os.environ.get("XDG_CONFIG_HOME", str(Path.home() / ".config"))) / "laces-file-converter" / "config.json"
    return Path.home() / ".lace_converter_config.json"


def dependency_hint() -> str:
    try:
        release = Path("/etc/os-release").read_text().lower()
    except OSError:
        release = ""
    if "arch" in release or "garuda" in release:
        return "sudo pacman -S --needed python tk ffmpeg"
    if "fedora" in release:
        return "sudo dnf install python3 python3-tkinter ffmpeg-free"
    if "opensuse" in release:
        return "sudo zypper install python3 python3-tk ffmpeg"
    return "sudo apt install python3 python3-venv python3-tk ffmpeg"


def check_environment() -> int:
    print(f"Python: {sys.version.split()[0]} ({sys.executable})")
    failed = sys.version_info < (3, 10)
    for module, required in (("tkinter", True), ("customtkinter", True), ("PIL", True),
                             ("tkinterdnd2", False), ("pygame", False)):
        try:
            os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
            importlib.import_module(module)
            print(f"{module}: OK")
        except Exception as exc:
            print(f"{module}: {'MISSING' if required else 'optional, unavailable'} — {exc}")
            failed |= required
    for name in ("ffmpeg", "ffprobe"):
        binary = find_binary(name, str(Path(__file__).parent))
        print(f"{name}: {binary or 'MISSING'}")
        failed |= binary is None
    if sys.platform == "linux":
        print(f"System dependencies: {dependency_hint()}")
        print("Python dependencies: rerun ./install-linux.sh (do not use sudo pip).")
        print("Tk needs an X11 display, or XWayland on a Wayland desktop.")
    return int(failed)
