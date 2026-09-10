#!/usr/bin/env python3
"""
================================================================================
BMS WINDOWS SERVICE WRAPPER  (win32serviceutil.ServiceFramework)
================================================================================
Registers 'BMSTelemetry' with the Windows Service Control Manager (SCM).
The daemon runs entirely inside csrss / services.exe — zero console windows,
survives user logoff, restarts on crash, starts before any user logs in.

Installation (requires Admin PowerShell):
    python bms_service.py install
    sc start BMSTelemetry

Removal:
    sc stop BMSTelemetry
    python bms_service.py remove

The service calls bms_engine.run_daemon_loop() directly — no subprocess fork.
================================================================================
"""

import sys
import os
import time
import logging
import threading
from http.server import HTTPServer

# ── Locate engine regardless of CWD ────────────────────────────────────────
_HERE = os.path.dirname(os.path.abspath(__file__))
_ENGINE_DIR = r"C:\ProgramData\BMS"

# Prefer the installed engine; fall back to repo copy during dev
if os.path.isfile(os.path.join(_ENGINE_DIR, "bms_engine.py")):
    sys.path.insert(0, _ENGINE_DIR)
else:
    sys.path.insert(0, _HERE)

import bms_engine  # noqa: E402  — engine must be importable before pywin32

try:
    import bms_ui  # noqa: E402
except ImportError:
    bms_ui = None

try:
    import win32serviceutil
    import win32service
    import win32event
    import servicemanager
except ImportError:
    print(
        "[!] pywin32 is required.  Install with:  pip install pywin32\n"
        "    Then run:  python bms_service.py install"
    )
    sys.exit(1)

# ── Logging to Windows Application Event Log ────────────────────────────────
_LOG_DIR = _ENGINE_DIR
os.makedirs(_LOG_DIR, exist_ok=True)

logging.basicConfig(
    filename=os.path.join(_LOG_DIR, "bms_service.log"),
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)
log = logging.getLogger("BMSTelemetry")


class BMSTelemetryService(win32serviceutil.ServiceFramework):
    """Windows Service: BMS High-Precision Battery Cycle Tracking Daemon."""

    _svc_name_ = "BMSTelemetry"
    _svc_display_name_ = "BMS Battery Telemetry Service"
    _svc_description_ = (
        "High-precision Coulomb-counting cycle tracker for Infinix ZERO BOOK 13. "
        "Compensates for missing ACPI _BIX in EC firmware. "
        "Persists state across reboots and OS reinstallation."
    )

    def __init__(self, args):
        win32serviceutil.ServiceFramework.__init__(self, args)
        self._stop_event = win32event.CreateEvent(None, 0, 0, None)
        self._running = True
        self._httpd = None

    def SvcStop(self):
        """Called by SCM when the service is stopping."""
        log.info("BMSTelemetry: SvcStop received — flushing shutdown state.")
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
        self._running = False
        win32event.SetEvent(self._stop_event)
        if self._httpd:
            try:
                self._httpd.shutdown()
                self._httpd.server_close()
                log.info("BMSTelemetry: Web server shut down successfully.")
            except Exception as exc:
                log.warning("Web server shutdown warning: %s", exc)
        # Give bms_engine a chance to write Q_shutdown before we die
        try:
            bms_engine._flush_shutdown_state()
        except Exception as exc:
            log.warning("Shutdown flush warning: %s", exc)

    def SvcDoRun(self):
        """Main service body — runs the BMS daemon loop."""
        servicemanager.LogMsg(
            servicemanager.EVENTLOG_INFORMATION_TYPE,
            servicemanager.PYS_SERVICE_STARTED,
            (self._svc_name_, ""),
        )
        log.info("BMSTelemetry service starting.")
        try:
            self._run()
        except Exception as exc:
            log.exception("BMSTelemetry crashed: %s", exc)
            servicemanager.LogMsg(
                servicemanager.EVENTLOG_ERROR_TYPE,
                servicemanager.PYS_SERVICE_STOPPED,
                (self._svc_name_, str(exc)),
            )
        finally:
            log.info("BMSTelemetry service stopped.")

    def _run(self):
        """Mirrors run_daemon_loop and hosts embedded real-time UI web server."""
        log.info("Engine initialising…")
        # ── Launch embedded 4 Hz real-time Web Dashboard on http://127.0.0.1:8989 ──
        if bms_ui:
            try:
                self._httpd = HTTPServer(("127.0.0.1", 8989), bms_ui.BMSHandler)
                web_thread = threading.Thread(
                    target=self._httpd.serve_forever,
                    daemon=True,
                    name="BMSWebThread"
                )
                web_thread.start()
                log.info("BMSTelemetry: Real-Time Web Dashboard listening on http://127.0.0.1:8989")
            except Exception as exc:
                log.warning("Failed to bind embedded web server to port 8989: %s", exc)

        state = bms_engine.load_state()
        telem = bms_engine.get_telemetry()
        state = bms_engine.process_telemetry_and_update_state(telem, state)
        log.info(
            "Initial state loaded. Cycles=%s Health=%s%%",
            state["accumulated_cycles"],
            state["virtual_health_percentage"],
        )

        TICK_SECONDS = 60
        while self._running:
            # Wait up to TICK_SECONDS or until stop event fires
            rc = win32event.WaitForSingleObject(self._stop_event, TICK_SECONDS * 1000)
            if rc == win32event.WAIT_OBJECT_0:
                break  # stop requested
            try:
                telem = bms_engine.get_telemetry()
                state = bms_engine.process_telemetry_and_update_state(telem, state)
            except Exception as exc:
                log.warning("Tick error (non-fatal): %s", exc)
                time.sleep(5)


def _cli():
    """Handle CLI invocations (install / remove / start / stop / status)."""
    if len(sys.argv) == 1:
        # Invoked by SCM — hand off to servicemanager
        servicemanager.Initialize()
        servicemanager.PrepareToHostSingle(BMSTelemetryService)
        servicemanager.StartServiceCtrlDispatcher()
    else:
        win32serviceutil.HandleCommandLine(BMSTelemetryService)


if __name__ == "__main__":
    _cli()
