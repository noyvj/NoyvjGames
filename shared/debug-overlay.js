/*
 * Developer overlay (TODO Z-24), shown only when the page address carries ?debug=1. Without that
 * flag this file does nothing at all: no element, no listener, no timer, no patched function.
 *
 * A small corner box (top right, click-through, hidden from screen readers and from print) shows:
 *   fps          frames per second over the last second (requestAnimationFrame)
 *   state        size in bytes of the game's get_state() as JSON, re-measured every 5 seconds
 *   last save    length in bytes of the last body this page sent to a /saves endpoint, and when
 *   heap         JS heap in use, where the browser reports it (Chromium)
 *   lite         whether lite mode is on (shared/lite-mode.js)
 *   errors       how many the error boundary caught (shared/error-boundary.js)
 *   boot         the Pyodide boot milestones from shared/perf-mark.js
 * Nothing is stored or sent. The one thing it patches is window.fetch, only to read the length of
 * save request bodies (it still calls the original fetch unchanged).
 */
(function () {
  "use strict";
  const params = new URLSearchParams(location.search);
  window.NoyvjDebug = { active: params.get("debug") === "1" };
  if (!window.NoyvjDebug.active) return;

  const encoder = typeof TextEncoder === "function" ? new TextEncoder() : null;
  const state = { fps: 0, stateBytes: null, saveBytes: null, saveAt: 0, saveMethod: "" };

  function byteLength(text) { return encoder ? encoder.encode(text).length : text.length; }

  // ---- last save payload length ----
  const realFetch = window.fetch;
  if (typeof realFetch === "function") {
    window.fetch = function (input, init) {
      try {
        const url = typeof input === "string" ? input : (input && input.url) || "";
        const method = String((init && init.method) || (input && input.method) || "GET").toUpperCase();
        if (/\/saves(\/|$|\?)|\/slots\//.test(url) && (method === "POST" || method === "PUT")) {
          const body = init && init.body;
          if (typeof body === "string") {
            state.saveBytes = byteLength(body);
            state.saveAt = Date.now();
            state.saveMethod = method;
          }
        }
      } catch (e) { /* measuring must never break a request */ }
      return realFetch.apply(this, arguments);
    };
  }

  // ---- state size ----
  function measureState() {
    const py = window.pyodide;
    if (!py || !py.globals) return;
    let fn = null, proxy = null;
    try {
      fn = py.globals.get("get_state");
      if (!fn) return;
      proxy = fn();
      const plain = proxy && typeof proxy.toJs === "function"
        ? proxy.toJs({ dict_converter: Object.fromEntries, create_pyproxies: false })
        : proxy;
      state.stateBytes = byteLength(JSON.stringify(plain));
    } catch (e) {
      state.stateBytes = null;
    } finally {
      try { if (proxy && typeof proxy.destroy === "function") proxy.destroy(); } catch (e) { /* already gone */ }
      try { if (fn && typeof fn.destroy === "function") fn.destroy(); } catch (e) { /* already gone */ }
    }
  }

  // ---- fps ----
  let frames = 0;
  let windowStart = performance.now();
  function frame(t) {
    frames += 1;
    if (t - windowStart >= 1000) {
      state.fps = Math.round((frames * 1000) / (t - windowStart));
      frames = 0;
      windowStart = t;
      render();
    }
    requestAnimationFrame(frame);
  }

  // ---- the box ----
  let box = null;
  function fmtBytes(n) { return n === null ? "n/a" : `${n} B${n >= 1024 ? ` (${(n / 1024).toFixed(1)} KB)` : ""}`; }

  function lines() {
    const out = [`fps        ${state.fps}`, `state      ${fmtBytes(state.stateBytes)}`];
    const ago = state.saveAt ? `, ${Math.round((Date.now() - state.saveAt) / 1000)}s ago (${state.saveMethod})` : "";
    out.push(`last save  ${state.saveBytes === null ? "none yet" : fmtBytes(state.saveBytes) + ago}`);
    if (performance.memory && performance.memory.usedJSHeapSize) out.push(`heap       ${(performance.memory.usedJSHeapSize / 1048576).toFixed(1)} MB`);
    out.push(`lite       ${window.NoyvjLite ? (window.NoyvjLite.on() ? "on" : "off") : "n/a"}`);
    out.push(`errors     ${window.NoyvjErrors ? window.NoyvjErrors.count() : "n/a"}`);
    const perf = window.NoyvjPerf ? window.NoyvjPerf.summary() : null;
    if (perf) {
      Object.keys(perf.marks).forEach((k) => out.push(`${k.padEnd(18)} ${perf.marks[k]}ms`));
    }
    return out;
  }

  function render() {
    if (!box) return;
    box.textContent = lines().join("\n");
  }

  function mount() {
    box = document.createElement("div");
    box.id = "noyvj-debug-overlay";
    box.setAttribute("aria-hidden", "true");
    box.style.cssText = [
      "position:fixed", "top:6px", "right:6px", "z-index:2147483002", "pointer-events:none", "white-space:pre",
      "padding:6px 8px", "border-radius:6px", "background:rgba(0,0,0,.78)", "color:#9fe9a8",
      "font:11px/1.35 ui-monospace,Menlo,Consolas,monospace", "max-width:60vw", "overflow:hidden",
    ].join(";");
    document.body.appendChild(box);
    const style = document.createElement("style");
    style.textContent = "@media print { #noyvj-debug-overlay { display: none !important; } }";
    document.head.appendChild(style);
    measureState();
    render();
    requestAnimationFrame(frame);
    setInterval(() => { measureState(); render(); }, 5000);
  }

  window.NoyvjDebug.measureState = () => { measureState(); render(); return state.stateBytes; };
  window.NoyvjDebug.snapshot = () => Object.assign({}, state);

  if (document.body) mount();
  else document.addEventListener("DOMContentLoaded", mount, { once: true });
})();
