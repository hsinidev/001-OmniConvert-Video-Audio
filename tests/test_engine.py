"""
Engine Verification Tests for OmniConvert Video & Audio
"""

import sys
import os
import queue
import time
import subprocess

# Add project root path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.binary_resolver import BinaryResolver
from engine.hw_accel import HWAccelProber
from engine.ffprobe_parser import FFprobeParser
from engine.telemetry import TelemetryParser
from engine.transcode_worker import TranscodeWorker, TranscodeJob


def test_binary_resolver():
    print("Testing BinaryResolver...")
    resolver = BinaryResolver()
    print(f"Resolved FFmpeg: {resolver.ffmpeg_path}")
    print(f"Resolved FFprobe: {resolver.ffprobe_path}")
    valid = resolver.validate_binaries()
    print(f"Validation results: {valid}")
    assert valid.get("ffmpeg") is True, "FFmpeg validation failed!"
    assert valid.get("ffprobe") is True, "FFprobe validation failed!"
    print("BinaryResolver PASS!")


def test_hw_accel():
    print("\nTesting HWAccelProber...")
    resolver = BinaryResolver()
    prober = HWAccelProber(resolver.ffmpeg_path)
    print(f"Supported Hardware Acceleration: {prober.supported_hardware}")
    enc = prober.get_video_encoder("CPU Software", "h264")
    print(f"CPU h264 encoder: {enc}")
    assert enc == "libx264"
    print("HWAccelProber PASS!")


def test_telemetry_parser():
    print("\nTesting TelemetryParser...")
    parser = TelemetryParser(total_duration_seconds=100.0)
    line1 = "frame=  120 fps= 30.5 q=28.0 size=    1024kB time=00:00:10.00 bitrate= 838.9kbits/s speed= 2.5x"
    res = parser.parse_line(line1)
    print(f"Parsed Telemetry: {res}")
    assert res is not None
    assert abs(res["progress_percent"] - 10.0) < 0.1
    assert abs(res["speed"] - 2.5) < 0.01
    assert abs(res["fps"] - 30.5) < 0.01
    print("TelemetryParser PASS!")


def test_synthetic_transcode():
    print("\nTesting Synthetic FFmpeg Transcode...")
    resolver = BinaryResolver()
    ffmpeg_path = resolver.ffmpeg_path
    
    # Generate 2 second synthetic test video file using ffmpeg
    test_dir = os.path.dirname(os.path.abspath(__file__))
    input_test_mp4 = os.path.join(test_dir, "test_input.mp4")
    output_dir = os.path.join(test_dir, "test_output")
    os.makedirs(output_dir, exist_ok=True)

    cmd = [
        ffmpeg_path,
        "-y",
        "-f", "lavfi",
        "-i", "testsrc=duration=2:size=640x360:rate=24",
        "-f", "lavfi",
        "-i", "sine=frequency=440:duration=2",
        "-c:v", "libx264",
        "-c:a", "aac",
        input_test_mp4
    ]
    creationflags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
    subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, creationflags=creationflags)
    
    assert os.path.exists(input_test_mp4), "Failed to generate synthetic test media file!"
    print(f"Generated synthetic test input: {input_test_mp4}")

    # Test FFprobe parser on input
    ffprobe = FFprobeParser(resolver.ffprobe_path)
    meta = ffprobe.probe_file(input_test_mp4)
    print(f"Probed Metadata: {meta}")
    assert meta["valid"] is True
    assert meta["duration"] > 1.5

    # Test TranscodeWorker
    event_q = queue.Queue()
    job = TranscodeJob(
        job_id="test_1",
        input_path=input_test_mp4,
        output_dir=output_dir,
        output_format="mp4",
        hw_accel="CPU Software",
        crf=23,
        preset="ultrafast",
        resolution="Original",
        audio_bitrate="128k",
        total_duration=meta["duration"]
    )

    worker = TranscodeWorker(ffmpeg_path, job, event_q)
    worker.start()
    worker.join(timeout=15)

    events = []
    while not event_q.empty():
        e = event_q.get()
        events.append(e)
        if e.get("type") in ["LOG", "ERROR"]:
            print(f"EVENT {e.get('type')}: {e.get('data')}")

    statuses = [e for e in events if e.get("type") == "STATUS"]
    print(f"Captured Status Events: {[s['data']['status'] for s in statuses]}")
    assert any(s["data"]["status"] == "Done" for s in statuses), "Transcode did not complete successfully!"
    assert os.path.exists(job.output_path), "Converted output file missing!"
    print(f"Transcode Worker PASS! Output created: {job.output_path}")

    # Cleanup test files
    try:
        os.remove(input_test_mp4)
        if os.path.exists(job.output_path):
            os.remove(job.output_path)
        os.rmdir(output_dir)
    except Exception:
        pass


if __name__ == "__main__":
    test_binary_resolver()
    test_hw_accel()
    test_telemetry_parser()
    test_synthetic_transcode()
    print("\nALL ENGINE TESTS PASSED SUCCESSFULLY!")
