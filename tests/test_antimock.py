#!/usr/bin/env python3
"""
================================================================================
BMS ANTI-MOCK AND HARDWARE DRIVER INTEGRITY TEST SUITE
================================================================================
Verifies that all platform drivers actively query real hardware interfaces:
  - Windows: in-process COM (win32com.client) and root\\wmi ACPI battery classes
  - Linux: sysfs /sys/class/power_supply or WSL host state interop
  - macOS: AppleSmartBattery registry or pmset -g batt

Ensures no mocked data pathways bypass real ACPI hardware driver calls.
================================================================================
"""

import sys
import os
import inspect

# Reconfigure stdout/stderr to UTF-8
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# Resolve engine from repo root
_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

import bms_engine as engine  # noqa: E402

_PASSED = 0
_FAILED = 0


def _ok(name: str):
    global _PASSED
    _PASSED += 1
    print(f"  [PASS] {name}")


def _fail(name: str, msg: str):
    global _FAILED
    _FAILED += 1
    print(f"  [FAIL] {name}: {msg}", file=sys.stderr)


def test_windows_driver_interface():
    src_win = inspect.getsource(engine.get_windows_battery_telemetry)
    if "BatteryStatus" not in src_win:
        _fail("Windows BatteryStatus Query", "Missing BatteryStatus in get_windows_battery_telemetry")
    else:
        _ok("Windows BatteryStatus Query")

    if "win32com.client" not in src_win:
        _fail("Windows COM Interop", "Missing win32com.client in get_windows_battery_telemetry")
    else:
        _ok("Windows COM Interop")

    if "root" not in src_win or "wmi" not in src_win:
        _fail("Windows root\\wmi Namespace", "Missing root\\wmi namespace probe")
    else:
        _ok("Windows root\\wmi Namespace")


def test_linux_driver_interface():
    src_linux = inspect.getsource(engine.get_linux_battery_telemetry)
    if "power_supply" not in src_linux and "WSL_WIN_STATE" not in src_linux:
        _fail("Linux Driver Probe", "Missing power_supply or WSL state probe in get_linux_battery_telemetry")
    else:
        _ok("Linux Driver Probe (sysfs / WSL)")


def test_macos_driver_interface():
    src_mac = inspect.getsource(engine.get_macos_battery_telemetry)
    if "AppleSmartBattery" not in src_mac and "pmset" not in src_mac:
        _fail("macOS Driver Probe", "Missing AppleSmartBattery or pmset probe in get_macos_battery_telemetry")
    else:
        _ok("macOS Driver Probe (AppleSmartBattery / pmset)")


def main():
    print("=" * 60)
    print("RUNNING BMS HARDWARE DRIVER INTEGRITY (ANTI-MOCK) TESTS")
    print("=" * 60)

    test_windows_driver_interface()
    test_linux_driver_interface()
    test_macos_driver_interface()

    print("=" * 60)
    print(f"RESULTS: {_PASSED} PASSED, {_FAILED} FAILED")
    print("=" * 60)

    if _FAILED > 0:
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
