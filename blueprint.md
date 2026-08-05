🏗️ Technical Architecture Blueprint: OmniConvert Video & Audio

Category: Media Engine & File Converters

Application ID: 001

Target OS: Windows 10 / Windows 11 (x64)

Primary Technology Stack: Python 3.10+, CustomTkinter, TkinterDnD2, FFmpeg / FFprobe Subprocesses, threading, queue.Queue

📐 1. System Architecture & Telemetry Pipeline

The architecture follows an Event-Driven Model-View-Controller (MVC) design pattern. Heavy FFmpeg transcoding operations run as isolated child subprocesses wrapped inside dedicated worker threads. Telemetry is streamed asynchronously via an inter-thread queue back to the main GUI thread to maintain a 60 FPS responsive user interface.

+---------------------------------------------------------------------------------------+
|                                  GUI LAYER (Main Thread)                              |
|  - CustomTkinter Responsive Window (Dark / Light Theme)                              |
|  - Event Loop (root.mainloop) with 50ms Queue Polling Routine                         |
|  - Queue Consumer & State Handlers (Progress Bar, Speed Gauge, Log Console Update)    |
+---------------------------------------------------------------------------------------+
                                           ^
                                           |  Thread-Safe Event Payloads (queue.Queue)
                                           |  - STATUS: Pending | Converting | Completed | Error
                                           |  - METRICS: Progress %, FPS, ETA, Speed (e.g. 2.4x)
                                           |  - LOG: Raw FFmpeg Stderr Telemetry / Warnings
                                           v
+---------------------------------------------------------------------------------------+
|                               THREAD-SAFE MESSAGE QUEUE                               |
|  - Thread-safe payload buffer decoupling Subprocess IO from UI Rendering Loop        |
+---------------------------------------------------------------------------------------+
                                           ^
                                           |  Non-Blocking Thread Dispatch
                                           v
+---------------------------------------------------------------------------------------+
|                             BACKGROUND WORKER ENGINE                                  |
|  - Batch Queue Execution Manager                                                      |
|  - FFprobe Metadata Extractor (JSON Stream & Duration Probe)                          |
|  - Transcode Worker Threads (threading.Thread)                                        |
+---------------------------------------------------------------------------------------+
                                           |
                                           |  subprocess.Popen (CREATE_NO_WINDOW)
                                           v
+---------------------------------------------------------------------------------------+
|                             EMBEDDED FFMPEG CORE ENGINE                               |
|  - Binary Execution (ffmpeg.exe / ffprobe.exe)                                        |
|  - Continuous Stderr Pipe Reader (Regex Regex Matchers)                               |
|  - Process Group Task-Kill Handle for Safe Job Cancellation                           |
+---------------------------------------------------------------------------------------+

📁 2. Project Directory Layout & File Roles

001-OmniConvert-Video-Audio/
├── prompt.json                   # AI Agent & System Core JSON Specification
├── roadmap.md                    # Implementation Execution Roadmap
├── blueprint.md                  # Comprehensive Architecture Blueprint (This File)
├── skills.md                     # Technical Competency & Skill Matrix
├── requirements.txt              # Standardized Python Dependency Specs
├── OmniConvert.spec              # Production PyInstaller Build Blueprint
├── main.py                       # Application Entry Point & Bootstrapper
├── gui/
│   ├── __init__.py
│   ├── app.py                    # Main Window Setup, Theme Engine, & Queue Loop
│   ├── components/
│   │   ├── __init__.py
│   │   ├── drop_zone.py          # Drag-and-Drop Batch File Queue Frame
│   │   ├── file_card.py          # Individual Queue Item Widget with Progress Bar
│   │   ├── control_panel.py      # CRF Sliders, Codec, Preset & Bitrate Selectors
│   │   ├── hardware_selector.py  # GPU Acceleration Auto-Detection Component
│   │   └── console_log.py        # Collapsible Real-Time Log Viewer Frame
│   └── styles/
│       ├── __init__.py
│       └── theme.json            # CustomTkinter Dark/Light Color Tokens
├── engine/
│   ├── __init__.py
│   ├── binary_resolver.py        # Dynamic Binary Path Auto-Discovery Engine
│   ├── hw_accel.py               # GPU Encoder Prober (NVENC, AMF, QSV, CPU)
│   ├── ffprobe_parser.py         # JSON Metadata & Stream Probe Utilities
│   ├── transcode_worker.py       # Async Transcode Thread & Subprocess Controller
│   └── telemetry.py              # Regex Engine for FFmpeg Stderr Stream Parsing
└── utils/
    ├── __init__.py
    ├── logger.py                 # Thread-Safe System Logger
    └── helpers.py                # Time Formatter, File Size Calculator, Path Sanitizer

🛠️ 3. Technology Stack Matrix

Architectural Layer

Component / Package

Technical Purpose & Scope

GUI Framework

CustomTkinter (>= 5.2.0)

High-DPI responsive modern UI components, custom sliders, theme toggles.

Drag & Drop API

TkinterDnD2 / tkinterdnd2-universal

Native Windows file drop support directly onto the conversion queue frame.

Media Processing

FFmpeg & FFprobe (Static Binaries Build 6.0+)

Video/Audio decoding, stream filtering, spatial scaling, frame encoding.

Concurrency Core

threading.Thread & queue.Queue

Non-blocking execution of probe operations, file conversions, and UI event loops.

Subprocess Mgmt

subprocess.Popen

Silent process execution with creationflags=subprocess.CREATE_NO_WINDOW.

Telemetry Parsing

Python re Module

Regex extraction of timestamp (time=), target duration, frame rate, and speed factor.

Packaging & Executable

PyInstaller (>= 6.0)

Compiles runtime, libraries, icons, and ffmpeg binaries into a standalone .exe.

⚡ 4. Concurrency & Telemetry Protocol

4.1 Queue Event Payloads

To prevent thread race conditions, worker threads never interact directly with GUI controls. All status changes and progress metrics are encapsulated into structured dictionary payloads pushed to a thread-safe queue.Queue.

# Standard Telemetry Payload Structure

{
    "event": "PROGRESS",          # 'STATUS', 'PROGRESS', 'CONSOLE_LOG', 'COMPLETED', 'ERROR'
    "file_id": "file_0042",       # Unique item identifier in file queue
    "percent": 45.8,             # Normalized float [0.0 - 100.0]
    "current_time": "00:02:14",   # Processed duration timestamp
    "total_duration": "00:04:52", # Media total duration timestamp
    "fps": 58.4,                  # Current encoding frames per second
    "speed": "2.3x",              # Conversion speed multiplier
    "raw_log": "frame=  7776 fps=58 q=24.0 size=   45056kB time=00:02:14.33 bitr..."
}

4.2 GUI Queue Polling Protocol

The main CustomTkinter thread initializes a persistent non-blocking timer routine:

def poll_event_queue(self):
    try:
        while True:
            payload = self.event_queue.get_nowait()
            self.handle_telemetry_event(payload)
            self.event_queue.task_done()
    except queue.Empty:
        pass
    finally:
        # Schedule next queue check in 50ms (20 Hz update rate)
        self.root.after(50, self.poll_event_queue)

🔍 5. External Binary Auto-Resolution Engine

The dynamic binary resolution hierarchy ensures ffmpeg.exe and ffprobe.exe are located seamlessly across development, standalone execution, and custom user environments.

    +-----------------------------------+
                  |   1. Check sys._MEIPASS           |
                  |   (PyInstaller Frozen Bundle)     |
                  +-----------------------------------+
                                    | Missing
                                    v
                  +-----------------------------------+
                  |   2. Check Script Working Dir     |
                  |   (os.path.dirname(__file__))     |
                  +-----------------------------------+
                                    | Missing
                                    v
                  +-----------------------------------+
                  |   3. Check Relative './bin/' Dir  |
                  |   (Application Local Binaries)    |
                  +-----------------------------------+
                                    | Missing
                                    v
                  +-----------------------------------+
                  |   4. Check System Environment PATH|
                  |   (shutil.which('ffmpeg'))        |
                  +-----------------------------------+
                                    | Missing
                                    v
                  +-----------------------------------+
                  |   5. Raise Error & Prompt User    |
                  |   (Fallback Path Selector Dialog) |
                  +-----------------------------------+

🏎️ 6. Hardware Acceleration Auto-Detection Engine

On boot, the application runs a lightweight probe against FFmpeg to check available GPU codecs:

Hardware Vendor

Target H.264 Encoder

Target HEVC Encoder

FFmpeg Probe Command

NVIDIA Graphics

h264_nvenc

hevc_nvenc

ffmpeg -hide_banner -encoders | findstr nvenc

AMD Radeon

h264_amf

hevc_amf

ffmpeg -hide_banner -encoders | findstr amf

Intel QuickSync

h264_qsv

hevc_qsv

ffmpeg -hide_banner -encoders | findstr qsv

Software CPU

libx264

libx265

Default Software Encoding Fallback

🛡️ 7. Process Lifecycle & Safe Cancellation Architecture

When a conversion job is canceled by the user or when the main UI window is closed during batch conversion:

Subprocess Isolation: Subprocesses are spawned with creationflags=subprocess.CREATE_NO_WINDOW | subprocess.CREATE_NEW_PROCESS_GROUP.

Graceful Cancellation: The application sends a SIGTERM / taskkill signal targeted specifically at the process group ID (pgid) to ensure orphan ffmpeg.exe processes do not remain background leaks.

Temp File Cleanup: Partial or corrupted output files are automatically removed from disk upon cancellation.

📦 8. PyInstaller Packaging Specification

The build configuration bundles assets, fonts, icons, and static binaries into a single executable OmniConvert.exe:

# PyInstaller Spec Highlights (OmniConvert.spec)

import sys
import os
from PyInstaller.utils.hooks import collect_all

block_cipher = None

datas = [
    ('gui/styles', 'gui/styles'),
    ('bin/ffmpeg.exe', '.'),
    ('bin/ffprobe.exe', '.')
]
binaries = []
hiddenimports = ['tkinterdnd2', 'customtkinter', 'PIL', 'queue', 'json', 're']

for pkg in ['customtkinter', 'tkinterdnd2']:
    tmp = collect_all(pkg)
    datas += tmp[0]
    binaries += tmp[1]
    hiddenimports += tmp[2]

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='OmniConvert',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    icon='assets/icon.ico'
)
