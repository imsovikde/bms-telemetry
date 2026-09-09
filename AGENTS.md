# AGENTS.md: Developer & Agent Directives for BMS Telemetry

## Core Invariants
1. **Mathematical Precision Invariant:** All calculations relating to charging cycles, State of Charge, and Virtual Health MUST use Python `decimal.Decimal` with at least 60 digits internal precision, quantized to exactly 30 decimal places. IEEE 754 floats (`float`) MUST NEVER be used for cumulative calculations.
2. **Cryptographic Sealing Invariant:** Every state serialization MUST increment `monotonic_seq` and compute HMAC-SHA256 over the canonical JSON representation of `payload`.
3. **Zero-Data-Loss Persistence:** Changes to persistence paths must maintain backward compatibility with secondary partitions (`D:\`, `S:\`) and Linux targets (`/var/lib/bms`).
4. **Test Verification Before Completion:** Any modifications to arithmetic equations or storage schemas must pass `python verify_100.py` with 100/100 tests.
