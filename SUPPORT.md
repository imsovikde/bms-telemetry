# Support & Community Help

Welcome to the **BMS Telemetry** support guide.

---

## Frequently Asked Questions (FAQ)

### 1. Why does my OEM laptop report 0 cycles in Windows or Linux?
Many OEM laptop vendors (such as Infinix on the ZERO BOOK 13 / EM_IDL822_V2.0) implement the ACPI `_BIF` table but completely omit the ACPI `_BIX` table in their Embedded Controller (EC) firmware. Because standard OS battery drivers rely on `_BIX` for cycle counts, they report 0. `bms` resolves this by continuously calculating Coulomb integration at the hardware layer.

### 2. Does the daemon consume CPU or battery power?
No. The background daemon uses an event-driven 60-second polling interval consuming `<0.01%` CPU and `~14 MB` RAM.

### 3. Was there a terminal popup bug in earlier versions?
Yes. Prior to v4.0.0, the polling loop used a subprocess without `CREATE_NO_WINDOW`, causing a brief 50ms console flash. This was completely eliminated in v4.0.0 through **In-Process COM WMI Interop** and migration to a native Windows Service (`BMSTelemetry`).

### 4. How does the system survive a complete format of `C:\`?
The state is cryptographically sealed with HMAC-SHA256 and mirrored across 7 tiers, including secondary physical NVMe partitions (`D:\`, `S:\`) and user profile directories. Reinstalling or running `bms status` automatically detects and restores the canonical state.

---

## Getting Help

- **Bug Reports**: Open an issue using our [Bug Report Template](https://github.com/imsovikde/bms-telemetry/issues/new?template=bug_report.yml).
- **Feature Requests**: Propose enhancements via our [Feature Request Template](https://github.com/imsovikde/bms-telemetry/issues/new?template=feature_request.yml).
- **Architecture & Specifications**: Review [PRD.md](./PRD.md), [ARCHITECTURE.md](./ARCHITECTURE.md), and [SPEC.md](./SPEC.md).
