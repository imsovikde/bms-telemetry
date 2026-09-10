#!/usr/bin/env python3
"""
================================================================================
BMS GENERATIVE ARCHITECTURAL WEB UI & REAL-TIME TELEMETRY DASHBOARD
================================================================================
Zero-dependency local HTTP server providing a real-time, glassmorphism dashboard
for Infinix ZERO BOOK 13 (EM_IDL822_V2.0) BMS hardware telemetry, 30-decimal
cycle tracking, and electrochemical degradation modeling.

Usage:
    python bms_ui.py [--port 8989] [--no-browser]
    bms ui
================================================================================
"""

import sys
import os
import json
import time
import webbrowser
import threading
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
import decimal
from decimal import Decimal, getcontext

decimal.DefaultContext.prec = 80
getcontext().prec = 80

# Ensure local engine is importable
_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)
import bms_engine as engine

HTML_DASHBOARD = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>BMS Telemetry & Hardware Cycle Engine</title>
<style>
  :root {
    --bg-base: #06090e;
    --bg-panel: rgba(13, 20, 32, 0.82);
    --border-glow: rgba(0, 240, 255, 0.25);
    --text-main: #e2e8f0;
    --text-dim: #94a3b8;
    --cyan: #00f0ff;
    --emerald: #00ff88;
    --amber: #ffb800;
    --rose: #ff3366;
    --purple: #a855f7;
    --font-mono: 'JetBrains Mono', 'Cascadia Code', 'Fira Code', 'Consolas', monospace;
  }
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body {
    background: var(--bg-base);
    color: var(--text-main);
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    min-height: 100vh;
    padding: 24px;
    background-image: 
      radial-gradient(ellipse at top left, rgba(0, 240, 255, 0.08), transparent 45%),
      radial-gradient(ellipse at bottom right, rgba(0, 255, 136, 0.06), transparent 50%),
      linear-gradient(180deg, rgba(6, 9, 14, 0.95), #06090e);
    background-attachment: fixed;
  }
  .container { max-width: 1280px; margin: 0 auto; }
  header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    border-bottom: 1px solid var(--border-glow);
    padding-bottom: 16px;
    margin-bottom: 24px;
  }
  .title-group h1 {
    font-size: 20px;
    font-weight: 700;
    letter-spacing: 1px;
    color: #fff;
    display: flex;
    align-items: center;
    gap: 10px;
  }
  .pulse-dot {
    width: 10px;
    height: 10px;
    border-radius: 50%;
    background: var(--emerald);
    box-shadow: 0 0 10px var(--emerald);
    animation: pulse 1.5s infinite;
  }
  @keyframes pulse {
    0%, 100% { opacity: 1; transform: scale(1); }
    50% { opacity: 0.4; transform: scale(0.85); }
  }
  .title-group p { font-size: 12px; color: var(--text-dim); margin-top: 4px; font-family: var(--font-mono); }
  .badge-chip {
    padding: 6px 14px;
    border-radius: 20px;
    font-size: 12px;
    font-weight: 600;
    font-family: var(--font-mono);
    text-transform: uppercase;
    letter-spacing: 0.5px;
    display: inline-flex;
    align-items: center;
    gap: 6px;
  }
  .badge-charging {
    background: rgba(0, 255, 136, 0.15);
    border: 1px solid var(--emerald);
    color: var(--emerald);
  }
  .badge-discharging {
    background: rgba(255, 184, 0, 0.15);
    border: 1px solid var(--amber);
    color: var(--amber);
  }
  .badge-idle {
    background: rgba(0, 240, 255, 0.12);
    border: 1px solid var(--cyan);
    color: var(--cyan);
  }
  .grid {
    display: grid;
    grid-template-columns: repeat(12, 1fr);
    gap: 20px;
  }
  .card {
    background: var(--bg-panel);
    backdrop-filter: blur(12px);
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 12px;
    padding: 20px;
    position: relative;
    overflow: hidden;
  }
  .card::before {
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0; height: 1px;
    background: linear-gradient(90deg, transparent, var(--cyan), transparent);
  }
  .card-gauge { grid-column: span 4; display: flex; flex-direction: column; align-items: center; justify-content: center; text-align: center; }
  .card-main-stats { grid-column: span 8; display: flex; flex-direction: column; justify-content: space-around; gap: 14px; }
  .card-registers { grid-column: span 12; }
  .card-degradation { grid-column: span 6; }
  .card-waveform { grid-column: span 6; }

  /* SVG Circular Gauge */
  .gauge-svg { width: 220px; height: 220px; }
  .gauge-bg { fill: none; stroke: rgba(255,255,255,0.06); stroke-width: 14; }
  .gauge-fill {
    fill: none;
    stroke: url(#gauge-grad);
    stroke-width: 14;
    stroke-linecap: round;
    stroke-dasharray: 565.48;
    stroke-dashoffset: 100;
    transform: rotate(-90deg);
    transform-origin: 50% 50%;
    transition: stroke-dashoffset 0.3s ease;
  }
  .gauge-text {
    font-size: 28px;
    font-weight: 800;
    fill: #fff;
    font-family: var(--font-mono);
  }
  .gauge-sub {
    font-size: 11px;
    fill: var(--text-dim);
    font-family: var(--font-mono);
  }

  /* Mono Display Rows */
  .reg-block {
    background: rgba(0, 0, 0, 0.35);
    border: 1px solid rgba(0, 240, 255, 0.15);
    border-radius: 8px;
    padding: 12px 16px;
    margin-bottom: 10px;
  }
  .reg-label {
    font-size: 11px;
    text-transform: uppercase;
    color: var(--text-dim);
    font-family: var(--font-mono);
    letter-spacing: 0.8px;
    display: flex;
    justify-content: space-between;
    margin-bottom: 6px;
  }
  .reg-val-30 {
    font-family: var(--font-mono);
    font-size: 15px;
    color: var(--cyan);
    word-break: break-all;
    line-height: 1.4;
  }
  .reg-val-30 span.high { color: #fff; font-weight: bold; }
  .reg-val-30 span.micro { color: var(--emerald); font-weight: 600; text-shadow: 0 0 8px rgba(0,255,136,0.5); }

  .stat-row { display: flex; justify-content: space-between; padding: 6px 0; border-bottom: 1px solid rgba(255,255,255,0.04); font-size: 13px; }
  .stat-row:last-child { border-bottom: none; }
  .stat-name { color: var(--text-dim); }
  .stat-num { font-family: var(--font-mono); font-weight: 600; color: #fff; }

  /* Degradation Bars */
  .bar-group { margin-top: 10px; }
  .bar-label { display: flex; justify-content: space-between; font-size: 12px; font-family: var(--font-mono); margin-bottom: 4px; }
  .bar-track { height: 8px; background: rgba(255,255,255,0.06); border-radius: 4px; overflow: hidden; margin-bottom: 12px; }
  .bar-fill { height: 100%; border-radius: 4px; transition: width 0.3s ease; }
  .bar-fill-cyan { background: var(--cyan); }
  .bar-fill-purple { background: var(--purple); }
  .bar-fill-rose { background: var(--rose); }

  canvas { width: 100%; height: 180px; display: block; }
  footer { margin-top: 24px; text-align: center; font-size: 11px; color: var(--text-dim); font-family: var(--font-mono); }
</style>
</head>
<body>
<div class="container">
  <header>
    <div class="title-group">
      <h1><div class="pulse-dot"></div> INFINIX ZERO BOOK 13 BMS TELEMETRY</h1>
      <p>EM_IDL822_V2.0 / Raptor Lake-P · Intel 600 Series PCH · ACPI \_SB.PC00.LPCB.H_EC.BAT0</p>
    </div>
    <div id="status-badge" class="badge-chip badge-idle">INITIALIZING</div>
  </header>

  <div class="grid">
    <!-- SVG Circular Gauge -->
    <div class="card card-gauge">
      <svg class="gauge-svg" viewBox="0 0 200 200">
        <defs>
          <linearGradient id="gauge-grad" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stop-color="#00f0ff"/>
            <stop offset="100%" stop-color="#00ff88"/>
          </linearGradient>
        </defs>
        <circle class="gauge-bg" cx="100" cy="100" r="85"/>
        <circle id="gauge-fill" class="gauge-fill" cx="100" cy="100" r="85"/>
        <text id="gauge-pct" class="gauge-text" x="100" y="98" text-anchor="middle">--.-%</text>
        <text id="gauge-sub" class="gauge-sub" x="100" y="122" text-anchor="middle">STATE OF CHARGE</text>
      </svg>
      <div style="font-family: var(--font-mono); font-size: 13px; color: var(--text-dim); margin-top: 10px;">
        Remaining: <span id="mwh-rem" style="color:#fff; font-weight:600;">--</span> / <span id="mwh-fcc" style="color:#fff;">--</span> mWh
      </div>
    </div>

    <!-- Main Stats Overview -->
    <div class="card card-main-stats">
      <div class="stat-row">
        <span class="stat-name">Instantaneous Terminal Voltage</span>
        <span id="stat-volt" class="stat-num">-- V</span>
      </div>
      <div class="stat-row">
        <span class="stat-name">Active Power Dynamics (Charge / Drain)</span>
        <span id="stat-power" class="stat-num" style="color:var(--emerald);">-- mW</span>
      </div>
      <div class="stat-row">
        <span class="stat-name">AC Mains Connectivity</span>
        <span id="stat-mains" class="stat-num">--</span>
      </div>
      <div class="stat-row">
        <span class="stat-name">Electrochemical Virtual Health (SoH%)</span>
        <span id="stat-vhealth" class="stat-num" style="color:var(--emerald);">--%</span>
      </div>
      <div class="stat-row">
        <span class="stat-name">ACPI Firmware Status</span>
        <span class="stat-num" style="color:var(--amber);">_BIX Omitted (Compensatory Engine Active)</span>
      </div>
      <div class="stat-row">
        <span class="stat-name">Silicon Master Key Fingerprint</span>
        <span id="stat-key" class="stat-num" style="color:var(--cyan);">--</span>
      </div>
    </div>

    <!-- 30-Decimal Registers -->
    <div class="card card-registers">
      <div class="reg-block">
        <div class="reg-label">
          <span>Accumulated Charging Cycles (30-Decimal Coulomb Integration)</span>
          <span style="color:var(--emerald);">ZERO-DRIFT FIXED POINT</span>
        </div>
        <div id="cycles-30" class="reg-val-30">--</div>
      </div>
      <div class="reg-block">
        <div class="reg-label">
          <span>Real-Time State of Charge Percentage (30 Decimal Digits)</span>
          <span style="color:var(--cyan);">CONTINUOUS SUB-SECOND INTEGRATION</span>
        </div>
        <div id="soc-30" class="reg-val-30">--</div>
      </div>
      <div class="reg-block">
        <div class="reg-label">
          <span>Electrochemical Virtual Health Percentage (30 Decimal Digits)</span>
          <span style="color:var(--purple);">MULTI-FACTOR SCIENTIFIC MODEL</span>
        </div>
        <div id="vhealth-30" class="reg-val-30">--</div>
      </div>
    </div>

    <!-- Multi-Factor Degradation Card -->
    <div class="card card-degradation">
      <h3 style="font-size: 14px; font-family: var(--font-mono); margin-bottom: 14px; color: var(--cyan);">
        ELECTROCHEMICAL AGING BREAKDOWN
      </h3>
      <div class="bar-group">
        <div class="bar-label">
          <span>SEI Layer Power-Law Cycle Loss (z=0.82)</span>
          <span id="loss-cycle">0.00%</span>
        </div>
        <div class="bar-track">
          <div id="bar-cycle" class="bar-fill bar-fill-rose" style="width: 2%;"></div>
        </div>

        <div class="bar-label">
          <span>Arrhenius Thermal Aging (Ea/R=3788 K, T=31.5°C)</span>
          <span id="loss-thermal">0.00%</span>
        </div>
        <div class="bar-track">
          <div id="bar-thermal" class="bar-fill bar-fill-purple" style="width: 1%;"></div>
        </div>

        <div class="bar-label">
          <span>High-Voltage Float Overpotential Stress</span>
          <span id="loss-voltage">0.00%</span>
        </div>
        <div class="bar-track">
          <div id="bar-voltage" class="bar-fill bar-fill-cyan" style="width: 0%;"></div>
        </div>
      </div>
      <div style="font-size: 11px; color: var(--text-dim); margin-top: 12px; font-family: var(--font-mono);">
        S5 Offline Accounting: <span id="s5-info" style="color:#fff;">0 events</span>
      </div>
    </div>

    <!-- Real-Time Wattage Waveform Canvas -->
    <div class="card card-waveform">
      <h3 style="font-size: 14px; font-family: var(--font-mono); margin-bottom: 10px; color: var(--emerald);">
        INSTANTANEOUS POWER OSCILLOSCOPE (mW)
      </h3>
      <canvas id="scope"></canvas>
    </div>
  </div>

  <footer>
    Hardware Mirrors Active: C:\ProgramData\BMS · D:\.bms_hardware_nvram.dat · S:\.bms_hardware_nvram.dat · Linux /var/lib/bms
  </footer>
</div>

<script>
  const powerHistory = [];
  const MAX_POINTS = 60;

  function updateWaveform(val) {
    powerHistory.push(val);
    if (powerHistory.length > MAX_POINTS) powerHistory.shift();

    const canvas = document.getElementById('scope');
    const ctx = canvas.getContext('2d');
    const w = canvas.width = canvas.parentElement.clientWidth - 40;
    const h = canvas.height = 160;

    ctx.clearRect(0, 0, w, h);

    // Grid lines
    ctx.strokeStyle = 'rgba(255, 255, 255, 0.05)';
    ctx.lineWidth = 1;
    for (let y = 0; y < h; y += 30) {
      ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(w, y); ctx.stroke();
    }

    if (powerHistory.length < 2) return;

    const min = Math.min(...powerHistory, 0);
    const max = Math.max(...powerHistory, 30000);
    const range = max - min || 1;

    ctx.strokeStyle = '#00ff88';
    ctx.lineWidth = 2;
    ctx.beginPath();

    for (let i = 0; i < powerHistory.length; i++) {
      const x = (i / (MAX_POINTS - 1)) * w;
      const y = h - ((powerHistory[i] - min) / range) * (h - 20) - 10;
      if (i === 0) ctx.moveTo(x, y);
      else ctx.lineTo(x, y);
    }
    ctx.stroke();

    // Glow gradient
    ctx.lineTo(w, h);
    ctx.lineTo(0, h);
    ctx.closePath();
    const grad = ctx.createLinearGradient(0, 0, 0, h);
    grad.addColorStop(0, 'rgba(0, 255, 136, 0.25)');
    grad.addColorStop(1, 'transparent');
    ctx.fillStyle = grad;
    ctx.fill();
  }

  function format30(str) {
    if (!str) return '--';
    const s = String(str);
    const parts = s.split('.');
    if (parts.length < 2) return s;
    const intPart = parts[0];
    const dec = parts[1];
    return `<span class="high">${intPart}.${dec.slice(0, 6)}</span><span>${dec.slice(6, 22)}</span><span class="micro">${dec.slice(22)}</span>`;
  }

  const evtSource = new EventSource('/api/stream');
  evtSource.onmessage = function(e) {
    try {
      const data = JSON.parse(e.data);
      const telem = data.telemetry;
      const state = data.state;

      // Update badge
      const badge = document.getElementById('status-badge');
      const chgRate = telem.charge_rate_mw || 0;
      const disRate = telem.discharge_rate_mw || 0;

      if (telem.charging) {
        badge.className = 'badge-chip badge-charging';
        badge.textContent = `CHARGING: +${(chgRate/1000).toFixed(2)} W`;
        updateWaveform(chgRate);
      } else if (telem.discharging) {
        badge.className = 'badge-chip badge-discharging';
        badge.textContent = `DRAINING: -${(disRate/1000).toFixed(2)} W`;
        updateWaveform(-disRate);
      } else {
        badge.className = 'badge-chip badge-idle';
        badge.textContent = `AC MAINS IDLE`;
        updateWaveform(0);
      }

      // Update Gauge
      const socFloat = parseFloat(state.state_of_charge_percentage || 100.0);
      const circumference = 2 * Math.PI * 85;
      const offset = circumference - (socFloat / 100.0) * circumference;
      document.getElementById('gauge-fill').style.strokeDashoffset = offset;
      document.getElementById('gauge-pct').textContent = socFloat.toFixed(1) + '%';
      document.getElementById('mwh-rem').textContent = Math.round(telem.remaining_capacity_mwh).toLocaleString();
      document.getElementById('mwh-fcc').textContent = Math.round(telem.full_charge_capacity_mwh).toLocaleString();

      // Stats
      document.getElementById('stat-volt').textContent = (telem.voltage_mv / 1000.0).toFixed(3) + ' V';
      document.getElementById('stat-power').textContent = (telem.charging ? '+' + chgRate : (telem.discharging ? '-' + disRate : '0')) + ' mW';
      document.getElementById('stat-mains').textContent = telem.power_online ? 'Connected (Online)' : 'Disconnected (Battery)';
      document.getElementById('stat-vhealth').textContent = parseFloat(state.virtual_health_percentage || 100).toFixed(2) + '%';
      document.getElementById('stat-key').textContent = data.hardware_identity ? data.hardware_identity.master_key_fingerprint : '--';

      // 30-decimal registers
      document.getElementById('cycles-30').innerHTML = format30(state.accumulated_cycles);
      document.getElementById('soc-30').innerHTML = format30(state.state_of_charge_percentage);
      document.getElementById('vhealth-30').innerHTML = format30(state.virtual_health_percentage);

      // Degradation bars
      const lCycle = parseFloat(state.cycle_degradation_loss_pct || 0);
      const lThermal = parseFloat(state.thermal_stress_loss_pct || 0);
      const lVolt = parseFloat(state.voltage_stress_loss_pct || 0);
      document.getElementById('loss-cycle').textContent = '-' + lCycle.toFixed(4) + '%';
      document.getElementById('bar-cycle').style.width = Math.min(100, lCycle * 5) + '%';
      document.getElementById('loss-thermal').textContent = '-' + lThermal.toFixed(4) + '%';
      document.getElementById('bar-thermal').style.width = Math.min(100, lThermal * 20) + '%';
      document.getElementById('loss-voltage').textContent = '-' + lVolt.toFixed(4) + '%';
      document.getElementById('bar-voltage').style.width = Math.min(100, lVolt * 10) + '%';

      document.getElementById('s5-info').textContent = `${state.s5_offline_charges_count || 0} events (+${parseFloat(state.s5_offline_cycles_accumulated || 0).toFixed(4)} cyc)`;
    } catch(err) {
      console.error(err);
    }
  };
</script>
</body>
</html>
"""


class BMSHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        # Silence standard HTTP access logging to keep terminal pristine
        pass

    def do_GET(self):
        if self.path == "/" or self.path == "/index.html":
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(HTML_DASHBOARD.encode("utf-8"))
        elif self.path == "/api/status":
            state = engine.load_state()
            telem = engine.get_telemetry()
            state = engine.process_telemetry_and_update_state(telem, state, persist=False)
            payload = {
                "timestamp_utc": time.time(),
                "telemetry": telem,
                "state": state,
                "hardware_identity": {
                    "master_key_fingerprint": engine.HARDWARE_KEY_HEX[:16],
                    "motherboard_uuid": engine.MOTHERBOARD_UUID,
                }
            }
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps(payload).encode("utf-8"))
        elif self.path == "/api/stream":
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Cache-Control", "no-cache")
            self.send_header("Connection", "keep-alive")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()

            state = engine.load_state()
            last_tick = time.time()

            try:
                while True:
                    now = time.time()
                    dt = now - last_tick
                    last_tick = now

                    telem = engine.get_telemetry()

                    # Micro-coulomb integration for live 30-decimal updates
                    chg_mw = telem.get("charge_rate_mw", 0.0)
                    dis_mw = telem.get("discharge_rate_mw", 0.0)
                    design_cap = engine.to_dec30(state.get("design_capacity_mwh", engine.DESIGN_CAPACITY_MWH))
                    full_cap = engine.to_dec30(state.get("last_full_charge_capacity_mwh", engine.DESIGN_CAPACITY_MWH))
                    cur_rem = engine.to_dec30(state.get("last_remaining_capacity_mwh", engine.DESIGN_CAPACITY_MWH))
                    accum_cyc = engine.to_dec30(state.get("accumulated_cycles", engine.HISTORICAL_BASELINE_CYCLES))
                    accum_e = engine.to_dec30(state.get("accumulated_energy_mwh", engine.HISTORICAL_BASELINE_MWH))

                    if telem.get("charging") and chg_mw > 0:
                        d_e = engine.to_dec30(Decimal(str(chg_mw)) * Decimal(str(dt)) / Decimal("3600.0"))
                        d_cyc = d_e / design_cap
                        cur_rem = min(full_cap, cur_rem + d_e)
                        accum_cyc += d_cyc
                        accum_e += d_e
                    elif telem.get("discharging") and dis_mw > 0:
                        d_e = engine.to_dec30(Decimal(str(dis_mw)) * Decimal(str(dt)) / Decimal("3600.0"))
                        cur_rem = max(Decimal("0.0"), cur_rem - d_e)

                    soc = (cur_rem / full_cap) * Decimal("100.0") if full_cap > 0 else Decimal("0.0")
                    if soc > Decimal("100.0"):
                        soc = Decimal("100.0")

                    volt_mv = engine.to_dec30(telem.get("voltage_mv") or engine.NOMINAL_VOLTAGE_MV)
                    h_res = engine.calculate_virtual_health(
                        full_cap, design_cap, accum_cyc, volt_mv,
                        Decimal(str(chg_mw)), Decimal(str(dis_mw)), 31.5, telem.get("power_online", True)
                    )

                    state["accumulated_cycles"] = engine.fmt30(accum_cyc)
                    state["accumulated_energy_mwh"] = engine.fmt30(accum_e)
                    state["last_remaining_capacity_mwh"] = engine.fmt30(cur_rem)
                    state["state_of_charge_percentage"] = engine.fmt30(soc)
                    state["virtual_health_percentage"] = engine.fmt30(h_res["virtual_health_pct"])
                    state["cycle_degradation_loss_pct"] = engine.fmt30(h_res["loss_cycle_pct"])
                    state["thermal_stress_loss_pct"] = engine.fmt30(h_res["loss_thermal_pct"])
                    state["voltage_stress_loss_pct"] = engine.fmt30(h_res["loss_voltage_pct"])

                    payload = {
                        "telemetry": telem,
                        "state": state,
                        "hardware_identity": {
                            "master_key_fingerprint": engine.HARDWARE_KEY_HEX[:16]
                        }
                    }
                    msg = f"data: {json.dumps(payload)}\n\n"
                    self.wfile.write(msg.encode("utf-8"))
                    self.wfile.flush()
                    time.sleep(0.25)
            except (BrokenPipeError, ConnectionResetError):
                pass
        else:
            self.send_error(404)


def start_server(port: int = 8989, open_browser: bool = True):
    server = ThreadingHTTPServer(("127.0.0.1", port), BMSHandler)
    url = f"http://127.0.0.1:{port}"
    print("\n" + "=" * 76)
    print("      BMS REAL-TIME GENERATIVE UI & TELEMETRY DASHBOARD ONLINE       ")
    print("=" * 76)
    print(f" Local Web Dashboard : {url}")
    print(" Telemetry Stream    : Server-Sent Events (SSE) @ 4 Hz")
    print(" Real-Time Registers : 30-Decimal Arbitrary Precision")
    print(" Press Ctrl+C to terminate dashboard server.")
    print("=" * 76 + "\n")

    if open_browser:
        threading.Thread(target=lambda: (time.sleep(0.5), webbrowser.open(url)), daemon=True).start()

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[*] Stopping BMS Telemetry Web Server...")
    finally:
        server.server_close()


if __name__ == "__main__":
    port = 8989
    if "--port" in sys.argv:
        idx = sys.argv.index("--port")
        if idx + 1 < len(sys.argv):
            port = int(sys.argv[idx + 1])
    open_b = "--no-browser" not in sys.argv
    start_server(port, open_b)
