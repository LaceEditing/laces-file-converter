"""Build a small native Linux source installer archive, excluding build caches."""

from pathlib import Path
import tarfile

root = Path(__file__).resolve().parents[1]
output = root / "dist/laces-file-converter-4.1.2-linux.tar.gz"
output.parent.mkdir(exist_ok=True)
files = ["main.py", "converter.py", "linux_support.py", "ui_components.py", "requirements.txt", "install-linux.sh",
         "laces-file-converter.sh", "README.md", "LICENSE",
         "io.github.LaceEditing.LacesFileConverter.desktop", "scripts/install_linux.py", "scripts/build_linux.py",
         "tests/test_converter.py", "tests/gui_smoke.py", "tests/gui_layout.py", "tests/install_smoke.py", "assets"]
with tarfile.open(output, "w:gz") as archive:
    for filename in files:
        archive.add(root / filename, arcname=f"laces-file-converter/{filename}")
print(output)
