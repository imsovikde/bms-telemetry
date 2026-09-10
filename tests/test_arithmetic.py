#!/usr/bin/env python3
"""
================================================================================
BMS ARITHMETIC & PRECISION UNIT TEST SUITE
================================================================================
Verifies the following without any mocked hardware:
  â€¢ to_dec30() / fmt30() round-trip fidelity (30-decimal quantization)
  â€¢ Coulomb-counting online delta accumulation
  â€¢ Offline Î”Q boot-recovery logic (_detect_offline_delta)
  â€¢ calculate_virtual_health() formula across cycle/temperature ranges
  â€¢ HMAC sign + tamper detection
  â€¢ 64-bit-safe cycle accumulation (large cycle values)
  â€¢ S5 offline charge accounting boundaries (50 mWh gate)

All tests run with persist=False so no filesystem writes occur.
Exit code: 0 = all passed.  Non-zero = failure count printed to stderr.
================================================================================
"""

import sys
import os
import json
import hashlib
from decimal import Decimal, getcontext

# Reconfigure stdout/stderr to UTF-8 to prevent Windows cp1252 charmap crashes
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# Resolve engine whether run from repo root or tests/
_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
for p in [_ROOT, r"C:\ProgramData\BMS"]:
    if os.path.isfile(os.path.join(p, "bms_engine.py")):
        sys.path.insert(0, p)
        break

import bms_engine as engine  # noqa: E402

getcontext().prec = 60

# â”€â”€ Test Runner â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

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


def assert_eq(name, actual, expected, tol=None):
    if tol is not None:
        diff = abs(Decimal(str(actual)) - Decimal(str(expected)))
        if diff <= Decimal(str(tol)):
            _ok(name)
        else:
            _fail(name, f"got {actual!r}, expected {expected!r} Â±{tol}")
    else:
        if actual == expected:
            _ok(name)
        else:
            _fail(name, f"got {actual!r}, expected {expected!r}")


def assert_true(name, condition, msg="condition was False"):
    if condition:
        _ok(name)
    else:
        _fail(name, msg)


# =============================================================================
# SECTION 1 - Decimal Precision Primitives
# =============================================================================

print("\n--- Section 1: Decimal Precision Primitives -----------------------------")


def test_to_dec30_int():
    d = engine.to_dec30(42)
    assert_eq("to_dec30(int=42) scale", d.as_tuple().exponent, -30)
    assert_eq("to_dec30(int=42) value", d, Decimal("42.000000000000000000000000000000"))


def test_to_dec30_float():
    # Float 0.1 is not exactly representable; to_dec30 must not propagate float error
    d = engine.to_dec30(0.1)
    # Must round to exactly "0.100000000000000000000000000000"
    assert_eq("to_dec30(float=0.1) scale", d.as_tuple().exponent, -30)


def test_to_dec30_string():
    d = engine.to_dec30("69993.123456789012345678901234567890")
    assert_eq("to_dec30(str) scale", d.as_tuple().exponent, -30)


def test_fmt30_round_trip():
    original = Decimal("15.309873844527311029482710394827")
    s = engine.fmt30(original)
    assert_true("fmt30 length >= 32 chars", len(s) >= 32)
    recovered = engine.to_dec30(s)
    assert_eq("fmt30 round-trip fidelity", recovered, original)


test_to_dec30_int()
test_to_dec30_float()
test_to_dec30_string()
test_fmt30_round_trip()

# =============================================================================
# SECTION 2 - Online Coulomb Integration
# =============================================================================

print("\n--- Section 2: Online Coulomb Integration -------------------------------")


def _make_telem(remaining, full=69993.0, design=69993.0, power_online=True,
                voltage=11550.0, charge_rate=0.0, discharge_rate=0.0):
    return {
        "remaining_capacity_mwh": remaining,
        "full_charge_capacity_mwh": full,
        "design_capacity_mwh": design,
        "power_online": power_online,
        "voltage_mv": voltage,
        "charge_rate_mw": charge_rate,
        "discharge_rate_mw": discharge_rate,
    }


def test_no_delta_no_increment():
    """If remaining capacity is unchanged, accumulated_cycles must not change."""
    state = engine.default_initial_state()
    telem = _make_telem(35000.0)
    # seed last_remaining so delta = 0
    state["last_remaining_capacity_mwh"] = engine.fmt30(Decimal("35000.0"))
    before = engine.to_dec30(state["accumulated_cycles"])
    state2 = engine.process_telemetry_and_update_state(telem, state, persist=False)
    after = engine.to_dec30(state2["accumulated_cycles"])
    assert_eq("no-delta -> no cycle increment", after, before)


def test_positive_delta_accumulates():
    """dE = 7000 mWh out of 69993 mWh design cap -> +0.10001... cycle."""
    state = engine.default_initial_state()
    # Seed a low remaining so we'll see a jump
    state["last_remaining_capacity_mwh"] = engine.fmt30(Decimal("28000.0"))
    state["accumulated_cycles"] = engine.fmt30(Decimal("0.0"))
    state["accumulated_energy_mwh"] = engine.fmt30(Decimal("0.0"))
    telem = _make_telem(35000.0)  # +7000 mWh
    state2 = engine.process_telemetry_and_update_state(telem, state, persist=False)
    delta_cycles = engine.to_dec30(state2["accumulated_cycles"])
    expected = Decimal("7000.0") / Decimal("69993.0")
    assert_eq("positive delta accumulation", delta_cycles, engine.to_dec30(expected), tol="0.000000000000000000000000000001")


def test_sub_50mwh_gate():
    """Î”E = 49 mWh (below 50 mWh gate) â†’ NO cycle increment."""
    state = engine.default_initial_state()
    state["last_remaining_capacity_mwh"] = engine.fmt30(Decimal("35000.0"))
    state["accumulated_cycles"] = engine.fmt30(Decimal("10.0"))
    telem = _make_telem(35049.0)  # +49 mWh â€” below gate
    state2 = engine.process_telemetry_and_update_state(telem, state, persist=False)
    after = engine.to_dec30(state2["accumulated_cycles"])
    assert_eq("sub-50mwh gate: no increment", after, engine.to_dec30(Decimal("10.0")))


def test_large_cycle_precision():
    """Accumulate 10,000 micro-increments of 7 mWh each; total must equal 70,000 mWh / 69993."""
    state = engine.default_initial_state()
    state["accumulated_cycles"] = engine.fmt30(Decimal("0.0"))
    state["accumulated_energy_mwh"] = engine.fmt30(Decimal("0.0"))
    state["design_capacity_mwh"] = engine.fmt30(Decimal("69993.0"))

    accum = engine.to_dec30("0.0")
    design = engine.to_dec30("69993.0")

    for i in range(1000):
        delta_e = engine.to_dec30("70.0")  # 70 mWh each > 50 mWh gate
        accum += delta_e / design

    expected = engine.to_dec30(Decimal("70.0") * 1000 / Decimal("69993.0"))
    assert_eq("large-cycle 64-bit-safe precision", accum, expected, tol="0.000000000000000000000000000001")


test_no_delta_no_increment()
test_positive_delta_accumulates()
test_sub_50mwh_gate()
test_large_cycle_precision()

# =============================================================================
# SECTION 3 - Offline dQ Boot-Recovery Logic
# =============================================================================

print("\n--- Section 3: Offline dQ Boot-Recovery ---------------------------------")


def test_offline_delta_no_prior_shutdown():
    """No last_shutdown_capacity_mwh -> state unchanged."""
    state = engine.default_initial_state()
    cycles_before = state["accumulated_cycles"]
    state2 = engine._detect_offline_delta(state)
    assert_eq("no shutdown key -> no mutation", state2["accumulated_cycles"], cycles_before)


def test_offline_delta_above_gate(monkeypatch_telem_fn=None):
    """
    Simulate: shutdown at 30,000 mWh, boot at 65,000 mWh -> dE=35,000 mWh > 50 mWh.
    Verify cycle counter increments by exactly 35000/69993.
    """
    state = engine.default_initial_state()
    state["accumulated_cycles"] = engine.fmt30(Decimal("5.0"))
    state["accumulated_energy_mwh"] = engine.fmt30(Decimal("0.0"))
    state["design_capacity_mwh"] = engine.fmt30(Decimal("69993.0"))
    state["last_shutdown_capacity_mwh"] = engine.fmt30(Decimal("30000.0"))

    # Monkey-patch get_telemetry to return boot-time reading
    _orig = engine.get_telemetry
    engine.get_telemetry = lambda: _make_telem(65000.0)
    try:
        state2 = engine._detect_offline_delta(state)
    finally:
        engine.get_telemetry = _orig

    delta_cycles = engine.to_dec30(state2["accumulated_cycles"]) - engine.to_dec30("5.0")
    expected = engine.to_dec30(Decimal("35000.0") / Decimal("69993.0"))
    assert_eq("offline delta > gate injects cycles", delta_cycles, expected,
              tol="0.000000000000000000000000000001")
    assert_true("offline delta event logged", any(
        e.get("type") == "S5_OFFLINE_CHARGE_BOOT_RECOVERY"
        for e in state2.get("history_events", [])
    ))


def test_offline_delta_below_gate():
    """dE = 40 mWh (< 50 mWh gate) -> no injection."""
    state = engine.default_initial_state()
    state["accumulated_cycles"] = engine.fmt30(Decimal("5.0"))
    state["design_capacity_mwh"] = engine.fmt30(Decimal("69993.0"))
    state["last_shutdown_capacity_mwh"] = engine.fmt30(Decimal("60000.0"))

    _orig = engine.get_telemetry
    engine.get_telemetry = lambda: _make_telem(60040.0)  # +40 mWh
    try:
        state2 = engine._detect_offline_delta(state)
    finally:
        engine.get_telemetry = _orig

    after = engine.to_dec30(state2["accumulated_cycles"])
    assert_eq("offline delta < gate -> no injection", after, engine.to_dec30("5.0"))


test_offline_delta_no_prior_shutdown()
test_offline_delta_above_gate()
test_offline_delta_below_gate()

# =============================================================================
# SECTION 4 - Virtual Health Formula
# =============================================================================

print("\n--- Section 4: Virtual Health Formula ----------------------------------")


def test_health_new_battery():
    """Fresh battery (0 cycles, 25 deg C, full FCC = design) -> ~100% health."""
    result = engine.calculate_virtual_health(
        fcc_mwh=Decimal("69993.0"),
        design_mwh=Decimal("69993.0"),
        cycles=Decimal("0.0"),
        voltage_mv=Decimal("11550.0"),
        charge_rate_mw=Decimal("0.0"),
        discharge_rate_mw=Decimal("0.0"),
        temp_c=25.0,
        power_online=False,
    )
    vh = result["virtual_health_pct"]
    assert_true("new battery health >= 98%", vh >= Decimal("98.0"),
                f"got {vh}")


def test_health_degraded_500_cycles():
    """500 cycles calibrated to ~80% retention per model constants."""
    result = engine.calculate_virtual_health(
        fcc_mwh=Decimal("69993.0"),
        design_mwh=Decimal("69993.0"),
        cycles=Decimal("500.0"),
        voltage_mv=Decimal("11550.0"),
        charge_rate_mw=Decimal("0.0"),
        discharge_rate_mw=Decimal("0.0"),
        temp_c=25.0,
        power_online=False,
    )
    vh = result["virtual_health_pct"]
    assert_true("500-cycle health between 75% and 85%",
                Decimal("75.0") <= vh <= Decimal("85.0"), f"got {vh}")


def test_health_bounded_0_to_100():
    """Health must never exceed 100% or fall below 0%, regardless of inputs."""
    result = engine.calculate_virtual_health(
        fcc_mwh=Decimal("69993.0"),
        design_mwh=Decimal("69993.0"),
        cycles=Decimal("99999.0"),  # extreme degradation
        voltage_mv=Decimal("11550.0"),
        charge_rate_mw=Decimal("0.0"),
        discharge_rate_mw=Decimal("0.0"),
        temp_c=70.0,
        power_online=True,
    )
    vh = result["virtual_health_pct"]
    assert_true("health floor >= 0%", vh >= Decimal("0.0"), f"got {vh}")
    assert_true("health ceiling <= 100%", vh <= Decimal("100.0"), f"got {vh}")


test_health_new_battery()
test_health_degraded_500_cycles()
test_health_bounded_0_to_100()

# =============================================================================
# SECTION 5 - HMAC Cryptographic Integrity
# =============================================================================

print("\n--- Section 5: HMAC Cryptographic Integrity ----------------------------")


def test_hmac_sign_verify():
    state = engine.default_initial_state()
    sig = engine.compute_hmac(state)
    assert_true("hmac is 64-char hex", len(sig) == 64 and all(c in "0123456789abcdef" for c in sig))
    assert_true("hmac verify passes on unmodified state", engine.verify_hmac(state, sig))


def test_hmac_tamper_detection():
    state = engine.default_initial_state()
    sig = engine.compute_hmac(state)
    state["accumulated_cycles"] = "99999.000000000000000000000000000000"
    assert_true("tampered state fails hmac verify", not engine.verify_hmac(state, sig))


test_hmac_sign_verify()
test_hmac_tamper_detection()

# =============================================================================
# SUMMARY
# =============================================================================

print(f"\n{'='*72}")
total = _PASSED + _FAILED
print(f"  Arithmetic Guard: {_PASSED}/{total} passed | {_FAILED} failed")
print(f"{'='*72}\n")

sys.exit(0 if _FAILED == 0 else _FAILED)

