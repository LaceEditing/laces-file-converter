"""Real install/upgrade/uninstall in /tmp. Requires system Tk and PyPI access."""

import os
from pathlib import Path
import subprocess
import sys
import tarfile
import tempfile

REPO = Path(__file__).resolve().parents[1]


def main():
    subprocess.run([sys.executable, str(REPO / "scripts/build_linux.py")], check=True)
    with tempfile.TemporaryDirectory(prefix="lace-install-") as folder:
        temp = Path(folder)
        with tarfile.open(REPO / "dist/laces-file-converter-4.1.2-linux.tar.gz") as archive:
            archive.extractall(temp, filter="data")
        source = temp / "laces-file-converter"
        prefix = temp / "prefix with spaces % ü"
        command = [str(source / "install-linux.sh"), "--prefix", str(prefix)]
        subprocess.run(command, check=True)
        launcher = prefix / "bin/laces-file-converter"
        desktop = prefix / "share/applications/io.github.LaceEditing.LacesFileConverter.desktop"
        subprocess.run(["desktop-file-validate", str(desktop)], check=True)
        subprocess.run([str(launcher), "--check"], check=True, cwd="/")
        current = prefix / "share/laces-file-converter/current"
        previous = current.resolve()
        subprocess.run(command, check=True)
        assert current.resolve() != previous
        assert previous.exists()
        version = subprocess.check_output([str(launcher), "--version"], text=True, cwd="/")
        assert "4.1.2" in version
        # Failed dependency installation must preserve the working release.
        active = current.resolve()
        environment = dict(os.environ, PIP_NO_INDEX="1", PIP_FIND_LINKS=str(temp / "empty-wheels"))
        (temp / "empty-wheels").mkdir()
        failed = subprocess.run(command, env=environment)
        assert failed.returncode != 0
        assert current.resolve() == active
        # A moved checkout does not break the installed launcher.
        moved = temp / "moved installer"
        source.rename(moved)
        subprocess.run([str(launcher), "--check"], check=True, cwd="/")
        output = prefix / "keep-converted.mp4"
        output.write_bytes(b"user media")
        subprocess.run([str(moved / "install-linux.sh"), "--prefix", str(prefix), "--uninstall"], check=True)
        assert not launcher.exists()
        assert not desktop.exists()
        assert not current.parent.exists()
        assert output.read_bytes() == b"user media"
        print("Installer smoke passed: archive, install, upgrade, failed-upgrade recovery, moved source, uninstall.")


if __name__ == "__main__":
    main()
