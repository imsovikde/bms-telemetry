#!/usr/bin/env bash
# ==============================================================================
# BMS Battery Telemetry — Linux / macOS Installer v4.0
# ==============================================================================
# Linux  : deploys systemd unit (Type=simple) — survives reboot, root-owned.
# macOS  : deploys LaunchDaemon to /Library/LaunchDaemons/ (system-level),
#          requires sudo, RunAtLoad=true — survives all user sessions.
# ==============================================================================
set -euo pipefail

CYAN='\033[0;36m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${CYAN}================================================================================${NC}"
echo -e "${CYAN}  BMS BATTERY TELEMETRY — UNIX INSTALLER v4.0                                 ${NC}"
echo -e "${CYAN}================================================================================${NC}"

# ── 0. Determine OS and Architecture ────────────────────────────────────────
OS="$(uname -s)"
ARCH="$(uname -m)"
echo -e "\n[+] Platform Topology:"
echo -e "    OS   : ${GREEN}${OS}${NC} ($(uname -r))"
echo -e "    Arch : ${GREEN}${ARCH}${NC}"

# ── 1. Python Guard ──────────────────────────────────────────────────────────
PYTHON3="$(command -v python3 2>/dev/null || true)"
if [ -z "$PYTHON3" ]; then
    echo -e "${RED}[!] python3 not found in PATH. Install Python 3.10+ and retry.${NC}"
    exit 1
fi
echo -e "    Python : ${GREEN}$($PYTHON3 --version)${NC}"

# ── 2. Resolve Paths ─────────────────────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"
ENGINE_SRC="${REPO_ROOT}/bms_engine.py"

if [ ! -f "$ENGINE_SRC" ]; then
    echo -e "${RED}[!] bms_engine.py not found at ${ENGINE_SRC}${NC}"
    exit 1
fi

# Determine sudo access
SUDO=""
if [ "$EUID" -ne 0 ]; then
    if command -v sudo &>/dev/null; then
        SUDO="sudo"
    else
        echo -e "${YELLOW}[!] Not root and sudo not available. Some steps may require elevation.${NC}"
    fi
fi

# ── 3. Install Engine ────────────────────────────────────────────────────────
INSTALL_DIR="/usr/local/lib/bms"
$SUDO mkdir -p "$INSTALL_DIR"
$SUDO cp "$ENGINE_SRC" "$INSTALL_DIR/bms_engine.py"
$SUDO chmod 644 "$INSTALL_DIR/bms_engine.py"

# Global CLI shim
CLI_BIN="/usr/local/bin/bms"
$SUDO tee "$CLI_BIN" > /dev/null << SHIM
#!/usr/bin/env bash
exec python3 /usr/local/lib/bms/bms_engine.py "\$@"
SHIM
$SUDO chmod 755 "$CLI_BIN"
echo -e "\n[+] Engine deployed  → ${GREEN}${INSTALL_DIR}${NC}"
echo -e "    CLI shim         → ${GREEN}${CLI_BIN}${NC}"

# ── 4. Multi-Tier Persistence Directories ───────────────────────────────────
echo -e "\n[+] Provisioning persistence layers:"
mkdir -p "${HOME}/.bms"
echo -e "    User cache  : ${GREEN}${HOME}/.bms${NC}"

if [ "$OS" = "Linux" ]; then
    $SUDO mkdir -p /var/lib/bms /etc/bms
    $SUDO chmod 755 /var/lib/bms /etc/bms
    echo -e "    System NVRAM: ${GREEN}/var/lib/bms${NC} & ${GREEN}/etc/bms${NC}"
fi

# ── 5a. Linux: systemd Unit ──────────────────────────────────────────────────
if [ "$OS" = "Linux" ] && command -v systemctl &>/dev/null; then
    SERVICE_FILE="/etc/systemd/system/bms-daemon.service"
    $SUDO tee "$SERVICE_FILE" > /dev/null << EOF
[Unit]
Description=BMS High-Precision Coulomb-Counting Battery Cycle Daemon
Documentation=https://github.com/imsovikde/bms-telemetry
After=multi-user.target
Wants=multi-user.target

[Service]
Type=simple
ExecStart=${CLI_BIN} daemon
Restart=always
RestartSec=10
Nice=19
CPUQuota=1%
MemoryMax=32M
ProtectSystem=full
NoNewPrivileges=true

[Install]
WantedBy=multi-user.target
EOF

    $SUDO systemctl daemon-reload
    $SUDO systemctl enable bms-daemon.service --now 2>/dev/null || true
    SVC_STATUS="$(systemctl is-active bms-daemon.service 2>/dev/null || echo unknown)"
    echo -e "\n[+] systemd Service:"
    echo -e "    Unit   : ${GREEN}/etc/systemd/system/bms-daemon.service${NC}"
    echo -e "    Status : ${GREEN}${SVC_STATUS}${NC}"

elif [ "$OS" = "Linux" ]; then
    # Non-systemd Linux fallback → crontab
    (crontab -l 2>/dev/null | grep -v 'bms' ; \
     echo "*/5 * * * * ${CLI_BIN} status >/dev/null 2>&1") | crontab - 2>/dev/null || true
    echo -e "\n[+] Background SVC: ${YELLOW}cron (5-min state sync — no systemd detected)${NC}"
fi

# ── 5b. macOS: LaunchDaemon (system-level, NOT LaunchAgent) ─────────────────
if [ "$OS" = "Darwin" ]; then
    DAEMON_DIR="/Library/LaunchDaemons"
    PLIST="${DAEMON_DIR}/com.bms.daemon.plist"

    # Unload any old LaunchAgent version
    OLD_AGENT="${HOME}/Library/LaunchAgents/com.bms.daemon.plist"
    if [ -f "$OLD_AGENT" ]; then
        launchctl unload -w "$OLD_AGENT" 2>/dev/null || true
        rm -f "$OLD_AGENT"
        echo -e "    [REMOVED] Legacy LaunchAgent: ${OLD_AGENT}"
    fi

    $SUDO tee "$PLIST" > /dev/null << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.bms.daemon</string>
    <key>ProgramArguments</key>
    <array>
        <string>${CLI_BIN}</string>
        <string>daemon</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>/var/log/bms-daemon.log</string>
    <key>StandardErrorPath</key>
    <string>/var/log/bms-daemon.log</string>
    <key>Nice</key>
    <integer>19</integer>
</dict>
</plist>
EOF

    $SUDO chmod 644 "$PLIST"
    $SUDO launchctl load -w "$PLIST" 2>/dev/null || true
    echo -e "\n[+] macOS LaunchDaemon (system-level):"
    echo -e "    Plist  : ${GREEN}${PLIST}${NC}"
    echo -e "    Domain : ${GREEN}system (survives all user sessions and logoff)${NC}"
fi

# ── 6. Verification ──────────────────────────────────────────────────────────
echo -e "\n[+] 100-Cycle Deep Verification Suite:"
"$CLI_BIN" test-100

echo -e "\n[+] Live Telemetry Snapshot:"
"$CLI_BIN" status

echo -e "\n${GREEN}================================================================================${NC}"
echo -e "${GREEN}  BMS INSTALLATION COMPLETE                                                    ${NC}"
if [ "$OS" = "Linux" ]; then
echo -e "${GREEN}  Daemon: systemd bms-daemon.service (headless, auto-restart, CPUQuota=1%)     ${NC}"
elif [ "$OS" = "Darwin" ]; then
echo -e "${GREEN}  Daemon: launchd com.bms.daemon (system LaunchDaemon, RunAtLoad=true)         ${NC}"
fi
echo -e "${GREEN}  CLI   : bms [status|full|test-100|sync-hw|daemon|help]                      ${NC}"
echo -e "${GREEN}================================================================================${NC}"
