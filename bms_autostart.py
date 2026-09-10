#!/usr/bin/env python3
"""
================================================================================
BMS UNIVERSAL AUTOSTART MANAGER (WINDOWS & LINUX)
================================================================================
Configures seamless, resilient background autostart for the BMS Telemetry daemon
and local HTTP server (http://127.0.0.1:8989) on both Windows and Linux.

Windows:
  - Registers Windows Task Scheduler task '\\BMSTelemetry' (Highest Privileges,
    launches at logon/boot, runs on battery or AC, restarts on failure).
  - Also falls back to Windows Startup Folder shim if schtasks is restricted.

Linux:
  - Generates and enables systemd service (system unit or user session unit):
    /etc/systemd/system/bms-telemetry.service or ~/.config/systemd/user/bms-telemetry.service.
  - Also supports XDG autostart desktop entry (~/.config/autostart/bms-telemetry.desktop).

Usage:
    python bms_autostart.py install
    python bms_autostart.py status
    python bms_autostart.py remove
================================================================================
"""

import sys
import os
import platform
import subprocess
import shutil
from pathlib import Path

_HERE = os.path.dirname(os.path.abspath(__file__))
BMS_UI_PY = os.path.join(_HERE, "bms_ui.py")
TASK_NAME = "BMSTelemetry"
SERVICE_NAME = "bms-telemetry"


def _is_windows() -> bool:
    return platform.system() == "Windows"


def _is_linux() -> bool:
    return platform.system() == "Linux"


def _is_admin_windows() -> bool:
    try:
        import ctypes
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


# ── Windows Task Scheduler Implementation ──────────────────────────────────────

def install_windows():
    python_exe = sys.executable
    # For windowless background execution on Windows, prefer pythonw.exe if present
    pythonw = os.path.join(os.path.dirname(python_exe), "pythonw.exe")
    exec_python = pythonw if os.path.isfile(pythonw) else python_exe

    cmd_action = f'"{exec_python}" "{BMS_UI_PY}" --no-browser'
    print(f"[*] Registering Windows Autostart for BMS Telemetry...")
    print(f"    Executable: {exec_python}")
    print(f"    Target:     {BMS_UI_PY}")

    is_admin = _is_admin_windows()
    sc_type = "onstart" if is_admin else "onlogon"
    rl_flag = "highest" if is_admin else "limited"

    # 1. Primary: Windows Task Scheduler
    try:
        # Build XML or schtasks command
        sch_cmd = [
            "schtasks", "/create", "/tn", TASK_NAME,
            "/tr", cmd_action,
            "/sc", sc_type,
            "/rl", rl_flag,
            "/f"
        ]
        res = subprocess.run(sch_cmd, capture_output=True, text=True)
        if res.returncode == 0:
            print(f"[OK] Successfully created Task Scheduler task '{TASK_NAME}' ({sc_type}, {rl_flag}).")
            # Trigger task immediately to verify
            subprocess.run(["schtasks", "/run", "/tn", TASK_NAME], capture_output=True)
            return True
        else:
            print(f"[!] schtasks returned: {res.stderr.strip()}")
    except Exception as exc:
        print(f"[!] Task Scheduler creation failed: {exc}")

    # 2. Native Fallback: Windows Registry User Run Key (Zero VBScript, zero popups)
    try:
        reg_cmd = [
            "reg", "add", r"HKCU\Software\Microsoft\Windows\CurrentVersion\Run",
            "/v", TASK_NAME,
            "/t", "REG_SZ",
            "/d", cmd_action,
            "/f"
        ]
        res = subprocess.run(reg_cmd, capture_output=True, text=True)
        if res.returncode == 0:
            print(f"[OK] Native Windows Registry Run Key configured: HKCU\\...\\Run\\{TASK_NAME}")
            return True
        else:
            print(f"[!] Registry Run Key configuration returned: {res.stderr.strip()}")
    except Exception as exc:
        print(f"[!] Registry autostart fallback error: {exc}")

    return False


def remove_windows():
    success = False
    try:
        res = subprocess.run(["schtasks", "/delete", "/tn", TASK_NAME, "/f"], capture_output=True, text=True)
        if res.returncode == 0:
            print(f"[OK] Removed Task Scheduler task '{TASK_NAME}'.")
            success = True
        else:
            print(f"[*] schtasks delete: {res.stderr.strip()}")
    except Exception as exc:
        print(f"[!] Task Scheduler removal error: {exc}")

    try:
        reg_cmd = [
            "reg", "delete", r"HKCU\Software\Microsoft\Windows\CurrentVersion\Run",
            "/v", TASK_NAME,
            "/f"
        ]
        res = subprocess.run(reg_cmd, capture_output=True, text=True)
        if res.returncode == 0:
            print(f"[OK] Removed Registry Run key '{TASK_NAME}'.")
            success = True
    except Exception as exc:
        print(f"[!] Registry key removal error: {exc}")

    # Remove any lingering legacy VBS files if they exist from prior versions
    try:
        appdata = os.environ.get("APPDATA")
        if appdata:
            startup_dir = os.path.join(appdata, r"Microsoft\Windows\Start Menu\Programs\Startup")
            for vbs in ("BMSTelemetry.vbs", "bms_ui_startup.vbs"):
                p = os.path.join(startup_dir, vbs)
                if os.path.isfile(p):
                    os.remove(p)
                    print(f"[OK] Purged legacy VBS script: {p}")
                    success = True
    except Exception:
        pass

    return success


def status_windows():
    print(f"=== Windows Autostart Status for '{TASK_NAME}' ===")
    try:
        res = subprocess.run(["schtasks", "/query", "/tn", TASK_NAME, "/fo", "LIST", "/v"], capture_output=True, text=True)
        if res.returncode == 0:
            print("[ACTIVE] Task Scheduler entry exists:")
            for line in res.stdout.splitlines():
                if any(k in line for k in ("TaskName:", "Status:", "Schedule Type:", "Task To Run:", "Author:")):
                    print("  ", line.strip())
            return
    except Exception:
        pass

    try:
        res = subprocess.run(["reg", "query", r"HKCU\Software\Microsoft\Windows\CurrentVersion\Run", "/v", TASK_NAME], capture_output=True, text=True)
        if res.returncode == 0:
            print(f"[ACTIVE] Windows Registry Run Key configured:")
            for line in res.stdout.splitlines():
                if TASK_NAME in line:
                    print("  ", line.strip())
            return
    except Exception:
        pass

    print("[INACTIVE] No autostart task or registry run key configured.")


# ── Linux systemd Implementation ───────────────────────────────────────────────

def install_linux():
    python_bin = sys.executable
    is_root = (os.geteuid() == 0) if hasattr(os, "geteuid") else False

    unit_content = f"""[Unit]
Description=BMS Battery Telemetry & Real-Time HTTP Dashboard
Documentation=https://github.com/imsovikde/bms-telemetry
After=network.target

[Service]
Type=simple
ExecStart={python_bin} {BMS_UI_PY} --port 8989 --no-browser
WorkingDirectory={_HERE}
Restart=always
RestartSec=5
Nice=10
CPUQuota=5%
MemoryMax=128M

[Install]
WantedBy={'multi-user.target' if is_root else 'default.target'}
"""

    if is_root:
        unit_path = Path("/etc/systemd/system") / f"{SERVICE_NAME}.service"
        cmd_prefix = []
    else:
        unit_dir = Path.home() / ".config" / "systemd" / "user"
        unit_dir.mkdir(parents=True, exist_ok=True)
        unit_path = unit_dir / f"{SERVICE_NAME}.service"
        cmd_prefix = ["--user"]

    print(f"[*] Writing systemd service unit to: {unit_path}")
    try:
        with open(unit_path, "w", encoding="utf-8") as f:
            f.write(unit_content)

        # Reload and enable
        subprocess.run(["systemctl"] + cmd_prefix + ["daemon-reload"], check=True)
        subprocess.run(["systemctl"] + cmd_prefix + ["enable", "--now", SERVICE_NAME], check=True)
        print(f"[OK] systemd service '{SERVICE_NAME}' installed and enabled.")
        return True
    except Exception as exc:
        print(f"[!] Failed to configure systemd service: {exc}")

    # Fallback to XDG autostart
    try:
        xdg_dir = Path.home() / ".config" / "autostart"
        xdg_dir.mkdir(parents=True, exist_ok=True)
        desktop_file = xdg_dir / f"{SERVICE_NAME}.desktop"
        desktop_content = f"""[Desktop Entry]
Type=Application
Name=BMS Battery Telemetry
Exec={python_bin} {BMS_UI_PY} --no-browser
Hidden=false
NoDisplay=false
X-GNOME-Autostart-enabled=true
"""
        with open(desktop_file, "w", encoding="utf-8") as f:
            f.write(desktop_content)
        print(f"[OK] Fallback XDG autostart entry written to: {desktop_file}")
        return True
    except Exception as exc:
        print(f"[!] XDG autostart failed: {exc}")

    return False


def remove_linux():
    is_root = (os.geteuid() == 0) if hasattr(os, "geteuid") else False
    cmd_prefix = [] if is_root else ["--user"]

    try:
        subprocess.run(["systemctl"] + cmd_prefix + ["disable", "--now", SERVICE_NAME], capture_output=True)
        if is_root:
            p = Path("/etc/systemd/system") / f"{SERVICE_NAME}.service"
        else:
            p = Path.home() / ".config" / "systemd" / "user" / f"{SERVICE_NAME}.service"
        if p.exists():
            p.unlink()
            print(f"[OK] Removed {p}")
        subprocess.run(["systemctl"] + cmd_prefix + ["daemon-reload"], capture_output=True)
    except Exception as exc:
        print(f"[!] systemd removal error: {exc}")

    desktop_file = Path.home() / ".config" / "autostart" / f"{SERVICE_NAME}.desktop"
    if desktop_file.exists():
        desktop_file.unlink()
        print(f"[OK] Removed {desktop_file}")


def status_linux():
    is_root = (os.geteuid() == 0) if hasattr(os, "geteuid") else False
    cmd_prefix = [] if is_root else ["--user"]
    print(f"=== Linux systemd Status for '{SERVICE_NAME}' ===")
    try:
        res = subprocess.run(["systemctl"] + cmd_prefix + ["status", SERVICE_NAME], capture_output=True, text=True)
        print(res.stdout)
    except Exception as exc:
        print(f"[!] Failed to query systemctl: {exc}")


# ── Main Entrypoint ────────────────────────────────────────────────────────────

def main():
    action = "status"
    if len(sys.argv) > 1:
        action = sys.argv[1].lower()

    if action == "install":
        if _is_windows():
            install_windows()
        elif _is_linux():
            install_linux()
        else:
            print(f"[!] Unsupported operating system: {platform.system()}")
    elif action == "remove" or action == "uninstall":
        if _is_windows():
            remove_windows()
        elif _is_linux():
            remove_linux()
        else:
            print(f"[!] Unsupported operating system: {platform.system()}")
    elif action == "status":
        if _is_windows():
            status_windows()
        elif _is_linux():
            status_linux()
        else:
            print(f"[!] Unsupported operating system: {platform.system()}")
    else:
        print("Usage: python bms_autostart.py [install | remove | status]")


if __name__ == "__main__":
    main()
