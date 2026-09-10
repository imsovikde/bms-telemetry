# Security Policy

## Supported Versions

We provide security updates and patches for the following versions of `bms-telemetry`:

| Version | Supported          |
| ------- | ------------------ |
| 4.0.x   | :white_check_mark: |
| < 4.0.0 | :x:                |

---

## Security Architecture & Threat Model

`bms-telemetry` interacts directly with low-level kernel drivers, ACPI hardware interfaces, and physical disk partitions:

1. **Silicon Identity Keying**:
   - The master encryption/HMAC key is derived using PBKDF2-HMAC-SHA256 (100,000 iterations) using hardware-bound strings (`Motherboard UUID`, `Baseboard Serial`, `Battery Serial`).
   - Tampered state files are automatically detected and discarded during the canonical replica election phase.
2. **Execution Boundary & Privilege**:
   - The Windows Service (`BMSTelemetry`) runs under Session 0 (`services.exe`), ensuring total isolation from interactive user desktops.
   - Subprocesses are strictly guarded with `CREATE_NO_WINDOW` and `SW_HIDE` to prevent desktop manipulation.
3. **Secret Hygiene**:
   - No hardcoded credentials, personal tokens, or API secrets are stored within the repository.

---

## Reporting a Vulnerability

If you discover a security vulnerability within `bms-telemetry`, please do NOT open a public GitHub issue.

Instead, please send a detailed vulnerability report via email to:
**souvikdey.contact@gmail.com**

Please include:
- A description of the vulnerability and its potential impact.
- Exact reproduction steps, proof of concept, or command logs.
- Affected operating systems and hardware configurations.

You will receive an acknowledgment within 48 hours, followed by a status update and estimated resolution timeline.
