## Description
Provide a concise, mechanistic description of the changes introduced in this PR.

## Invariant Checklist
- [ ] **Zero-Window Headless Invariant**: No interactive consoles, popups, or terminal windows are created. All subprocesses pass `CREATE_NO_WINDOW` and `SW_HIDE`.
- [ ] **Deterministic Arithmetic Invariant**: All cycle and degradation logic uses Python's `Decimal` quantized to 30 decimal places (`DEC_30`).
- [ ] **Anti-Mock Invariant**: Telemetry functions probe real OS kernel/ACPI interfaces.
- [ ] **Zero-Data-Loss Invariant**: State mutations update monotonic sequence numbers and preserve HMAC-SHA256 signatures.

## Verification Evidence
Paste raw terminal outputs from local tests:
```bash
python tests/test_arithmetic.py
python bms_engine.py test-100
python bms_engine.py status
```

## Related Issues
Closes #
