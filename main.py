"""Lace's Total File Converter — a free, open-source batch file converter.

Converts video, audio, and image files between a wide range of formats using
FFmpeg under the hood.  Built with CustomTkinter for a modern dark-mode GUI
and tkinterdnd2 for native drag-and-drop support.

Repository : https://github.com/LaceEditing/laces-file-converter
License    : MIT
"""

from __future__ import annotations

import json
import os
import queue
import subprocess
import sys
import threading
import time
from pathlib import Path

from converter import Converter, Progress, Settings, find_binary, format_time
from linux_support import check_environment, config_path

VERSION = "4.1.2"
if __name__ == "__main__" and "--check" in sys.argv:
    sys.exit(check_environment())
if __name__ == "__main__" and "--version" in sys.argv:
    print(f"Lace's Total File Converter {VERSION}")
    sys.exit(0)

try:
    from tkinter import filedialog, messagebox
    from tkinter import font as tkfont
    import customtkinter as ctk
except ImportError:
    check_environment()
    sys.exit(1)

from ui_components import AutoHideScrollableFrame, configure_linux_display, load_logo_font

if sys.platform == "linux":
    # Font-based corner glyphs can be substituted or mis-sized by Fontconfig.
    # Drawing shapes directly also works before a newly installed font is cached.
    from customtkinter.windows.widgets.core_rendering import DrawEngine
    DrawEngine.preferred_drawing_method = "polygon_shapes"

try:
    import tkinterdnd2 as tkdnd
except ImportError:
    tkdnd = None
try:
    os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
    from pygame import mixer
except ImportError:
    mixer = None


class FileConverterApp(ctk.CTk, tkdnd.TkinterDnD.DnDWrapper if tkdnd else object):
    """Main application window for Lace's Total File Converter.

    Inherits from both :class:`customtkinter.CTk` (modern themed Tk root) and
    :class:`tkinterdnd2.TkinterDnD.DnDWrapper` (whole-window drag-and-drop).
    """

    CURRENT_VERSION = VERSION
    GITHUB_REPO = "LaceEditing/laces-file-converter"

    # ── Supported extensions ─────────────────────────────────────────────
    VIDEO_EXTENSIONS = {
        '.mp4', '.avi', '.mkv', '.mov', '.wmv', '.flv', '.webm',
        '.m4v', '.mpg', '.mpeg', '.3gp', '.ts', '.ogv', '.vob',
    }
    AUDIO_EXTENSIONS = {
        '.mp3', '.wav', '.flac', '.m4a', '.aac', '.ogg', '.opus',
        '.wma', '.aiff',
    }
    IMAGE_EXTENSIONS = {
        '.jpg', '.jpeg', '.png', '.bmp', '.gif', '.webp',
        '.tiff', '.tif', '.svg', '.ico', '.avif', '.heic', '.heif',
    }

    # ── Output format lists ──────────────────────────────────────────────
    VIDEO_FORMATS = ["mp4", "mkv", "avi", "mov", "webm", "flv", "wmv", "m4v", "ts", "ogv"]
    AUDIO_FORMATS = ["mp3", "m4a", "wav", "flac", "ogg", "aac", "opus", "wma", "aiff"]
    IMAGE_FORMATS = ["jpg", "png", "webp", "bmp", "gif", "tiff", "ico", "avif"]
    # When video files are loaded, user can also extract audio:
    VIDEO_PLUS_AUDIO_FORMATS = VIDEO_FORMATS + ["── Audio Only ──"] + AUDIO_FORMATS

    # ── Green dark-mode palette ──────────────────────────────────────────
    COLORS = {
        'bg':            "#0d1f17",
        'accent':        "#2e8b57",
        'accent_dark':   "#1f6b42",
        'accent_light':  "#3cb371",
        'frame_bg':      "#132e1f",
        'text':          "#e0f0e8",
        'text_dim':      "#8ab89e",
        'button':        "#2e8b57",
        'button_hover':  "#3cb371",
        'entry_bg':      "#1a3d28",
        'progress_track': "#1a3d28",
        'border':        "#2e8b57",
    }

    # ─────────────────────────────────────────────────────────────────────
    #  __init__
    # ─────────────────────────────────────────────────────────────────────
    def __init__(self) -> None:
        """Initialise the converter window, state, and UI widgets."""
        load_logo_font(os.path.join(self._base_path(), "assets", "fonts", "BubblegumSans-Regular.ttf"))
        ctk.CTk.__init__(self, className="laces-file-converter")
        self.display_scale = configure_linux_display(self) if sys.platform == "linux" else 1.0
        self.dnd_available = False
        if tkdnd:
            try:
                self.TkdndVersion = tkdnd.TkinterDnD._require(self)
                self.dnd_available = True
            except Exception as exc:
                print(f"Drag-and-drop unavailable; use Browse for Files: {exc}", file=sys.stderr)

        self.title(f"Lace's Total File Converter · v{self.CURRENT_VERSION}")
        self.geometry("920x800")
        self.minsize(760, 620)

        self.set_icon()

        # Pygame mixer for notification sound
        try:
            mixer.init()
        except Exception:
            pass

        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("green")
        self.configure(fg_color=self.COLORS['bg'])

        # ── State variables ──────────────────────────────────────────────
        self.video_quality = ctk.StringVar(value="High")
        self.encoding_speed = ctk.StringVar(value="Fast")
        self.conversion_mode = ctk.StringVar(value="Convert")
        self.audio_bitrate = ctk.StringVar(value="320 kbps")
        self.image_quality = ctk.StringVar(value="95")
        self.video_output_format = ctk.StringVar(value="mp4")
        self.audio_output_format = ctk.StringVar(value="mp3")
        self.image_output_format = ctk.StringVar(value="jpg")
        self.output_folder = ctk.StringVar(value=str(Path.home() / "Downloads"))
        self.input_files: list[str] = []
        self.is_converting: bool = False
        self.cancel_event = threading.Event()
        self.ui_events = queue.SimpleQueue()
        self.worker = None
        self.closing = False
        self.batch_started = 0.0
        self.batch_output = ""
        self.details = []
        self.indeterminate = False
        self.current_file_type: str | None = None
        self.ffmpeg_available: bool = self.check_ffmpeg()
        self.recent_folders: list[str] = self.load_recent_folders()

        self.setup_ui()

        # Whole-window drag-and-drop
        if self.dnd_available:
            self.drop_target_register(tkdnd.DND_FILES)
            self.dnd_bind('<<Drop>>', self.on_drop)
        else:
            self.status_label.configure(text="Ready. Use Browse for Files (drag-and-drop unavailable).")

        self.protocol("WM_DELETE_WINDOW", self.on_close)
        self.after(100, self._poll_events)

        if not self.ffmpeg_available:
            self.after(500, self.show_ffmpeg_warning)

    # ─────────────────────────────────────────────────────────────────────
    #  Asset helpers
    # ─────────────────────────────────────────────────────────────────────
    @staticmethod
    def _base_path() -> str:
        """Return the root directory for bundled assets.

        When running from a PyInstaller bundle this resolves to the
        temporary ``_MEIPASS`` extraction folder; otherwise it is simply
        the directory containing this source file.
        """
        if getattr(sys, 'frozen', False):
            # noinspection PyProtectedMember
            return sys._MEIPASS  # type: ignore[attr-defined]
        return os.path.dirname(os.path.abspath(__file__))

    def set_icon(self) -> None:
        """Set the window icon from *assets/icons/*."""
        try:
            bp = self._base_path()
            if sys.platform == "win32":
                self.iconbitmap(os.path.join(bp, "assets", "icons", "icon2.ico"))
            else:
                from PIL import Image, ImageTk
                self._window_icon = ImageTk.PhotoImage(Image.open(os.path.join(bp, "assets", "icons", "icon2.ico")))
                self.iconphoto(True, self._window_icon)
        except Exception:
            pass

    def play_notification_sound(self) -> None:
        """Play *assets/sounds/notification.mp3* through pygame mixer."""
        try:
            p = os.path.join(self._base_path(), 'assets', 'sounds', 'notification.mp3')
            if os.path.exists(p):
                mixer.music.load(p)
                mixer.music.play()
        except Exception:
            pass

    # ─────────────────────────────────────────────────────────────────────
    #  Recent folders persistence
    # ─────────────────────────────────────────────────────────────────────
    def load_recent_folders(self) -> list[str]:
        """Load the most-recently-used output folders from the user config."""
        try:
            cfg = config_path()
            if not cfg.exists():
                cfg = Path.home() / '.lace_converter_config.json'
            if cfg.exists():
                with open(cfg, 'r', encoding='utf-8') as f:
                    return json.load(f).get('recent_folders', [])
        except Exception:
            pass
        return []

    def save_recent_folders(self) -> None:
        """Persist recent folders in the platform's user configuration directory."""
        try:
            cfg = config_path()
            cfg.parent.mkdir(parents=True, exist_ok=True)
            with open(cfg, 'w', encoding='utf-8') as f:
                json.dump({'recent_folders': self.recent_folders}, f)
        except Exception:
            pass

    def add_recent_folder(self, folder: str) -> None:
        """Push *folder* to the top of the MRU list (max 10 entries)."""
        if folder in self.recent_folders:
            self.recent_folders.remove(folder)
        self.recent_folders.insert(0, folder)
        self.recent_folders = self.recent_folders[:10]
        self.save_recent_folders()
        self.update_recent_dropdown()

    # ─────────────────────────────────────────────────────────────────────
    #  FFmpeg detection
    # ─────────────────────────────────────────────────────────────────────
    def check_ffmpeg(self) -> bool:
        """Return *True* if a usable ``ffmpeg`` binary can be found.

        Checks environment overrides, native bundled binaries, and system PATH.
        """
        self.ffmpeg_binary = find_binary("ffmpeg", self._base_path())
        self.ffprobe_binary = find_binary("ffprobe", self._base_path())
        if not self.ffprobe_binary and self.ffmpeg_binary:
            self.ffprobe_binary = find_binary("ffprobe", str(Path(self.ffmpeg_binary).parent))
        return self.ffmpeg_binary is not None

    def show_ffmpeg_warning(self) -> None:
        messagebox.showerror("FFmpeg Required", (
            "FFmpeg was not found. Install FFmpeg and ffprobe, then restart the app.\n\n"
            "Garuda / Arch: sudo pacman -S --needed ffmpeg\n"
            "Ubuntu / Debian: sudo apt install ffmpeg\n\n"
            "Windows: place ffmpeg.exe and ffprobe.exe next to main.py.\n"
            "Run the launcher with --check for dependency diagnostics."
        ))

    # ─────────────────────────────────────────────────────────────────────
    #  File-type detection & drag-and-drop
    # ─────────────────────────────────────────────────────────────────────
    def detect_file_type(self, filepath: str) -> str | None:
        """Classify *filepath* as ``'video'``, ``'audio'``, ``'image'``, or *None*."""
        ext = Path(filepath).suffix.lower()
        if ext in self.VIDEO_EXTENSIONS:
            return "video"
        if ext in self.AUDIO_EXTENSIONS:
            return "audio"
        if ext in self.IMAGE_EXTENSIONS:
            return "image"
        return None

    def on_drop(self, event) -> None:
        """Handle a drag-and-drop event on the application window."""
        files = self.tk.splitlist(event.data)
        self.add_files(files)

    def add_files(self, files: list[str] | tuple[str, ...]) -> None:
        if self.is_converting:
            return
        valid_files = []
        file_types = set()

        for f in files:
            if os.path.isfile(f):
                ft = self.detect_file_type(f)
                if ft:
                    valid_files.append(f)
                    file_types.add(ft)

        if not valid_files:
            messagebox.showwarning("Invalid Files", "No supported files found!")
            return

        if len(file_types) > 1:
            if file_types == {"video", "audio"}:
                main_type = "video"
            else:
                messagebox.showwarning(
                    "Mixed File Types",
                    "Please select files of the same type or compatible types (video/audio)!"
                )
                return
        else:
            main_type = list(file_types)[0]

        self.input_files = valid_files
        self.current_file_type = main_type

        if len(valid_files) == 1:
            display = self._short_filename(Path(valid_files[0]).name)
        else:
            display = f"{len(valid_files)} files selected"

        self.file_status_label.configure(text=display, text_color=self.COLORS['accent_light'])
        self.update_ui_for_file_type(main_type)

    # ─────────────────────────────────────────────────────────────────────
    #  Dynamic quality / format UI switching
    # ─────────────────────────────────────────────────────────────────────
    def update_ui_for_file_type(self, file_type: str) -> None:
        """Show the quality/format widgets appropriate for *file_type*."""
        # Hide all option menus first
        for w in (self.video_quality_menu, self.audio_bitrate_menu,
                  self.image_quality_menu, self.video_format_menu,
                  self.audio_format_menu, self.image_format_menu):
            w.grid_forget()

        if file_type == "video":
            extracting = self.video_output_format.get() in self.AUDIO_FORMATS
            self.quality_label.configure(text="Bitrate:" if extracting else "Quality:")
            (self.audio_bitrate_menu if extracting else self.video_quality_menu).grid(row=0, column=1, padx=(0, 20), pady=4, sticky="ew")
            self.format_label.configure(text="Output Format:")
            self.video_format_menu.grid(row=1, column=1, padx=(0, 20), pady=4, sticky="ew")
        elif file_type == "audio":
            self.quality_label.configure(text="Bitrate:")
            self.audio_bitrate_menu.grid(row=0, column=1, padx=(0, 20), pady=4, sticky="ew")
            self.format_label.configure(text="Output Format:")
            self.audio_format_menu.grid(row=1, column=1, padx=(0, 20), pady=4, sticky="ew")
        else:  # image
            self.quality_label.configure(text="Quality:")
            self.image_quality_menu.grid(row=0, column=1, padx=(0, 20), pady=4, sticky="ew")
            self.format_label.configure(text="Output Format:")
            self.image_format_menu.grid(row=1, column=1, padx=(0, 20), pady=4, sticky="ew")
        self._update_mode_options()

    def _update_mode_options(self, _choice=None) -> None:
        kind = self.current_file_type or "video"
        copy = self.conversion_mode.get() == "Copy streams" and kind != "image"
        self.mode_menu.configure(state="disabled" if kind == "image" else "normal")
        speed_applies = kind == "video" and self.video_output_format.get() in {"mp4", "mkv", "mov", "m4v", "ts", "webm"}
        self.speed_menu.configure(state="normal" if speed_applies and not copy else "disabled")
        for widget in (self.video_quality_menu, self.audio_bitrate_menu):
            widget.configure(state="disabled" if copy else "normal")
        if copy:
            text = "Copy streams skips encoding and preserves quality. The output container must support the source codecs."
        elif kind == "image":
            text = "Image quality applies when supported by the selected format."
        elif speed_applies:
            text = "Fast saves encoding time; slower speeds favor smaller files. Quality is controlled separately."
        else:
            text = "The selected output uses its own codec settings; video encoding speed does not apply."
        self.encoding_hint.configure(text=text)

    # ─────────────────────────────────────────────────────────────────────
    #  UI SETUP — green dark theme matching the mockup
    # ─────────────────────────────────────────────────────────────────────
    def setup_ui(self) -> None:
        """A compact setup area with progress and actions fixed below it."""
        C = self.COLORS
        family = tkfont.nametofont("TkDefaultFont").actual("family")
        self._label_font = ctk.CTkFont(family=family, size=14, weight="bold")
        self._small_font = ctk.CTkFont(family=family, size=13)
        self._btn_font = ctk.CTkFont(family=family, size=13, weight="bold")
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=24, pady=(22, 18))
        header.grid_columnconfigure(0, weight=1)
        self.title_label = ctk.CTkLabel(
            header, text="Lace's Total File Converter", anchor="center",
            font=ctk.CTkFont(family="Bubblegum Sans", size=38, weight="bold"), text_color=C['accent_light'])
        self.title_label.grid(row=0, column=0, sticky="ew")

        self.main_frame = AutoHideScrollableFrame(self, fg_color=C['bg'],
                                                   scrollbar_button_color="#385a46",
                                                   scrollbar_button_hover_color=C['accent'])
        self.main_frame.grid(row=1, column=0, sticky="nsew", padx=24)
        self.main_frame.grid_columnconfigure(0, weight=1)
        card_kw = dict(fg_color=C['frame_bg'], corner_radius=10, border_width=1, border_color="#294735")
        button_kw = dict(height=36, corner_radius=7, font=self._btn_font,
                         fg_color=C['button'], hover_color=C['button_hover'],
                         text_color=C['text'], text_color_disabled="#799184")
        secondary_kw = dict(button_kw, fg_color=C['entry_bg'], hover_color="#254e36", border_width=1, border_color="#365940")

        self.input_frame = ctk.CTkFrame(self.main_frame, **card_kw)
        self.input_frame.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        self.input_frame.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(self.input_frame, text="1   Files", font=self._label_font,
                     text_color=C['text']).grid(row=0, column=0, padx=16, pady=(10, 6))
        file_actions = ctk.CTkFrame(self.input_frame, fg_color="transparent")
        file_actions.grid(row=1, column=0, pady=(0, 4))
        self.browse_input_btn = ctk.CTkButton(file_actions, text="Browse files", command=self.browse_input,
                                              width=126, **button_kw)
        self.browse_input_btn.grid(row=0, column=0, padx=(0, 10))
        self.clear_btn = ctk.CTkButton(file_actions, text="Clear", command=self.clear_files,
                                       width=74, **secondary_kw)
        self.clear_btn.grid(row=0, column=1)
        self.empty_selection_text = "Drop files here or use Browse files." if self.dnd_available else "Choose one or more files with Browse files."
        self.file_status_label = ctk.CTkLabel(self.input_frame, text=self.empty_selection_text, width=1,
                                             font=self._small_font, text_color=C['text_dim'], anchor="center")
        self.file_status_label.grid(row=2, column=0, sticky="ew", padx=16, pady=(0, 10))

        self.options_frame = ctk.CTkFrame(self.main_frame, **card_kw)
        self.options_frame.grid(row=1, column=0, sticky="ew", pady=(0, 10))
        ctk.CTkLabel(self.options_frame, text="2   Conversion settings", font=self._label_font,
                     text_color=C['text']).pack(padx=16, pady=(10, 6))
        opts_grid = ctk.CTkFrame(self.options_frame, fg_color="transparent")
        opts_grid.pack(padx=16, pady=(0, 6))
        self.quality_label = ctk.CTkLabel(opts_grid, text="Quality:", font=self._small_font, text_color=C['text'])
        self.quality_label.grid(row=0, column=0, padx=(0, 12), sticky="e")
        self.format_label = ctk.CTkLabel(opts_grid, text="Output format:", font=self._small_font, text_color=C['text'])
        self.format_label.grid(row=1, column=0, padx=(0, 12), sticky="e")
        menu_kw = dict(width=150, height=36, corner_radius=7, font=self._small_font,
                       dropdown_font=self._small_font, dynamic_resizing=False,
                       fg_color=C['entry_bg'], button_color="#274e36", button_hover_color="#356849",
                       text_color=C['text'], text_color_disabled="#799184",
                       dropdown_fg_color=C['frame_bg'], dropdown_hover_color=C['accent_dark'], dropdown_text_color=C['text'])
        self.video_quality_menu = ctk.CTkOptionMenu(opts_grid, values=["High", "Medium", "Low"],
                                                   variable=self.video_quality, **menu_kw)
        self.audio_bitrate_menu = ctk.CTkOptionMenu(opts_grid, values=["320 kbps", "256 kbps", "192 kbps", "128 kbps"],
                                                   variable=self.audio_bitrate, **menu_kw)
        self.image_quality_menu = ctk.CTkOptionMenu(opts_grid, values=["100 (Best)", "95", "90", "85", "80", "75", "70"],
                                                   variable=self.image_quality, **menu_kw)
        self.video_format_menu = ctk.CTkOptionMenu(opts_grid, values=self.VIDEO_PLUS_AUDIO_FORMATS,
                                                  variable=self.video_output_format, command=self._on_video_format_selected, **menu_kw)
        self.audio_format_menu = ctk.CTkOptionMenu(opts_grid, values=self.AUDIO_FORMATS,
                                                  variable=self.audio_output_format, **menu_kw)
        self.image_format_menu = ctk.CTkOptionMenu(opts_grid, values=self.IMAGE_FORMATS,
                                                  variable=self.image_output_format, **menu_kw)
        ctk.CTkLabel(opts_grid, text="Encoding speed:", font=self._small_font, text_color=C['text']).grid(
            row=0, column=2, padx=(0, 12), sticky="e")
        self.speed_menu = ctk.CTkOptionMenu(opts_grid, values=["Fast", "Balanced", "Smaller files"],
                                           variable=self.encoding_speed, **menu_kw)
        self.speed_menu.grid(row=0, column=3, pady=4, sticky="ew")
        ctk.CTkLabel(opts_grid, text="Mode:", font=self._small_font, text_color=C['text']).grid(
            row=1, column=2, padx=(0, 12), sticky="e")
        self.mode_menu = ctk.CTkOptionMenu(opts_grid, values=["Convert", "Copy streams"],
                                          variable=self.conversion_mode, command=self._update_mode_options, **menu_kw)
        self.mode_menu.grid(row=1, column=3, pady=4, sticky="ew")
        self.encoding_hint = ctk.CTkLabel(self.options_frame, text="", font=self._small_font, width=1,
                                         text_color=C['text_dim'], wraplength=800, justify="center", anchor="center")
        self.encoding_hint.pack(fill="x", padx=16, pady=(0, 12))
        self.options_frame.bind("<Configure>", lambda e: self.encoding_hint.configure(
            wraplength=max(200, e.width / self.options_frame._get_widget_scaling() - 36)))
        self.update_ui_for_file_type("video")

        self.output_frame = ctk.CTkFrame(self.main_frame, **card_kw)
        self.output_frame.grid(row=2, column=0, sticky="ew", pady=(0, 4))
        self.output_frame.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(self.output_frame, text="3   Save to", font=self._label_font,
                     text_color=C['text']).grid(row=0, column=0, columnspan=3, padx=16, pady=(10, 6))
        self.output_entry = ctk.CTkEntry(self.output_frame, textvariable=self.output_folder, height=36,
                                         font=self._small_font, border_width=1, corner_radius=7,
                                         border_color="#365940", fg_color=C['entry_bg'], text_color=C['text'])
        self.output_entry.grid(row=1, column=0, sticky="ew", padx=(16, 8), pady=(2, 14))
        self.recent_dropdown = ctk.CTkOptionMenu(self.output_frame, values=["Recent folders"],
                                                 command=self.on_recent_selected, **dict(menu_kw, width=148))
        self.recent_dropdown.grid(row=1, column=1, padx=(0, 8), pady=(2, 14))
        self.update_recent_dropdown()
        self.browse_output_btn = ctk.CTkButton(self.output_frame, text="Browse", command=self.browse_output,
                                                width=86, **secondary_kw)
        self.browse_output_btn.grid(row=1, column=2, padx=(0, 16), pady=(2, 14))

        # Always visible: scrolling setup must never hide progress or Cancel.
        self.progress_frame = ctk.CTkFrame(self, **card_kw)
        self.progress_frame.grid(row=2, column=0, sticky="ew", padx=24, pady=(12, 20))
        self.progress_frame.grid_columnconfigure(0, weight=1)
        progress_header = ctk.CTkFrame(self.progress_frame, fg_color="transparent")
        progress_header.grid(row=0, column=0, sticky="ew", padx=16, pady=(12, 6))
        progress_header.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(progress_header, text="Conversion progress", font=self._label_font,
                     text_color=C['text']).grid(row=0, column=0)
        self.status_label = ctk.CTkLabel(self.progress_frame, text="Ready. Select your files to get started.",
                                        width=1, height=22, font=self._small_font, text_color=C['text_dim'], anchor="center")
        self.status_label.grid(row=1, column=0, sticky="ew", padx=16, pady=(0, 6))
        bars = ctk.CTkFrame(self.progress_frame, fg_color="transparent")
        bars.grid(row=2, column=0, sticky="ew", padx=16)
        bars.grid_columnconfigure((0, 1), weight=1, uniform="progress")
        self.file_progress_label = ctk.CTkLabel(bars, text="Current file: 0%", font=self._small_font,
                                               height=24, text_color=C['text'], anchor="center")
        self.file_progress_label.grid(row=0, column=0, sticky="ew", padx=(0, 16))
        self.batch_progress_label = ctk.CTkLabel(bars, text="Batch: 0 files processed", font=self._small_font,
                                                height=24, text_color=C['text'], anchor="center")
        self.batch_progress_label.grid(row=0, column=1, sticky="ew")
        bar_kw = dict(height=10, corner_radius=5, fg_color=C['progress_track'])
        self.progress_bar = ctk.CTkProgressBar(bars, progress_color=C['accent_light'], **bar_kw)
        self.progress_bar.grid(row=1, column=0, sticky="ew", padx=(0, 16), pady=(2, 8))
        self.progress_bar.set(0)
        self.batch_progress_bar = ctk.CTkProgressBar(bars, progress_color=C['accent'], **bar_kw)
        self.batch_progress_bar.grid(row=1, column=1, sticky="ew", pady=(2, 8))
        self.batch_progress_bar.set(0)
        self.metrics_label = ctk.CTkLabel(self.progress_frame, text="Elapsed: 0:00   ·   File remaining: —   ·   Speed: —",
                                         font=self._small_font, text_color=C['text'], height=24, anchor="center")
        self.metrics_label.grid(row=3, column=0, sticky="ew", padx=16)
        self.media_label = ctk.CTkLabel(self.progress_frame, text="Media processed: —", font=self._small_font,
                                       text_color=C['text_dim'], height=24, anchor="center")
        self.media_label.grid(row=4, column=0, sticky="ew", padx=16)
        result_row = ctk.CTkFrame(self.progress_frame, fg_color="transparent")
        result_row.grid(row=5, column=0, sticky="ew", padx=16, pady=(8, 14))
        result_row.grid_columnconfigure((0, 2), weight=1, uniform="actions")
        self.convert_btn = ctk.CTkButton(result_row, text="Start conversion", command=self.start_conversion,
                                         width=178, **button_kw)
        self.convert_btn.grid(row=0, column=1)
        self.details_btn = ctk.CTkButton(result_row, text="View details", command=self.show_details,
                                        width=124, state="disabled", **secondary_kw)
        self.details_btn.grid(row=0, column=0, sticky="e", padx=(0, 12))
        self.open_output_btn = ctk.CTkButton(result_row, text="Open output folder", state="disabled",
                                            width=166, command=lambda: self.open_folder(self.batch_output), **secondary_kw)
        self.open_output_btn.grid(row=0, column=2, sticky="w", padx=(12, 0))

    @staticmethod
    def _short_filename(name: str, limit: int = 64) -> str:
        return name if len(name) <= limit else name[:limit - 21] + "…" + name[-20:]

    # ─────────────────────────────────────────────────────────────────────
    #  Video format dropdown guard (skip the separator label)
    # ─────────────────────────────────────────────────────────────────────
    def _on_video_format_selected(self, choice: str) -> None:
        """Guard the video format dropdown — ignore the separator label."""
        if choice == "── Audio Only ──":
            self.video_output_format.set("mp4")
        self.update_ui_for_file_type("video")

    # ─────────────────────────────────────────────────────────────────────
    #  Browse / clear
    # ─────────────────────────────────────────────────────────────────────
    def clear_files(self) -> None:
        """Reset the file selection back to empty."""
        if self.is_converting:
            return
        self.input_files = []
        self.current_file_type = None
        self.file_status_label.configure(text=self.empty_selection_text,
                                         text_color=self.COLORS['text_dim'])

    def browse_input(self) -> None:
        """Open a file-picker dialog and register the chosen files."""
        filetypes = [
            ("All Supported",
             "*.mp4 *.avi *.mkv *.mov *.wmv *.flv *.webm *.m4v *.mpg *.mpeg *.3gp "
             "*.ts *.ogv *.vob "
             "*.mp3 *.wav *.flac *.m4a *.aac *.ogg *.opus *.wma *.aiff "
             "*.jpg *.jpeg *.png *.bmp *.gif *.webp *.tiff *.tif *.svg "
             "*.ico *.avif *.heic *.heif"),
            ("Video", "*.mp4 *.avi *.mkv *.mov *.wmv *.flv *.webm *.m4v *.mpg *.mpeg *.3gp *.ts *.ogv *.vob"),
            ("Audio", "*.mp3 *.wav *.flac *.m4a *.aac *.ogg *.opus *.wma *.aiff"),
            ("Image", "*.jpg *.jpeg *.png *.bmp *.gif *.webp *.tiff *.tif *.svg *.ico *.avif *.heic *.heif"),
        ]
        files = filedialog.askopenfilenames(filetypes=filetypes)
        if files:
            self.add_files(files)

    def browse_output(self) -> None:
        """Open a folder-picker dialog for the output directory."""
        folder = filedialog.askdirectory()
        if folder:
            self.output_folder.set(folder)
            self.add_recent_folder(folder)

    def update_recent_dropdown(self) -> None:
        """Refresh the *Recent…* dropdown values from the MRU list."""
        if self.recent_folders:
            names: list[str] = []
            for folder in self.recent_folders[:10]:
                n = Path(folder).name or folder
                names.append(n[:17] + "..." if len(n) > 20 else n)
            self.recent_dropdown.configure(values=names)
        else:
            self.recent_dropdown.configure(values=["No recent folders"])
        self.recent_dropdown.set("Recent folders")

    def on_recent_selected(self, choice: str) -> None:
        if choice and choice != "No recent folders":
            for i, folder in enumerate(self.recent_folders[:10]):
                n = Path(folder).name or folder
                if (n[:17] + "..." if len(n) > 20 else n) == choice:
                    self.output_folder.set(self.recent_folders[i])
                    break

    # Worker threads send plain data; every Tk operation stays on the main thread.
    def _poll_events(self) -> None:
        for _ in range(100):
            try:
                event, payload = self.ui_events.get_nowait()
            except queue.Empty:
                break
            if event == "progress":
                self._display_progress(*payload)
            elif event == "result":
                index, total, name, result = payload
                label = "Cancelled" if result.cancelled else ("Saved" if result.output else "Failed")
                detail = result.output or result.error or "Conversion cancelled."
                self.details.append(f"[{index + 1}/{total}] {label}: {name}\n{detail}\n")
            elif event == "finished":
                self._finish_batch(*payload)
        if self.closing and not self.is_converting:
            self.destroy()
            return
        self.after(100, self._poll_events)

    def _display_progress(self, index: int, total: int, name: str, progress: Progress) -> None:
        fraction = progress.fraction
        unknown = fraction is None
        if unknown != self.indeterminate:
            self.progress_bar.stop()
            self.progress_bar.configure(mode="indeterminate" if unknown else "determinate")
            self.indeterminate = unknown
            if unknown:
                self.progress_bar.start()
        if not unknown:
            self.progress_bar.set(fraction)
        self.batch_progress_bar.set((index + (fraction or 0)) / total)
        percent = f"{fraction:.0%}" if fraction is not None else (
            "Reading media…" if progress.phase in {"Preparing", "Reading media"} else "Duration unavailable")
        phase = "Cancelling…" if self.cancel_event.is_set() else progress.phase
        self.status_label.configure(text=f"File {index + 1} of {total} · {phase}: {self._short_filename(name)}")
        self.file_progress_label.configure(text=f"Current file: {percent}")
        self.batch_progress_label.configure(text=f"Batch: {index} of {total} files processed" if progress.phase != "Complete"
                                           else f"Batch: {index + 1} of {total} files processed")
        media = format_time(progress.media_seconds)
        if progress.duration:
            media += " / " + format_time(progress.duration)
        speed = f"{progress.speed:.2f}×" if progress.speed else "Measuring…"
        remaining = "Finalizing…" if progress.phase == "Finalizing" else format_time(progress.eta)
        if unknown:
            remaining = "Unavailable"
        self.metrics_label.configure(text=f"Elapsed: {format_time(time.monotonic() - self.batch_started)}   ·   "
                                     f"File remaining: {remaining}   ·   Speed: {speed}")
        detail = f"Media processed: {media}"
        if progress.fps:
            detail += f"   ·   {progress.fps:.1f} fps"
        if progress.size_bytes:
            detail += f"   ·   Written: {progress.size_bytes / 1024**2:.1f} MiB"
        self.media_label.configure(text=detail)

    def _set_controls(self, busy: bool) -> None:
        for widget in (self.browse_input_btn, self.clear_btn, self.browse_output_btn,
                       self.output_entry, self.recent_dropdown, self.video_quality_menu,
                       self.audio_bitrate_menu, self.image_quality_menu, self.video_format_menu,
                       self.audio_format_menu, self.image_format_menu, self.speed_menu, self.mode_menu):
            widget.configure(state="disabled" if busy else "normal")
        if not busy:
            self._update_mode_options()

    def _finish_batch(self, successful: int, failed: int, total: int, cancelled: bool, fatal: str | None) -> None:
        self.is_converting = False
        self.progress_bar.stop()
        self.progress_bar.configure(mode="determinate")
        self.indeterminate = False
        if not cancelled and not fatal:
            self.batch_progress_bar.set(1)
        label = "Cancelled" if cancelled else "Finished"
        if fatal:
            label = "Stopped"
            self.details.append(fatal)
        self.status_label.configure(text=f"{label}: {successful}/{total} converted, {failed} failed."
                                    + (" See details." if failed or fatal else ""))
        self.batch_progress_label.configure(text=f"Batch: {successful + failed} of {total} files processed")
        self.metrics_label.configure(text=f"Total elapsed: {format_time(time.monotonic() - self.batch_started)}")
        self.file_progress_label.configure(text="Current file: " + ("Cancelled" if cancelled else "Complete" if successful == total else "See details"))
        self.convert_btn.configure(state="normal", text="Start conversion", command=self.start_conversion,
                                   fg_color=self.COLORS['accent'], hover_color=self.COLORS['accent_light'])
        self._set_controls(False)
        self.details_btn.configure(state="normal")
        self.open_output_btn.configure(state="normal")
        if successful and not cancelled and not self.closing:
            self.play_notification_sound()

    def show_details(self) -> None:
        window = ctk.CTkToplevel(self)
        window.title("Conversion details")
        window.geometry("800x450")
        box = ctk.CTkTextbox(window, wrap="word")
        box.pack(fill="both", expand=True, padx=15, pady=15)
        box.insert("1.0", "\n".join(self.details) or "No conversions yet.")
        box.configure(state="disabled")
        window.after(50, window.lift)

    def open_folder(self, path: str) -> None:
        try:
            if sys.platform == "win32":
                os.startfile(path)
            else:
                subprocess.Popen(["open" if sys.platform == "darwin" else "xdg-open", path])
        except Exception as exc:
            messagebox.showerror("Error", f"Could not open folder: {exc}")

    def request_cancel(self) -> None:
        self.cancel_event.set()
        self.convert_btn.configure(state="disabled", text="Cancelling…")
        self.status_label.configure(text="Cancelling… Cleaning up the current file.")

    def on_close(self) -> None:
        self.closing = True
        if self.is_converting:
            self.request_cancel()
        else:
            self.destroy()

    def batch_convert(self, files: tuple[str, ...], kinds: tuple[str, ...], output_dir: str, settings: Settings) -> None:
        successful = failed = 0
        fatal = None
        try:
            converter = Converter(self.ffmpeg_binary, self.ffprobe_binary)
            for index, (source, kind) in enumerate(zip(files, kinds)):
                if self.cancel_event.is_set():
                    break
                name = Path(source).name
                def report(progress, i=index, n=name):
                    self.ui_events.put(("progress", (i, len(files), n, progress)))
                report(Progress("Preparing", 0))
                result = converter.convert(source, output_dir, kind, settings, self.cancel_event, report)
                self.ui_events.put(("result", (index, len(files), name, result)))
                if result.cancelled:
                    break
                if result.output:
                    successful += 1
                else:
                    failed += 1
        except Exception as exc:
            fatal = str(exc)
        finally:
            self.ui_events.put(("finished", (successful, failed, len(files), self.cancel_event.is_set(), fatal)))

    def start_conversion(self) -> None:
        if self.is_converting:
            return
        if not self.check_ffmpeg():
            self.show_ffmpeg_warning()
            return
        if not self.input_files:
            messagebox.showwarning("No Input Files", "Please select files to convert.")
            return
        variables = {"video": self.video_output_format, "audio": self.audio_output_format, "image": self.image_output_format}
        ext = variables[self.current_file_type].get()
        kinds = tuple(self.detect_file_type(f) for f in self.input_files)
        if "audio" in kinds and ext not in self.AUDIO_FORMATS:
            messagebox.showwarning("Audio Output Required", "This batch contains audio files. Select an audio output format, or load only video files.")
            return
        output_dir = self.output_folder.get().strip()
        if not output_dir:
            messagebox.showerror("Invalid Folder", "Please select an output folder.")
            return
        output_dir = str(Path(output_dir).expanduser().absolute())
        try:
            Path(output_dir).mkdir(parents=True, exist_ok=True)
            if not Path(output_dir).is_dir():
                raise OSError("Not a directory")
        except OSError as exc:
            messagebox.showerror("Invalid Folder", f"Cannot use the output folder: {exc}")
            return
        settings = Settings(ext, self.video_quality.get(), self.encoding_speed.get(),
                            self.audio_bitrate.get().split()[0], int(self.image_quality.get().split()[0]),
                            self.conversion_mode.get() == "Copy streams" and self.current_file_type != "image")
        self.cancel_event.clear()
        self.is_converting = True
        self.batch_started = time.monotonic()
        self.batch_output = output_dir
        self.details = []
        self.progress_bar.set(0)
        self.batch_progress_bar.set(0)
        self.add_recent_folder(output_dir)
        self._set_controls(True)
        self.details_btn.configure(state="disabled")
        self.open_output_btn.configure(state="disabled")
        self.convert_btn.configure(text="Cancel", command=self.request_cancel,
                                   fg_color="#8b2e2e", hover_color="#b33c3c")
        self.worker = threading.Thread(target=self.batch_convert,
                                       args=(tuple(self.input_files), kinds, output_dir, settings), daemon=True)
        self.worker.start()


if __name__ == "__main__":
    app = FileConverterApp()
    paths = [str(Path(p).expanduser().absolute()) for p in sys.argv[1:] if p != "--"]
    if paths:
        app.after(100, lambda: app.add_files(paths))
    app.mainloop()
