"""FFmpeg conversion engine; independent of Tk so jobs can be tested headlessly."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
import json
import math
import os
from pathlib import Path
import queue
import shutil
import subprocess
import sys
import tempfile
import threading
import time
from typing import Callable

AUDIO_FORMATS = {"mp3", "m4a", "wav", "flac", "ogg", "aac", "opus", "wma", "aiff"}


def find_binary(name: str, base_path: str) -> str | None:
    """Respect explicit overrides, then native bundled binaries, then PATH."""
    override = os.environ.get(f"{name.upper()}_BINARY")
    if override:
        return shutil.which(override)
    filename = name + (".exe" if sys.platform == "win32" else "")
    for folder in (Path(base_path), Path(base_path) / "bin", Path(base_path) / "ffmpeg"):
        candidate = folder / filename
        if candidate.is_file() and os.access(candidate, os.X_OK):
            return str(candidate)
    return shutil.which(name)


@dataclass(frozen=True)
class Settings:
    output_format: str
    video_quality: str = "High"
    speed: str = "Fast"
    audio_bitrate: str = "192"
    image_quality: int = 95
    copy_streams: bool = False


@dataclass(frozen=True)
class Progress:
    phase: str
    elapsed: float
    duration: float | None = None
    media_seconds: float = 0
    speed: float | None = None
    fps: float | None = None
    size_bytes: int | None = None

    @property
    def fraction(self) -> float | None:
        if self.phase == "Complete":
            return 1.0
        if not self.duration:
            return None
        # Muxers may still be flushing/indexing after FFmpeg reports progress=end.
        return min(0.99, max(0, self.media_seconds / self.duration))

    @property
    def eta(self) -> float | None:
        if self.phase != "Converting" or not self.duration or not self.speed:
            return None
        return max(0, self.duration - self.media_seconds) / self.speed


@dataclass(frozen=True)
class Result:
    output: str | None = None
    error: str | None = None
    cancelled: bool = False


def positive_number(value: str | None) -> float | None:
    try:
        number = float(value)
        return number if math.isfinite(number) and number > 0 else None
    except (TypeError, ValueError):
        return None


def parse_progress(fields: dict[str, str], duration: float | None, elapsed: float) -> Progress:
    seconds = None
    # Both out_time_us and the older out_time_ms are microseconds in FFmpeg.
    for key in ("out_time_us", "out_time_ms"):
        value = positive_number(fields.get(key))
        if value is not None:
            seconds = value / 1_000_000
            break
    if seconds is None:
        try:
            h, m, s = fields.get("out_time", "0:0:0").split(":")
            seconds = positive_number(str(float(h) * 3600 + float(m) * 60 + float(s)))
        except ValueError:
            seconds = None
    size = positive_number(fields.get("total_size"))
    return Progress(
        "Finalizing" if fields.get("progress") == "end" else "Converting",
        elapsed, duration, seconds or 0,
        positive_number(fields.get("speed", "").rstrip("x")),
        positive_number(fields.get("fps")), int(size) if size else None,
    )


def audio_args(ext: str, bitrate: str) -> list[str]:
    codecs = {"mp3": "libmp3lame", "aac": "aac", "m4a": "aac", "opus": "libopus",
              "ogg": "libvorbis", "wav": "pcm_s16le", "flac": "flac",
              "aiff": "pcm_s16be", "wma": "wmav2"}
    args = ["-c:a", codecs[ext]]
    if ext not in {"wav", "flac", "aiff"}:
        args += ["-b:a", f"{bitrate}k"]
    return args


def build_command(binary: str, source: str, target: str, kind: str, settings: Settings) -> list[str]:
    """Choose codecs explicitly; container defaults do not share x264 options."""
    ext = settings.output_format
    cmd = [binary, "-hide_banner", "-nostdin", "-loglevel", "warning", "-nostats",
           "-stats_period", "0.25", "-progress", "pipe:1", "-i", source]
    if kind != "image" and ext in AUDIO_FORMATS:
        cmd += ["-map", "0:a:0", "-vn"]
        cmd += ["-c:a", "copy"] if settings.copy_streams else audio_args(ext, settings.audio_bitrate)
    elif kind == "video":
        if settings.copy_streams:
            # Keep all video/audio streams; subtitles/data can be container-specific.
            cmd += ["-map", "0:V", "-map", "0:a?", "-c", "copy"]
        else:
            cmd += ["-map", "0:V:0", "-map", "0:a:0?"]
            crf = {"High": "18", "Medium": "23", "Low": "28"}[settings.video_quality]
            q = {"High": "3", "Medium": "5", "Low": "8"}[settings.video_quality]
            if ext == "webm":
                cmd += ["-c:v", "libvpx-vp9", "-crf", {"High": "24", "Medium": "32", "Low": "40"}[settings.video_quality],
                        "-b:v", "0", "-deadline", "good", "-cpu-used",
                        {"Fast": "4", "Balanced": "2", "Smaller files": "1"}[settings.speed],
                        "-row-mt", "1", "-c:a", "libopus", "-b:a", "192k"]
            elif ext == "ogv":
                cmd += ["-c:v", "libtheora", "-q:v", {"High": "8", "Medium": "5", "Low": "3"}[settings.video_quality],
                        "-c:a", "libvorbis", "-q:a", "6"]
            elif ext in {"avi", "wmv", "flv"}:
                video, audio = {"avi": ("mpeg4", "libmp3lame"), "wmv": ("wmv2", "wmav2"),
                                "flv": ("flv", "libmp3lame")}[ext]
                cmd += ["-c:v", video, "-q:v", q, "-c:a", audio, "-b:a", "192k"]
            else:
                cmd += ["-c:v", "libx264", "-preset",
                        {"Fast": "veryfast", "Balanced": "medium", "Smaller files": "slow"}[settings.speed],
                        "-crf", crf, "-c:a", "aac", "-b:a", "192k"]
            cmd += ["-pix_fmt", "yuv420p"]
        if ext in {"mp4", "mov", "m4v"}:
            cmd += ["-movflags", "+faststart"]
        if ext == "m4v":
            cmd += ["-f", "mp4"]  # FFmpeg otherwise selects raw MPEG-4 video.
        elif ext == "ts":
            cmd += ["-f", "mpegts"]
    elif kind == "audio":
        raise ValueError("Select an audio output format for a batch containing audio files.")
    else:
        quality = settings.image_quality
        cmd += ["-an"]
        if ext not in {"gif", "webp"}:
            cmd += ["-frames:v", "1"]
        if ext == "jpg":
            cmd += ["-q:v", str(max(1, round((100 - quality) / 4)))]
        elif ext == "png":
            cmd += ["-compression_level", "6"]
        elif ext == "webp":
            cmd += ["-quality", str(quality)]
        elif ext == "ico":
            cmd += ["-vf", "scale=256:256:force_original_aspect_ratio=decrease", "-c:v", "bmp"]
        elif ext == "avif":
            cmd += ["-c:v", "libaom-av1", "-still-picture", "1", "-cpu-used", "6",
                    "-row-mt", "1", "-crf", str(round(63 * (100 - quality) / 100))]
    return cmd + ["-y", target]


def stop_process(process: subprocess.Popen) -> None:
    """Reap a child even if it ignores a graceful termination request."""
    if process.poll() is None:
        try:
            process.terminate()
            process.wait(timeout=2)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()
        except ProcessLookupError:
            process.wait()


def process_options() -> dict:
    return {"creationflags": subprocess.CREATE_NO_WINDOW} if sys.platform == "win32" else {}


class Converter:
    def __init__(self, ffmpeg: str, ffprobe: str | None):
        self.ffmpeg = ffmpeg
        self.ffprobe = ffprobe

    def probe_duration(self, source: str, cancel: threading.Event,
                       report: Callable[[Progress], None]) -> float | None:
        if not self.ffprobe or cancel.is_set():
            return None
        started = time.monotonic()
        try:
            process = subprocess.Popen(
                [self.ffprobe, "-v", "error", "-show_entries", "format=duration:stream=duration",
                 "-of", "json", source], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                stdin=subprocess.DEVNULL, text=True, encoding="utf-8", errors="replace", **process_options())
        except OSError:
            return None
        try:
            while not cancel.is_set() and time.monotonic() - started < 10:
                report(Progress("Reading media", time.monotonic() - started))
                try:
                    output, _ = process.communicate(timeout=0.25)
                    if process.returncode:
                        return None
                    data = json.loads(output)
                    duration = positive_number(data.get("format", {}).get("duration"))
                    durations = [positive_number(s.get("duration")) for s in data.get("streams", [])]
                    return duration or max((d for d in durations if d), default=None)
                except subprocess.TimeoutExpired:
                    continue
                except (ValueError, TypeError):
                    return None
            return None
        finally:
            stop_process(process)
            process.stdout.close()

    def convert(self, source: str, output_dir: str, kind: str, settings: Settings,
                cancel: threading.Event, report: Callable[[Progress], None]) -> Result:
        """Drain both pipes continuously, keep a bounded error tail, publish only success."""
        temp_path = None
        process = None
        readers = []
        errors: deque[str] = deque(maxlen=60)
        try:
            if cancel.is_set():
                return Result(cancelled=True)
            duration = self.probe_duration(source, cancel, report) if kind != "image" else None
            if cancel.is_set():
                return Result(cancelled=True)
            fd, temp_path = tempfile.mkstemp(prefix=".lace-converting-", suffix=f".{settings.output_format}", dir=output_dir)
            os.close(fd)
            cmd = build_command(self.ffmpeg, source, temp_path, kind, settings)
            process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                       stdin=subprocess.DEVNULL, text=True, encoding="utf-8",
                                       errors="replace", **process_options())
            packets: queue.Queue[dict[str, str]] = queue.Queue(maxsize=32)
            stdout_done = threading.Event()

            def read_progress():
                fields = {}
                try:
                    for line in process.stdout:
                        key, sep, value = line.strip().partition("=")
                        if sep:
                            fields[key] = value
                            if key == "progress":
                                try:
                                    packets.put_nowait(fields)
                                except queue.Full:
                                    pass  # The next update will catch up; never block FFmpeg.
                                fields = {}
                finally:
                    stdout_done.set()

            def read_errors():
                for line in process.stderr:
                    errors.append(line[-2000:].rstrip())

            readers = [threading.Thread(target=read_progress, daemon=True),
                       threading.Thread(target=read_errors, daemon=True)]
            for reader in readers:
                reader.start()
            started = time.monotonic()
            fields = {}
            report(Progress("Converting", 0, duration))
            while True:
                if cancel.is_set():
                    return Result(cancelled=True)
                try:
                    fields = packets.get(timeout=0.2)
                except queue.Empty:
                    pass
                report(parse_progress(fields, duration, time.monotonic() - started))
                if process.poll() is not None and stdout_done.is_set() and packets.empty():
                    break
            for reader in readers:
                reader.join()
            if process.returncode:
                return Result(error="\n".join(errors) or f"FFmpeg exited with code {process.returncode}.")
            if not Path(temp_path).stat().st_size:
                return Result(error="FFmpeg produced an empty output file.")
            if cancel.is_set():
                return Result(cancelled=True)
            output = self._publish(temp_path, source, output_dir, settings.output_format)
            report(Progress("Complete", time.monotonic() - started, duration, duration or 0))
            return Result(output=str(output))
        except Exception as exc:
            return Result(error=str(exc), cancelled=cancel.is_set())
        finally:
            if process is not None:
                stop_process(process)
                for reader in readers:
                    reader.join(timeout=3)
                process.stdout.close()
                process.stderr.close()
            if temp_path:
                Path(temp_path).unlink(missing_ok=True)

    @staticmethod
    def _publish(temp_path: str, source: str, output_dir: str, ext: str) -> Path:
        """Reserve a unique name atomically so two jobs cannot overwrite each other."""
        stem = Path(source).stem + "_converted"
        counter = 0
        while True:
            suffix = f"_{counter}" if counter else ""
            target = Path(output_dir) / f"{stem}{suffix}.{ext}"
            try:
                fd = os.open(target, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o666)
            except FileExistsError:
                counter += 1
                continue
            os.close(fd)
            try:
                os.replace(temp_path, target)
            except OSError:
                target.unlink(missing_ok=True)
                raise
            return target


def format_time(seconds: float | None) -> str:
    if seconds is None:
        return "Estimating…"
    seconds = max(0, int(seconds))
    hours, remainder = divmod(seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{hours:d}:{minutes:02d}:{seconds:02d}" if hours else f"{minutes:d}:{seconds:02d}"
