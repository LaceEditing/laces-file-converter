"""Build a single-file Windows executable with PyInstaller.

Run from the project's virtual environment after ``pip install -r requirements.txt pyinstaller``.
FFmpeg is bundled when ffmpeg.exe and ffprobe.exe are found next to main.py or in --ffmpeg-dir;
otherwise the executable uses FFmpeg from PATH or from beside the .exe at runtime.
"""

import argparse
from pathlib import Path
import sys

root = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
parser.add_argument("--ffmpeg-dir", type=Path, default=root, help="folder containing ffmpeg.exe and ffprobe.exe")
args = parser.parse_args()

try:
    import PyInstaller.__main__
except ImportError:
    sys.exit("PyInstaller is not installed. Run: python -m pip install pyinstaller")

options = [
    str(root / "main.py"), "--noconfirm", "--clean", "--onefile", "--windowed",
    "--name", "LacesFileConverter", "--icon", str(root / "assets/icons/icon2.ico"),
    "--add-data", f"{root / 'assets'};assets",
    # CustomTkinter themes and tkdnd's native libraries are data files PyInstaller cannot discover.
    "--collect-data", "customtkinter", "--collect-all", "tkinterdnd2",
    "--distpath", str(root / "dist"), "--workpath", str(root / "build"), "--specpath", str(root / "build"),
]
binaries = [args.ffmpeg_dir / name for name in ("ffmpeg.exe", "ffprobe.exe")]
if all(binary.is_file() for binary in binaries):
    for binary in binaries:
        options += ["--add-binary", f"{binary};."]
    print(f"Bundling FFmpeg from {args.ffmpeg_dir}")
else:
    print("FFmpeg not bundled; the executable will use FFmpeg from PATH or beside the .exe.")

PyInstaller.__main__.run(options)
print(root / "dist/LacesFileConverter.exe")
