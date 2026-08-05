# 🚀 Production Implementation Roadmap: OmniConvert Video & Audio

> **Project ID** : `001`
>
> **Category** : Media Engine & File Converters
>
> **Target OS** : Windows 10 / Windows 11 (x64)
>
> **Core Stack** : Python 3.10+, CustomTkinter, TkinterDnD2, FFmpeg Subprocesses, `threading`, `queue.Queue`

## 📌 Project Overview

OmniConvert is a high-performance desktop application for batch audio and video conversion. Powered by CustomTkinter for modern UI rendering and an embedded FFmpeg binary core for media encoding, it provides real-time encoding telemetry, hardware-accelerated encoding detection (NVENC, AMF, QSV), granular quality control (CRF/presets/bitrates), and zero UI freezes via asynchronous thread messaging queues.

## 🗓️ Implementation Phases & Task Breakdown

### Phase 1: Environment Setup & Project Foundation

* [ ] **Virtual Environment Setup**
  * Create Python 3.10+ virtual environment (`python -m venv venv`).
  * Configure `requirements.txt` with locked versions (`customtkinter>=5.2.0`, `tkinterdnd2-universal>=2.0.0`, `Pillow>=10.0.0`, `pyinstaller>=6.0.0`).
* [ ] **Directory Architecture Initializer**
  * Scaffold project folder structure (`gui/components`, `gui/styles`, `engine/`, `utils/`, `bin/`, `assets/`).
  * Create package initialization files (`__init__.py`) for clear namespace resolution.
* [ ] **Binary & Dependency Staging**
  * Place static Windows builds of `ffmpeg.exe` and `ffprobe.exe` (v6.0+) inside `./bin/`.
  * Add standard `.gitignore` rules for virtual environment, build outputs (`dist/`, `build/`), and PyInstaller artifacts.

### Phase 2: Core Processing Engine & Telemetry Pipeline

* [ ] **Binary Auto-Resolver (`engine/binary_resolver.py`)**
  * Implement a 5-stage discovery hierarchy: PyInstaller runtime `sys._MEIPASS` $\rightarrow$ Script Working Directory $\rightarrow$ Application `./bin/` subfolder $\rightarrow$ System Environment `PATH` (`shutil.which`) $\rightarrow$ User File Selector Fallback Dialog.
  * Implement dynamic binary validation functions (`check_executable_version`).
* [ ] **Hardware Acceleration Detector (`engine/hw_accel.py`)**
  * Build background probe commands to query FFmpeg `-encoders` for `nvenc`, `amf`, and `qsv`.
  * Return structured dict mapping hardware availability to target encoder strings (`h264_nvenc`, `hevc_nvenc`, `h264_amf`, etc.).
* [ ] **FFprobe Metadata Extractor (`engine/ffprobe_parser.py`)**
  * Execute non-blocking `ffprobe` processes with `-print_format json -show_format -show_streams`.
  * Extract media duration, video stream resolution ($W \times H$), frame rate ($FPS$), video codec, audio sample rate, and channel configuration.
* [ ] **Continuous Telemetry & Subprocess Engine (`engine/telemetry.py` & `engine/transcode_worker.py`)**
  * Build regex matchers to capture real-time stderr streams (`time=`, `fps=`, `speed=`, `frame=`).
  * Implement `TranscodeWorker(threading.Thread)` with isolated `subprocess.Popen(creationflags=subprocess.CREATE_NO_WINDOW)`.
  * Compute normalized progress percentages ($0.0 - 100.0\%$), current timestamps, estimated time remaining (ETA), and speed multipliers (e.g., `2.4x`).
  * Enqueue structured event payloads into a thread-safe `queue.Queue`.

### Phase 3: Modern Desktop GUI & Reactive Controls

* [ ] **Main Application Frame & Theme Engine (`gui/app.py`)**
  * Instantiate CustomTkinter root window with responsive layout grids.
  * Integrate theme switching subsystem (Dark/Light visual tokens via `gui/styles/theme.json`).
  * Implement non-blocking `poll_event_queue()` loop using `root.after(50, self.poll_event_queue)` operating at 20 Hz.
* [ ] **Drag-and-Drop Batch File Queue (`gui/components/drop_zone.py` & `file_card.py`)**
  * Integrate `TkinterDnD2` file drop listener to handle single and multiple file drop events.
  * Build custom file item cards featuring dynamic status indicators ( *Pending* ,  *Converting* ,  *Done* ,  *Error* ), file metadata labels, and dedicated progress bars.
  * Provide controls to reorder or remove individual items from the queue.
* [ ] **Encoding Control Panel (`gui/components/control_panel.py`)**
  * **Output Container Selector** : MP4, MKV, AVI, MP3, FLAC, WAV.
  * **Video CRF Slider** : Interactive range slider (18–28) with live visual numerical feedback.
  * **Encoding Preset Dropdown** : Ultrafast, Superfast, Veryfast, Faster, Fast, Medium, Slow, Slower, Veryslow.
  * **Resolution Scaler Dropdown** : Original, 3840x2160 (4K), 1920x1080 (1080p), 1280x720 (720p), 854x480 (480p).
  * **Audio Bitrate Selector** : 96k, 128k, 192k, 256k, 320k.
* [ ] **Hardware Selector Component (`gui/components/hardware_selector.py`)**
  * Render dynamic GPU selector dropdown automatically populated based on `HWAccelProber` scan results.
* [ ] **Collapsible Log Console (`gui/components/console_log.py`)**
  * Build expandable log viewer frame with auto-scrolling terminal output for real-time stderr logs, system warnings, and command flags.

### Phase 4: Resilience, Lifecycle & Edge Cases

* [ ] **Process Group Cancellation & Cleanup Engine**
  * Spawn FFmpeg with `subprocess.CREATE_NEW_PROCESS_GROUP`.
  * Implement safe job cancellation using targeted process group `taskkill` calls to guarantee zero background process leaks.
  * Automatically delete incomplete or corrupted output temporary files upon user cancel or process failure.
* [ ] **Robust Exception Handling Boundary**
  * Wrap file IO operations, path sanitization, and probe operations in try-except blocks.
  * Handle special characters, spaces, and non-ASCII characters in input/output file paths gracefully.
  * Provide fallback behavior for unsupported media codecs or zero-length input files.

### Phase 5: Build Verification & Standalone Packaging

* [ ] **End-to-End Functional Verification**
  * Test batch conversions across mixed formats (e.g., `.mkv` to `.mp4`, `.wav` to `.mp3`).
  * Validate hardware acceleration on available GPU drivers (NVIDIA/AMD/Intel).
  * Test UI responsiveness during high-throughput encoding sessions.
* [ ] **PyInstaller Bundling (`OmniConvert.spec`)**
  * Configure spec file with explicit hidden imports (`customtkinter`, `tkinterdnd2`, `PIL`).
  * Bundle `ffmpeg.exe`, `ffprobe.exe`, application icons, and custom style assets.
  * Compile standalone executable: `pyinstaller --noconfirm OmniConvert.spec`.
* [ ] **Binary Release & Delivery**
  * Verify standalone execution of `dist/OmniConvert.exe` on clean Windows 10 and Windows 11 environments without pre-installed Python runtime.
