#!/usr/bin/env bash
# ==============================================================================
# BMS Universal Autonomous Bootstrap Installer (Linux / macOS / Unix)
# Zero-Dependency, Hardware-Aware, Multi-Architecture System Integration
# ==============================================================================
set -e

CYAN='\033[0;36m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${CYAN}================================================================================${NC}"
echo -e "${CYAN}     BMS UNIVERSAL AUTONOMOUS BOOTSTRAP INSTALLER (Linux & macOS)              ${NC}"
echo -e "${CYAN}================================================================================${NC}"

# 1. Detect Operating System & CPU Architecture
OS="$(uname -s)"
ARCH="$(uname -m)"
KERNEL="$(uname -r)"

echo -e "[+] Probing Platform Topology:"
echo -e "    OS Kernel      : ${GREEN}${OS}${NC} (${KERNEL})"
echo -e "    Processor Arch : ${GREEN}${ARCH}${NC}"

# 2. Verify Python 3
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}[!] Python 3 is required but not found in PATH. Aborting.${NC}"
    exit 1
fi
PYTHON_VER="$(python3 --version)"
echo -e "    Runtime Engine : ${GREEN}${PYTHON_VER}${NC}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENGINE_SRC="${SCRIPT_DIR}/bms_engine.py"

if [ ! -f "${ENGINE_SRC}" ]; then
    echo -e "${RED}[!] bms_engine.py not found in ${SCRIPT_DIR}. Aborting.${NC}"
    exit 1
fi

# 3. Determine Installation Paths
TARGET_BIN="/usr/local/bin/bms"
if [ ! -w "/usr/local/bin" ] && [ "$EUID" -ne 0 ]; then
    if command -v sudo &> /dev/null; then
        SUDO="sudo"
    else
        TARGET_BIN="${HOME}/.local/bin/bms"
        mkdir -p "${HOME}/.local/bin"
    fi
else
    SUDO=""
fi

echo -e "\n[+] Deploying Universal CLI Executable:"
${SUDO} cp "${ENGINE_SRC}" "${TARGET_BIN}"
${SUDO} chmod +x "${TARGET_BIN}"
echo -e "    Installed CLI  : ${GREEN}${TARGET_BIN}${NC}"

# 4. Provision Multi-Layer Persistence Targets
echo -e "\n[+] Provisioning Hardware Persistence Layers:"
mkdir -p "${HOME}/.bms"
echo -e "    User Cache     : ${GREEN}${HOME}/.bms${NC}"

if [ "${OS}" = "Linux" ]; then
    if [ "$EUID" -eq 0 ] || [ -n "${SUDO}" ]; then
        ${SUDO} mkdir -p /var/lib/bms /etc/bms
        ${SUDO} chmod 755 /var/lib/bms /etc/bms
        echo -e "    System NVRAM   : ${GREEN}/var/lib/bms${NC} & ${GREEN}/etc/bms${NC}"
    fi

    # Systemd / Cron Daemon Setup
    if command -v systemctl &> /dev/null && [ "$EUID" -eq 0 ]; then
        SERVICE_FILE="/etc/systemd/system/bms-daemon.service"
        cat <<EOF | ${SUDO} tee "${SERVICE_FILE}" > /dev/null
[Unit]
Description=BMS High-Precision Cycle Tracking Daemon
After=network.target

[Service]
Type=simple
ExecStart=${TARGET_BIN} daemon
Restart=always
RestartSec=10
Nice=19
CPUQuota=1%

[Install]
WantedBy=multi-user.target
EOF
        ${SUDO} systemctl daemon-reload
        ${SUDO} systemctl enable bms-daemon.service --now 2>/dev/null || true
        echo -e "    Background SVC : ${GREEN}systemd (bms-daemon.service)${NC}"
    else
        # Fallback to user crontab
        (crontab -l 2>/dev/null | grep -v 'bms status' ; echo "*/5 * * * * ${TARGET_BIN} status >/dev/null 2>&1") | crontab - 2>/dev/null || true
        echo -e "    Background SVC : ${GREEN}Cron (5-minute state sync)${NC}"
    fi

elif [ "${OS}" = "Darwin" ]; then
    PLIST_DIR="${HOME}/Library/LaunchAgents"
    mkdir -p "${PLIST_DIR}"
    PLIST_FILE="${PLIST_DIR}/com.bms.daemon.plist"
    cat <<EOF > "${PLIST_FILE}"
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.bms.daemon</string>
    <key>ProgramArguments</key>
    <array>
        <string>${TARGET_BIN}</string>
        <string>daemon</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
</dict>
</plist>
EOF
    launchctl load -w "${PLIST_FILE}" 2>/dev/null || true
    echo -e "    Background SVC : ${GREEN}macOS launchd (${PLIST_FILE})${NC}"
fi

# 5. Execute 100-Cycle Deep Verification
echo -e "\n[+] Executing Automated 100-Cycle Deep Verification Suite:"
${TARGET_BIN} test-100

echo -e "\n[+] Initializing Real-Time Telemetry:"
${TARGET_BIN} status

echo -e "${GREEN}================================================================================${NC}"
echo -e "${GREEN}  BMS INSTALLATION & 100-CYCLE VERIFICATION COMPLETE (READY ACROSS ALL PATHS)  ${NC}"
echo -e "${GREEN}================================================================================${NC}"
echo -e "You can now run 'bms' or 'bms status' from any directory."
