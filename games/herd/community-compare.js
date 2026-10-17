// F7 (planning/TODO.md, "farm cooperative" comparison): cross-player
// percentile against the shared aggregate-stats endpoint (Z1). Exact
// same optional-hook architecture as Grid's own C15 (the reference
// integration for this feature) -- game.py's _request_comparison()
// calls window.herdCompare() if it exists; this script is what defines
// it. Fails soft: any error, an unreachable backend, or a too-small
// sample (the endpoint's own `suppressed` flag) all leave the plain
// "isn't available yet" fallback text game.py already wrote into
// #report-card-compare -- never a raw error or JSON shown to the player.
//

(function () {
  const API_BASE = "https://noyvjgames.fastapicloud.dev";
  const cache = new Map();
  function show(text, title) {
    const el = document.getElementById("report-card-compare");
    if (el && text) {
      el.textContent = text;
      el.title = title || "";
    }
  }
  window.herdCompare = function (methane) {
    const key = Math.round(methane);
    const hit = cache.get(key);
    if (hit && Date.now() - hit.at < 60000) { show(hit.text, hit.title); return; }
    if (hit) return; // in flight
    cache.set(key, { at: Date.now(), text: null, title: "" });
    fetch(`${API_BASE}/stats/games/herd/percentile?field=methane&value=${key}`)
      .then((r) => (r.ok ? r.json() : null))
      .then((d) => {
        let text = null;
        let title = "";
        if (d && !d.suppressed && typeof d.percentile === "number") {
          const lower = Math.round(100 - d.percentile);
          // F10: a small trend arrow, cheap because it never asks the
          // backend for history -- the shared stats endpoint only ever
          // returns a live snapshot. Instead this browser remembers its
          // own last reading and compares against that. Shape-coded
          // (not color-only), same convention as Thaw's own
          // round-to-round trend arrows.
          let arrow = "";
          try {
            const prevRaw = localStorage.getItem("herd-community-lower-pct");
            if (prevRaw !== null) {
              const prev = parseInt(prevRaw, 10);
              if (!Number.isNaN(prev)) {
                if (lower > prev) { arrow = " ▲"; title = "Better than your last check."; }
                else if (lower < prev) { arrow = " ▼"; title = "Worse than your last check."; }
                else { arrow = " ▶"; title = "Same as your last check."; }
              }
            }
            localStorage.setItem("herd-community-lower-pct", String(lower));
          } catch (e) { /* localStorage unavailable -- no arrow, no crash */ }
          text = `Compared with ${d.count} other farms: your lifetime methane is lower than ${lower}%${arrow} of them.`;
        }
        cache.set(key, { at: Date.now(), text, title });
        show(text, title);
      })
      .catch(() => { cache.set(key, { at: Date.now(), text: null, title: "" }); });
  };
})();
