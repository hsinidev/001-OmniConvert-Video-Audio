🛠️ Required Technical Skills & Competencies: OmniConvert Video & Audio

Project ID: 001

Category: Media Engine & File Converters

Target OS: Windows 10 / Windows 11 (x64)

Core Stack: Python 3.10+, CustomTkinter, TkinterDnD2, FFmpeg Subprocesses, threading, queue.Queue

🎯 Technical Competencies & Mastery Matrix

This document defines the core engineering capabilities, architectural patterns, and domain expertise required to build, maintain, and package the OmniConvert Video & Audio production engine.

1. Core Python 3.10+ & Desktop UI Frameworks

[ ] Advanced Object-Oriented Python:

Mastery of class inheritance, encapsulation, custom exceptions, and type hinting (typing.Optional, typing.Callable, typing.Dict).

Strict utilization of context managers (with statements) for safe file I/O operations and process lifecycle handling.

[ ] Modern GUI Engineering (CustomTkinter):

Construction of responsive layout grids with dynamic resizing weights (grid_columnconfigure, grid_rowconfigure).

Custom widget encapsulation (building compound widgets like FileCard, DropZone, and ControlPanel).

Dynamic visual theme token management (Light/Dark mode switching via CTk JSON theme files).

[ ] Native Drag-and-Drop Integration (TkinterDnD2):

Binding native OS drop events (<<Drop></drop>>) to CustomTkinter root frames.

Parsing drop payloads containing single or multiple Windows path strings (including space-delimited and quoted path sanitization).

2. Media Engineering & FFmpeg Core Pipeline

[ ] FFmpeg Subprocess Orchestration:

Direct execution of static ffmpeg.exe and ffprobe.exe binaries using subprocess.Popen.

Application of process flags: creationflags=subprocess.CREATE_NO_WINDOW to prevent command prompt flashes on Windows.

Construction of non-blocking I/O pipes for stdout and stderr streams.

[ ] FFprobe JSON Metadata Extraction:

Construction of structured probe commands:

ffprobe -v quiet -print_format json -show_format -show_streams <input_path>

Deserialization and parsing of JSON outputs to extract media stream metadata:

Duration in fractional seconds ($\text{Total Duration}$).

Resolution ($W \times H$), Aspect Ratio, Frame Rate ($FPS$).

Video Codec (h264, hevc, vp9, mpeg4) and Audio Codec (aac, mp3, flac, pcm_s16le).

[ ] FFmpeg Encoding Command Formulation:

Dynamic assembly of complex command arrays for multi-format transcoding:

CRF Quality Control: -crf 18 (Near Lossless) to -crf 28 (High Compression).

Preset Control: -preset ultrafast to -preset veryslow.

Resolution Scaling: -vf scale=1920:1080 (with aspect ratio preservation via -vf scale=1920:-2).

Audio Bitrate Allocation: -b:a 192k, -b:a 320k for lossy containers, -c:a flac or -c:a pcm_s16le for lossless.

3. Hardware Acceleration & Transcoding Optimization

[ ] GPU Encoder Auto-Probing:

Querying FFmpeg encoder capability matrices at runtime (ffmpeg -hide_banner -encoders).

Detection and configuration of vendor-specific hardware acceleration codecs:

NVIDIA CUDA / NVENC: h264_nvenc, hevc_nvenc.

AMD AMF: h264_amf, hevc_amf.

Intel QuickSync (QSV): h264_qsv, hevc_qsv.

[ ] Encoder Fallback Logic:

Graceful fallback to software CPU encoders (libx264, libx265, libvpx-vp9) if hardware encoder initialization fails due to driver incompatibility or missing hardware.

4. Concurrency, Telemetry Parsing & Asynchronous Architecture

[ ] Event-Driven Non-Blocking Architecture:

Strict separation between the main UI thread (60 FPS rendering loop) and media processing threads.

Implementation of worker threads (threading.Thread) for non-blocking file conversion and probing.

[ ] Thread-Safe Queue Messaging (queue.Queue):

Pushing structured event dictionaries (STATUS, PROGRESS, LOG, COMPLETED, ERROR) from background workers.

Implementing UI event polling loops via root.after(50, self.poll_queue) operating at a 20 Hz update frequency.

[ ] Real-Time Telemetry Parsing Engine:

Constructing compiled regular expressions (re.compile) to parse FFmpeg stderr stream updates line-by-line:

Timestamp Matcher: time=(\d{2}):(\d{2}):(\d{2})\.(\d{2})

Frame Rate Matcher: fps=\s*([0-9.]+)

Speed Multiplier Matcher: speed=\s*([0-9.]+)x

Real-time mathematical calculation of percentage completion:

$$
\text{Progress \%} = \left( \frac{\text{Current Seconds}}{\text{Total Duration Seconds}} \right) \times 100
$$

Real-time estimation of Time Remaining (ETA) using current speed factor and remaining duration.

5. Systems Programming, OS Resilience & Lifecycle Control

[ ] Dynamic External Binary Auto-Resolution Engine:

Implementing a 5-tier resolution hierarchy to locate ffmpeg.exe and ffprobe.exe:

PyInstaller frozen runtime root (sys._MEIPASS).

Working script directory (os.path.dirname(__file__)).

Application relative directory (./bin/).

System environment PATH (shutil.which).

Interactive UI file selector fallback dialog.

[ ] Process Group Safety & Cancellation Management:

Spawning subprocesses within an isolated process group (subprocess.CREATE_NEW_PROCESS_GROUP).

Executing clean job cancellations using targeted process group termination (taskkill /F /PID <pid></pid> /T) to guarantee zero orphan ffmpeg.exe instances.

Automatic identification and cleanup of temporary or corrupted .tmp target output files upon job abort or unexpected failure.

[ ] Windows Path & Character Sanitization:

Robust handling of non-ASCII characters, spaces, and special symbols in file paths using long path syntax (\\?\) where appropriate.

Defense against destination file overwrites and disk space pre-checks.

6. Executable Packaging, Build Engineering & Delivery

[ ] PyInstaller Bundling (OmniConvert.spec):

Crafting custom PyInstaller specifications with explicit binary embedding and asset inclusion (datas and binaries).

Utilizing PyInstaller.utils.hooks.collect_all to collect hidden imports and dynamic link libraries (DLLs) for customtkinter, tkinterdnd2, and PIL.

Configuring single-file (--onefile) or single-folder bundle execution with custom icon assets (.ico).

[ ] Standalone System Verification:

Testing binary releases on clean Windows 10 and Windows 11 instances lacking pre-installed Python interpreters or system FFmpeg installations.
