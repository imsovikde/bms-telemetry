import { format30 } from "../web/js/state.js";
import { BmsVectorChart } from "../web/js/chart.js";
import assert from "node:assert";

// Test 1: format30 with exact 30 decimal digits
const raw30 = "12.345678901234567890123456789012";
const formatted = format30(raw30);
assert(formatted.includes('<span class="high">12.345678</span>'), "High segment must match first 6 decimals");
assert(formatted.includes('<span>9012345678901234</span>'), "Middle segment must match next 16 decimals");
assert(formatted.includes('<span class="micro">56789012</span>'), "Micro segment must match remaining 8 decimals");
console.log("format30 verified: strictly preserves all 30 decimals without floating point cast.");

// Test 2: LTTB downsampler algorithm
const chart = Object.create(BmsVectorChart.prototype);
chart.useSmoothCurves = true;

const rawPoints = [];
for (let i = 0; i < 2000; i++) {
  rawPoints.push({ x: i * 0.5, y: 150 + Math.sin(i * 0.1) * 50 });
}

const sampled = chart.lttbDownsample(rawPoints, 500);
assert.strictEqual(sampled.length, 500, "LTTB must downsample exactly to threshold");
assert.strictEqual(sampled[0].x, rawPoints[0].x, "LTTB must preserve first point");
assert.strictEqual(sampled[sampled.length - 1].x, rawPoints[rawPoints.length - 1].x, "LTTB must preserve last point");
console.log("LTTB downsampling verified: 2000 points downsampled to 500 points preserving endpoints.");

// Test 3: Safe SVG path generation with zero NaNs
const pathD = chart.buildPath(sampled, true, 288);
assert(!pathD.includes("NaN"), "Path must contain zero NaN values");
assert(pathD.startsWith("M "), "Path must start with M move command");
assert(pathD.includes(" C "), "Smooth path must contain cubic Bezier C commands");
assert(pathD.endsWith(" Z"), "Closed path must end with Z close command");
console.log("SVG vector path builder verified: generated smooth cubic Bezier path with zero NaNs.");

// Test 4: Mathematical Monotonicity Invariant (Zero Retrograde Loops: prevX <= cp1x <= cp2x <= x)
// Regex match all "C cp1x cp1y, cp2x cp2y, x y" commands
const bezierRegex = /C\s+([\d.-]+)\s+([\d.-]+),\s+([\d.-]+)\s+([\d.-]+),\s+([\d.-]+)\s+([\d.-]+)/g;
let match;
let prevX = sampled[0].x;
let curveCount = 0;
while ((match = bezierRegex.exec(pathD)) !== null) {
  const cp1x = parseFloat(match[1]);
  const cp2x = parseFloat(match[3]);
  const x = parseFloat(match[5]);

  assert(cp1x >= prevX - 0.05, `cp1x (${cp1x}) must be >= prevX (${prevX})`);
  assert(cp2x >= cp1x - 0.05, `cp2x (${cp2x}) must be >= cp1x (${cp1x})`);
  assert(x >= cp2x - 0.05, `x (${x}) must be >= cp2x (${cp2x})`);

  prevX = x;
  curveCount++;
}
assert(curveCount > 100, "Must have verified over 100 curve segments");
console.log(`Monotonic cubic spline verified: ${curveCount} Bezier segments strictly satisfy prevX <= cp1x <= cp2x <= x with ZERO retrograde loops.`);

// Test 5: Extreme Non-Uniform Spacing Stress Test (Triggers retrograde loops in unconstrained Bezier)
const irregularPoints = [
  { x: 10, y: 100 },
  { x: 500, y: 50 },
  { x: 501, y: 200 }, // tiny delta (1px) following large gap (490px)
  { x: 502, y: 150 },
  { x: 900, y: 80 }
];
const irregularPath = chart.buildPath(irregularPoints, false);
let irregPrevX = irregularPoints[0].x;
let irregMatch;
while ((irregMatch = bezierRegex.exec(irregularPath)) !== null) {
  const cp1x = parseFloat(irregMatch[1]);
  const cp2x = parseFloat(irregMatch[3]);
  const x = parseFloat(irregMatch[5]);

  assert(cp1x >= irregPrevX - 0.05, `Stress test: cp1x (${cp1x}) >= prevX (${irregPrevX})`);
  assert(cp2x >= cp1x - 0.05, `Stress test: cp2x (${cp2x}) >= cp1x (${cp1x})`);
  assert(x >= cp2x - 0.05, `Stress test: x (${x}) >= cp2x (${cp2x})`);
  irregPrevX = x;
}
console.log("Non-uniform spacing stress test passed: zero overshoot loops on extreme dt differentials.");

// Test 6: Pixel-Density Binning Noise Reduction (Barcode Elimination)
const noisyJitterPoints = [];
for (let i = 0; i < 150; i++) {
  // 150 points oscillating inside a 2px horizontal band [100.0, 101.9]
  noisyJitterPoints.push({
    x: 100 + (i % 20) * 0.09,
    y: 50 + (i % 2 === 0 ? 80 : -80),
    rawVal: 25000 * (i % 2 === 0 ? 1 : -1),
    point: { epoch_ms: 1000 + i * 250 }
  });
}
const binned = chart.smoothAndBinPoints(noisyJitterPoints, 2.0);
assert(binned.length <= 2, `150 jitter points in 2px must be aggregated into <= 2 points (got ${binned.length})`);
assert(!isNaN(binned[0].x) && !isNaN(binned[0].y), "Binned points must have valid numeric coordinates");
console.log(`Pixel-density binning verified: 150 power-jitter points reduced from 150 to ${binned.length}, eliminating barcode comb.`);

