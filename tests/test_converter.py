import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

from converter import Converter, Progress, Settings, build_command, find_binary, parse_progress


class ProgressTests(unittest.TestCase):
    def test_microseconds_eta_and_finalization(self):
        progress = parse_progress({"out_time_us": "25000000", "speed": "2.5x", "fps": "60",
                                   "total_size": "1048576", "progress": "continue"}, 100, 10)
        self.assertEqual(progress.fraction, 0.25)
        self.assertEqual(progress.eta, 30)
        self.assertEqual(progress.size_bytes, 1048576)
        end = parse_progress({"out_time_us": "100000000", "progress": "end"}, 100, 10)
        self.assertEqual(end.fraction, 0.99)
        self.assertIsNone(end.eta)
        self.assertEqual(Progress("Complete", 10, 100).fraction, 1)

    def test_unavailable_and_invalid_values(self):
        progress = parse_progress({"out_time_us": "-100", "out_time": "N/A", "speed": "NaNx",
                                   "fps": "inf", "total_size": "N/A"}, None, 20)
        self.assertIsNone(progress.fraction)
        self.assertIsNone(progress.eta)
        self.assertIsNone(progress.fps)
        self.assertEqual(progress.media_seconds, 0)

    def test_older_progress_keys(self):
        self.assertEqual(parse_progress({"out_time_ms": "12000000"}, 24, 1).fraction, 0.5)
        self.assertEqual(parse_progress({"out_time": "01:00:10.500"}, None, 1).media_seconds, 3610.5)

    def test_native_binary_selection(self):
        with tempfile.TemporaryDirectory() as folder, patch.dict(os.environ, {}, clear=True):
            win_binary = Path(folder) / "ffmpeg.exe"
            win_binary.touch()
            win_binary.chmod(0o755)
            with patch("converter.sys.platform", "linux"), patch("converter.shutil.which", return_value=None):
                self.assertIsNone(find_binary("ffmpeg", folder))

    def test_quality_does_not_force_slow_preset(self):
        fast = build_command("ffmpeg", "a.mp4", "b.mp4", "video", Settings("mp4"))
        slow = build_command("ffmpeg", "a.mp4", "b.mp4", "video", Settings("mp4", speed="Smaller files"))
        self.assertEqual(fast[fast.index("-crf") + 1], slow[slow.index("-crf") + 1])
        self.assertEqual(fast[fast.index("-preset") + 1], "veryfast")


class ProcessTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="lace-test-")
        self.addCleanup(self.temp.cleanup)
        self.folder = Path(self.temp.name)
        self.source = self.folder / "source with spaces ü.mp4"
        self.source.write_bytes(b"original")

    def fake_program(self, body):
        script = self.folder / "fake-ffmpeg"
        script.write_text(f"#!{sys.executable}\nimport sys, time, pathlib, signal\n" + body)
        script.chmod(0o755)
        return str(script)

    def convert(self, binary, cancel=None, report=None, probe=None):
        return Converter(binary, probe).convert(str(self.source), str(self.folder), "video", Settings("mp4"),
                                               cancel or threading.Event(), report or (lambda p: None))

    def test_stderr_flood_does_not_block_progress(self):
        binary = self.fake_program('''
for i in range(6000):
    print("diagnostic " + "x" * 200, file=sys.stderr)
print("out_time_us=1000000\\nspeed=2x\\nprogress=end", flush=True)
pathlib.Path(sys.argv[-1]).write_bytes(b"success")
''')
        reports = []
        result = self.convert(binary, report=reports.append)
        self.assertIsNone(result.error)
        self.assertEqual(Path(result.output).read_bytes(), b"success")
        self.assertTrue(any(p.speed == 2 for p in reports))
        self.assertFalse(list(self.folder.glob(".lace-converting-*")))

    def test_failure_retains_diagnostics_and_removes_partial(self):
        binary = self.fake_program('''
pathlib.Path(sys.argv[-1]).write_bytes(b"partial")
print("Encoder unavailable", file=sys.stderr)
sys.exit(1)
''')
        result = self.convert(binary)
        self.assertIn("Encoder unavailable", result.error)
        self.assertFalse(list(self.folder.glob("*converted*")))
        self.assertFalse(list(self.folder.glob(".lace-converting-*")))
        self.assertEqual(self.source.read_bytes(), b"original")

    def test_cancel_silent_child_that_ignores_terminate(self):
        if sys.platform == "win32":
            self.skipTest("POSIX signal behavior")
        binary = self.fake_program('''
signal.signal(signal.SIGTERM, signal.SIG_IGN)
pathlib.Path(sys.argv[-1]).write_bytes(b"partial")
time.sleep(30)
''')
        cancel = threading.Event()
        timer = threading.Timer(0.5, cancel.set)
        timer.start()
        self.addCleanup(timer.cancel)
        started = time.monotonic()
        result = self.convert(binary, cancel)
        self.assertTrue(result.cancelled)
        self.assertLess(time.monotonic() - started, 5)
        self.assertFalse(list(self.folder.glob(".lace-converting-*")))

    def test_cancel_during_probe(self):
        binary = self.fake_program("time.sleep(30)\n")
        cancel = threading.Event()
        result = self.convert(binary, cancel, lambda p: cancel.set(), probe=binary)
        self.assertTrue(result.cancelled)
        self.assertFalse(list(self.folder.glob(".lace-converting-*")))

    def test_unknown_duration_still_reports_activity(self):
        binary = self.fake_program('''
time.sleep(0.8)
pathlib.Path(sys.argv[-1]).write_bytes(b"output")
''')
        reports = []
        result = self.convert(binary, report=reports.append)
        self.assertIsNotNone(result.output)
        self.assertTrue(any(p.elapsed > 0.3 and p.fraction is None for p in reports))

    def test_existing_output_is_preserved(self):
        binary = self.fake_program('pathlib.Path(sys.argv[-1]).write_bytes(b"new")\n')
        existing = self.folder / (self.source.stem + "_converted.mp4")
        existing.write_bytes(b"keep")
        result = self.convert(binary)
        self.assertEqual(existing.read_bytes(), b"keep")
        self.assertTrue(result.output.endswith("_converted_1.mp4"))

    def test_bad_probe_falls_back_to_unknown_duration(self):
        binary = self.fake_program('pathlib.Path(sys.argv[-1]).write_bytes(b"new")\n')
        probe = self.folder / "probe"
        probe.write_text(f'#!{sys.executable}\nprint(\'{{"format": {{"duration": "NaN"}}}}\')\n')
        probe.chmod(0o755)
        self.assertIsNotNone(self.convert(binary, probe=str(probe)).output)


@unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe"), "FFmpeg and ffprobe required")
class FFmpegIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix="lace-media-")
        cls.folder = Path(cls.temp.name)
        cls.video = cls.folder / "video with spaces ü.mp4"
        cls.audio = cls.folder / "sound.wav"
        cls.image = cls.folder / "picture.png"
        cls.engine = Converter(shutil.which("ffmpeg"), shutil.which("ffprobe"))
        base = [cls.engine.ffmpeg, "-hide_banner", "-loglevel", "error", "-y"]
        subprocess.run(base + ["-f", "lavfi", "-i", "testsrc2=size=320x180:rate=24", "-f", "lavfi", "-i", "sine=frequency=440",
                               "-t", "1.2", "-c:v", "libx264", "-preset", "ultrafast", "-c:a", "aac", str(cls.video)], check=True)
        subprocess.run(base + ["-i", str(cls.video), "-vn", str(cls.audio)], check=True)
        subprocess.run(base + ["-i", str(cls.video), "-frames:v", "1", str(cls.image)], check=True)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def run_conversion(self, source, kind, ext, **kwargs):
        events = []
        result = self.engine.convert(str(source), str(self.folder), kind, Settings(ext, **kwargs), threading.Event(), events.append)
        self.assertIsNone(result.error, f"{ext}: {result.error}")
        self.assertTrue(Path(result.output).stat().st_size > 0)
        self.assertEqual(events[-1].fraction, 1)
        probe = subprocess.check_output([self.engine.ffprobe, "-v", "error", "-show_streams", "-of", "json", result.output], text=True)
        streams = json.loads(probe)["streams"]
        self.assertTrue(streams, f"No streams in {ext} output")
        # Decode the result to catch corrupt/truncated files, not just a valid header.
        subprocess.run([self.engine.ffmpeg, "-v", "error", "-i", result.output, "-f", "null", "-"], check=True,
                       stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        return streams

    def test_video_containers(self):
        for ext in ("mp4", "mkv", "avi", "mov", "webm", "flv", "wmv", "m4v", "ts", "ogv"):
            with self.subTest(ext=ext):
                streams = self.run_conversion(self.video, "video", ext)
                self.assertIn("video", [s["codec_type"] for s in streams])
                self.assertIn("audio", [s["codec_type"] for s in streams])

    def test_audio_formats_and_extraction(self):
        for ext in ("mp3", "m4a", "wav", "flac", "ogg", "aac", "opus", "wma", "aiff"):
            with self.subTest(ext=ext):
                self.run_conversion(self.audio, "audio", ext)
        streams = self.run_conversion(self.video, "video", "mp3")
        self.assertEqual([s["codec_type"] for s in streams], ["audio"])

    def test_image_formats(self):
        for ext in ("jpg", "png", "webp", "bmp", "gif", "tiff", "ico", "avif"):
            with self.subTest(ext=ext):
                self.run_conversion(self.image, "image", ext)

    def test_copy_streams_and_incompatible_container(self):
        streams = self.run_conversion(self.video, "video", "mkv", copy_streams=True)
        self.assertEqual([s["codec_name"] for s in streams], ["h264", "aac"])
        self.run_conversion(self.video, "video", "m4a", copy_streams=True)
        result = self.engine.convert(str(self.video), str(self.folder), "video", Settings("webm", copy_streams=True),
                                     threading.Event(), lambda p: None)
        self.assertIsNotNone(result.error)
        self.assertFalse(list(self.folder.glob(".lace-converting-*")))


if __name__ == "__main__":
    unittest.main()
