# Lace's Total File Converter

<p align="center">
  <img src="assets/icons/icon2.png" alt="Lace's Total File Converter" width="128" />
</p>

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

- **Batch conversion** — convert one file or hundreds at once
- **Drag-and-drop** — drop files anywhere on the window to load them
- **Video → Audio extraction** — pull the audio track out of any video file
- **Real-time progress** — per-file progress bar powered by FFmpeg's `-progress` pipe
- **Cancel mid-conversion** — stop a running batch at any time without leaving ghost processes
- **Wide format support** — 40+ input/output formats across video, audio, and image (see [Supported Formats](#supported-formats))
- **Quality control** — choose CRF presets for video, bitrate for audio, and quality level for images
- **Recent folders** — quickly pick from your last 10 output directories
- **Dark-mode UI** — modern green-on-dark theme using CustomTkinter
- **Notification sound** — plays a chime when your conversion finishes
- **Portable** — ships with FFmpeg; no system-wide install required
- **Cross-platform friendly** — primarily developed for Windows, also runs on macOS/Linux with minimal changes

---

## Screenshots

> *Screenshots coming soon — contributions welcome!*

---

## Installation

### Prerequisites

| Dependency | Version | Notes |
|---|---|---|
| **Python** | 3.10+ | 3.12 or 3.13 recommended |
| **FFmpeg** | 5.0+ | Must be on `PATH` or placed next to `main.py` |

### Quick Start

```bash
# 1. Clone the repository
git clone https://github.com/LaceEditing/laces-file-converter.git
cd laces-file-converter

# 2. Create and activate a virtual environment (recommended)
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate

# 3. Install Python dependencies
pip install -r requirements.txt

# 4. Place ffmpeg
#    Option A: Download from https://ffmpeg.org/download.html and put
#              ffmpeg.exe (and ffprobe.exe) in this folder.
#    Option B: Install system-wide so it's on your PATH.

# 5. Run the app
python main.py
```

### FFmpeg

The converter **requires** FFmpeg to function. If FFmpeg is not found the app will show an error dialog on startup.

| Platform | Easiest method |
|---|---|
| **Windows** | Download a [release build](https://www.gyan.dev/ffmpeg/builds/), extract `ffmpeg.exe` + `ffprobe.exe` into the project folder |
| **macOS** | `brew install ffmpeg` |
| **Linux** | `sudo apt install ffmpeg` (Debian/Ubuntu) or your distro's package manager |

---

## Usage

### 1. Select Files

Click **Browse for Files** or **drag-and-drop** files anywhere on the application window. You can select multiple files — they will all be converted in one batch.

> **Note:** All files in a batch must be the same type (video, audio, or image). Video and audio files *can* be mixed together.

### 2. Choose Quality & Output Format

- **Video:** choose a quality preset (High / Medium / Low) and an output container. You can also pick an audio format from the dropdown to **extract audio only**.
- **Audio:** choose a bitrate and output format.
- **Image:** choose a quality level and output format (including `.ico` and `.avif`).

### 3. Choose Output Folder

Set the destination folder for converted files. The **Recent…** dropdown remembers your last 10 output directories.

### 4. Convert

Click **START CONVERSION**. The progress bar updates in real time. Click **CANCEL** at any time to abort — partial output files are cleaned up automatically.

When the batch finishes, a notification sound plays and you're offered a shortcut to open the output folder.

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
├── main.py                  # Application entry point (single-file app)
├── requirements.txt         # Python dependencies
├── LICENSE                  # MIT license
├── README.md                # This file
├── ffmpeg.exe               # (user-provided) FFmpeg binary
├── ffprobe.exe              # (user-provided) FFprobe binary
└── assets/
    ├── fonts/
    │   ├── BubblegumSans-Regular.ttf   # Title font
    │   └── Bartino.ttf                 # UI label font
    ├── icons/
    │   ├── icon2.ico                   # Window icon (ICO)
    │   └── icon2.png                   # Window icon (PNG fallback)
    └── sounds/
        └── notification.mp3            # Completion chime
```

---

## Building from Source

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

All listed in [`requirements.txt`](requirements.txt).

---

## Contributing

Contributions are welcome! Here's how to get involved:

1. **Fork** the repository
2. **Create** a feature branch (`git checkout -b feature/my-feature`)
3. **Commit** your changes (`git commit -m "Add my feature"`)
4. **Push** to your branch (`git push origin feature/my-feature`)
5. **Open** a Pull Request

### Guidelines

- Keep changes focused — one feature or fix per PR
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

This project is licensed under the **MIT License** — see the [LICENSE](LICENSE) file for details.

You are free to use, modify, and distribute this software for any purpose, including commercial use.

---

<p align="center">
  Made with 💚 by <a href="https://github.com/LaceEditing">Lace</a>
</p>
