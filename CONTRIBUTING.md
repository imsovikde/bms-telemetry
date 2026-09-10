# Contributing to BMS Telemetry

Thank you for your interest in contributing to **BMS Telemetry** (`bms`). We maintain an uncompromising standard of technical rigor, zero-window headless execution, deterministic 30-decimal arithmetic, and hardware-level ACPI driver integrity.

---

## Development Philosophy & Code Invariants

1. **Zero-Window Headless Invariant**:
   - The daemon MUST NEVER allocate a console window, spawn an interactive terminal, or trigger window activation focus shifts.
   - Any telemetry query on Windows MUST prefer in-process COM (`win32com.client`).
   - Any fallback subprocess invocation on Windows MUST pass `creationflags=subprocess.CREATE_NO_WINDOW` (`0x08000000`) and `STARTUPINFO(dwFlags=STARTF_USESHOWWINDOW, wShowWindow=SW_HIDE)`.
2. **Deterministic Arithmetic Invariant**:
   - All Coulomb accumulation and degradation calculations MUST utilize Python's `Decimal` module quantized to 30 decimal places (`DEC_30`, rounding `ROUND_HALF_UP`) with an internal precision of 60 digits (`getcontext().prec = 60`).
   - Standard IEEE 754 floating-point operations are strictly forbidden in cycle state accumulation.
3. **Anti-Mock Invariant**:
   - Production telemetry drivers MUST probe real OS hardware interfaces (WMI `root\wmi` on Windows, sysfs `/sys/class/power_supply` on Linux, `AppleSmartBattery` / `pmset` on macOS). Synthetic mocks in production drivers are strictly prohibited.
4. **Zero-Data-Loss Invariant**:
   - State mutations MUST be signed with HMAC-SHA256 keyed to immutable silicon hardware identifiers and mirrored across all accessible physical storage tiers (`C:\ProgramData\BMS`, `~/.bms`, `D:\`, `S:\`, `E:\`, `/var/lib/bms`).

---

## Local Development Workflow

### Prerequisites
- Python 3.10, 3.11, or 3.12
- Windows: `pywin32` (`pip install pywin32`)
- Linux: `systemd` or `cron`
- macOS: `launchd`

### Cloning & Branching
```bash
git clone https://github.com/imsovikde/bms-telemetry.git
cd bms-telemetry
git checkout -b feat/your-feature-name
```

### Running Tests
Before committing any changes, run the local verification suite:

```bash
# 1. Execute the 21-test arithmetic & precision suite (runs in-memory, persist=False)
python tests/test_arithmetic.py

# 2. Execute the 100-cycle stress test & self-healing wipe harness
python bms_engine.py test-100

# 3. Verify real-time telemetry extraction
python bms_engine.py status
```

### Code Style & Quality
- Code formatting follows PEP 8 standards.
- Ensure all public functions include clear docstrings.
- Verify that `tests/test_arithmetic.py` passes 21/21 tests with zero failures.

---

## Submitting Pull Requests

1. Commit atomically with descriptive Conventional Commit messages (e.g., `feat(telemetry): ...`, `fix(service): ...`).
2. Ensure all 5 CI guards pass in GitHub Actions (`ci-guards.yml` on Windows, Linux, and macOS).
3. Open a Pull Request referencing any related issues.
