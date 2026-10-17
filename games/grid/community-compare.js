// The gridCompare hook the Run Summary panel (game.py, summary_panel_html) calls. Loaded after tutorial-steps.js and before boot.js, as in the old inline script.
// C15: optional cross-player comparison for the Run Summary panel,
// against the shared aggregate-stats endpoint (planning/TODO.md Z1).
// Fails soft: any error/suppression leaves game.py's fallback text.
(function () {
  const API_BASE = "https://noyvjgames.fastapicloud.dev";
  const cache = new Map();
  function show(text) {
    const el = document.getElementById("summary-compare");
    if (el && text) el.textContent = text;
  }
  window.gridCompare = function (emissions) {
    const key = Math.round(emissions);
    const hit = cache.get(key);
    if (hit && Date.now() - hit.at < 60000) { show(hit.text); return; }
    if (hit) return; // in flight
    cache.set(key, { at: Date.now(), text: null });
    fetch(`${API_BASE}/stats/games/grid/percentile?field=emissions&value=${key}`)
      .then((r) => (r.ok ? r.json() : null))
      .then((d) => {
        let text = null;
        if (d && !d.suppressed && typeof d.percentile === "number") {
          const lower = Math.round(100 - d.percentile);
          text = `Compared with ${d.count} other saved grids: your emissions are lower than ${lower}% of them.`;
        }
        cache.set(key, { at: Date.now(), text });
        show(text);
      })
      .catch(() => { cache.set(key, { at: Date.now(), text: null }); });
  };
})();
