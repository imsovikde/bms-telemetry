# BMS Telemetry Technical Specification

## 1. Precision & Arithmetic Standards
- **Precision Floor:** 30 Decimal Places.
- **Internal Working Context:** 60 Decimal Digits (`decimal.getcontext().prec = 60`).
- **Rounding Algorithm:** `ROUND_HALF_UP` (Deterministic commercial rounding).
- **String Serialization:** Strictly fixed notation `0.000000000000000000000000000000` (scientific exponential notation forbidden in state files).

---

## 2. Cryptographic Envelope Specification

State blocks are sealed in a JSON envelope verified by HMAC-SHA256:

```json
{
  "magic": "BMS_HW_NVRAM_V2",
  "hardware_id": "<UUID>::<BASEBOARD_SERIAL>::<BATTERY_SERIAL>",
  "hmac_sha256": "<64-character-hex-digest>",
  "payload": {
    "version": "3.0.0",
    "precision_decimal_places": 30,
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
    "last_power_online": true,
    "s5_offline_charges_count": 1,
    "s5_offline_cycles_accumulated": "0.928564284999928564284999928564",
    "s5_offline_energy_mwh": "64993.000000000000000000000000000000",
    "last_checkpoint_utc": "2026-09-09T18:55:55.648619+00:00",
    "history_events": []
  }
}
```

### Key Derivation
- **Algorithm:** PBKDF2-HMAC-SHA256
- **Passphrase:** `UUID + BASEBOARD_SERIAL + BATTERY_SERIAL`
- **Salt:** `b"INFINIX_BMS_SILICON_KEY_v2.0"`
- **Iterations:** `100,000`
- **Digest Length:** `32 bytes (256 bits)`

---

## 3. Resource Bounds & Performance Constraints
- **Average CPU Utilization:** `< 0.01%` (Evaluation loop sleeps for 60 seconds).
- **Resident Memory (RSS):** `< 16 MB` (No external C libraries, zero binary bloat).
- **Execution Latency:**
  - `bms status`: `< 150 ms`
  - `bms test-100`: `< 200 ms` for 100 verification cycles.
