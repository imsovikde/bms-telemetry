/**
 * BMS Pure SVG Vector Telemetry Chart Engine
 * Features LTTB downsampling, Fritsch-Carlson monotonic cubic Bezier paths (zero retrograde loops),
 * pixel-density noise binning, multi-axis domains, non-overlapping Y-axis ticks,
 * interactive crosshair scrubbing, and requestAnimationFrame render pacing.
 * Zero em-dashes or en-dashes
 */

export class BmsVectorChart {
  constructor(svgId, tooltipId) {
    this.svg = document.getElementById(svgId);
    this.tooltip = document.getElementById(tooltipId);
    this.dataset = [];
    this.visibleSeries = {
      power_mw: true,
      voltage_mv: true,
      soc_pct: true,
      temperature_c: false,
      virtual_health_pct: false
    };
    this.activeChannel = "power_mw";
    this.useSmoothCurves = true;
    this.renderScheduled = false;

    this.seriesConfig = [
      { key: "power_mw", min: -35000, max: 40000, lineId: "line-power", areaId: "area-power", dotId: "dot-power", unit: "mW", label: "Active Power" },
      { key: "voltage_mv", min: 9000, max: 13500, lineId: "line-voltage", areaId: "area-voltage", dotId: "dot-voltage", unit: "mV", label: "Pack Voltage" },
      { key: "soc_pct", min: 0, max: 100, lineId: "line-soc", areaId: "area-soc", dotId: "dot-soc", unit: "%", label: "State of Charge" },
      { key: "temperature_c", min: 15, max: 65, lineId: "line-temp", areaId: "area-temp", dotId: "dot-temp", unit: "deg C", label: "Cell Temp" },
      { key: "virtual_health_pct", min: 60, max: 100, lineId: "line-health", areaId: "area-health", dotId: "dot-health", unit: "%", label: "Virtual Health" }
    ];

    this.init();
  }

  init() {
    if (!this.svg) return;
    this.gridG = document.getElementById("chart-grid");
    this.axesG = document.getElementById("chart-axes");
    this.scrubLine = document.getElementById("scrub-line-x");
    this.chartBox = document.getElementById("svg-chart-box");
    this.miniPath = document.getElementById("mini-path");

    if (this.chartBox) {
      this.chartBox.addEventListener("mousemove", (e) => this.handleMouseMove(e));
      this.chartBox.addEventListener("mouseleave", () => this.handleMouseLeave());
    }

    // Toggle switches
    const smoothSwitch = document.getElementById("smooth-switch");
    if (smoothSwitch) {
      smoothSwitch.addEventListener("click", () => {
        this.useSmoothCurves = !this.useSmoothCurves;
        smoothSwitch.setAttribute("aria-checked", this.useSmoothCurves ? "true" : "false");
        this.requestRender();
      });
      smoothSwitch.addEventListener("keydown", (e) => {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          this.useSmoothCurves = !this.useSmoothCurves;
          smoothSwitch.setAttribute("aria-checked", this.useSmoothCurves ? "true" : "false");
          this.requestRender();
        }
      });
    }

    // Series toggle pills
    const pills = document.querySelectorAll(".series-pill");
    pills.forEach((pill) => {
      pill.addEventListener("click", () => {
        const key = pill.dataset.series;
        if (key && this.visibleSeries[key] !== undefined) {
          this.visibleSeries[key] = !this.visibleSeries[key];
          pill.classList.toggle("active", this.visibleSeries[key]);
          this.requestRender();
        }
      });
    });

    const resetBtn = document.getElementById("reset-zoom-btn");
    if (resetBtn) {
      resetBtn.addEventListener("click", () => {
        if (window.bmsApp) window.bmsApp.reloadHistory();
      });
    }
  }

  setData(points) {
    if (!Array.isArray(points)) return;
    this.dataset = points.filter((p) => p && typeof p.epoch_ms === "number" && !isNaN(p.epoch_ms));
    this.requestRender();
  }

  appendLivePoint(p) {
    if (!p || typeof p.epoch_ms !== "number") return;
    this.dataset.push(p);
    // Keep window bounded
    if (this.dataset.length > 5000) {
      this.dataset.shift();
    }
    this.requestRender();
  }

  setActiveChannel(channelKey) {
    this.activeChannel = channelKey;
    this.requestRender();
  }

  requestRender() {
    if (this.renderScheduled) return;
    this.renderScheduled = true;
    requestAnimationFrame(() => {
      this.render();
      this.renderScheduled = false;
    });
  }

  /**
   * Largest-Triangle-Three-Buckets (LTTB) Downsampling Algorithm
   */
  lttbDownsample(data, threshold) {
    if (!data || data.length <= threshold || threshold <= 2) return data;
    const sampled = [];
    const bucketSize = (data.length - 2) / (threshold - 2);
    let a = 0;
    sampled.push(data[a]);

    for (let i = 0; i < threshold - 2; i++) {
      let avgX = 0, avgY = 0;
      const avgStart = Math.floor((i + 1) * bucketSize) + 1;
      const avgEnd = Math.min(Math.floor((i + 2) * bucketSize) + 1, data.length);
      const avgLen = avgEnd - avgStart;
      for (let j = avgStart; j < avgEnd; j++) {
        avgX += data[j].x;
        avgY += data[j].y;
      }
      avgX /= avgLen || 1;
      avgY /= avgLen || 1;

      const rangeStart = Math.floor(i * bucketSize) + 1;
      const rangeEnd = Math.min(Math.floor((i + 1) * bucketSize) + 1, data.length);
      const pointA = data[a];
      let maxArea = -1;
      let maxAreaPoint = data[rangeStart];

      for (let j = rangeStart; j < rangeEnd; j++) {
        const area = Math.abs(
          (pointA.x - avgX) * (data[j].y - pointA.y) -
          (pointA.x - data[j].x) * (avgY - pointA.y)
        ) * 0.5;
        if (area > maxArea) {
          maxArea = area;
          maxAreaPoint = data[j];
          a = j;
        }
      }
      sampled.push(maxAreaPoint);
    }
    sampled.push(data[data.length - 1]);
    return sampled;
  }

  /**
   * Pixel-density binning and noise attenuation
   * Groups high-frequency points sharing horizontal pixel buckets to eliminate barcode oscillation
   */
  smoothAndBinPoints(points, bucketWidth = 2.0) {
    if (!points || points.length <= 2) return points || [];
    const binned = [];
    let currentBucket = [];
    let currentBucketIdx = null;

    for (let i = 0; i < points.length; i++) {
      const pt = points[i];
      const bIdx = Math.floor(pt.x / bucketWidth);
      if (currentBucketIdx === null || bIdx === currentBucketIdx) {
        currentBucket.push(pt);
        currentBucketIdx = bIdx;
      } else {
        binned.push(this._aggregateBucket(currentBucket));
        currentBucket = [pt];
        currentBucketIdx = bIdx;
      }
    }
    if (currentBucket.length > 0) {
      binned.push(this._aggregateBucket(currentBucket));
    }
    return binned;
  }

  _aggregateBucket(bucket) {
    if (bucket.length === 1) return bucket[0];
    let sumX = 0, sumY = 0, sumVal = 0;
    for (let i = 0; i < bucket.length; i++) {
      sumX += bucket[i].x;
      sumY += bucket[i].y;
      sumVal += bucket[i].rawVal;
    }
    const len = bucket.length;
    return {
      x: sumX / len,
      y: sumY / len,
      rawVal: sumVal / len,
      point: bucket[Math.floor(len / 2)].point
    };
  }

  /**
   * Fritsch-Carlson Monotonic Cubic Spline SVG Path Construction
   * Enforces strict horizontal monotonicity (p1.x <= cp1x <= cp2x <= p2.x) to
   * mathematically prevent retrograde time-reversal loops (dx/dt < 0) and overshoot oscillations.
   */
  buildPath(points, closeBottom = false, bottomY = 288) {
    if (!points || points.length === 0) return "";
    if (points.length === 1) return `M ${points[0].x.toFixed(1)} ${points[0].y.toFixed(1)}`;

    let d = `M ${points[0].x.toFixed(1)} ${points[0].y.toFixed(1)}`;
    const n = points.length;

    if (!this.useSmoothCurves || n < 3) {
      for (let i = 1; i < n; i++) {
        d += ` L ${points[i].x.toFixed(1)} ${points[i].y.toFixed(1)}`;
      }
    } else {
      // 1. Calculate secant slopes: s[i] = (y[i+1] - y[i]) / (x[i+1] - x[i])
      const dxs = new Array(n - 1);
      const dys = new Array(n - 1);
      const slopes = new Array(n - 1);

      for (let i = 0; i < n - 1; i++) {
        dxs[i] = points[i + 1].x - points[i].x;
        dys[i] = points[i + 1].y - points[i].y;
        slopes[i] = dxs[i] > 1e-6 ? dys[i] / dxs[i] : 0;
      }

      // 2. Calculate initial tangent slopes at each point
      const tangents = new Array(n);
      tangents[0] = slopes[0];
      tangents[n - 1] = slopes[n - 2];

      for (let i = 1; i < n - 1; i++) {
        const s0 = slopes[i - 1];
        const s1 = slopes[i];
        if (s0 * s1 <= 0) {
          tangents[i] = 0; // Local extremum: flat tangent
        } else {
          tangents[i] = (s0 + s1) / 2;
        }
      }

      // 3. Apply Fritsch-Carlson monotonic clamping
      for (let i = 0; i < n - 1; i++) {
        const s = slopes[i];
        if (Math.abs(s) < 1e-6) {
          tangents[i] = 0;
          tangents[i + 1] = 0;
        } else {
          const a = tangents[i] / s;
          const b = tangents[i + 1] / s;
          if (a < 0) tangents[i] = 0;
          if (b < 0) tangents[i + 1] = 0;
          const hyp = a * a + b * b;
          if (hyp > 9) {
            const tau = 3 / Math.sqrt(hyp);
            tangents[i] = tau * a * s;
            tangents[i + 1] = tau * b * s;
          }
        }
      }

      // 4. Construct cubic Bezier control points with strict horizontal bounding
      for (let i = 0; i < n - 1; i++) {
        const p1 = points[i];
        const p2 = points[i + 1];
        const segDx = dxs[i];

        if (segDx <= 1e-4) {
          d += ` L ${p2.x.toFixed(1)} ${p2.y.toFixed(1)}`;
          continue;
        }

        // Tangent step: dx/3
        const stepX = segDx / 3.0;
        let cp1x = p1.x + stepX;
        let cp1y = p1.y + tangents[i] * stepX;
        let cp2x = p2.x - stepX;
        let cp2y = p2.y - tangents[i + 1] * stepX;

        // Strict horizontal monotonicity enforcement (dx/dt > 0 invariant)
        cp1x = Math.max(p1.x, Math.min(cp1x, p1.x + 0.45 * segDx));
        cp2x = Math.max(p1.x + 0.55 * segDx, Math.min(cp2x, p2.x));

        if (isNaN(cp1x) || isNaN(cp1y) || isNaN(cp2x) || isNaN(cp2y)) {
          d += ` L ${p2.x.toFixed(1)} ${p2.y.toFixed(1)}`;
        } else {
          d += ` C ${cp1x.toFixed(1)} ${cp1y.toFixed(1)}, ${cp2x.toFixed(1)} ${cp2y.toFixed(1)}, ${p2.x.toFixed(1)} ${p2.y.toFixed(1)}`;
        }
      }
    }

    if (closeBottom && points.length > 0) {
      const last = points[points.length - 1];
      const first = points[0];
      d += ` L ${last.x.toFixed(1)} ${bottomY} L ${first.x.toFixed(1)} ${bottomY} Z`;
    }
    return d;
  }

  render() {
    if (!this.dataset || this.dataset.length === 0) return;

    const padLeft = 72;
    const padRight = 30;
    const padTop = 25;
    const padBottom = 32;
    const w = 1000;
    const h = 320;
    const plotW = w - padLeft - padRight;
    const plotH = h - padTop - padBottom;
    const bottomY = h - padBottom;

    const minT = this.dataset[0].epoch_ms;
    const maxT = this.dataset[this.dataset.length - 1].epoch_ms;
    const rangeT = maxT - minT || 1;

    // Reset Grid and Axes
    if (this.gridG) this.gridG.innerHTML = "";
    if (this.axesG) this.axesG.innerHTML = "";

    // 5 horizontal gridlines
    for (let i = 0; i <= 4; i++) {
      const yVal = padTop + (plotH / 4) * i;
      if (this.gridG) {
        this.gridG.innerHTML += `<line class="grid-line" x1="${padLeft}" y1="${yVal}" x2="${w - padRight}" y2="${yVal}"/>`;
      }
    }

    // 6 vertical gridlines with non-colliding formatted time ticks
    for (let i = 0; i <= 5; i++) {
      const xVal = padLeft + (plotW / 5) * i;
      const tAt = new Date(minT + (rangeT / 5) * i);
      if (this.gridG) {
        this.gridG.innerHTML += `<line class="grid-line" x1="${xVal}" y1="${padTop}" x2="${xVal}" y2="${bottomY}"/>`;
      }

      let tLabel = tAt.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" });
      if (rangeT > 86400000 * 2) {
        tLabel = `${tAt.getMonth() + 1}/${tAt.getDate()} ${tAt.getHours()}:00`;
      }
      if (this.axesG) {
        this.axesG.innerHTML += `<text class="axis-label" x="${xVal}" y="${bottomY + 18}" text-anchor="middle">${tLabel}</text>`;
      }
    }

    // Render Clean, Non-Overlapping Y-Axis Ticks for Active Channel
    const activeCfg = this.seriesConfig.find((c) => c.key === this.activeChannel) || this.seriesConfig[0];
    if (this.axesG && activeCfg) {
      for (let i = 0; i <= 4; i++) {
        const yVal = padTop + (plotH / 4) * i;
        const tickNum = activeCfg.max - ((activeCfg.max - activeCfg.min) / 4) * i;
        const formattedTick = Math.abs(tickNum) >= 1000 ? Math.round(tickNum).toLocaleString() : tickNum.toFixed(1);
        this.axesG.innerHTML += `<text class="axis-label y-axis-label" x="${padLeft - 10}" y="${yVal + 4}" text-anchor="end">${formattedTick} ${activeCfg.unit}</text>`;
      }
    }

    // Render each active metric series
    this.seriesConfig.forEach((cfg) => {
      const lineEl = document.getElementById(cfg.lineId);
      const areaEl = document.getElementById(cfg.areaId);

      if (!lineEl || !areaEl) return;
      if (!this.visibleSeries[cfg.key]) {
        lineEl.setAttribute("d", "");
        areaEl.setAttribute("d", "");
        return;
      }

      const rawPoints = [];
      for (let i = 0; i < this.dataset.length; i++) {
        const p = this.dataset[i];
        let val = p[cfg.key];
        if (typeof val !== "number" || isNaN(val)) {
          val = cfg.min;
        }
        const normY = Math.max(0, Math.min(1, (val - cfg.min) / (cfg.max - cfg.min)));
        const px = padLeft + ((p.epoch_ms - minT) / rangeT) * plotW;
        const py = bottomY - normY * plotH;
        if (!isNaN(px) && !isNaN(py)) {
          rawPoints.push({ x: px, y: py, rawVal: val, point: p });
        }
      }

      if (rawPoints.length === 0) return;

      // 1. Pixel-density binning eliminates high-frequency vertical barcode comb
      const binned = this.smoothAndBinPoints(rawPoints, 2.0);

      // 2. LTTB downsampling for performance bounded to 500 visual points
      const downsampled = this.lttbDownsample(binned, 500);

      // 3. Monotonic spline construction (zero retrograde loops)
      lineEl.setAttribute("d", this.buildPath(downsampled, false));
      areaEl.setAttribute("d", this.buildPath(downsampled, true, bottomY));
    });

    // Render Synchronized Multi-Track Sparkline Rails
    this.renderSparklines(minT, rangeT);

    // Render Mini-Map Overview Brush
    if (this.miniPath && this.dataset.length > 0) {
      const miniPts = [];
      for (let i = 0; i < this.dataset.length; i++) {
        const p = this.dataset[i];
        const val = typeof p.power_mw === "number" ? p.power_mw : 0;
        const ny = Math.max(0, Math.min(1, (val + 35000) / 75000));
        const mx = ((p.epoch_ms - minT) / rangeT) * 1000;
        const my = 34 - ny * 30;
        if (!isNaN(mx) && !isNaN(my)) {
          miniPts.push({ x: mx, y: my, rawVal: val, point: p });
        }
      }
      if (miniPts.length > 0) {
        const binnedMini = this.smoothAndBinPoints(miniPts, 3.0);
        this.miniPath.setAttribute("d", this.buildPath(this.lttbDownsample(binnedMini, 250), false));
      }
    }
  }

  renderSparklines(minT, rangeT) {
    const rails = [
      { id: "mini-spark-power", key: "power_mw", min: -35000, max: 40000 },
      { id: "mini-spark-voltage", key: "voltage_mv", min: 9000, max: 13500 },
      { id: "mini-spark-soc", key: "soc_pct", min: 0, max: 100 }
    ];

    rails.forEach((rail) => {
      const el = document.getElementById(rail.id);
      if (!el) return;
      const pts = [];
      for (let i = 0; i < this.dataset.length; i++) {
        const p = this.dataset[i];
        const val = typeof p[rail.key] === "number" ? p[rail.key] : rail.min;
        const ny = Math.max(0, Math.min(1, (val - rail.min) / (rail.max - rail.min)));
        const mx = ((p.epoch_ms - minT) / rangeT) * 300;
        const my = 32 - ny * 28;
        if (!isNaN(mx) && !isNaN(my)) {
          pts.push({ x: mx, y: my, rawVal: val, point: p });
        }
      }
      if (pts.length > 0) {
        const binned = this.smoothAndBinPoints(pts, 1.5);
        el.setAttribute("d", this.buildPath(this.lttbDownsample(binned, 120), false, 32));
      }
    });
  }

  handleMouseMove(e) {
    if (!this.dataset || this.dataset.length === 0 || !this.chartBox || !this.scrubLine || !this.tooltip) return;
    const rect = this.chartBox.getBoundingClientRect();
    const relX = (e.clientX - rect.left) / rect.width;
    const svgX = relX * 1000;

    const padLeft = 72;
    const padRight = 30;
    if (svgX < padLeft || svgX > 1000 - padRight) {
      this.handleMouseLeave();
      return;
    }

    const minT = this.dataset[0].epoch_ms;
    const maxT = this.dataset[this.dataset.length - 1].epoch_ms;
    const targetT = minT + ((svgX - padLeft) / (1000 - padLeft - padRight)) * (maxT - minT);

    // Binary search for nearest point
    let low = 0, high = this.dataset.length - 1;
    while (low < high) {
      const mid = Math.floor((low + high) / 2);
      if (this.dataset[mid].epoch_ms < targetT) low = mid + 1;
      else high = mid;
    }
    const pt = this.dataset[low];
    if (!pt) return;

    this.scrubLine.setAttribute("x1", svgX.toFixed(1));
    this.scrubLine.setAttribute("x2", svgX.toFixed(1));
    this.scrubLine.classList.remove("is-hidden");

    // Update Tooltip Card
    const dObj = new Date(pt.epoch_ms);
    const timeEl = document.getElementById("tt-time");
    if (timeEl) timeEl.textContent = `${dObj.toISOString().replace("T", " ").slice(0, 19)} UTC`;

    this.setTooltipRow("tt-val-power", pt.power_mw, "mW");
    this.setTooltipRow("tt-val-voltage", pt.voltage_mv, "mV");
    this.setTooltipRow("tt-val-soc", pt.soc_pct, "%");
    this.setTooltipRow("tt-val-temp", pt.temperature_c, "deg C");
    this.setTooltipRow("tt-val-health", pt.virtual_health_pct, "%");

    this.tooltip.classList.remove("is-hidden");
    if (relX > 0.65) {
      this.tooltip.classList.add("tooltip-flip-left");
    } else {
      this.tooltip.classList.remove("tooltip-flip-left");
    }

    // Position indicator dots on curves
    const padTop = 25;
    const bottomY = 288;
    const plotH = bottomY - padTop;
    this.seriesConfig.forEach((c) => {
      const dot = document.getElementById(c.dotId);
      if (!dot) return;
      if (!this.visibleSeries[c.key]) {
        dot.classList.add("is-hidden");
        return;
      }
      const val = typeof pt[c.key] === "number" ? pt[c.key] : c.min;
      const ny = Math.max(0, Math.min(1, (val - c.min) / (c.max - c.min)));
      dot.setAttribute("cx", svgX.toFixed(1));
      dot.setAttribute("cy", (bottomY - ny * plotH).toFixed(1));
      dot.classList.remove("is-hidden");
    });
  }

  setTooltipRow(id, val, unit) {
    const el = document.getElementById(id);
    if (el) {
      el.textContent = (typeof val === "number" && !isNaN(val)) ? `${val} ${unit}` : `-- ${unit}`;
    }
  }

  handleMouseLeave() {
    if (this.scrubLine) this.scrubLine.classList.add("is-hidden");
    if (this.tooltip) this.tooltip.classList.add("is-hidden");
    this.seriesConfig.forEach((c) => {
      const dot = document.getElementById(c.dotId);
      if (dot) dot.classList.add("is-hidden");
    });
  }
}
