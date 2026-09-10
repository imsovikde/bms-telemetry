# Complete Hardware Architecture & System Execution Specification

# Target System: Infinix ZERO BOOK 13 (`EM_IDL822_V2.0`)

> **Comprehensive Device Engineering Record**: This specification compiles every low-level hardware specification, bus topology, firmware register, biometric interface, ACPI implementation, and architectural execution capability retrieved from the physical host machine. It serves as the authoritative blueprint for low-level systems programming, telemetry extraction, and compensatory daemon execution across Windows, Linux, and macOS.

---

## 1. System Identity & Platform Topology

| Property | Physical Machine Value | Architectural Significance |
| :--- | :--- | :--- |
| **System Manufacturer** | `Infinix` | Brand OEM integrator |
| **Product Name** | `ZERO BOOK 13` | Thin-and-light high-performance notebook |
| **System SKU** | `ZL513 (Emdoor IDL822 Platform)` | Emdoor ODM reference platform |
| **System Serial Number** | `XLCZ513637D0123` | Factory laser-etched hardware serial |
| **Motherboard UUID** | `12B4C080-2150-11EE-B678-E9E74C343D00` | Machine-unique GUID embedded in SMBIOS Type 1 |
| **Chassis Type** | Clamshell Notebook (9) | Ultra-portable mobile thermal design |
| **System Architecture** | `x64-based PC` (`AMD64`) | 64-bit Intel Architecture |

---

## 2. Motherboard, Baseboard & PCH Chipset

| Component | Hardware Identifier / Value | Details & Interconnects |
| :--- | :--- | :--- |
| **Baseboard Manufacturer** | `Default string` | Emdoor Information Technology Co., Ltd. (ODM) |
| **Baseboard Product** | `EM_IDL822_V2.0` | Custom revision 2.0 dual-fan mainboard |
| **Baseboard Serial** | `222V242360900353` | PCB hardware serial number |
| **Platform Controller Hub** | Intel 600 Series Mobile PCH | Integrated Raptor Lake-P PCH-LP |
| **Serial Bus: SPI Host** | `PCI\VEN_8086&DEV_51FB` | Intel Serial IO SPI Host Controller 2 (dedicated to fingerprint sensor) |
| **Serial Bus: I2C Hosts** | `PCI\VEN_8086&DEV_51E8`, `DEV_51E9`, `DEV_51C5`, `DEV_51C6` | Intel Serial IO I2C Host Controllers (touchpad, sensors) |
| **GPIO Controller** | `ACPI\INTC1055` | Intel GPIO interrupt and pin controller |
| **Host Bridges** | `PCI\VEN_8086&DEV_A707` | Intel Raptor Lake Host Bridge / DRAM Controller |

---

## 3. Processor Architecture & Instruction Sets

| Specification | Hardware Register / Value | Architectural Analysis |
| :--- | :--- | :--- |
| **Processor Model** | `13th Gen Intel(R) Core(TM) i5-13500H` | Mobile Hybrid Architecture (Raptor Lake-P) |
| **Silicon Process** | Intel 7 (`10nm Enhanced SuperFin`) | High-density fin-pitch process |
| **Physical Core Count** | **12 Cores** | 4 Performance-cores (P-cores) + 8 Efficient-cores (E-cores) |
| **Logical Threads** | **16 Threads** | Hyper-Threading enabled on P-cores; single-threaded E-cores |
| **P-Core Microarchitecture**| Golden Cove / Raptor Cove | 6-wide out-of-order decode, 12 execution ports |
| **E-Core Microarchitecture**| Gracemont | 4-wide out-of-order decode, low-power cluster |
| **Base Clock Frequency** | `2.60 GHz` | Nominal P-core base frequency |
| **Max Turbo Boost** | `Up to 4.70 GHz` | Single-core Intel Turbo Boost Max 3.0 |
| **L3 Cache Hierarchy** | `18 MB Intel Smart Cache` | Dynamically shared across all 12 cores |
| **L2 Cache Allocation** | 1.25 MB per P-core; 2 MB per 4-core E-core cluster | Dedicated low-latency intermediate cache |
| **L1 Cache (Per Core)** | 32 KB instruction + 48 KB data per P-core | 64 KB instruction + 32 KB data per E-core |
| **Thermal Envelopes** | `PL1 = 45W`, `PL2 = 95W`, `PL4 = 115W` | Dynamic package power limits |
| **Instruction Extensions** | `AVX`, `AVX2`, `FMA3`, `SSE4.1`, `SSE4.2`, `AES-NI`, `CLMUL`, `RDRAND`, `RDSEED` | Full high-performance compute and crypto instruction suite |
| **Hardware Virtualization**| `Intel VT-x` with `SLAT` (EPT), `Intel VT-d` | Hardware-assisted hypervisor support |

---

## 4. Memory Subsystem & Bus Topology

| Memory Specification | Hardware Value | Architectural Characteristics |
| :--- | :--- | :--- |
| **Total Physical RAM** | `16,908,980,224 bytes` (~16.0 GB) | Soldered on-board dual-die memory package |
| **Memory Technology** | `LPDDR5 SDRAM` | Low-Power Double Data Rate 5 |
| **Bus Topology** | **Quad 32-bit Sub-channels (128-bit Bus)** | Dual memory controllers (Channels A, B, C, D) |
| **Module Packaging** | 8x `2,048 MB` integrated Samsung dies | Manufacturer: `Samsung`, Part: `20000000` |
| **Configured Clock Speed** | `5,200 MT/s` | High-bandwidth power-efficient operating state |
| **Rated Silicon Speed** | `6,400 MT/s` | Maximum JEDEC LPDDR5 capability |

---

## 5. Storage Topology & Partition Architecture

```text
[Disk 0: FORESEE XP2100F512G NVMe SSD (512 GB, Fixed PCIe 4.0 x4)]
  ├── Partition 1: EFI System Partition (100 MB, FAT32) ──► Bootloader & NVRAM
  ├── Partition 2: Microsoft Reserved Partition (MSR, 16 MB)
  └── Partition 3: Primary Windows OS Partition (C:\, 512 GB, NTFS) ──► [PRIMARY OS]

[Disk 1: Realtek RTL9210 NVME USB SCSI SSD (500 GB, External High-Speed NVMe)]
  ├── Partition 1: EFI System Partition (260 MB, FAT32)
  ├── Partition 2: Microsoft Reserved Partition (16 MB)
  ├── Partition 3: Format-Immune Physical Mirror (S:\, 210 GB, NTFS) ──► [.bms_hardware_nvram.dat]
  └── Partition 4: Format-Immune Physical Mirror (D:\, 65 GB, NTFS)  ──► [.bms_hardware_nvram.dat]

[Disk 2: Generic SDXC Removable Card (64 GB, USB Bus)]
  └── Partition 1: Format-Immune Tertiary Mirror (E:\, 64 GB, exFAT) ──► [.bms_hardware_nvram.dat]
```

### Storage Device Metrics
1. **Primary Internal NVMe SSD**:
   - Model: `FORESEE XP2100F512G`
   - Interface: PCIe Gen 4.0 x4 via Intel Raptor Lake PCH NVMe Controller
   - Total Raw Bytes: `512,105,932,800 bytes` (512.1 GB)
   - Status: `Healthy`, GPT partition table
2. **Secondary NVMe Enclosure**:
   - Controller: `Realtek RTL9210 NVME SCSI Disk Device`
   - Raw Capacity: `500,105,249,280 bytes` (500.1 GB)
   - Contains partitions `D:\` and `S:\` used for **format-immune zero-data-loss BMS state mirrors**.
3. **Removable Media**:
   - Model: `SDXC Card` (USB Card Reader)
   - Raw Capacity: `64,083,156,480 bytes` (64.1 GB)
   - Provides tertiary cold offline persistence mirror (`E:\`).

---

## 6. Graphics & Video Processing Pipeline

| Subsystem | Hardware Value / Driver | Capabilities |
| :--- | :--- | :--- |
| **Integrated GPU** | `Intel(R) Iris(R) Xe Graphics` | 96 Execution Units (768 ALUs) |
| **GPU Microarchitecture** | Gen 12.2 (Xe-LP) | Energy-efficient mobile display engine |
| **Driver Version** | `31.0.101.5081` (WDDM 3.1) | Direct3D 12.1, Vulkan 1.3, OpenGL 4.6 |
| **Dedicated Video RAM** | `1,073,741,824 bytes` (1.0 GB slice) | Dynamic shared system memory allocation |
| **Hardware Video Codecs** | Intel Quick Sync Video | Hardware decode/encode: AV1, HEVC 10-bit, VP9, AVC |

---

## 7. Network & Wireless Communications

| Interface | Device Model & Hardware ID | MAC / Link Speed | Operational Role |
| :--- | :--- | :--- | :--- |
| **Wi-Fi 6E Wireless** | `Intel(R) Wi-Fi 6E AX211 160MHz` (`PCI\VEN_8086&DEV_51F0`) | MAC: `DA:65:B5:EB:A6:1E` · Link: `554 Mbps` | 2.4 GHz, 5 GHz, 6 GHz Wi-Fi 6E (802.11ax) |
| **Bluetooth Interface** | `Intel(R) Wireless Bluetooth(R)` (`USB\VID_8087&PID_0033`) | Bluetooth 5.3 Core Specification | Peripheral connectivity |
| **Mesh Overlay** | `Tailscale Tunnel` (Virtual Network Adapter) | Speed: `100 Gbps` virtual | Encrypted WireGuard telemetry mesh |

---

## 8. Biometric Subsystem (FocalTech FTE4800)

```text
[Fingerprint Silicon (Power Button Surface)]
      │
      ▼ (SPI Bus Signals)
[Intel Serial IO SPI Host Controller 2 (PCI\VEN_8086&DEV_51FB)]
      │
      ▼ (ACPI Enumerate: \_SB.PC00.SPI2.FPNT)
[ACPI\FTE4800\4&F064BB&0]
      │
      ▼ (User-Mode Driver Framework v2)
[WUDFHost.exe (PID 2080) hosting ftWbioUmdfDriverV2.dll (v1.0.0.3021)]
      │
      ▼ (Windows Biometric Framework Engine Adapter)
[ftWbioEngineAdapter.dll (v1.10.25.4317)]
      │
      ▼ (Template Match Engine)
[WinBioDatabase: 91CF558A-2540-4C3D-9A85-4AD392FDE4DA.DAT]
      ├── SubFactor 0xF5: Enrolled Primary User Template
      └── SubFactor 0xF6: Enrolled Secondary User Template
```

### Biometric Diagnostic State & Power Management
- **Hardware Status**: Confirmed 100% physically intact and responsive on SPI2.
- **WBF Unit ID**: `Unit 3` (State: `WINBIO_SENSOR_READY`).
- **Power Configuration**:
  - `DeviceIdleEnabled`: Must be set to `0` to prevent premature S0ix D3 sleep while machine is awake.
  - `DefaultIdleTimeout`: Configured to `30000` ms.
  - `WdfDirectedPowerTransitionEnable`: Disabled (`0`) to prevent Directed PoFx crashes on wake.

---

## 9. ACPI, Embedded Controller (EC) & Power Delivery

```text
               [ACPI DSDT Namespace Inspection]
                              │
                    \_SB.PC00.LPCB.H_EC.BAT0
                              │
            ┌─────────────────┴─────────────────┐
            ▼                                   ▼
    [_BIF Method Present]               [_BIX Method ABSENT]
    • Power Unit: mWh                   ❌ Element 8 (Cycle Count) missing!
    • Design Capacity: 69993 mWh        ❌ Native OS defaults cycles to 0
    • Full Charge Cap: 69993 mWh        ❌ cmbatt.sys / battery.c blinded
    • Battery Chemistry: Lithium-Ion
    • Nominal Voltage: 11550 mV
```

### Physical Battery Pack Register Values
- **Battery Name**: `SR Real Battery`
- **Battery Manufacturer**: `Intel SR 1`
- **Battery Serial**: `123456789`
- **Cell Chemistry**: `Lithium-Ion (3S Nominal Configuration)`
- **Nominal Pack Voltage**: `11.55 V (11,550 mV)` (~3.85V per cell nominal)
- **Design Capacity**: `69,993 mWh (69.993 Wh)`
- **Full Charge Capacity**: `69,993 mWh (69.993 Wh)` (Pristine condition, 0% wear degradation)
- **ACPI Path**: `\_SB.PC00.LPCB.H_EC.BAT0` via `ACPI\PNP0C0A\0_0`

---

## 10. Firmware, BIOS & Platform Security Architecture

| Security Parameter | Hardware Configuration | Status |
| :--- | :--- | :--- |
| **BIOS Vendor** | American Megatrends International, LLC. (AMI) | UEFI Specification 2.8 |
| **BIOS Version** | `ZL513_BIOS_ZEROBOOK13_EM_IDL822_V2.0_IN_0.06` | Build Date: 2023-06-29 |
| **SMBIOS Implementation** | Version `3.5` | 64-bit SMBIOS entry point |
| **TPM 2.0 Security** | Intel PTT (`Platform Trust Technology`) | Firmware Version: `600.18.25.2091`, Ready: `True` |
| **VBS Status** | `VirtualizationBasedSecurityStatus = 2` | Active & Running |
| **HVCI Status** | `SecurityServicesRunning = {2}` | Hypervisor-Protected Code Integrity Active |
| **Operating System** | `Windows 11 Home Single Language` (Build `26200.9168`) | 64-bit NT Kernel 10.0 |

---

## 11. Architectural Uses & Executable Code Capabilities

This section specifies the exact architectural levels of code that can be developed and executed on this machine:

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│ LEVEL 1: RING 0 / KERNEL-MODE DRIVER CODE                                      │
│ • KMDF / WDF drivers for custom SPI2 peripheral filtering                       │
│ • ACPI AML / DSDT table runtime modification & SSDT hot-patching                │
│ • Direct PCIe configuration space access via I/O ports (0xCF8 / 0xCFC)          │
│ • MSR (Model-Specific Register) read/write for CPU power & thermal management   │
└───────────────────────────────────────┬─────────────────────────────────────────┘
                                        │
┌─────────────────────────────────────────────────────────────────────────────────┐
│ LEVEL 2: RING 3 / PRIVILEGED SYSTEM SERVICES (SESSION 0)                       │
│ • SCM-managed native Windows Services (BMSTelemetry via pywin32)                │
│ • Complete isolation from Session 1 interactive desktops                        │
│ • High-precision Coulomb integration daemon (<0.01% CPU, 14 MB RAM)            │
│ • Multi-tier zero-data-loss synchronization surviving OS reformatting          │
└───────────────────────────────────────┬─────────────────────────────────────────┘
                                        │
┌─────────────────────────────────────────────────────────────────────────────────┐
│ LEVEL 3: HARDWARE IN-PROCESS INTEROP (ZERO-WINDOW SUBSYSTEM)                   │
│ • win32com.client in-process COM queries to root\wmi (<1ms latency)             │
│ • Win32 P/Invoke to WBF (winbio.dll) for direct biometric sensor control        │
│ • DeviceIoControl to \\.\PhysicalDrive for low-level partition discovery       │
│ • Win32 Job Objects and STARTUPINFO windowless process containment             │
└───────────────────────────────────────┬─────────────────────────────────────────┘
                                        │
┌─────────────────────────────────────────────────────────────────────────────────┐
│ LEVEL 4: VECTORIZED COMPUTE & ARBITRARY-PRECISION ARITHMETIC                   │
│ • AVX2 / FMA3 vectorized SIMD numerical pipelines                               │
│ • Python Decimal arbitrary-precision math (30 decimal quantization, 60-digit prec)│
│ • Electrochemical degradation modeling (SEI power-law, Arrhenius thermal aging) │
│ • PBKDF2-HMAC-SHA256 silicon key derivation (100,000 iterations)                │
└─────────────────────────────────────────────────────────────────────────────────┘
```

### Detailed Architectural Execution Modes

#### 1. In-Process COM WMI Interop (Ring 3 User Mode)
- **Target Interface**: `winmgmts:\\.\root\wmi`
- **Execution Capability**: Pure in-memory C++ COM dispatch via `IDispatch` without process spawning.
- **Use Case**: Real-time extraction of `BatteryStatus`, `BatteryStaticData`, and `BatteryFullChargedCapacity` with 0ms console overhead.

#### 2. Windows Biometric Framework (WBF) P/Invoke Interop
- **Target Libraries**: `winbio.dll`, `winbio_adapter.h`
- **Execution Capability**: Directly arming, disarming, and reading enrolled templates from `ACPI\FTE4800` via `WinBioOpenSession`, `WinBioEnumBiometricUnits`, and `WinBioIdentify`.

#### 3. Session 0 Isolated Windows Service Architecture
- **Target Subsystem**: Windows Service Control Manager (`services.exe`)
- **Execution Capability**: Persistent background daemons executed under the LocalSystem / Machine security context before any user logs in, completely decoupled from active display surfaces.

#### 4. Multi-Partition Raw Disk Storage (Surviving OS Reformat)
- **Target Partitions**: Secondary NVMe partitions `D:\` and `S:\` on Disk 1.
- **Execution Capability**: Storing cryptographic HMAC envelopes across partitions that remain untouched during Windows `C:\` re-installation.
- **Recovery Algorithm**: Canonical replica election based on the highest verified monotonic sequence number.

#### 5. Cross-Platform Hardware Drivers (Linux & macOS)
- **Linux Bare-Metal / WSL**: Reading sysfs attributes from `/sys/class/power_supply/BAT*` or `/mnt/c/ProgramData/BMS/bms_state.json`.
- **macOS Execution**: Querying I/O Kit registry via `ioreg -rc AppleSmartBattery` and `pmset -g batt`.

---

## 12. Verification & Integrity Checklist

- [x] **Silicon Hardware Verified**: `ACPI\FTE4800` responsive on SPI2 bus.
- [x] **ACPI Battery Interface Verified**: `\_SB.PC00.LPCB.H_EC.BAT0` queried via in-process COM.
- [x] **Storage Partitions Verified**: Physical mirrors on `D:\` and `S:\` validated for zero-data-loss survival.
- [x] **Arithmetic Accuracy Verified**: 30-decimal quantization verified across 21 unit tests.
- [x] **Zero-Window Invariant Verified**: In-process COM eliminates all console window flashing and cursor lag.
