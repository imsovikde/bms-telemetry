#!/usr/bin/env bash
# ==============================================================================
# Universal BMS Installer & System Autostart Setup (Linux / macOS / WSL)
# ==============================================================================
# Installs BMS system-wide, registers boot autostart service, compiles C++ core,
# and launches the 4 Hz real-time dashboard in the default browser.
# ==============================================================================

set -e

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd)"
echo "=== Installing BMS Telemetry & Hardware Engine ==="

# 1. Ensure Python3 is available
if ! command -v python3 &>/dev/null; then
    echo "[!] python3 is required. Please install python3."
    exit 1
fi

# 2. Make launcher executable
chmod +x "$DIR/bms"

# 3. Register global CLI binary in /usr/local/bin or ~/.local/bin
if [ -w "/usr/local/bin" ]; then
    ln -sf "$DIR/bms" /usr/local/bin/bms
    echo "[+] Linked bms to /usr/local/bin/bms"
else
    mkdir -p "$HOME/.local/bin"
    ln -sf "$DIR/bms" "$HOME/.local/bin/bms"
    echo "[+] Linked bms to $HOME/.local/bin/bms"
fi

# 4. Compile native C++20 engine if g++ is present
if command -v g++ &>/dev/null; then
    echo "[*] Compiling high-performance native C++20 engine..."
    g++ -O3 -std=c++20 "$DIR/bms_core.cpp" -o "$DIR/bms_core" || true
fi

# 5. Register Autostart (systemd user service or XDG autostart)
mkdir -p "$HOME/.config/systemd/user"
cat <<EOF > "$HOME/.config/systemd/user/bms-ui.service"
[Unit]
Description=BMS Telemetry 4 Hz Real-Time Web Server
After=network.target

[Service]
Type=simple
ExecStart=$(which python3) $DIR/bms_ui.py --no-browser
Restart=always
RestartSec=3

[Install]
WantedBy=default.target
EOF

systemctl --user daemon-reload 2>/dev/null || true
systemctl --user enable bms-ui.service 2>/dev/null || true
systemctl --user start bms-ui.service 2>/dev/null || true

# 6. Start server and launch default browser
echo "[+] Starting BMS Web Server and opening browser..."
python3 "$DIR/bms_engine.py" ui
