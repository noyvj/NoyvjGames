// K27: keyboard shortcuts + the "?" cheat-sheet. Plain DOM, no Python.
document.addEventListener("keydown", function (event) {
  const t = event.target;
  if (t && (t.tagName === "INPUT" || t.tagName === "TEXTAREA" || t.tagName === "SELECT" || t.isContentEditable)) return;
  if (event.ctrlKey || event.metaKey || event.altKey) return;
  const panel = document.getElementById("shortcuts-panel");
  if (event.key === "Escape") { panel.hidden = true; return; }
  // K-30: the keys come from Settings (settings.js), defaults otherwise.
  const keys = window.ContinuumKeys;
  if (keys && keys.isCapturing && keys.isCapturing()) return;
  const defaults = { "?": "help", "p": "pause", "1": "camera-overview", "2": "camera-closeup", "3": "camera-aerial", "4": "camera-isometric", "s": "screensaver" };
  const action = keys ? keys.actionFor(event.key) : defaults[String(event.key).toLowerCase()];
  if (action === "help") { panel.hidden = !panel.hidden; return; }
  if (action === "pause") {
    // U1: pause / resume (resume at 1x).
    const paused = document.getElementById("speed-pause-button").getAttribute("aria-pressed") === "true";
    document.getElementById(paused ? "speed-1x-button" : "speed-pause-button").click();
    return;
  }
  if (action === "screensaver" && window.ContinuumCamera && window.ContinuumCamera.screensaver) { window.ContinuumCamera.screensaver(); return; }
  if (action && action.indexOf("camera-") === 0 && window.ContinuumCamera) window.ContinuumCamera.preset(action.slice(7));
});
