// G11 (planning/TODO.md, needs Z1): optional cross-player comparison of
// "average acceleration factor" for the Community Comparison panel,
// against the shared aggregate-stats endpoint (planning/TODO.md Z1).
// Follows Grid's C15 architecture exactly (games/grid/index.html) --
// game.py calls window.thawCompare(...) through an optional-hook guard
// (getattr(window, "thawCompare", None)) so it's a safe no-op in the
// pytest fake-DOM harness; this script owns the real fetch() and fails
// soft on any error/suppression, leaving game.py's own fallback text
// (COMMUNITY_COMPARE_FALLBACK) in place.
//
// "region.average_acceleration_factor" is registered in app/stats.py's
// field whitelist for "thaw" (added alongside this feature) -- until
// that's deployed to production, or while there aren't yet MIN_BUCKET
// saves to compare against, the percentile fetch below 404s/suppresses
// and this falls through to the fallback text, exactly like any other
// soft-fail case already handled here.
(function () {
  const API_BASE = "https://noyvjgames.fastapicloud.dev";
  const cache = new Map();
  function show(text) {
    const el = document.getElementById("community-compare-display");
    if (el && text) el.textContent = text;
  }
  window.thawCompare = function (accelerationFactor) {
    const key = Math.round(accelerationFactor * 100) / 100;
    const hit = cache.get(key);
    if (hit && Date.now() - hit.at < 60000) { show(hit.text); return; }
    if (hit) return; // in flight
    cache.set(key, { at: Date.now(), text: null });
    fetch(`${API_BASE}/stats/games/thaw/percentile?field=region.average_acceleration_factor&value=${key}`)
      .then((r) => (r.ok ? r.json() : null))
      .then((d) => {
        let text = null;
        if (d && !d.suppressed && typeof d.percentile === "number") {
          // Lower acceleration is better (1.0x = no runaway feedback
          // yet), so "lower than X% of them" reads the same
          // direction Grid's own emissions percentile does.
          const lower = Math.round(100 - d.percentile);
          if (lower >= 50) {
            text = `Out of ${d.count} other saved regions, your warming has accelerated less than ${lower}% of them — real proof that intervention slows the slope, and most players are managing to slow it at least some too.`;
          } else {
            const higher = 100 - lower;
            text = `Out of ${d.count} other saved regions, ${higher}% have slowed their warming even further than yours — a sign of how much intervention can still do here, not that it isn't working: every bit of preserve/monitor investment already measurably flattens your own slope versus doing nothing.`;
          }
        }
        cache.set(key, { at: Date.now(), text });
        show(text);
        // G-30: keep this result in the short "last five comparisons" list (Python owns the list).
        if (d && !d.suppressed && typeof d.percentile === "number" && window.pyodide) {
          try {
            const keep = window.pyodide.globals.get("record_compare_result");
            if (keep) { keep(Math.round(100 - d.percentile), d.count); keep.destroy && keep.destroy(); }
          } catch (e) { /* the list is a nicety; never break the comparison */ }
        }
      })
      .catch(() => { cache.set(key, { at: Date.now(), text: null }); });
  };
})();
