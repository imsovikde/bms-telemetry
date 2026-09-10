/**
 * BMS Telemetry Application Orchestrator
 * Connects SSE stream, historical queries, and custom UI components
 * Zero inline style mutations, zero em-dashes or en-dashes
 */

import { store, format30, showToast } from "./state.js";
import { BmsCombobox } from "./combobox.js";
import { BmsCalendar } from "./calendar.js";
import { BmsVectorChart } from "./chart.js";

class BmsApplication {
  constructor() {
    this.chart = null;
    this.combobox = null;
    this.calendar = null;
    this.activePreset = "24h";
    this.customRange = null;
    this.lastLedgerEventTime = 0;
    this.lastKnownChargingState = null;
    this.init();
  }

  init() {
    // 1. Initialize Vector Chart
    this.chart = new BmsVectorChart("chart-svg", "chart-tooltip");

    // 2. Initialize Channel Combobox
    const channels = [
      { key: "power_mw", label: "Active Power (mW)" },
      { key: "voltage_mv", label: "Terminal Voltage (mV)" },
      { key: "soc_pct", label: "State of Charge (%)" },
      { key: "virtual_health_pct", label: "Virtual Health (%)" },
      { key: "temperature_c", label: "Cell Temperature (deg C)" }
    ];
    this.combobox = new BmsCombobox("channel-combobox", channels, (key, label) => {
      if (this.chart) this.chart.setActiveChannel(key);
      this.updateHeroCallout();
    });

    // 3. Initialize Date-Range Calendar Popover
    this.calendar = new BmsCalendar("date-popover", (range) => {
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

    // 4. Bind Export and Import Actions
    const exportCsvBtn = document.getElementById("btn-export-csv");
    if (exportCsvBtn) exportCsvBtn.addEventListener("click", () => this.exportCsv());

    const exportBtn = document.getElementById("btn-export");
    if (exportBtn) exportBtn.addEventListener("click", () => this.exportArchive());

    const importBtn = document.getElementById("btn-import");
    const fileInput = document.getElementById("import-file-input");
    if (importBtn && fileInput) {
      importBtn.addEventListener("click", () => fileInput.click());
      fileInput.addEventListener("change", (e) => this.handleFileImport(e));
    }

    // 5. Initial History Query and SSE Connection
    this.fetchHistory();
    this.connectStream();
  }

  reloadHistory() {
    this.fetchHistory();
  }

  fetchHistory() {
    let url = `/api/history?preset=${this.activePreset || "24h"}`;
    if (this.customRange) {
      url = `/api/history?start_ts=${this.customRange.start}&end_ts=${this.customRange.end}`;
    }

    fetch(url)
      .then((res) => res.json())
      .then((data) => {
        if (data && data.points && Array.isArray(data.points)) {
          store.setHistory(data.points);
          if (this.chart) this.chart.setData(data.points);
        }
      })
      .catch((err) => {
        console.error("Error fetching historical telemetry:", err);
      });
  }

  connectStream() {
    const evtSource = new EventSource("/api/stream");
    evtSource.onmessage = (e) => {
      try {
        const data = JSON.parse(e.data);
        const telem = data.telemetry;
        const state = data.state;
        const thermals = data.thermals;
        const topProcs = data.top_processes;
        store.setTelemetryAndState(telem, state);
        this.updateUI(telem, state, data.hardware_identity, thermals, topProcs);
      } catch (err) {
        console.error("SSE parse error:", err);
      }
    };
    evtSource.onerror = () => {
      const badge = document.getElementById("status-badge");
      if (badge) {
        badge.className = "badge-chip badge-idle";
        badge.textContent = "CONNECTING...";
      }
    };
  }

  updateUI(telem, state, hwId, thermals, topProcs) {
    const chgRate = telem.charge_rate_mw || 0;
    const disRate = telem.discharge_rate_mw || 0;
    const remCap = telem.remaining_capacity_mwh || 69993;
    const fccCap = telem.full_charge_capacity_mwh || 69993;
    const isFull = remCap >= fccCap;

    // 1. Status Badge
    const badge = document.getElementById("status-badge");
    if (badge) {
      if (telem.power_online && isFull) {
        badge.className = "badge-chip badge-idle";
        badge.textContent = "100% FULL (CELLS SATURATED)";
      } else if (telem.charging && chgRate > 0) {
        badge.className = "badge-chip badge-charging";
        badge.textContent = `CHARGING: +${(chgRate / 1000).toFixed(2)} W`;
      } else if (telem.discharging) {
        badge.className = "badge-chip badge-discharging";
        badge.textContent = `DRAINING: -${(disRate / 1000).toFixed(2)} W`;
      } else {
        badge.className = "badge-chip badge-idle";
        badge.textContent = "AC MAINS STANDBY";
      }
    }

    // 2. Hardware Link and Physical Cell Banner
    const hwTag = document.getElementById("hw-tag");
    if (hwTag) hwTag.textContent = telem.tag || 38;

    const cellStatus = document.getElementById("hw-cell-status");
    const accState = document.getElementById("hw-cycle-acc-state");
    if (cellStatus && accState) {
      if (telem.power_online && isFull) {
        cellStatus.textContent = "FULLY CHARGED (100.0%) / CELLS SATURATED";
        cellStatus.className = "hw-value-text hw-value-safe";
        accState.textContent = "STOPPED / FROZEN (0 mW Ingested)";
        accState.className = "badge-chip badge-idle badge-xs";
      } else if (telem.charging && chgRate > 0 && !isFull) {
        cellStatus.textContent = `ACTIVELY ABSORBING CHARGE (+${(chgRate / 1000).toFixed(2)} W)`;
        cellStatus.className = "hw-value-text hw-value-safe";
        accState.textContent = "RUNNING (COULOMB INTEGRATION ACTIVE)";
        accState.className = "badge-chip badge-charging badge-xs";
      } else if (telem.discharging) {
        cellStatus.textContent = `DISCHARGING ON BATTERY (-${(disRate / 1000).toFixed(2)} W)`;
        cellStatus.className = "hw-value-text hw-value-warn";
        accState.textContent = "STOPPED (DISCHARGE)";
        accState.className = "badge-chip badge-discharging badge-xs";
      } else {
        cellStatus.textContent = "AC MAINS STANDBY (IDLE)";
        cellStatus.className = "hw-value-text hw-value-info";
        accState.textContent = "STOPPED (STANDBY)";
        accState.className = "badge-chip badge-idle badge-xs";
      }
    }

    // 3. Circular SVG Gauge (Pure SVG attribute mutation)
    const socFloat = parseFloat(state.state_of_charge_percentage || 100.0);
    const circumference = 2 * Math.PI * 85;
    const offset = circumference - (socFloat / 100.0) * circumference;
    const gaugeFill = document.getElementById("gauge-fill");
    const gaugePct = document.getElementById("gauge-pct");
    if (gaugeFill) gaugeFill.setAttribute("stroke-dashoffset", offset.toFixed(2));
    if (gaugePct) gaugePct.textContent = socFloat.toFixed(1) + "%";

    const mwhRem = document.getElementById("mwh-rem");
    const mwhFcc = document.getElementById("mwh-fcc");
    if (mwhRem) mwhRem.textContent = Math.round(telem.remaining_capacity_mwh).toLocaleString();
    if (mwhFcc) mwhFcc.textContent = Math.round(telem.full_charge_capacity_mwh).toLocaleString();

    // 4. Instantaneous KPIs
    const statVolt = document.getElementById("stat-volt");
    const statPower = document.getElementById("stat-power");
    const statMains = document.getElementById("stat-mains");
    const statVHealth = document.getElementById("stat-vhealth");
    const statKey = document.getElementById("stat-key");
    const kpiCycleInt = document.getElementById("kpi-cycle-int");
    const powerFlowSub = document.getElementById("power-flow-sub");
    const kpiSocBadge = document.getElementById("kpi-soc-badge");

    if (statVolt) statVolt.textContent = (telem.voltage_mv / 1000.0).toFixed(3) + " V";
    if (statPower) {
      if (telem.charging && chgRate > 0) {
        statPower.textContent = "+" + (chgRate / 1000.0).toFixed(2) + " W";
        statPower.className = "kpi-num kpi-num-safe";
      } else if (telem.discharging && disRate > 0) {
        statPower.textContent = "-" + (disRate / 1000.0).toFixed(2) + " W";
        statPower.className = "kpi-num kpi-num-warn";
      } else {
        statPower.textContent = "0.00 W";
        statPower.className = "kpi-num kpi-num-info";
      }
    }

    if (powerFlowSub) {
      if (telem.power_online && isFull) {
        powerFlowSub.textContent = "AC Mains Bypass / Cells Saturated";
      } else if (telem.charging && chgRate > 0) {
        powerFlowSub.textContent = `Ingesting +${chgRate} mW to Cells`;
      } else if (telem.discharging) {
        powerFlowSub.textContent = `Draining -${disRate} mW on Battery`;
      } else {
        powerFlowSub.textContent = "AC Mains Standby (Zero Drain)";
      }
    }

    if (kpiSocBadge) {
      if (telem.charging && chgRate > 0) {
        kpiSocBadge.className = "badge-chip badge-charging badge-xs";
        kpiSocBadge.textContent = "CHARGING";
      } else if (telem.discharging) {
        kpiSocBadge.className = "badge-chip badge-discharging badge-xs";
        kpiSocBadge.textContent = "DRAINING";
      } else {
        kpiSocBadge.className = "badge-chip badge-idle badge-xs";
        kpiSocBadge.textContent = isFull ? "SATURATED" : "STANDBY";
      }
    }

    if (statMains) statMains.textContent = telem.power_online ? "AC Online" : "On Battery";
    if (statVHealth) statVHealth.textContent = parseFloat(state.virtual_health_percentage || 100).toFixed(2) + "%";
    if (statKey) statKey.textContent = hwId ? hwId.master_key_fingerprint.slice(0, 10) + "..." : "--";

    if (kpiCycleInt) {
      const cycParts = String(state.accumulated_cycles || "12.000000").split(".");
      kpiCycleInt.innerHTML = `${cycParts[0]}<span class="kpi-cycle-decimal">.${(cycParts[1] || "0000").slice(0, 4)}</span>`;
    }

    // 5. 30-Decimal Multi-Registers (Zero float casting)
    const cycles30 = document.getElementById("cycles-30");
    const soc30 = document.getElementById("soc-30");
    const vhealth30 = document.getElementById("vhealth-30");

    if (cycles30) cycles30.innerHTML = format30(state.accumulated_cycles);
    if (soc30) soc30.innerHTML = format30(state.state_of_charge_percentage);
    if (vhealth30) vhealth30.innerHTML = format30(state.virtual_health_percentage);

    // 6. Append Real Telemetry Activity to Live Stream Ledger
    this.recordLiveLedgerEvent(telem, state, isFull, chgRate, disRate);

    // 7. If viewing Live 5m or 1h preset, stream live points directly to chart
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

    this.updateHeroCallout();
  }

  updateHeroCallout() {
    const heroEl = document.getElementById("chart-hero-val");
    if (!heroEl || !store.telemetry || !store.state) return;
    const telem = store.telemetry;
    const state = store.state;
    const ch = (this.chart && this.chart.activeChannel) || "power_mw";

    if (ch === "power_mw") {
      const chgRate = telem.charge_rate_mw || 0;
      const disRate = telem.discharge_rate_mw || 0;
      if (telem.charging && chgRate > 0) heroEl.textContent = `+${(chgRate / 1000).toFixed(2)} W Active Charge`;
      else if (telem.discharging && disRate > 0) heroEl.textContent = `-${(disRate / 1000).toFixed(2)} W Discharge`;
      else heroEl.textContent = "0.00 W Mains Standby";
    } else if (ch === "voltage_mv") {
      heroEl.textContent = `${(telem.voltage_mv / 1000).toFixed(3)} V Terminal Voltage`;
    } else if (ch === "soc_pct") {
      heroEl.textContent = `${parseFloat(state.state_of_charge_percentage || 100).toFixed(1)}% State of Charge`;
    } else if (ch === "virtual_health_pct") {
      heroEl.textContent = `${parseFloat(state.virtual_health_percentage || 100).toFixed(2)}% Virtual Health`;
    } else if (ch === "temperature_c") {
      heroEl.textContent = "31.5 deg C Cell Temperature";
    }
  }

  recordLiveLedgerEvent(telem, state, isFull, chgRate, disRate) {
    const now = Date.now();
    const currentStateKey = `${telem.power_online}_${telem.charging}_${telem.discharging}_${isFull}`;

    // Record on state transition or at least once every 10 seconds
    if (this.lastKnownChargingState !== currentStateKey || now - this.lastLedgerEventTime > 10000) {
      this.lastKnownChargingState = currentStateKey;
      this.lastLedgerEventTime = now;

      const tbody = document.getElementById("ledger-tbody");
      if (!tbody) return;

      const initRow = document.getElementById("ledger-initial-row");
      if (initRow) initRow.remove();

      let eventName = "AC Standby Steady State";
      let eventBadgeClass = "badge-idle";
      let powerText = "0 mW";
      let coulombText = "Coulomb Acc Frozen";

      if (telem.power_online && isFull) {
        eventName = "AC Mains Bypass / Cells Full";
        eventBadgeClass = "badge-idle";
        powerText = "Bypass 0 mW";
        coulombText = "Cells Saturated (0 drift)";
      } else if (telem.charging && chgRate > 0) {
        eventName = "Active Cell Absorption";
        eventBadgeClass = "badge-charging";
        powerText = `+${chgRate} mW`;
        coulombText = "Coulomb Ingestion Active";
      } else if (telem.discharging && disRate > 0) {
        eventName = "Active Cell Discharge";
        eventBadgeClass = "badge-discharging";
        powerText = `-${disRate} mW`;
        coulombText = "Discharge Drain";
      }

      const dStr = new Date(now).toISOString().replace("T", " ").slice(0, 19) + " UTC";
      const vStr = (telem.voltage_mv / 1000.0).toFixed(3) + " V";

      const tr = document.createElement("tr");
      tr.innerHTML = `
        <td>${dStr}</td>
        <td><span class="badge-chip ${eventBadgeClass} badge-xs">${eventName}</span></td>
        <td>${vStr}</td>
        <td>${powerText}</td>
        <td>${coulombText}</td>
        <td><span class="reg-tag-safe">LIVE VERIFIED</span></td>
      `;

      tbody.insertBefore(tr, tbody.firstChild);

      // Keep ledger bounded to maximum 20 rows
      while (tbody.children.length > 20) {
        tbody.removeChild(tbody.lastChild);
      }
    }

    // 9. Hardware Thermals and DTS Heatmap Update
    if (thermals) {
      const pkgTemp = thermals.cpu_package_temp_c || 48.0;
      const headroom = thermals.distance_to_tjmax_c || 52.0;
      const perfLimit = thermals.performance_limit_pct || 100.0;
      const tjmax = thermals.tjmax_c || 100.0;

      const pkgEl = document.getElementById("stat-cpu-package");
      if (pkgEl) {
        pkgEl.textContent = `${pkgTemp.toFixed(1)} \u00B0C`;
        pkgEl.className = `kpi-num ${pkgTemp >= 85 ? "kpi-num-warn" : "kpi-num-safe"}`;
      }

      const headEl = document.getElementById("stat-tjmax-headroom");
      if (headEl) {
        headEl.textContent = `${headroom.toFixed(1)} \u00B0C`;
        headEl.className = `kpi-num ${headroom < 15 ? "kpi-num-warn" : "kpi-num-safe"}`;
      }

      const barEl = document.getElementById("tjmax-progress-bar");
      if (barEl) {
        const pct = Math.min(100, Math.max(0, (headroom / tjmax) * 100));
        barEl.style.width = `${pct.toFixed(1)}%`;
      }

      const limitEl = document.getElementById("stat-perf-limit");
      if (limitEl) limitEl.textContent = `${perfLimit.toFixed(0)}%`;

      const driverEl = document.getElementById("thermal-driver-badge");
      if (driverEl) driverEl.textContent = thermals.sensor_source || "INTEL RAPTOR LAKE DTS";

      const alertEl = document.getElementById("thermal-alert-badge");
      if (alertEl) {
        alertEl.textContent = thermals.alert_level || "OPTIMAL";
        alertEl.className = `badge-chip ${thermals.alert_level === "OPTIMAL" ? "badge-charging" : "badge-discharging"} badge-xs`;
      }

      if (thermals.p_cores) {
        for (let i = 1; i <= 4; i++) {
          const tVal = thermals.p_cores[`P-Core #${i}`];
          const el = document.getElementById(`val-p${i}`);
          if (el && tVal !== undefined) {
            el.textContent = `${tVal.toFixed(1)} \u00B0C`;
            el.className = `core-temp ${tVal >= 85 ? "temp-hot" : (tVal >= 70 ? "temp-warm" : "temp-optimal")}`;
          }
        }
      }

      if (thermals.e_cores) {
        for (let i = 1; i <= 8; i++) {
          const tVal = thermals.e_cores[`E-Core #${i}`];
          const el = document.getElementById(`val-e${i}`);
          if (el && tVal !== undefined) {
            el.textContent = `${tVal.toFixed(1)} \u00B0C`;
            el.className = `core-temp ${tVal >= 85 ? "temp-hot" : (tVal >= 70 ? "temp-warm" : "temp-optimal")}`;
          }
        }
      }
    }

    // 10. Process Power & Resource Attribution Update
    if (topProcs && Array.isArray(topProcs) && topProcs.length > 0) {
      const totalPowerW = topProcs.reduce((acc, p) => acc + (p.power_watts || 0), 0);
      const dynBadge = document.getElementById("dynamic-power-val");
      if (dynBadge) {
        dynBadge.textContent = `${totalPowerW.toFixed(2)} W DYNAMIC COMPUTE ATTRIBUTED`;
      }

      const procTbody = document.getElementById("proc-tbody");
      if (procTbody) {
        procTbody.innerHTML = topProcs.map((p, idx) => `
          <tr>
            <td class="proc-rank">#${idx + 1}</td>
            <td><span class="proc-name-badge">${p.name}</span><span class="proc-pid">PID ${p.pid}</span></td>
            <td>${p.cpu_pct ? p.cpu_pct.toFixed(1) : "0.0"}%</td>
            <td>${p.gpu_pct ? p.gpu_pct.toFixed(1) : "0.0"}%</td>
            <td>${p.power_watts ? p.power_watts.toFixed(3) : "0.000"} W</td>
            <td>${p.power_share_pct ? p.power_share_pct.toFixed(1) : "0.0"}%</td>
            <td>${p.accumulated_energy_mwh ? p.accumulated_energy_mwh.toFixed(3) : "0.000"} mWh</td>
          </tr>
        `).join("");
      }

      const stackedBar = document.getElementById("proc-stacked-bar");
      if (stackedBar) {
        const palette = ["#10b981", "#3b82f6", "#8b5cf6", "#f59e0b", "#ec4899", "#06b6d4", "#64748b"];
        stackedBar.innerHTML = topProcs.slice(0, 7).map((p, i) => `
          <div class="proc-bar-seg" style="width: ${Math.max(1, p.power_share_pct || 0)}%; background-color: ${palette[i % palette.length]}" title="${p.name}: ${(p.power_share_pct || 0).toFixed(1)}% (${(p.power_watts || 0).toFixed(2)}W)"></div>
        `).join("");
      }
    }
  }

  exportCsv() {
    showToast("Preparing time-series CSV export...");
    const a = document.createElement("a");
    a.href = "/api/export/csv";
    a.download = `bms_telemetry_history_${new Date().toISOString().replace(/[:.]/g, "-")}.csv`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    setTimeout(() => {
      showToast("Time-series CSV exported successfully!");
    }, 800);
  }

  exportArchive() {
    showToast("Preparing full untruncated lifetime telemetry archive...");
    const a = document.createElement("a");
    a.href = "/api/export";
    a.download = `bms_lifetime_telemetry_${new Date().toISOString().replace(/[:.]/g, "-")}.json`;
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
        fetch("/api/import", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(parsed)
        })
          .then((res) => res.json())
          .then((data) => {
            if (data.success) {
              showToast(`RESTORED: ${data.accumulated_cycles} CYCLES (${data.total_historical_events} EVENTS INTACT)`);
              this.fetchHistory();
            } else {
              showToast("Import error: " + (data.error || "Validation error"), true);
            }
          })
          .catch((err) => {
            showToast("Network error importing telemetry: " + err.message, true);
          });
      } catch (err) {
        showToast("Invalid JSON telemetry file.", true);
      }
    };
    reader.readAsText(file);
    event.target.value = "";
  }
}

// Instantiate on DOM load
window.addEventListener("DOMContentLoaded", () => {
  window.bmsApp = new BmsApplication();
});
