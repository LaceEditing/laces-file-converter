"""Install/update or uninstall the native Linux desktop app for the current user."""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import sys
import tempfile
import venv

SOURCE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SOURCE))
from linux_support import dependency_hint

APP_ID = "io.github.LaceEditing.LacesFileConverter"


def desktop_quote(value: str) -> str:
    # Desktop Exec uses its own escaping rules, not shell quoting.
    for char in ("\\", '"', "`", "$"):
        value = value.replace(char, "\\" + char)
    return '"' + value.replace("%", "%%").replace("\\", "\\\\") + '"'


def refresh_desktop(prefix: Path) -> None:
    if shutil.which("update-desktop-database"):
        subprocess.run(["update-desktop-database", str(prefix / "share/applications")], check=False)
    if shutil.which("gtk-update-icon-cache"):
        subprocess.run(["gtk-update-icon-cache", "-f", "-t", str(prefix / "share/icons/hicolor")],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prefix", type=Path, default=Path.home() / ".local",
                        help="Installation prefix (default: ~/.local)")
    parser.add_argument("--uninstall", action="store_true", help="Remove the app; keep converted files and settings")
    args = parser.parse_args()
    if sys.platform != "linux":
        parser.error("This installer is for Linux. See README.md for other platforms.")
    if os.geteuid() == 0:
        parser.error("Run as your regular user, without sudo.")
    prefix = args.prefix.expanduser().absolute()
    root = prefix / "share/laces-file-converter"
    launcher = prefix / "bin/laces-file-converter"
    desktop = prefix / f"share/applications/{APP_ID}.desktop"
    icon = prefix / f"share/icons/hicolor/256x256/apps/{APP_ID}.png"
    marker = root / ".native-install"
    if args.uninstall:
        if not marker.is_file():
            print(f"No native installation found in {root}")
            return 1
        shutil.rmtree(root)
        for path in (launcher, desktop, icon):
            path.unlink(missing_ok=True)
        refresh_desktop(prefix)
        print("Uninstalled. Your converted files and settings have been kept.")
        return 0
    if sys.version_info < (3, 10):
        parser.error("Python 3.10 or newer is required.")
    try:
        import tkinter
        assert tkinter.TkVersion >= 8.6
    except (ImportError, AssertionError) as exc:
        print(f"Tk 8.6 is required: {exc}\nInstall system dependencies first:\n  {dependency_hint()}", file=sys.stderr)
        return 1
    missing = [name for name in ("ffmpeg", "ffprobe") if not shutil.which(name)]
    if missing:
        print(f"Missing: {', '.join(missing)}\nInstall system dependencies first:\n  {dependency_hint()}", file=sys.stderr)
        return 1
    if root.exists() and not marker.is_file():
        parser.error(f"{root} already exists and is not managed by this installer.")
    if launcher.exists() and not marker.is_file():
        parser.error(f"{launcher} already exists and is not managed by this installer.")
    root.mkdir(parents=True, exist_ok=True)
    marker.touch()
    versions = root / "versions"
    versions.mkdir(exist_ok=True)
    # Build at its permanent path: moving a virtualenv breaks entry-point shebangs.
    release = Path(tempfile.mkdtemp(prefix="4.1.2-", dir=versions))
    activated = False
    try:
        print("Creating an isolated Python environment…", flush=True)
        venv.EnvBuilder(with_pip=True).create(release / ".venv")
        python = release / ".venv/bin/python"
        subprocess.run([str(python), "-m", "pip", "install", "--disable-pip-version-check",
                        "-r", str(SOURCE / "requirements.txt")], check=True)
        for filename in ("main.py", "converter.py", "linux_support.py", "ui_components.py", "requirements.txt", "LICENSE"):
            shutil.copy2(SOURCE / filename, release / filename)
        shutil.copytree(SOURCE / "assets", release / "assets")
        subprocess.run([str(python), str(release / "main.py"), "--check"], check=True)
        launcher.parent.mkdir(parents=True, exist_ok=True)
        desktop.parent.mkdir(parents=True, exist_ok=True)
        icon.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run([str(python), "-c", "from PIL import Image; import sys; Image.open(sys.argv[1]).resize((256, 256)).save(sys.argv[2])",
                        str(release / "assets/icons/icon2.ico"), str(icon)], check=True)
        current = root / "current"
        pending = root / ".current-new"
        pending.unlink(missing_ok=True)
        pending.symlink_to(release.relative_to(root), target_is_directory=True)
        pending.replace(current)
        activated = True
        launcher.write_text("#!/bin/sh\nexec " + shlex.quote(str(current / ".venv/bin/python")) + " "
                            + shlex.quote(str(current / "main.py")) + ' "$@"\n')
        launcher.chmod(0o755)
        text = (SOURCE / f"{APP_ID}.desktop").read_text()
        text = text.replace("Exec=laces-file-converter %F", f"Exec={desktop_quote(str(launcher))} %F")
        desktop.write_text(text)
        refresh_desktop(prefix)
        print(f"\nInstalled! Open Lace's Total File Converter from your application menu.\n"
              f"Launch: {shlex.quote(str(launcher))}\n"
              f"Diagnostics: {shlex.quote(str(launcher))} --check\n"
              "Rerun this installer after updating the source to upgrade.\n"
              f"Uninstall: ./install-linux.sh --prefix {shlex.quote(str(prefix))} --uninstall")
        if str(launcher.parent) not in os.environ.get("PATH", "").split(os.pathsep):
            print(f"For terminal use, add {launcher.parent} to PATH. The menu launcher already works.")
        return 0
    except (OSError, subprocess.CalledProcessError) as exc:
        print(f"Installation failed: {exc}", file=sys.stderr)
        return 1
    finally:
        if not activated:
            shutil.rmtree(release, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
