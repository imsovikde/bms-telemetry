# BMS Telemetry & Cycle Engine (`bms`)

> **Autonomous, Multi-Architecture Hardware Battery Telemetry, Compensatory Cycle Tracking, and 30-Decimal Arbitrary-Precision Engine**  
> *Engineered for Linux, Windows NT, and macOS (Intel x86_64, AMD64, ARM64, and Apple Silicon)*

[![CI Status](https://github.com/imsovikde/bms-telemetry/actions/workflows/ci.yml/badge.svg)](https://github.com/imsovikde/bms-telemetry/actions/workflows/ci.yml)
[![CI Guards](https://github.com/imsovikde/bms-telemetry/actions/workflows/ci-guards.yml/badge.svg)](https://github.com/imsovikde/bms-telemetry/actions/workflows/ci-guards.yml)
[![Precision](https://img.shields.io/badge/Arithmetic%20Precision-30%20Decimals-blueviolet)](https://github.com/imsovikde/bms-telemetry)
[![Hardware Persistence](https://img.shields.io/badge/Hardware%20Persistence-Zero--Data--Loss-success)](https://github.com/imsovikde/bms-telemetry)
[![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20Linux%20%7C%20macOS-blue)](https://github.com/imsovikde/bms-telemetry)
[![License](https://img.shields.io/badge/License-MIT-green)](./LICENSE)

---

## ⚡ Problem Overview & The Infinix Firmware Defect

In OEM laptop architectures—specifically the **Infinix ZERO BOOK 13 (EM_IDL822_V2.0 / Raptor Lake-P)**—the BIOS and Embedded Controller (EC) firmware engineers implemented the ACPI 1.0 `_BIF` method (Battery Information, 13 fields) but completely omitted the ACPI 4.0 `_BIX` method (Battery Information Extended, 21 fields, element 8: `Cycle Count`).

Because standard operating systems (`cmbatt.sys` on Windows, `battery.c` on Linux, and `AppleSmartBattery` on macOS) rely on `_BIX` to expose battery wear cycles, the operating system indefinitely reports **0 charging cycles**, blinding users to battery degradation and lifespan erosion.

**BMS Telemetry** solves this firmware limitation by establishing an independent, hardware-anchored compensatory tracking engine. It continuously measures Coulomb integration, audits offline charging across power-off states ($S5$), evaluates electrochemical State of Health via multi-factor physics models, and guarantees persistence across complete operating system formatting.

---

## 🚀 Instant Deployment (1-Command)

Clone the repository and run the installer. It auto-detects your OS, installs the engine, deploys a **true headless background service**, and registers the global `bms` CLI.

### Linux & macOS
```bash
git clone https://github.com/imsovikde/bms-telemetry.git
cd bms-telemetry
chmod +x scripts/install.sh
sudo ./scripts/install.sh
```

### Windows (elevated PowerShell — required for Windows Service registration)
```powershell
git clone https://github.com/imsovikde/bms-telemetry.git
cd bms-telemetry
# Must be run as Administrator:
Set-ExecutionPolicy -Scope Process Bypass
.\scripts\install.ps1
```

Once installed, **`bms` is available from any terminal** (`C:\`, `/root`, `$HOME`, or Desktop).

---

## 🏗️ Headless Background Service Architecture

The daemon runs as a **true system service** — never a VBS script, never a visible terminal window:

| Platform | Mechanism | Level | Details |
| :--- | :--- | :--- | :--- |
| **Windows** | `BMSTelemetry` Windows Service (SCM) | System | `bms_service.py` via `pywin32`; survives user logoff; auto-restarts on crash (5s/10s/30s escalation) |
| **Linux** | `bms-daemon.service` systemd unit | System | `Type=simple`, `CPUQuota=1%`, `MemoryMax=32M`, `ProtectSystem=full`, `WantedBy=multi-user.target` |
| **macOS** | `com.bms.daemon` LaunchDaemon | System | `/Library/LaunchDaemons/` (not LaunchAgent); `RunAtLoad=true`; `KeepAlive=true` |

### Graceful Shutdown & Offline ΔQ Recovery

Every service stop flushes `last_shutdown_capacity_mwh` to the state file.  
On next boot, the daemon computes:

```
ΔE = max(0, Q_boot − Q_shutdown)
```

If `ΔE > 50 mWh`, the charging that occurred while the machine was fully powered off (S5 state) is injected into the cycle counter. The event is recorded to `history_events` with type `S5_OFFLINE_CHARGE_BOOT_RECOVERY`.

---

## 💎 Core Architectural Highlights

| Subsystem | Specification & Capability |
| :--- | :--- |
| **Arithmetic Precision** | **30 Decimal Places** using Python `Decimal` (60-digit internal context). Zero IEEE 754 float drift. |
| **Cycle Tracking** | Compensatory Coulomb integration + cold-boot S5 offline ΔQ audit. |
| **Virtual Health (SoH%)** | SEI power-law decay ($N^{0.82}$) + Arrhenius thermal ($E_a/R=3788$ K) + float overpotential stress. |
| **Zero-Data-Loss Persistence** | HMAC-SHA256 envelope keyed to silicon identifiers. 7-tier mirror spanning `C:\ProgramData\BMS`, `~/.bms`, `D:\`, `S:\`, `E:\`, `/var/lib/bms`, `/etc/bms`. Survives `C:\` format. |
| **Headless Daemon** | True Windows Service (SCM), systemd, or LaunchDaemon. Never a VBS script or popup window. |
| **Resource Overhead** | `<0.01%` CPU, `~14 MB` RAM, 60-second tickless poll. |
| **CI Guards** | 5 automated guards: CLI Integrity, Anti-Mock, Arithmetic (21 unit tests), 100-Cycle Suite, Windows Service importability. |

---

## 📊 Live Telemetry Dashboard

```text
====================================================================================
   INFINIX ZERO BOOK 13 (EM_IDL822_V2.0) - BMS HARDWARE & CYCLE TELEMETRY
====================================================================================
 Timestamp (UTC)         : 2026-09-09 18:56:50 UTC
 Telemetry Source        : Windows WMI ACPI Subsystem
 Silicon Master Key (Hex): 63c0ab3e4d04339d...010f7407 (HMAC-SHA256)

 [CAPACITY & REAL-TIME POWER DYNAMICS]
  Design Capacity        : 69,993 mWh (69.993 Wh)
  Full Charge Capacity   : 69,993 mWh
  STATE OF CHARGE (SoC%) : 100.000000000000000000000000000000%

 [MULTI-FACTOR ELECTROCHEMICAL DEGRADATION]
  Power-Law Cycle Fade   : -1.146968033262214056042949952849%
  Arrhenius Thermal Loss : -0.023835305059133080251878638415%
  VIRTUAL HEALTH (SoH%)  : 98.829196661678652863705171408736%

 [CONTINUOUS CYCLE ENGINE (30-DECIMAL COMPENSATOR)]
  EC Firmware Native Flag: _BIX Absent in DSDT → 0 Native ACPI cycles
  ACCUMULATED CYCLES     : 15.309873844527311029482710394827

 [HARDWARE PERSISTENCE — 7 TIERS ONLINE]
  State Monotonic Counter: #109
  Cryptographic Seal     : HMAC-SHA256 Authenticated
====================================================================================
```

---

## 📖 Documentation Index

| Document | Purpose |
| :--- | :--- |
| [`CLI.md`](./CLI.md) | Complete CLI command reference |
| [`ARCHITECTURE.md`](./ARCHITECTURE.md) | DSDT forensics, math models, persistence tiering |
| [`SPEC.md`](./SPEC.md) | JSON schema, crypto envelope, resource bounds |
| [`AGENTS.md`](./AGENTS.md) | Developer & AI agent invariants |

---

## 🔒 Security & Provenance
Authored by **Souvik Dey (@imsovikde)**. Released under the [MIT License](./LICENSE).
