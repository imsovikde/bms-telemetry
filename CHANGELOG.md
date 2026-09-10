# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [4.2.0] - 2026-09-10

### Added
- **Untruncated Lifetime Historical Telemetry**:
  - Removed 50-event rolling window slicing (`events[-50:]`) in `bms_engine.py` across both active Coulomb integration and S5 offline charge boot recovery.
  - Lifetime event history now grows append-only in perpetuity without loss, maintaining every single micro-delta, timestamp, and energy transition.
- **Complete Lifetime Telemetry Export & Import Subsystem**:
  - Added `export_lifetime_data()` and `import_lifetime_data()` to `bms_engine.py` supporting full 30-decimal registers, S5 audit, and untruncated event ledger.
  - Added CLI subcommands `bms export [file]` and `bms import <file>` with automatic schema validation and multi-tier HMAC re-sealing.
  - Added REST API endpoints `GET /api/export` and `POST /api/import` to `bms_ui.py`.
  - Added interactive glassmorphism **EXPORT LIFETIME JSON** and **IMPORT JSON** buttons to the Generative Web Dashboard with real-time animated toast notifications and local file reader upload.
- **Automated 1-Command Cross-Platform Installers**:
  - `install.ps1`: Automated Windows deployment copying files to `C:\ProgramData\BMS`, adding directory to system/user PATH, creating silent autostart VBS in `shell:startup`, launching the background daemon, and opening the browser dashboard.
  - `install.sh`: Automated Linux/macOS deployment compiling `bms_core.cpp`, symlinking `/usr/local/bin/bms`, registering systemd service, and opening default browser.
  - Added root executable launchers `bms` (shell script) and `bms.cmd` (Windows command wrapper) for zero-setup execution.

### Fixed
- **Thread-Local Decimal Precision Invalidation**:
  - Resolved `decimal.InvalidOperation` in multi-threaded HTTP/SSE contexts by setting `decimal.DefaultContext.prec = 80`. New threads spawned by `ThreadingHTTPServer` inherit 80-digit precision instead of Python's default 28-digit limit.
- **Concurrent Web Server Threading**:
  - Replaced synchronous `HTTPServer` with `socketserver.ThreadingMixIn` / `ThreadingHTTPServer` in `bms_ui.py` and `bms_service.py`, preventing 4 Hz Server-Sent Events (SSE) from blocking concurrent `/api/status`, `/api/export`, and `/api/import` requests.

---

## [4.1.0] - 2026-09-10

### Fixed
- **CI Guards Matrix Failures (All 9 Matrix Jobs Resolved)**:
  - Resolved `pywin32_postinstall` module execution failure on Windows runners by cleaning up setup step in `.github/workflows/ci-guards.yml`.
  - Resolved `ModuleNotFoundError: No module named 'bms_engine'` on Ubuntu and macOS runners in Guard B by prepending workspace directory to Python `sys.path`.
  - Resolved Windows `cp1252` `UnicodeEncodeError` in `tests/test_arithmetic.py` and `bms_engine.py` by enabling UTF-8 stream reconfiguration and cleaning non-ASCII box characters.

### Added
- **Real-Time Live Interactive TUI (`bms live` / `bms tui`)**:
  - Sub-second Coulomb integration running at 4 Hz, live updating the 30-decimal digits of accumulated charging cycles and state of charge in real time.
  - Zero-flicker double-buffered ANSI rendering utilizing alternate screen buffers (`\033[?1049h`), cursor hiding (`\033[?25l`), and in-place cursor homing (`\033[H`).
  - Integrated live instantaneous wattage oscilloscope / sparkline and interactive keyboard navigation (`q` to quit, `space` to pause, `s` to sync NVRAM).
- **Generative Glassmorphism Web Dashboard (`bms ui` / `bms web` via `bms_ui.py`)**:
  - Zero-dependency local web dashboard served via Python standard library on `http://127.0.0.1:8989`.
  - Real-time SVG circular state-of-charge gauge, live 30-decimal odometer counter, and Server-Sent Events (SSE) push streaming at 4 Hz.
- **Native C++20 Engine (`bms_core.cpp`)**:
  - High-performance native implementation with direct Win32 COM `root\wmi` queries (<0.5ms latency, 0 subprocesses, <2 MB RSS).
  - 128-bit fixed-point `Fixed30` arithmetic struct providing 30 decimal digits of zero-drift precision.
  - Verified compilation on modern GCC 15 with zero errors.

---

## [4.0.0] - 2026-09-10

### Fixed (Catastrophic Bug Remediation)
- **Console Window Flashing**: Eliminated the recurring 60-second terminal popup window that flashed on screen for milliseconds and disrupted user focus.
- **Cursor Freezing & Focus Stealing**: Resolved mouse cursor stuttering and window focus preemption caused by `powershell.exe` / `conhost.exe` desktop allocation.
- **In-Process COM WMI Interop**: Replaced subprocess execution in `get_windows_battery_telemetry()` with direct in-process C++ COM calls via `win32com.client` (<1ms execution, 0 child processes, 0 console windows).
- **Subprocess Windowless Guard**: Wrapped all fallback Windows subprocess calls with `STARTUPINFO(dwFlags=STARTF_USESHOWWINDOW, wShowWindow=SW_HIDE)` and `creationflags=CREATE_NO_WINDOW` (`0x08000000`).
- **Legacy Startup VBS Removal**: Deprecated and uninstalled `BMS_Cycle_Daemon.vbs` from user and system Startup directories.

### Added
- **Native Windows Service (`BMSTelemetry`)**: Implemented `bms_service.py` using `win32serviceutil.ServiceFramework`, running in Session 0 under `services.exe` with SCM-managed auto-restart (5s/10s/30s escalation).
- **Offline S5 Boot-Recovery Engine**:
  - `_flush_shutdown_state()`: Captures $Q_{\text{shutdown}}$ on `SIGTERM` / SCM service stop.
  - `_detect_offline_delta()`: Reconstructs $\Delta E_{\text{offline}} = \max(0, Q_{\text{boot}} - Q_{\text{shutdown}})$ and injects offline cycles on boot.
- **CI Guards Workflow (`.github/workflows/ci-guards.yml`)**:
  - Guard A: CLI Integrity (`bms status` exit code 0).
  - Guard B: Anti-Mock Verification (verifies active hardware ACPI probing across Windows, Linux, and macOS).
  - Guard C: Arithmetic Unit Suite (21 unit tests in `tests/test_arithmetic.py`).
  - Guard D: 100-Cycle Deep Verification Suite.
  - Guard E: Windows Service importability validation.
- **New Installer Scripts**:
  - `scripts/install.ps1`: Automated elevated Windows Service installer.
  - `scripts/install.sh`: Linux `systemd` and macOS `LaunchDaemon` installer.
- **Dependabot Integration**: Automated weekly dependency scanning for pip and GitHub Actions.
- **Comprehensive PRD (`PRD.md`)**: Full product requirements document including catastrophic defect post-mortem and forensic analysis.
- **Community Health Suite**: `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md`, `SECURITY.md`, `SUPPORT.md`, `.github/ISSUE_TEMPLATE/`, `.github/PULL_REQUEST_TEMPLATE.md`, `.github/CODEOWNERS`, `.editorconfig`, `.gitattributes`.

---

## [3.0.0] - 2026-09-09

### Added
- **100-Cycle Automated Verification Suite**: Standalone test harness (`verify_100.py` / `bms test-100`) executing 100 deep tests in <0.2 seconds.
- **HMAC-SHA256 Silicon Envelope**: Key derivation via PBKDF2-HMAC-SHA256 bound to motherboard UUID, baseboard serial, and battery serial.
- **Self-Healing Storage Mirrors**: Multi-tier persistence surviving complete `C:\` primary OS format via secondary NVMe partitions (`D:\`, `S:\`).

---

## [2.0.0] - 2026-09-09

### Added
- **30-Decimal Arbitrary Precision**: Integrated Python `Decimal` with 60-digit internal context and 30-digit quantized storage (`DEC_30`), eliminating IEEE 754 float drift.
- **Multi-Factor Electrochemical Degradation**: SEI layer power-law decay ($N^{0.82}$), Arrhenius thermal kinetics ($E_a/R=3788\text{ K}$), and float overpotential stress.

---

## [1.0.0] - 2026-09-08

### Added
- Initial proof-of-concept Coulomb-counting cycle tracker for the Infinix ZERO BOOK 13 (EM_IDL822_V2.0).
