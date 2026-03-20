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
import re
import shutil
import subprocess
import sys
import threading
from pathlib import Path
from tkinter import filedialog, messagebox

import customtkinter as ctk
import tkinterdnd2 as tkdnd
from pygame import mixer


class FileConverterApp(ctk.CTk, tkdnd.TkinterDnD.DnDWrapper):
    """Main application window for Lace's Total File Converter.

    Inherits from both :class:`customtkinter.CTk` (modern themed Tk root) and
    :class:`tkinterdnd2.TkinterDnD.DnDWrapper` (whole-window drag-and-drop).
    """

    CURRENT_VERSION = "4.0.0"
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
        ctk.CTk.__init__(self)
        self.TkdndVersion = tkdnd.TkinterDnD._require(self)

        self.title(f"Hey besties let's convert those files! (v{self.CURRENT_VERSION})")
        self.geometry("950x780")
        self.minsize(900, 720)

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
        self.audio_bitrate = ctk.StringVar(value="320 kbps")
        self.image_quality = ctk.StringVar(value="95")
        self.video_output_format = ctk.StringVar(value="mp4")
        self.audio_output_format = ctk.StringVar(value="mp3")
        self.image_output_format = ctk.StringVar(value="jpg")
        self.output_folder = ctk.StringVar(value=str(Path.home() / "Downloads"))
        self.input_files: list[str] = []
        self.is_converting: bool = False
        self.cancel_requested: bool = False
        self.current_process: subprocess.Popen | None = None
        self.current_file_type: str | None = None
        self.ffmpeg_available: bool = self.check_ffmpeg()
        self.recent_folders: list[str] = self.load_recent_folders()

        self.load_custom_fonts()
        self.setup_ui()

        # Whole-window drag-and-drop
        self.drop_target_register(tkdnd.DND_FILES)
        self.dnd_bind('<<Drop>>', self.on_drop)

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
            for name in ('icon2.ico', 'icon2.png'):
                p = os.path.join(bp, 'assets', 'icons', name)
                if os.path.exists(p):
                    self.iconbitmap(p)
                    return
        except Exception:
            pass

    def load_custom_fonts(self) -> None:
        """Detect whether the bundled custom fonts exist on disk."""
        try:
            bp = self._base_path()
            self.bubblegum_font_path = os.path.join(bp, 'assets', 'fonts', 'BubblegumSans-Regular.ttf')
            self.bartino_font_path = os.path.join(bp, 'assets', 'fonts', 'Bartino.ttf')
            self.has_bubblegum = os.path.exists(self.bubblegum_font_path)
            self.has_bartino = os.path.exists(self.bartino_font_path)
        except Exception:
            self.has_bubblegum = False
            self.has_bartino = False

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
            cfg = Path.home() / '.lace_converter_config.json'
            if cfg.exists():
                with open(cfg, 'r', encoding='utf-8') as f:
                    return json.load(f).get('recent_folders', [])
        except Exception:
            pass
        return []

    def save_recent_folders(self) -> None:
        """Persist the recent-folders list to *~/.lace_converter_config.json*."""
        try:
            cfg = Path.home() / '.lace_converter_config.json'
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

        Searches next to the application first, then falls back to the
        system PATH.  When found locally the path is stored in the
        ``FFMPEG_BINARY`` environment variable for later use.
        """
        bp = self._base_path()
        candidates = [
            os.path.join(bp, 'ffmpeg.exe'),
            os.path.join(bp, 'ffmpeg', 'ffmpeg.exe'),
            os.path.join(bp, 'bin', 'ffmpeg.exe'),
            os.path.join(bp, 'ffmpeg'),
            os.path.join(bp, 'ffmpeg', 'ffmpeg'),
            os.path.join(bp, 'bin', 'ffmpeg'),
        ]
        for p in candidates:
            if os.path.isfile(p) and os.access(p, os.X_OK):
                os.environ['FFMPEG_BINARY'] = p
                return True
        if shutil.which('ffmpeg'):
            return True
        return False

    def show_ffmpeg_warning(self) -> None:
        """Show an error dialog when FFmpeg is not available."""
        messagebox.showerror("FFmpeg Required", (
            "FFmpeg Not Found!\n\n"
            "FFmpeg is REQUIRED for file conversion.\n"
            "This app cannot function without it.\n\n"
            "To add FFmpeg:\n"
            "1. Download ffmpeg from https://ffmpeg.org/download.html\n"
            "2. Place ffmpeg.exe in the same folder as this app\n"
            "   OR install it system-wide\n\n"
            "Then restart the app!"
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
        valid_files = []
        file_types = set()

        for f in files:
            f = f.strip('{}')
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
            display = Path(valid_files[0]).name
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
            self.quality_label.configure(text="Quality:")
            self.video_quality_menu.grid(row=0, column=1, padx=(0, 10), sticky="w")
            self.format_label.configure(text="Output Format:")
            self.video_format_menu.grid(row=1, column=1, padx=(0, 10), sticky="w")
        elif file_type == "audio":
            self.quality_label.configure(text="Bitrate:")
            self.audio_bitrate_menu.grid(row=0, column=1, padx=(0, 10), sticky="w")
            self.format_label.configure(text="Output Format:")
            self.audio_format_menu.grid(row=1, column=1, padx=(0, 10), sticky="w")
        else:  # image
            self.quality_label.configure(text="Quality:")
            self.image_quality_menu.grid(row=0, column=1, padx=(0, 10), sticky="w")
            self.format_label.configure(text="Output Format:")
            self.image_format_menu.grid(row=1, column=1, padx=(0, 10), sticky="w")

    # ─────────────────────────────────────────────────────────────────────
    #  UI SETUP — green dark theme matching the mockup
    # ─────────────────────────────────────────────────────────────────────
    def setup_ui(self) -> None:
        """Build every widget in the application window."""
        C = self.COLORS

        # ── Scrollable main frame ────────────────────────────────────────
        self.main_frame = ctk.CTkFrame(self, fg_color=C['bg'])
        self.main_frame.pack(fill="both", expand=True, padx=20, pady=15)

        # ── Title ────────────────────────────────────────────────────────
        if self.has_bubblegum:
            title_font = ctk.CTkFont(family="Bubblegum Sans", size=42, weight="bold")
        else:
            title_font = ctk.CTkFont(size=42, weight="bold")

        self.title_label = ctk.CTkLabel(
            self.main_frame,
            text="Lace's Total File Converter",
            font=title_font,
            text_color=C['accent_light'],
        )
        self.title_label.pack(pady=(0, 18))

        # ── Shared fonts ─────────────────────────────────────────────────
        if self.has_bartino:
            self._label_font = ctk.CTkFont(family="Bartino", size=15, weight="bold")
            self._small_font = ctk.CTkFont(family="Bartino", size=13)
            self._btn_font = ctk.CTkFont(family="Bartino", size=13, weight="bold")
        else:
            self._label_font = ctk.CTkFont(size=15, weight="bold")
            self._small_font = ctk.CTkFont(size=13)
            self._btn_font = ctk.CTkFont(size=13, weight="bold")

        # ═══════════════════════════════════════════════════════════════
        #  STEP 1 — Select Files
        # ═══════════════════════════════════════════════════════════════
        self.input_frame = ctk.CTkFrame(self.main_frame, fg_color=C['frame_bg'],
                                        corner_radius=12, border_width=1,
                                        border_color=C['accent_dark'])
        self.input_frame.pack(fill="x", pady=(0, 10))

        ctk.CTkLabel(
            self.input_frame, text="Step 1: Select Files",
            font=self._label_font, text_color=C['text'],
        ).pack(anchor="w", padx=18, pady=(14, 8))

        # Buttons row — centred
        btn_row = ctk.CTkFrame(self.input_frame, fg_color=C['frame_bg'])
        btn_row.pack(pady=(0, 6))

        self.browse_input_btn = ctk.CTkButton(
            btn_row, text="Browse for Files", command=self.browse_input,
            width=160, height=38, font=self._btn_font,
            fg_color=C['button'], hover_color=C['button_hover'], corner_radius=8,
        )
        self.browse_input_btn.pack(side="left", padx=(0, 12))

        self.clear_btn = ctk.CTkButton(
            btn_row, text="Clear", command=self.clear_files,
            width=90, height=38, font=self._btn_font,
            fg_color="#3d5c4a", hover_color=C['button_hover'], corner_radius=8,
        )
        self.clear_btn.pack(side="left")

        # File-status label (replaces the old textbox)
        self.file_status_label = ctk.CTkLabel(
            self.input_frame, text="No files selected",
            font=self._small_font, text_color=C['text_dim'],
        )
        self.file_status_label.pack(pady=(2, 14))

        # ═══════════════════════════════════════════════════════════════
        #  STEP 2 — Quality & Output Format
        # ═══════════════════════════════════════════════════════════════
        self.options_frame = ctk.CTkFrame(self.main_frame, fg_color=C['frame_bg'],
                                          corner_radius=12, border_width=1,
                                          border_color=C['accent_dark'])
        self.options_frame.pack(fill="x", pady=(0, 10))

        ctk.CTkLabel(
            self.options_frame, text="Step 2: Choose Quality & Output Format",
            font=self._label_font, text_color=C['text'],
        ).pack(anchor="w", padx=18, pady=(14, 10))

        # Grid of label + dropdown, centred
        opts_grid = ctk.CTkFrame(self.options_frame, fg_color=C['frame_bg'])
        opts_grid.pack(pady=(0, 16))

        self.quality_label = ctk.CTkLabel(opts_grid, text="Quality:",
                                          font=self._small_font, text_color=C['text'])
        self.quality_label.grid(row=0, column=0, padx=(10, 8), pady=4, sticky="e")

        self.format_label = ctk.CTkLabel(opts_grid, text="Output Format:",
                                         font=self._small_font, text_color=C['text'])
        self.format_label.grid(row=1, column=0, padx=(10, 8), pady=4, sticky="e")

        menu_kw = dict(width=150, height=32, font=self._small_font,
                       fg_color=C['button'], button_color=C['accent'],
                       button_hover_color=C['accent_light'],
                       dropdown_fg_color=C['frame_bg'],
                       dropdown_hover_color=C['accent_dark'],
                       dropdown_text_color=C['text'])

        self.video_quality_menu = ctk.CTkOptionMenu(
            opts_grid, values=["High", "Medium", "Low"],
            variable=self.video_quality, **menu_kw)

        self.audio_bitrate_menu = ctk.CTkOptionMenu(
            opts_grid, values=["320 kbps", "256 kbps", "192 kbps", "128 kbps"],
            variable=self.audio_bitrate, **menu_kw)

        self.image_quality_menu = ctk.CTkOptionMenu(
            opts_grid, values=["100 (Best)", "95", "90", "85", "80", "75", "70"],
            variable=self.image_quality, **menu_kw)

        self.video_format_menu = ctk.CTkOptionMenu(
            opts_grid, values=self.VIDEO_PLUS_AUDIO_FORMATS,
            variable=self.video_output_format,
            command=self._on_video_format_selected, **menu_kw)

        self.audio_format_menu = ctk.CTkOptionMenu(
            opts_grid, values=self.AUDIO_FORMATS,
            variable=self.audio_output_format, **menu_kw)

        self.image_format_menu = ctk.CTkOptionMenu(
            opts_grid, values=self.IMAGE_FORMATS,
            variable=self.image_output_format, **menu_kw)

        # ═══════════════════════════════════════════════════════════════
        #  STEP 3 — Output Folder
        # ═══════════════════════════════════════════════════════════════
        self.output_frame = ctk.CTkFrame(self.main_frame, fg_color=C['frame_bg'],
                                         corner_radius=12, border_width=1,
                                         border_color=C['accent_dark'])
        self.output_frame.pack(fill="x", pady=(0, 10))

        ctk.CTkLabel(
            self.output_frame, text="Step 3: Choose Output Folder",
            font=self._label_font, text_color=C['text'],
        ).pack(anchor="w", padx=18, pady=(14, 8))

        out_row = ctk.CTkFrame(self.output_frame, fg_color=C['frame_bg'])
        out_row.pack(fill="x", padx=18, pady=(0, 14))

        ctk.CTkLabel(out_row, text="Save to:", font=self._small_font,
                     text_color=C['text']).pack(side="left", padx=(0, 8))

        self.output_entry = ctk.CTkEntry(
            out_row, textvariable=self.output_folder, height=34,
            font=self._small_font, border_color=C['border'],
            fg_color=C['entry_bg'], text_color=C['text'],
        )
        self.output_entry.pack(side="left", fill="x", expand=True, padx=(0, 8))

        self.recent_dropdown = ctk.CTkOptionMenu(
            out_row, values=["Recent..."], command=self.on_recent_selected,
            width=100, height=34, font=self._small_font,
            fg_color=C['button'], button_color=C['accent'],
            button_hover_color=C['accent_light'],
            dropdown_fg_color=C['frame_bg'],
            dropdown_hover_color=C['accent_dark'],
            dropdown_text_color=C['text'],
        )
        self.recent_dropdown.pack(side="left", padx=(0, 8))
        self.update_recent_dropdown()

        self.browse_output_btn = ctk.CTkButton(
            out_row, text="Browse", command=self.browse_output,
            width=80, height=34, font=self._btn_font,
            fg_color=C['button'], hover_color=C['button_hover'], corner_radius=8,
        )
        self.browse_output_btn.pack(side="left")

        # ═══════════════════════════════════════════════════════════════
        #  CONVERT / CANCEL button
        # ═══════════════════════════════════════════════════════════════
        self.convert_btn = ctk.CTkButton(
            self.main_frame, text="START CONVERSION",
            command=self.start_conversion, height=52,
            font=ctk.CTkFont(size=17, weight="bold"),
            fg_color=C['accent'], hover_color=C['accent_light'],
            corner_radius=10,
        )
        self.convert_btn.pack(fill="x", pady=(4, 10))

        # ═══════════════════════════════════════════════════════════════
        #  PROGRESS section
        # ═══════════════════════════════════════════════════════════════
        self.progress_frame = ctk.CTkFrame(self.main_frame, fg_color=C['frame_bg'],
                                            corner_radius=12, border_width=1,
                                            border_color=C['accent_dark'])
        self.progress_frame.pack(fill="x", pady=(0, 0))

        ctk.CTkLabel(
            self.progress_frame, text="Progress:",
            font=self._label_font, text_color=C['text'],
        ).pack(anchor="w", padx=18, pady=(12, 6))

        self.progress_bar = ctk.CTkProgressBar(
            self.progress_frame, height=18,
            progress_color=C['accent_light'],
            fg_color=C['progress_track'], corner_radius=8,
        )
        self.progress_bar.pack(fill="x", padx=18, pady=(0, 6))
        self.progress_bar.set(0)

        self.status_label = ctk.CTkLabel(
            self.progress_frame, text="Ready! Select your files to get started.",
            font=self._small_font, text_color=C['text_dim'], anchor="w",
        )
        self.status_label.pack(anchor="w", padx=18, pady=(0, 14))

    # ─────────────────────────────────────────────────────────────────────
    #  Video format dropdown guard (skip the separator label)
    # ─────────────────────────────────────────────────────────────────────
    def _on_video_format_selected(self, choice: str) -> None:
        """Guard the video format dropdown — ignore the separator label."""
        if choice == "── Audio Only ──":
            self.video_output_format.set("mp4")

    # ─────────────────────────────────────────────────────────────────────
    #  Browse / clear
    # ─────────────────────────────────────────────────────────────────────
    def clear_files(self) -> None:
        """Reset the file selection back to empty."""
        self.input_files = []
        self.current_file_type = None
        self.file_status_label.configure(text="No files selected",
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

    def on_recent_selected(self, choice: str) -> None:
        if choice and choice != "No recent folders":
            for i, folder in enumerate(self.recent_folders[:10]):
                n = Path(folder).name or folder
                if (n[:17] + "..." if len(n) > 20 else n) == choice:
                    self.output_folder.set(self.recent_folders[i])
                    break

    # ─────────────────────────────────────────────────────────────────────
    #  Thread-safe UI helpers
    # ─────────────────────────────────────────────────────────────────────
    def _set_progress(self, value: float) -> None:
        """Thread-safe progress-bar update."""
        self.after(0, lambda: self.progress_bar.set(value))

    def _set_status(self, text: str) -> None:
        """Thread-safe status-label update."""
        self.after(0, lambda: self.status_label.configure(text=text))

    def _enable_convert_btn(self) -> None:
        """Thread-safe reset of the convert button back to its default state."""
        self.after(0, lambda: self.convert_btn.configure(
            state="normal", text="START CONVERSION",
            command=self.start_conversion,
            fg_color=self.COLORS['accent'],
        ))

    # ─────────────────────────────────────────────────────────────────────
    #  Folder opener & completion dialog
    # ─────────────────────────────────────────────────────────────────────
    def open_folder(self, path: str) -> None:
        """Open *path* in the platform's native file explorer."""
        try:
            if sys.platform == 'win32':
                os.startfile(path)
            elif sys.platform == 'darwin':
                subprocess.run(['open', path], check=False)
            else:
                subprocess.run(['xdg-open', path], check=False)
        except Exception as e:
            messagebox.showerror("Error", f"Could not open folder: {e}")

    def show_completion_dialog(self) -> None:
        """Play a notification sound and offer to open the output folder."""
        self.play_notification_sound()
        if messagebox.askyesno(
            "Conversion Complete!",
            "All files have been converted successfully!\n\n"
            "Do you wanna open the output folder?",
            icon='info',
        ):
            self.open_folder(self.output_folder.get())

    # ─────────────────────────────────────────────────────────────────────
    #  Cancel support
    # ─────────────────────────────────────────────────────────────────────
    def request_cancel(self) -> None:
        """Signal the worker thread to stop and kill the running ffmpeg process."""
        self.cancel_requested = True
        if self.current_process:
            try:
                self.current_process.terminate()
            except Exception:
                pass
        self._set_status("Cancelling…")

    # ─────────────────────────────────────────────────────────────────────
    #  Duration probe (for per-file progress)
    # ─────────────────────────────────────────────────────────────────────
    def _probe_duration(self, input_path: str) -> float | None:
        """Return the media duration in seconds via ``ffprobe``, or *None*."""
        try:
            ffmpeg_bin = os.environ.get('FFMPEG_BINARY', 'ffmpeg')
            # Derive ffprobe path by replacing only the final filename component
            # to avoid corrupting paths like  C:\tools\ffmpeg-7.1\ffmpeg.exe
            parent = os.path.dirname(ffmpeg_bin)
            basename = os.path.basename(ffmpeg_bin).replace('ffmpeg', 'ffprobe')
            ffprobe = os.path.join(parent, basename) if parent else basename
            if not os.path.isfile(ffprobe):
                ffprobe = shutil.which('ffprobe') or 'ffprobe'

            startupinfo = None
            if sys.platform == 'win32':
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

            out = subprocess.check_output(
                [ffprobe, '-v', 'error', '-show_entries', 'format=duration',
                 '-of', 'csv=p=0', input_path],
                stderr=subprocess.STDOUT, text=True, timeout=10,
                startupinfo=startupinfo,
            )
            return float(out.strip())
        except Exception:
            return None

    # ─────────────────────────────────────────────────────────────────────
    #  Single-file conversion
    # ─────────────────────────────────────────────────────────────────────
    @staticmethod
    def _audio_codec_args(output_ext: str, bitrate: str) -> list[str]:
        """Return the ffmpeg codec/bitrate flags for an audio output format.

        Parameters
        ----------
        output_ext : str
            Lowercase extension *with* the leading dot (e.g. ``'.mp3'``).
        bitrate : str
            Numeric bitrate in kbps (e.g. ``'320'``).
        """
        if output_ext == '.mp3':
            return ['-codec:a', 'libmp3lame', '-b:a', f'{bitrate}k']
        if output_ext in ('.aac', '.m4a'):
            return ['-codec:a', 'aac', '-b:a', f'{bitrate}k']
        if output_ext == '.opus':
            return ['-codec:a', 'libopus', '-b:a', f'{bitrate}k']
        if output_ext == '.ogg':
            return ['-codec:a', 'libvorbis', '-q:a', '8']
        if output_ext == '.wav':
            return ['-codec:a', 'pcm_s16le']
        if output_ext == '.flac':
            return ['-codec:a', 'flac']
        if output_ext == '.aiff':
            return ['-codec:a', 'pcm_s16be']
        if output_ext == '.wma':
            return ['-codec:a', 'wmav2', '-b:a', f'{bitrate}k']
        return ['-b:a', f'{bitrate}k']

    def convert_file(
        self,
        input_path: str,
        output_path: str,
        file_type: str,
        file_index: int = 0,
        total_files: int = 1,
    ) -> bool:
        """Convert a single file with ffmpeg.  Returns *True* on success."""
        try:
            if not self.ffmpeg_available:
                return False

            ffmpeg_cmd = os.environ.get('FFMPEG_BINARY', 'ffmpeg')
            cmd: list[str] = [ffmpeg_cmd, '-i', input_path]

            output_ext = Path(output_path).suffix.lower()

            # Detect if we're extracting audio from video
            is_video_to_audio = (
                file_type == "video"
                and output_ext.lstrip('.') in self.AUDIO_FORMATS
            )

            if is_video_to_audio:
                # Extract audio track from a video file
                cmd.extend(self._audio_codec_args(output_ext, '192'))
                cmd.append('-vn')

            elif file_type == "video":
                quality = self.video_quality.get()
                if output_ext == '.ogv':
                    q_map = {"High": '8', "Medium": '5', "Low": '3'}
                    cmd.extend(['-c:v', 'libtheora', '-q:v', q_map.get(quality, '5'),
                                '-c:a', 'libvorbis', '-q:a', '6'])
                elif output_ext == '.ts':
                    crf_map = {"High": '18', "Medium": '23', "Low": '28'}
                    cmd.extend(['-c:v', 'libx264', '-crf', crf_map.get(quality, '23'),
                                '-c:a', 'aac', '-b:a', '192k', '-f', 'mpegts'])
                else:
                    crf_map = {"High": '18', "Medium": '23', "Low": '28'}
                    preset_map = {"High": 'slow', "Medium": 'medium', "Low": 'fast'}
                    cmd.extend(['-preset', preset_map.get(quality, 'medium'),
                                '-crf', crf_map.get(quality, '23'),
                                '-c:a', 'aac', '-b:a', '192k'])

            elif file_type == "audio":
                bitrate = self.audio_bitrate.get().split()[0]
                cmd.extend(self._audio_codec_args(output_ext, bitrate))
                cmd.append('-vn')

            else:  # image
                quality = self.image_quality.get().split()[0]
                if output_ext in ('.jpg', '.jpeg'):
                    cmd.extend(['-q:v', str(max(1, int((100 - int(quality)) / 10)))])
                elif output_ext == '.png':
                    cmd.extend(['-compression_level', '9'])
                elif output_ext == '.webp':
                    cmd.extend(['-quality', quality])
                elif output_ext == '.ico':
                    cmd.extend(['-vframes', '1'])
                elif output_ext == '.avif':
                    cmd.extend(['-c:v', 'libaom-av1', '-still-picture', '1',
                                '-crf', str(max(0, 63 - int(int(quality) * 63 / 100)))])

            cmd.extend(['-y'])

            # For video/audio: use -progress for real-time progress
            duration = None
            use_progress = file_type in ("video", "audio") or is_video_to_audio
            if use_progress:
                duration = self._probe_duration(input_path)
                if duration:
                    cmd.extend(['-progress', 'pipe:1'])

            cmd.append(output_path)

            startupinfo = None
            if sys.platform == 'win32':
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

            process = subprocess.Popen(
                cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                universal_newlines=True, startupinfo=startupinfo,
            )
            self.current_process = process

            if duration and use_progress:
                # Read progress from stdout
                for line in process.stdout:
                    if self.cancel_requested:
                        process.terminate()
                        return False
                    m = re.search(r'out_time_us=(\d+)', line)
                    if m:
                        current_s = int(m.group(1)) / 1_000_000
                        file_frac = min(current_s / duration, 1.0)
                        overall = (file_index + file_frac) / total_files
                        self._set_progress(overall)
                process.wait()
            else:
                process.communicate()

            self.current_process = None
            return process.returncode == 0

        except Exception as e:
            self._set_status(f"Error: {Path(input_path).name}: {e}")
            self.current_process = None
            return False

    # ─────────────────────────────────────────────────────────────────────
    #  Batch conversion (runs in worker thread)
    # ─────────────────────────────────────────────────────────────────────
    def batch_convert(self) -> None:
        """Convert every file in ``self.input_files`` (runs in a worker thread)."""
        try:
            if not self.ffmpeg_available:
                self._set_status("Error: FFmpeg is required!")
                return

            output_dir = self.output_folder.get()
            file_type = self.current_file_type

            # Determine output extension
            if file_type == "video":
                ext = self.video_output_format.get()
                # If user picked the separator, fall back
                if ext == "── Audio Only ──":
                    ext = "mp4"
            elif file_type == "audio":
                ext = self.audio_output_format.get()
            else:
                ext = self.image_output_format.get()

            total = len(self.input_files)
            successful = 0

            for i, input_path in enumerate(self.input_files):
                if self.cancel_requested:
                    self._set_status(f"Cancelled. {successful}/{total} files converted.")
                    break

                name = Path(input_path).name
                self._set_status(f"[{i + 1}/{total}] Converting: {name}")
                self._set_progress(i / total)

                out_name = f"{Path(input_path).stem}_converted.{ext}"
                output_path = os.path.join(output_dir, out_name)

                counter = 1
                while os.path.exists(output_path):
                    output_path = os.path.join(
                        output_dir, f"{Path(input_path).stem}_converted_{counter}.{ext}")
                    counter += 1

                ok = self.convert_file(input_path, output_path, file_type,
                                       file_index=i, total_files=total)

                if self.cancel_requested:
                    # Clean up partial file
                    try:
                        if os.path.exists(output_path):
                            os.remove(output_path)
                    except Exception:
                        pass
                    self._set_status(f"Cancelled. {successful}/{total} files converted.")
                    break

                if ok:
                    successful += 1
                    self._set_status(f"[{i + 1}/{total}] ✓ {name}")
                else:
                    self._set_status(f"[{i + 1}/{total}] ✗ Failed: {name}")

            if not self.cancel_requested:
                self._set_progress(1.0)
                self._set_status(f"Done! {successful}/{total} files converted successfully.")
                if successful > 0:
                    self.after(200, self.show_completion_dialog)

        except Exception as e:
            self._set_status(f"Error: {e}")
        finally:
            self.is_converting = False
            self.cancel_requested = False
            self.current_process = None
            self._enable_convert_btn()

    # ─────────────────────────────────────────────────────────────────────
    #  Start / Cancel
    # ─────────────────────────────────────────────────────────────────────
    def start_conversion(self) -> None:
        """Validate inputs and launch :meth:`batch_convert` in a daemon thread."""
        if not self.ffmpeg_available:
            messagebox.showerror("FFmpeg Required",
                                 "FFmpeg is required for file conversion!")
            return
        if not self.input_files:
            messagebox.showwarning("No Input Files",
                                   "Please select files to convert!")
            return
        if self.is_converting:
            messagebox.showinfo("In Progress",
                                "Please wait for the current conversion to finish!")
            return

        output_dir = self.output_folder.get()
        if not os.path.exists(output_dir):
            try:
                os.makedirs(output_dir)
            except Exception:
                messagebox.showerror("Invalid Folder",
                                     "Please select a valid output folder!")
                return

        self.is_converting = True
        self.cancel_requested = False
        self.progress_bar.set(0)
        self.add_recent_folder(output_dir)

        # Switch button to Cancel mode
        self.convert_btn.configure(
            text="CANCEL", command=self.request_cancel,
            fg_color="#8b2e2e", hover_color="#b33c3c",
        )

        threading.Thread(target=self.batch_convert, daemon=True).start()


if __name__ == "__main__":
    app = FileConverterApp()
    app.mainloop()