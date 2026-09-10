/**
 * BMS Telemetry Application Orchestrator
 * Connects SSE stream, historical queries, and UI components
 */

import { store, format30, showToast } from './state.js';
import { BmsCombobox } from './combobox.js';
import { BmsCalendar } from './calendar.js';
import { BmsVectorChart } from './chart.js';

class BmsApplication {
  constructor() {
    this.chart = null;
    this.combobox = null;
    this.calendar = null;
    this.activePreset = "24h";
    this.customRange = null;
    this.init();
  }

  init() {
    // 1. Initialize Chart
    this.chart = new BmsVectorChart('chart-svg', 'chart-tooltip');

    // 2. Initialize Combobox
    const channels = [
      { key: "power_mw", label: "Active Power (mW)" },
      { key: "voltage_mv", label: "Terminal Voltage (mV)" },
      { key: "soc_pct", label: "State of Charge (%)" },
      { key: "virtual_health_pct", label: "Virtual Health (%)" },
      { key: "temperature_c", label: "Cell Temperature (°C)" }
    ];
    this.combobox = new BmsCombobox('channel-combobox', channels, (key, label) => {
      if (this.chart) this.chart.setActiveChannel(key);
    });

    // 3. Initialize Calendar
    this.calendar = new BmsCalendar('date-popover', (range) => {
      if (range.preset) {
        this.activePreset = range.preset;
        this.customRange = null;
        this.fetchHistory();
      } else if (range.startEpoch && range.endEpoch) {
        this.activePreset = null;
        this.customRange = { start: range.startEpoch, end: range.endEpoch };
        this.fetchHistory();
      }
    });

    // 4. Bind Action Buttons
    const exportBtn = document.getElementById('btn-export');
    if (exportBtn) exportBtn.addEventListener('click', () => this.exportArchive());

    const importBtn = document.getElementById('btn-import');
    const fileInput = document.getElementById('import-file-input');
    if (importBtn && fileInput) {
      importBtn.addEventListener('click', () => fileInput.click());
      fileInput.addEventListener('change', (e) => this.handleFileImport(e));
    }

    // 5. Initial Data Load & SSE Connection
    this.fetchHistory();
    this.connectStream();
  }

  reloadHistory() {
    this.fetchHistory();
  }

  fetchHistory() {
    let url = `/api/history?preset=${this.activePreset || '24h'}`;
    if (this.customRange) {
      url = `/api/history?start_ts=${this.customRange.start}&end_ts=${this.customRange.end}`;
    }

    fetch(url)
      .then(res => res.json())
      .then(data => {
        if (data && data.points && Array.isArray(data.points)) {
          store.setHistory(data.points);
          if (this.chart) this.chart.setData(data.points);
        }
      })
      .catch(err => {
        console.error("Error fetching historical telemetry:", err);
      });
  }

  connectStream() {
    const evtSource = new EventSource('/api/stream');
    evtSource.onmessage = (e) => {
      try {
        const data = JSON.parse(e.data);
        const telem = data.telemetry;
        const state = data.state;
        store.setTelemetryAndState(telem, state);
        this.updateUI(telem, state, data.hardware_identity);
      } catch (err) {
        console.error("SSE parse error:", err);
      }
    };
    evtSource.onerror = () => {
      const badge = document.getElementById('status-badge');
      if (badge) {
        badge.className = 'badge-chip badge-idle';
        badge.textContent = 'CONNECTING...';
      }
    };
  }

  updateUI(telem, state, hwId) {
    const chgRate = telem.charge_rate_mw || 0;
    const disRate = telem.discharge_rate_mw || 0;
    const remCap = telem.remaining_capacity_mwh || 69993;
    const fccCap = telem.full_charge_capacity_mwh || 69993;
    const isFull = remCap >= fccCap;

    // Status Badge
    const badge = document.getElementById('status-badge');
    if (badge) {
      if (telem.power_online && isFull) {
        badge.className = 'badge-chip badge-idle';
        badge.textContent = '100% FULL (CELLS SATURATED)';
      } else if (telem.charging && chgRate > 0) {
        badge.className = 'badge-chip badge-charging';
        badge.textContent = `CHARGING: +${(chgRate / 1000).toFixed(2)} W`;
      } else if (telem.discharging) {
        badge.className = 'badge-chip badge-discharging';
        badge.textContent = `DRAINING: -${(disRate / 1000).toFixed(2)} W`;
      } else {
        badge.className = 'badge-chip badge-idle';
        badge.textContent = 'AC MAINS STANDBY';
      }
    }

    // Hardware Link & Physical Cell Banner
    const hwTag = document.getElementById('hw-tag');
    if (hwTag) hwTag.textContent = telem.tag || 38;

    const cellStatus = document.getElementById('hw-cell-status');
    const accState = document.getElementById('hw-cycle-acc-state');
    if (cellStatus && accState) {
      if (telem.power_online && isFull) {
        cellStatus.textContent = 'FULLY CHARGED (100.0%) - CELLS SATURATED';
        cellStatus.style.color = 'var(--safe)';
        accState.textContent = 'STOPPED / FROZEN (0 mW Ingested)';
        accState.className = 'badge-chip badge-idle';
      } else if (telem.charging && chgRate > 0 && !isFull) {
        cellStatus.textContent = `ACTIVELY ABSORBING CHARGE (+${(chgRate / 1000).toFixed(2)} W)`;
        cellStatus.style.color = 'var(--safe)';
        accState.textContent = 'RUNNING (COULOMB INTEGRATION ACTIVE)';
        accState.className = 'badge-chip badge-charging';
      } else if (telem.discharging) {
        cellStatus.textContent = `DISCHARGING ON BATTERY (-${(disRate / 1000).toFixed(2)} W)`;
        cellStatus.style.color = 'var(--warn)';
        accState.textContent = 'STOPPED (DISCHARGE)';
        accState.className = 'badge-chip badge-discharging';
      } else {
        cellStatus.textContent = 'AC MAINS STANDBY (IDLE)';
        cellStatus.style.color = 'var(--cyan)';
        accState.textContent = 'STOPPED (STANDBY)';
        accState.className = 'badge-chip badge-idle';
      }
    }

    // Circular SVG Gauge
    const socFloat = parseFloat(state.state_of_charge_percentage || 100.0);
    const circumference = 2 * Math.PI * 85;
    const offset = circumference - (socFloat / 100.0) * circumference;
    const gaugeFill = document.getElementById('gauge-fill');
    const gaugePct = document.getElementById('gauge-pct');
    if (gaugeFill) gaugeFill.style.strokeDashoffset = offset;
    if (gaugePct) gaugePct.textContent = socFloat.toFixed(1) + '%';

    const mwhRem = document.getElementById('mwh-rem');
    const mwhFcc = document.getElementById('mwh-fcc');
    if (mwhRem) mwhRem.textContent = Math.round(telem.remaining_capacity_mwh).toLocaleString();
    if (mwhFcc) mwhFcc.textContent = Math.round(telem.full_charge_capacity_mwh).toLocaleString();

    // Instantaneous Stats & KPIs
    const statVolt = document.getElementById('stat-volt');
    const statPower = document.getElementById('stat-power');
    const statMains = document.getElementById('stat-mains');
    const statVHealth = document.getElementById('stat-vhealth');
    const statKey = document.getElementById('stat-key');
    const kpiCycleInt = document.getElementById('kpi-cycle-int');
    const powerFlowSub = document.getElementById('power-flow-sub');
    const kpiSocBadge = document.getElementById('kpi-soc-badge');

    if (statVolt) statVolt.textContent = (telem.voltage_mv / 1000.0).toFixed(3) + ' V';
    if (statPower) {
      if (telem.charging && chgRate > 0) {
        statPower.textContent = '+' + (chgRate / 1000.0).toFixed(2) + ' W';
        statPower.style.color = 'var(--safe)';
      } else if (telem.discharging && disRate > 0) {
        statPower.textContent = '-' + (disRate / 1000.0).toFixed(2) + ' W';
        statPower.style.color = 'var(--warn)';
      } else {
        statPower.textContent = '0.00 W';
        statPower.style.color = 'var(--cyan)';
      }
    }

    if (powerFlowSub) {
      if (telem.power_online && isFull) {
        powerFlowSub.textContent = 'AC Mains Bypass · Cells Saturated';
      } else if (telem.charging && chgRate > 0) {
        powerFlowSub.textContent = `Ingesting +${chgRate} mW to Cells`;
      } else if (telem.discharging) {
        powerFlowSub.textContent = `Draining -${disRate} mW on Battery`;
      } else {
        powerFlowSub.textContent = 'AC Mains Standby (Zero Drain)';
      }
    }

    if (kpiSocBadge) {
      if (telem.charging && chgRate > 0) {
        kpiSocBadge.className = 'badge-chip badge-charging';
        kpiSocBadge.textContent = 'CHARGING';
      } else if (telem.discharging) {
        kpiSocBadge.className = 'badge-chip badge-discharging';
        kpiSocBadge.textContent = 'DRAINING';
      } else {
        kpiSocBadge.className = 'badge-chip badge-idle';
        kpiSocBadge.textContent = isFull ? 'SATURATED' : 'STANDBY';
      }
    }

    if (statMains) statMains.textContent = telem.power_online ? 'AC Online' : 'On Battery';
    if (statVHealth) statVHealth.textContent = parseFloat(state.virtual_health_percentage || 100).toFixed(2) + '%';
    if (statKey) statKey.textContent = hwId ? hwId.master_key_fingerprint.slice(0, 10) + '...' : '--';

    if (kpiCycleInt) {
      const cycParts = String(state.accumulated_cycles || '12.000000').split('.');
      kpiCycleInt.innerHTML = `${cycParts[0]}<span style="font-size:13px; color:var(--muted-foreground);">.${(cycParts[1] || '0000').slice(0, 4)}</span>`;
    }

    // 30-Decimal Registers (Zero Float Casting)
    const cycles30 = document.getElementById('cycles-30');
    const soc30 = document.getElementById('soc-30');
    const vhealth30 = document.getElementById('vhealth-30');

    if (cycles30) cycles30.innerHTML = format30(state.accumulated_cycles);
    if (soc30) soc30.innerHTML = format30(state.state_of_charge_percentage);
    if (vhealth30) vhealth30.innerHTML = format30(state.virtual_health_percentage);

    // If viewing Live 5m or 1h preset, stream live points directly to chart
    if ((this.activePreset === "5m" || this.activePreset === "1h") && this.chart) {
      const nowMs = Date.now();
      const pNet = telem.charging ? chgRate : (telem.discharging ? -disRate : 0);
      this.chart.appendLivePoint({
        timestamp: new Date(nowMs).toISOString(),
        epoch_ms: nowMs,
        voltage_mv: telem.voltage_mv || 11550,
        current_ma: telem.current_ma || 0,
        power_mw: pNet,
        soc_pct: socFloat,
        temperature_c: 31.5,
        virtual_health_pct: parseFloat(state.virtual_health_percentage || 99.4)
      });
    }
  }

  exportArchive() {
    showToast("Preparing full untruncated lifetime telemetry archive...");
    const a = document.createElement('a');
    a.href = '/api/export';
    a.download = `bms_lifetime_telemetry_${new Date().toISOString().replace(/[:.]/g, '-')}.json`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    setTimeout(() => {
      showToast("Lifetime telemetry archive exported successfully!");
    }, 800);
  }

  handleFileImport(event) {
    const file = event.target.files[0];
    if (!file) return;

    showToast("Reading archive file...");
    const reader = new FileReader();
    reader.onload = (e) => {
      try {
        const parsed = JSON.parse(e.target.result);
        fetch('/api/import', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(parsed)
        })
        .then(res => res.json())
        .then(data => {
          if (data.success) {
            showToast(`RESTORED: ${data.accumulated_cycles} CYCLES (${data.total_historical_events} EVENTS INTACT)`);
            this.fetchHistory();
          } else {
            showToast("Import error: " + (data.error || "Validation error"), true);
          }
        })
        .catch(err => {
          showToast("Network error importing telemetry: " + err.message, true);
        });
      } catch (err) {
        showToast("Invalid JSON telemetry file.", true);
      }
    };
    reader.readAsText(file);
    event.target.value = '';
  }
}

// Instantiate on DOM load
window.addEventListener('DOMContentLoaded', () => {
  window.bmsApp = new BmsApplication();
});
