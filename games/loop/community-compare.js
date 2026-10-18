// Community comparison hook: game.py's render() calls window.loopCompare(lifetimeCircularFraction) when it exists.
// H5: optional cross-player comparison for lifetime circular share,
// against the shared aggregate-stats endpoint (planning/TODO.md Z1).
// Same shape as Grid's own C15 window.gridCompare -- fails soft on any
// error/suppression, leaving game.py's static "isn't available yet"
// fallback text in place.
(function () {
  const API_BASE = "https://noyvjgames.fastapicloud.dev";
  const cache = new Map();
  function show(text) {
    const el = document.getElementById("community-comparison-display");
    if (el && text) el.textContent = text;
  }
  window.loopCompare = function (lifetimeCircularFraction) {
    const key = Math.round(lifetimeCircularFraction * 1000);
    const hit = cache.get(key);
    if (hit && Date.now() - hit.at < 60000) { show(hit.text); return; }
    if (hit) return; // in flight
    cache.set(key, { at: Date.now(), text: null });
    fetch(`${API_BASE}/stats/games/loop/percentile?field=lifetime_circular_fraction&value=${key / 1000}`)
      .then((r) => (r.ok ? r.json() : null))
      .then((d) => {
        let text = null;
        if (d && !d.suppressed && typeof d.percentile === "number") {
          const rounded = Math.round(d.percentile);
          text = `Compared with ${d.count} other saved chains: your lifetime circular share beats ${rounded}% of them.`;
        }
        cache.set(key, { at: Date.now(), text });
        show(text);
      })
      .catch(() => { cache.set(key, { at: Date.now(), text: null }); });
  };
})();
