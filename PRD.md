# Product Requirements Document (PRD)

# BMS Universal Battery & Cycle Telemetry Engine (`bms-telemetry`)

> **Autonomous, Multi-Architecture Hardware Battery Telemetry, Compensatory Cycle Tracking, and 30-Decimal Arbitrary-Precision Engine**  
> *Target System: OEM Laptops with Defective or Missing ACPI `_BIX` Firmware (Flagship: Infinix ZERO BOOK 13 / EM_IDL822_V2.0 / Raptor Lake-P)*  
> *Version: 4.0.0 (Production / Headless SCM Edition)*  
> *Author: Souvik Dey ([@imsovikde](https://github.com/imsovikde))*

---

## 1. Executive Summary & Problem Space

Modern OEM laptop architectures frequently suffer from compromised Embedded Controller (EC) and ACPI DSDT implementations. On the **Infinix ZERO BOOK 13 (EM_IDL822_V2.0)**, the BIOS engineering team implemented the legacy ACPI 1.0 `_BIF` (Battery Information) method but completely omitted the ACPI 4.0 `_BIX` (Battery Information Extended) table.

Because operating system battery drivers (`cmbatt.sys` on Windows NT, `battery.c` on Linux, and `AppleSmartBattery` on macOS) rely exclusively on element 8 of the `_BIX` payload for cycle telemetry, the host operating system permanently reports **0 charging cycles**. Users are left blind to actual battery degradation, electrochemical wear, and remaining cell lifespan.

`bms-telemetry` provides an unkillable, hardware-anchored compensatory tracking engine that continuously measures Coulomb integration, audits offline charging across power-off states ($S5$), calculates degradation via multi-factor electrochemical models, and guarantees state survival across full operating system reformatting.

---

## 2. Forensic Post-Mortem: The Catastrophic Regression

### 2.1 The Incident & User-Facing Symptoms
Prior to Version 4.0.0, an execution bug severely impacted the host environment. During normal user operations (coding, typing, web browsing, gaming), the following disruptive anomalies occurred at 60-second intervals:
1. **Console Flashing / Window Flicker**: A terminal window popped up for a span of 50–200 milliseconds and instantly vanished. The user could not see which folder or program executed, creating the illusion of malware or system instability.
2. **Mouse Cursor Freezing / Stuttering**: At the exact instant the terminal appeared, the user's mouse cursor froze or lagged.
3. **Foreground Focus Stealing**: Active keystrokes were dropped because the foreground focus was abruptly stolen by the transient console window.

### 2.2 Mechanistic Root-Cause Analysis
The root cause was identified at the intersection of process management and Windows Win32 subsystem initialization:

```
[Daemon Loop (bms_engine.py)]
      │
      ├─► Every 60s: get_windows_battery_telemetry()
      │         │
      │         └─► subprocess.run(["powershell", "-NoProfile", "-Command", ps_cmd])
      │                   │
      │                   ▼  MISSING FLAGS:
      │                   ❌ No CREATE_NO_WINDOW (0x08000000)
      │                   ❌ No STARTUPINFO (STARTF_USESHOWWINDOW + SW_HIDE)
      │                   │
      │                   ▼
      │             [Win32 CreateProcessW Allocates Console]
      │                   │
      │                   ├─► conhost.exe & powershell.exe created
      │                   ├─► Desktop Window Manager (DWM) creates top-level HWND
      │                   ├─► Windows UI Automation & Thread Desktop attach/detach
      │                   ├─► FOREGROUND FOCUS STOLEN FROM USER ACTIVE WINDOW
      │                   └─► Mouse cursor input queue hitching / thread lag
      │
      └─► Legacy VBS Wrapper (BMS_Cycle_Daemon.vbs in Startup)
                │
                └─► Invoked pythonw.exe, but did NOT prevent child subprocess consoles!
```

1. **Subprocess Console Allocation**: While `pythonw.exe` runs without a console, any child process launched via `subprocess.run()` without explicit Win32 creation flags defaults to allocating a console window (`conhost.exe`).
2. **Desktop Window Manager (DWM) Preemption**: Spawning `powershell.exe` forced DWM to instantiate an OS-level console window. Even though execution lasted <100ms, Windows paused user-thread message loops to transition active window handles, causing the mouse cursor to freeze and text input to drop.
3. **Startup Script Vulnerability**: The installer deployed a Visual Basic Script (`BMS_Cycle_Daemon.vbs`) into `%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup`. This approach ran in the interactive user session (Session 1), allowing any subprocess anomaly to directly pollute the active desktop.

### 2.3 The Architectural Resolution: The 3-Layer Zero-Window Shield

To permanently eliminate this failure mode, Version 4.0.0 established a hardened, multi-tier execution architecture:

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                     LAYER 1: PURE IN-PROCESS COM WMI INTEROP                   │
│  win32com.client.GetObject("winmgmts:\\\\.\\root\\wmi")                         │
│  • 0 Subprocesses Spawned    • 0 Console Windows Allocated   • <1ms Execution   │
│  • Direct in-memory C++ COM calls to ACPI BatteryStatus, StaticData & FullCap   │
└───────────────────────────────────────┬─────────────────────────────────────────┘
                                        │ (Fallback if COM fails)
                                        ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                 LAYER 2: STRICT WINDOWLESS SUBPROCESS SHIELDING                 │
│  • STARTUPINFO.dwFlags |= STARTF_USESHOWWINDOW | wShowWindow = SW_HIDE          │
│  • creationflags = subprocess.CREATE_NO_WINDOW (0x08000000)                     │
│  • Guarantees Windows Kernel NEVER attaches conhost.exe or creates HWND         │
└───────────────────────────────────────┬─────────────────────────────────────────┘
                                        │
                                        ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│            LAYER 3: NATIVE SCM WINDOWS SERVICE (BMSTelemetry)                   │
│  • Registered in Service Control Manager (services.exe) under Session 0         │
│  • Completely isolated from interactive desktop (Session 1+)                    │
│  • Automatic restart on failure (5s / 10s / 30s escalation)                     │
│  • Survives user logoff and starts before any user logs in                      │
│  • Legacy Startup VBS hooks completely purged during installation               │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Product Vision & Goals

1. **True Headless Operation**: Zero popups, zero terminal flashing, zero cursor hitching, zero UI interruption across Windows, Linux, and macOS.
2. **Scientific Precision**: 30 decimal places of arithmetic precision (`Decimal`, 60-digit internal context) to prevent rounding drift over years of micro-charging.
3. **Zero-Data-Loss Survival**: State mirrored across 7 physical and logical tiers (including secondary NVMe partitions `D:\` and `S:\`), surviving full formatting of the primary `C:\` drive.
4. **Offline Charge Accounting**: Precise detection and accumulation of charging events that occur while the laptop is powered off ($S5$ state).
5. **Universal CLI**: Instant, single-command access (`bms status`, `bms full`, `bms test-100`) from any working directory on any supported OS.
6. **Automated Quality Verification**: 5 CI guards and a 100-cycle stress test executing in <0.2 seconds.

---

## 4. System Architecture & Component Breakdown

### 4.1 Cross-Platform Daemon Architecture

| Platform | Service Manager | Runtime Mode | Isolation Level | Lifecycle Policy |
| :--- | :--- | :--- | :--- | :--- |
| **Windows NT** | Service Control Manager (`sc.exe`) | `BMSTelemetry` (`bms_service.py` via `pywin32`) | Session 0 (Isolated from Desktop) | Auto-start on boot, restart on crash |
| **Linux (systemd)** | `systemd` (`bms-daemon.service`) | `Type=simple`, `Nice=19`, `CPUQuota=1%`, `MemoryMax=32M` | Root / Multi-User Target | Auto-restart, unprivileged sandbox |
| **macOS** | `launchd` (`com.bms.daemon`) | `LaunchDaemon` in `/Library/LaunchDaemons/` | System-wide daemon (`RunAtLoad=true`) | Auto-restart across all user sessions |

### 4.2 Mathematical & Degradation Engine

The engine computes the battery's **Virtual Health Percentage** using a multi-factor electrochemical degradation model:

$$\text{Virtual Health} = \text{SoH}_{\text{base}} - \text{Loss}_{\text{cycle}} - \text{Loss}_{\text{thermal}} - \text{Loss}_{\text{voltage}}$$

1. **Base Coulombic Ratio**:
   $$\text{SoH}_{\text{base}} = \left( \frac{\text{FCC}}{\text{Design Capacity}} \right) \times 100$$
2. **SEI Layer Power-Law Cycle Degradation**:
   $$\text{Loss}_{\text{cycle}} = A \times (\text{Cycles})^z \quad (z = 0.82, A \approx 0.122858)$$
   *Calibrated for nominal 80% capacity retention at 500 equivalent full cycles.*
3. **Arrhenius Thermal Aging**:
   $$\text{Loss}_{\text{thermal}} = k_{\text{thermal}} \times \exp\left( \frac{E_a}{R} \left( \frac{1}{T_{\text{ref}}} - \frac{1}{T_{\text{actual}}} \right) \right) \quad \left(\frac{E_a}{R} = 3788\text{ K}, T_{\text{ref}} = 298.15\text{ K}\right)$$
4. **High-Voltage Float Stress**:
   Overpotential degradation during prolonged saturation at peak terminal voltages ($V > 12.6\text{ V}$).

### 4.3 S5 Powered-Off Offline Charge Recovery

When the machine is charged while powered off, the Embedded Controller charges the physical pack without OS awareness. The daemon handles this seamlessly:
1. **Shutdown Hook**: On `SIGTERM` or SCM service stop, `_flush_shutdown_state()` stores $Q_{\text{shutdown}}$ and a UTC timestamp into the sealed state file.
2. **Boot Hook**: On startup, `_detect_offline_delta()` compares $Q_{\text{boot}}$ with $Q_{\text{shutdown}}$:
   $$\Delta E_{\text{offline}} = \max(0, Q_{\text{boot}} - Q_{\text{shutdown}})$$
3. If $\Delta E_{\text{offline}} > 50\text{ mWh}$, the recovered cycles are calculated and injected:
   $$\Delta \text{Cycles} = \frac{\Delta E_{\text{offline}}}{\text{Design Capacity}}$$
   An audit record of type `S5_OFFLINE_CHARGE_BOOT_RECOVERY` is appended to `history_events`.

### 4.4 Multi-Tier Storage Topology & Anti-Tamper Security

State is protected by an HMAC-SHA256 signature keyed to immutable silicon hardware identifiers:
- Motherboard UUID: `12B4C080-2150-11EE-B678-E9E74C343D00`
- Baseboard Serial: `XLCZ513637D0123`
- Battery Serial: `123456789`
- Key derivation: PBKDF2-HMAC-SHA256 (100,000 iterations with `INFINIX_BMS_SILICON_KEY_v2.0` salt)

#### 7 Persistence Mirrors
1. Primary OS Cache: `C:\ProgramData\BMS\bms_state.json` & `bms_hardware_nvram.dat`
2. User Profile Cache: `~/.bms/bms_state.json` & `bms_hardware_nvram.dat`
3. Physical Secondary NVMe Disk 1, Partition 4: `D:\.bms_hardware_nvram.dat` (Survives `C:\` format)
4. Physical Hidden NVMe Disk 1, Partition 3: `S:\.bms_hardware_nvram.dat` (Survives `C:\` format)
5. Physical USB/Removable Media: `E:\.bms_hardware_nvram.dat`
6. Linux System NVRAM: `/var/lib/bms/bms_state.json` & `/etc/bms/bms_hardware_nvram.dat`
7. WSL Host Mount: `/mnt/c/ProgramData/BMS/bms_state.json`

On boot or read, the highest monotonic sequence number with a valid HMAC signature wins canonical state election.

### 4.5 Untruncated Lifetime Historical Data & Portable Archive

The integrity of historical telemetry is governed by the **Untruncated Lifetime Persistence Invariant**:
1. **Append-Only History Ledger**: Historical battery events (discharge sessions, high-current charging transitions, and S5 boot recovery records) MUST NOT be sliced or limited by a rolling window. Slicing limits (such as legacy `events[-50:]`) are strictly prohibited.
2. **Cryptographically Sealed JSON Archive**: The system provides full export and import capabilities (`bms export`, `bms import`, `GET /api/export`, `POST /api/import`). The archive captures 100% of telemetry registers (formatted to 30 decimal places), offline charging audit summaries, complete event lists, and cryptographic integrity hashes.
3. **Multi-Mirror Restoration**: Importing an archive validates monotonic sequence counters and re-signs the entire state across all 7 hardware persistence tiers (`C:\ProgramData\BMS`, `~/.bms`, `D:\`, `S:\`, `E:\`, `/var/lib/bms`).

---

## 5. Requirements & Acceptance Criteria

### 5.1 Functional Requirements (FR)

- **FR-1**: The system MUST extract real-time battery voltage, charging status, current capacity, and design capacity from hardware ACPI tables via WMI, sysfs, or AppleSmartBattery.
- **FR-2**: The system MUST calculate accumulated charging cycles to 30 decimal places without using standard floating-point arithmetic.
- **FR-3**: The system MUST detect offline charging events when the device is powered off ($S5$ state) and increment the cycle counter accordingly.
- **FR-4**: The system MUST sign all state transitions with HMAC-SHA256 derived from the silicon master key.
- **FR-5**: The system MUST self-heal if the `C:\` drive or primary OS partition is formatted by restoring state from `D:\` or `S:\`.
- **FR-6**: The system MUST provide global CLI access via the `bms` command from any terminal working directory.
- **FR-7**: The system daemon MUST run completely in the background without creating a console window, flickering the display, or stealing user focus.
- **FR-8**: The biometric diagnostic module (`bms fix-bio`) MUST remain available to remediate Windows Hello fingerprint lockouts.
- **FR-9**: The system MUST preserve all historical charging events, micro-deltas, and S5 boot recovery records indefinitely in an append-only ledger without truncation or pruning.
- **FR-10**: The system MUST provide CLI commands (`bms export`, `bms import`) and interactive Generative Web UI buttons (`EXPORT LIFETIME JSON`, `IMPORT JSON`) to export and restore 100% of historical events and 30-decimal registers across hardware and OS boundaries.
- **FR-11 (Physical Cell Ingestion & Cycle Gating)**: Cycle accumulation MUST strictly halt whenever the battery is at 100% capacity ($Q_{\text{rem}} \ge Q_{\text{full}}$), discharging, or idle. Cycles SHALL ONLY increment when external power is active and physical energy is genuinely flowing into the battery cells ($Q_{\text{rem}} < Q_{\text{full}}$ and $P_{\text{charge}} > 0$).
- **FR-12 (Architectural Hardware Link Transparency)**: The system MUST visibly display the direct hardware communication status (`ACPI\PNP0C0A\0_0`, Tag number, bus type, and raw silicon registers) across all user interfaces (CLI status, live TUI, and Web dashboard) to certify that all telemetry originates directly from the physical battery fuel gauge.

### 5.2 Non-Functional Requirements (NFR)

- **NFR-1 (Resource Footprint)**: CPU utilization of the background daemon MUST NOT exceed 0.01% average; RAM usage MUST remain under 20 MB.
- **NFR-2 (Zero UI Disruption)**: Zero visual console windows, taskbar items, or system tray interruptions may occur during daemon polling ticks.
- **NFR-3 (Execution Latency)**: Telemetry queries MUST resolve in under 100 milliseconds.
- **NFR-4 (Deterministic Arithmetic)**: Repeating 1,000 micro-cycle additions MUST yield exact numerical equality down to the 30th decimal place.
- **NFR-5 (Test Performance)**: The 100-cycle verification suite MUST execute in under 0.5 seconds on host hardware.
- **NFR-6 (Thread-Safe Decimal Context)**: All concurrent server and worker threads MUST inherit a minimum 80-digit arbitrary-precision context (`decimal.DefaultContext.prec = 80`) ensuring zero `InvalidOperation` exceptions during high-frequency multithreaded quantization.

---

## 6. Automated Quality & CI Gates

The repository enforces 5 continuous integration guards across a matrix of 9 environments (`ubuntu-latest`, `macos-latest`, `windows-latest` $\times$ Python `3.10`, `3.11`, `3.12`):

1. **Guard A (CLI Integrity)**: `python bms_engine.py status` exits with code 0 on all platforms.
2. **Guard B (Anti-Mock Verification)**: Confirms that OS telemetry drivers actively probe real hardware interfaces (`root\wmi`, `sysfs`, `AppleSmartBattery`) and that fallback constants are restricted to emergency exception handlers.
3. **Guard C (Arithmetic Unit Suite)**: 21 unit tests in `tests/test_arithmetic.py` verifying precision, offline delta math, virtual health bounds, and HMAC tamper rejection.
4. **Guard D (100-Cycle Suite)**: 100 full simulated cycles with simulated `C:\` disk wipe and NVRAM restoration.
5. **Guard E (Service Importability)**: Verifies `bms_service.py` imports cleanly on Windows platforms.

---

## 7. Version History & Milestones

| Version | Release Date | Key Achievements & Architectural Changes |
| :--- | :--- | :--- |
| **v1.0.0** | 2026-09-08 | Initial proof-of-concept Coulomb counter. |
| **v2.0.0** | 2026-09-09 | 30-decimal arithmetic engine and multi-layer persistence. |
| **v3.0.0** | 2026-09-09 | 100-cycle verification harness and HMAC silicon envelope. |
| **v4.0.0** | **2026-09-10** | **Architectural Overhaul**: Elimination of catastrophic terminal popup bug via In-Process COM WMI Interop, migration to native Windows Service (`BMSTelemetry`) / systemd / LaunchDaemon, offline $S5$ boot-recovery, 5 CI guards, and full GH-Ready elevation. |
