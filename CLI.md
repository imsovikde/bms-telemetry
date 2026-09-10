# BMS Command-Line Interface (CLI) Reference Manual

The `bms` utility provides universal, single-command access to low-level hardware battery registers, 30-decimal arithmetic cycles, electrochemical degradation diagnostics, and multi-layer persistence controls across Windows, Linux, and macOS.

---

## 1. Global Command Invocation

`bms` is installed globally in system PATH and executable from **any working directory** (`C:\`, `/root`, `~`, `/tmp`):

```bash
bms [SUBCOMMAND] [OPTIONS]
```

### Available Subcommands

| Subcommand | Description | Default Target |
| :--- | :--- | :--- |
| `bms` / `bms status` | **Default:** Prints the ANSI-formatted 30-decimal telemetry and health dashboard. | Terminal STDOUT |
| `bms live` / `bms tui` | **Real-Time Interactive TUI (4 Hz):** Continuous Coulomb integration, live 30-decimal tickers, wattage oscilloscope, zero-flicker double-buffered ANSI dashboard. | Interactive Terminal |
| `bms ui` / `bms web` | **Generative Web Dashboard:** Launches local browser glassmorphism UI with real-time SVG circular gauges and Server-Sent Events (SSE). | Local Web Browser |
| `bms full` / `bms json` | Dumps raw cryptographic state and ACPI register telemetry in JSON format. | Machine Readable / Pipe |
| `bms test-100` | Executes the automated 100-cycle deep verification and stress test harness. | Self-Test Suite |
| `bms sync-hw` | Forces cryptographic synchronization across all hardware storage tiers. | Hardware Mirrors |
| `bms daemon` | Runs the persistent background polling loop (<0.01% CPU, 60s cadence). | Background Process |
| `bms fix-bio` | Dispatches elevated Windows Hello biometric credential provider repair. | UAC Elevated Session |
| `bms help` | Displays the command syntax and usage overview. | Terminal STDOUT |

---

## 2. Command Details & Examples

### `bms status` (Default)
Displays the formatted high-precision dashboard including hardware registers, state of charge, multi-factor electrochemical health, compensatory cycles, and persistence replica status.

```bash
# Windows Command Prompt or PowerShell:
C:\Users\user> bms

# Linux or macOS Terminal:
user@host:~$ bms status
```

**Key Metrics Displayed:**
- **Silicon Master Key (Hex):** First 16 and last 8 characters of derived PBKDF2-HMAC-SHA256 hardware root key.
- **State of Charge (SoC%):** Precise percentage to 30 decimal places:
  `100.000000000000000000000000000000%`
- **Virtual Health (SoH%):** Multi-factor electrochemical degradation percentage:
  `98.829196661678652863705171408736%`
- **Accumulated Cycles:** Cumulative charging cycles computed via Coulomb counting:
  `15.309873844527311029482710394827`
- **S5 Offline Charge Audit:** Offline charge events detected and energy gained while powered off.

---

### `bms full` / `bms json`
Emits an untruncated JSON structure suitable for programmatic consumption, telemetry ingestion pipelines, and shell pipeline scripting.

```bash
bms full | jq .state.virtual_health_percentage
```

**JSON Output Schema:**
```json
{
  "timestamp_utc": "2026-09-09T18:55:55.709075+00:00",
  "telemetry": {
    "active": true,
    "charging": false,
    "discharging": false,
    "power_online": true,
    "remaining_capacity_mwh": 69993.0,
    "full_charge_capacity_mwh": 69993.0,
    "design_capacity_mwh": 69993.0,
    "voltage_mv": 11550.0,
    "charge_rate_mw": 0.0,
    "discharge_rate_mw": 0.0,
    "source": "Windows WMI ACPI Subsystem"
  },
  "state": {
    "magic": "BMS_HW_NVRAM_V2",
    "version": "3.0.0",
    "precision_decimal_places": 30,
    "hardware_id": "12B4C080-2150-11EE-B678-E9E74C343D00::XLCZ513637D0123::123456789",
    "monotonic_seq": 106,
    "battery_serial": "123456789",
    "design_capacity_mwh": "69993.000000000000000000000000000000",
    "last_full_charge_capacity_mwh": "69993.000000000000000000000000000000",
    "last_remaining_capacity_mwh": "69993.000000000000000000000000000000",
    "accumulated_cycles": "15.309873844527311029482710394827",
    "accumulated_energy_mwh": "1071584.000000000000000000000000000000",
    "virtual_health_percentage": "98.829196661678652863705171408736",
    "state_of_charge_percentage": "100.000000000000000000000000000000",
    "cycle_degradation_loss_pct": "1.146968033262214056042949952849",
    "thermal_stress_loss_pct": "0.023835305059133080251878638415",
    "voltage_stress_loss_pct": "0.000000000000000000000000000000",
    "last_terminal_voltage_mv": "11550.000000000000000000000000000000",
    "s5_offline_charges_count": 1,
    "s5_offline_cycles_accumulated": "0.928564284999928564284999928564",
    "s5_offline_energy_mwh": "64993.000000000000000000000000000000"
  },
  "hardware_identity": {
    "motherboard_uuid": "12B4C080-2150-11EE-B678-E9E74C343D00",
    "baseboard_serial": "XLCZ513637D0123",
    "battery_serial": "123456789",
    "master_key_fingerprint": "63c0ab3e4d04339d"
  }
}
```

---

### `bms test-100`
Executes the automated 100-cycle stress test evaluating arithmetic stability, multi-factor equation sweeps, HMAC authentication, S5 offline deltas, and wipe self-healing:

```bash
bms test-100
```
- **Phase 1 (Tests 1–20):** 30-Decimal micro-step integration ($0.000123...$ mWh deltas) confirming zero float collapse.
- **Phase 2 (Tests 21–40):** Degradation sweep across cycles (0–1000) and temperatures (20°C–55°C).
- **Phase 3 (Tests 41–60):** Cryptographic signing and tamper rejection (bit-flip rejection verification).
- **Phase 4 (Tests 61–80):** S5 power-off charge delta detection across varying energy jumps.
- **Phase 5 (Tests 81–100):** Simulated C: wipe and recovery from secondary hardware storage tiers.

---

### `bms sync-hw`
Forces an immediate cryptographic sync and validates all accessible hardware storage replicas:
```bash
bms sync-hw
```
Outputs active replica paths (`D:\`, `S:\`, `/var/lib/bms`, `C:\ProgramData\BMS`).

---

### `bms daemon`
Launches the persistent background cycle tracking loop. Typically managed by the OS service manager (systemd, launchd, or Windows Startup VBS):
```bash
bms daemon
```
- **Tick Interval:** 60 seconds
- **CPU Overhead:** `<0.01%`
- **Memory Footprint:** `~14 MB`

---

## 3. Exit Codes

| Exit Code | Meaning |
| :--- | :--- |
| `0` | Success / Telemetry acquired / Test suite passed. |
| `1` | General error (missing runtime, permission error, unhandled exception). |
| `2` | Cryptographic signature validation failure (tampered storage block). |
