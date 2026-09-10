/**
 * BMS Reactive State Store & Precision Formatters
 * Strict 30-decimal string preservation without IEEE 754 float casting
 */

export const store = {
  telemetry: null,
  state: null,
  historyPoints: [],
  listeners: new Set(),

  subscribe(listener) {
    this.listeners.add(listener);
    return () => this.listeners.delete(listener);
  },

  notify(event, data) {
    this.listeners.forEach(fn => fn(event, data));
  },

  setTelemetryAndState(telem, st) {
    this.telemetry = telem;
    this.state = st;
    this.notify('telemetry_update', { telemetry: telem, state: st });
  },

  setHistory(points) {
    this.historyPoints = points;
    this.notify('history_update', points);
  }
};

/**
 * High-precision 30-decimal string formatter
 * Avoids JavaScript 64-bit float precision collapse (>15-17 digits)
 */
export function format30(str) {
  if (!str) return "--";
  const s = String(str);
  const parts = s.split(".");
  if (parts.length < 2) return s;
  const intPart = parts[0];
  const dec = parts[1];
  return `<span class="high">${intPart}.${dec.slice(0, 6)}</span><span>${dec.slice(6, 22)}</span><span class="micro">${dec.slice(22)}</span>`;
}

/**
 * Toast Notification Dispatcher
 */
export function showToast(msg, isError = false) {
  let toast = document.getElementById("toast-box");
  if (!toast) {
    toast = document.createElement("div");
    toast.id = "toast-box";
    toast.className = "toast-notification";
    document.body.appendChild(toast);
  }
  toast.textContent = msg;
  toast.className = "toast-notification toast-show " + (isError ? "toast-error" : "toast-success");
  setTimeout(() => {
    toast.className = "toast-notification";
  }, 4000);
}
