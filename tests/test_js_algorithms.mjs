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
const pathD = chart.buildPath(sampled, true, 290);
assert(!pathD.includes("NaN"), "Path must contain zero NaN values");
assert(pathD.startsWith("M "), "Path must start with M move command");
assert(pathD.includes(" C "), "Smooth path must contain cubic Bezier C commands");
assert(pathD.endsWith(" Z"), "Closed path must end with Z close command");
console.log("SVG vector path builder verified: generated smooth cubic Bezier path with zero NaNs.");
