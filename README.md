# Lace's Total File Converter

<p align="center">
  <strong>A free, open-source batch file converter for video, audio, and images.</strong><br>
  Built with Python, CustomTkinter, and FFmpeg.
</p>

<p align="center">
  <a href="#features">Features</a> •
  <a href="#screenshots">Screenshots</a> •
  <a href="#installation">Installation</a> •
  <a href="#usage">Usage</a> •
  <a href="#supported-formats">Supported Formats</a> •
  <a href="#building-from-source">Building from Source</a> •
  <a href="#contributing">Contributing</a> •
  <a href="#license">License</a>
</p>

---

## Features

- **Batch conversion**, convert one file or hundreds at once
- **Drag-and-drop**, drop files anywhere on the window to load them
- **Video → Audio extraction**, pull the audio track out of any video file
- **Live conversion details**, current-file percentage, batch progress, elapsed time, estimated file time remaining, encoding speed, FPS, and output size
- **Independent speed and quality**, fast encoding by default, with balanced and smaller-file settings
- **Copy streams mode**, change compatible video/audio containers without re-encoding
- **Cancel mid-conversion**, stop a running batch at any time without leaving ghost processes
- **Wide format support**, 40+ input/output formats across video, audio, and image (see [Supported Formats](#supported-formats))
- **Quality control**, choose CRF presets for video, bitrate for audio, and quality level for images
- **Recent folders**, quickly pick from your last 10 output directories
- **Linux-friendly UI**, the original Bubblegum Sans logo, centered controls, standard system fonts for text, matching text/control scaling, and an automatically hidden scrollbar
- **Always-visible progress**, conversion status and Cancel stay on screen when setup needs scrolling
- **Notification sound**, plays a chime when your conversion finishes
- **Native Linux installation**, isolated Python environment, application-menu entry, file-manager integration, upgrades, and uninstall
- **Cross-platform**, Python interface for Linux, Windows, and macOS; FFmpeg is installed separately

---

## Installation

### Linux (recommended)

Download/extract the native installer archive, or clone this repository. The installer works with Python 3.10+ and uses your distribution's FFmpeg and Tk 8.6 packages. On Wayland, Tk also needs XWayland (usually installed by your desktop). The app reads your Xft DPI setting through `xrdb` when available and scales text, controls, and window size together. This affects only the converter, not your desktop settings.

Install system dependencies once:

```bash
# Garuda / Arch
sudo pacman -S --needed python tk ffmpeg

# Ubuntu / Debian / Linux Mint
sudo apt update
sudo apt install python3 python3-venv python3-tk ffmpeg
```

Then, from the extracted/cloned folder, run **without sudo**:

```bash
./install-linux.sh
```

Open **Lace's Total File Converter** from the application menu, or run:

```bash
~/.local/bin/laces-file-converter
```

Installation downloads Python packages from PyPI into a private virtual environment. It copies the application into `~/.local/share/laces-file-converter`; the checkout or extracted installer can be moved/deleted afterward. No system Python packages are changed. The menu entry accepts files through your file manager's **Open With** action.

- **Upgrade:** update/extract the new source and rerun `./install-linux.sh`. The previous release remains available on disk; a failed dependency installation leaves the active release intact. Close a running app before upgrading.
- **Uninstall:** `./install-linux.sh --uninstall`. Converted files and settings are kept. Extract another copy of the installer if you deleted the original.
- **Custom prefix:** `./install-linux.sh --prefix /path/to/prefix`; supply the same prefix to uninstall. Only the standard `~/.local` location is normally searched by desktop menus automatically.
- **Diagnostics:** `~/.local/bin/laces-file-converter --check` checks Python, Tk, optional integrations, FFmpeg, and ffprobe without opening a window.
- **Settings:** `${XDG_CONFIG_HOME:-~/.config}/laces-file-converter/config.json`. Existing `~/.lace_converter_config.json` history is read automatically when no new settings exist.

For other distributions, install Python, Python's venv/ensurepip support, Tk bindings, FFmpeg, and ffprobe through your package manager. Codec availability varies by FFmpeg build; a missing encoder is reported in **View details**. Drag-and-drop and completion sound are optional at runtime; failures in these integrations no longer prevent the app from starting.

**Existing Flatpak users:** use the native installer for this release. The checked-in `LacesFileConverter.flatpak` is an older 4.0.0 build and does not contain these fixes. The legacy Flatpak recipe is not a verified release path: it expects an FFmpeg executable, but its codec extension does not supply the command-line tools. The native menu entry takes precedence over the old Flatpak entry without removing the old installation.

### Windows / macOS / running from source

Install Python 3.10+ with Tk, then:

```bash
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS / Linux:
source .venv/bin/activate

python -m pip install -r requirements.txt
python main.py
```

FFmpeg **and ffprobe** must be on `PATH`, or placed next to `main.py` (Windows: `ffmpeg.exe` and `ffprobe.exe`). You can also set `FFMPEG_BINARY` and `FFPROBE_BINARY` to their full paths. On macOS, install FFmpeg with `brew install ffmpeg` and use a Python build with Tk. If ffprobe is unavailable at runtime, conversion still works with an activity indicator and elapsed time instead of percentage/ETA.

---

## Usage

### 1. Select Files

Click **Browse for Files** or **drag-and-drop** files anywhere on the application window. You can select multiple files, they will all be converted in one batch.

> **Note:** All files in a batch must be the same type (video, audio, or image). Video and audio files *can* be mixed together when an audio output format is selected.

### 2. Choose Quality & Output Format

- **Video:** choose quality (High / Medium / Low), encoding speed, and an output container. **Fast** is the default. Balanced / Smaller files spend more encoding time on compression. Speed applies to H.264 and WebM outputs; other codecs use their own settings. Pick an audio format to **extract audio only**, with a selectable bitrate.
- **Copy streams:** for video/audio, choose this mode when you only need a compatible container change. It preserves compressed streams and skips encoding. Quality/bitrate controls are disabled. All video/audio tracks are kept for video outputs; audio extraction keeps the first audio track. Subtitles, attachments, and data tracks are not copied. Incompatible codec/container pairs fail with an explanation; choose **Convert** to re-encode them.
- **Audio:** choose a bitrate and output format.
- **Image:** choose a quality level and output format (including `.ico` and `.avif`).

### 3. Choose Output Folder

Set the destination folder for converted files. The **Recent…** dropdown remembers your last 10 output directories.

### 4. Convert

Click **Start conversion**. The current-file bar shows media-time progress; the batch bar counts files with a fractional contribution from the current file (it is not an estimate of total batch time). Live details show elapsed batch time, estimated time remaining for the current file, processing speed (`2×` means two seconds of media per second), FPS when available, and bytes written.

Estimates settle as encoding proceeds and may change with scene complexity or disk speed. Files with unknown duration, including still images, show an activity indicator and elapsed time. **Finalizing** covers flushing/indexing the output; a file is marked complete only after FFmpeg exits successfully. The completion notification reports successful and failed files accurately; **View details** shows output paths or FFmpeg's error messages. **Open output folder** opens the destination.

Click **Cancel** or close the window to stop the current job. The app waits for FFmpeg to exit (and kills it if needed), removes its temporary partial file, and keeps already completed files. Inputs and existing outputs are never overwritten. Settings and file selection are held fixed while a batch runs.

FFmpeg must include the codec/decoder needed by your chosen format. HEIC/HEIF, SVG, AVIF, and animation support depend on the installed FFmpeg build. Still-image targets use the first frame of animated inputs; GIF/WebP retain multiple frames when supported.

---

## Supported Formats

### Video

| Direction | Formats |
|---|---|
| **Input** | `.mp4` `.avi` `.mkv` `.mov` `.wmv` `.flv` `.webm` `.m4v` `.mpg` `.mpeg` `.3gp` `.ts` `.ogv` `.vob` |
| **Output** | `.mp4` `.mkv` `.avi` `.mov` `.webm` `.flv` `.wmv` `.m4v` `.ts` `.ogv` |

### Audio

| Direction | Formats |
|---|---|
| **Input** | `.mp3` `.wav` `.flac` `.m4a` `.aac` `.ogg` `.opus` `.wma` `.aiff` |
| **Output** | `.mp3` `.m4a` `.wav` `.flac` `.ogg` `.aac` `.opus` `.wma` `.aiff` |

### Image

| Direction | Formats |
|---|---|
| **Input** | `.jpg` `.jpeg` `.png` `.bmp` `.gif` `.webp` `.tiff` `.tif` `.svg` `.ico` `.avif` `.heic` `.heif` |
| **Output** | `.jpg` `.png` `.webp` `.bmp` `.gif` `.tiff` `.ico` `.avif` |

### Video → Audio Extraction

When video files are loaded, the output format dropdown also includes every audio format. Selecting one strips the video track and encodes the audio only.

---

## Project Structure

```
laces-file-converter/
├── main.py                  # Tk interface and main-thread progress updates
├── converter.py             # FFmpeg commands, process control, progress, safe output
├── linux_support.py         # Startup diagnostics and configuration paths
├── ui_components.py         # Linux DPI alignment and automatically hidden scrolling
├── install-linux.sh         # Native Linux installer entry point
├── scripts/
│   ├── install_linux.py     # User install, upgrades, desktop entry, uninstall
│   └── build_linux.py       # Build the distributable Linux installer archive
├── tests/                   # Process, progress, real FFmpeg, and GUI smoke checks
├── requirements.txt
└── assets/                  # Fonts, icon, notification sound
```

---

## Building from Source

### Native Linux installer archive

```bash
python3 scripts/build_linux.py
```

This creates `dist/laces-file-converter-4.1.2-linux.tar.gz`, including the installer and application assets. Python dependencies are downloaded during installation; this is not an offline bundle.

### Tests

```bash
python3 -m unittest discover -s tests -v
# With GUI dependencies installed and an X11/XWayland display:
.venv/bin/python tests/gui_smoke.py
.venv/bin/python tests/gui_layout.py
```

The integration tests generate synthetic media, convert all advertised output formats, probe and decode the results, and verify stream copying. Other tests cover stderr pipe saturation, silent/hung child cancellation, probe cancellation, unknown duration, invalid progress, failure cleanup, and filename collisions. No personal media is used.


### PyInstaller (single `.exe`)

```bash
pip install pyinstaller

pyinstaller --onefile --windowed \
    --add-data "assets;assets" \
    --add-binary "ffmpeg.exe;." \
    --add-binary "ffprobe.exe;." \
    --icon "assets/icons/icon2.ico" \
    --name "LacesFileConverter" \
    main.py
```

The resulting executable will be in the `dist/` folder.

---

## Dependencies

| Package | Purpose |
|---|---|
| [customtkinter](https://github.com/TomSchimansky/CustomTkinter) | Modern themed Tkinter widgets |
| [tkinterdnd2](https://github.com/pmgagne/tkinterdnd2) | Native drag-and-drop support |
| [pygame-ce](https://github.com/pygame-community/pygame-ce) | Audio playback for notification sounds |
| [Pillow](https://python-pillow.github.io/) | Linux window/menu icon support |

All listed in [`requirements.txt`](requirements.txt).

Implementation references: [FFmpeg progress output](https://ffmpeg.org/ffmpeg.html#Main-options), [FFmpeg encoder options](https://ffmpeg.org/ffmpeg-codecs.html), [Arch Tk package](https://archlinux.org/packages/extra/x86_64/tk/).

---

## Contributing

Contributions are welcome! Here's how to get involved:

1. **Fork** the repository
2. **Create** a feature branch (`git checkout -b feature/my-feature`)
3. **Commit** your changes (`git commit -m "Add my feature"`)
4. **Push** to your branch (`git push origin feature/my-feature`)
5. **Open** a Pull Request

### Guidelines

- Keep changes focused, one feature or fix per PR
- Follow the existing code style (PEP 8, type hints, docstrings)
- Test your changes on at least one platform before submitting
- If adding a new format, make sure FFmpeg supports it out of the box

### Reporting Bugs

Open an [issue](https://github.com/LaceEditing/laces-file-converter/issues) with:
- Steps to reproduce
- Expected vs actual behavior
- Your OS and Python version
- The full error traceback (if any)

---

## License

This project is licensed under the **MIT License**, see the [LICENSE](LICENSE) file for details.

You are free to use, modify, and distribute this software for any purpose, including commercial use.

---

<p align="center">
  Made with 💚 by <a href="https://github.com/LaceEditing">Lace</a>
</p>
