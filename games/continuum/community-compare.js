// K3: plain fetch + text render (no game-state logic). The endpoint may
// not be reachable, so every failure ends in one "not available" line,
// and nothing is fetched until the button is pressed.
(function () {
  const FIELDS = [
    ["current_state.city.season", "Seasons played"],
    ["current_state.city.population", "Population"],
    ["current_state.city.land_health", "Land health"],
    ["current_state.city.pollution", "Pollution"],
    ["current_state.city.sprawl", "Sprawl"],
    ["current_state.city.fed_fraction", "Fed fraction"],
  ];
  const button = document.getElementById("community-city-button");
  const result = document.getElementById("community-city-result");
  if (!button) return;
  function mineFor(path) {
    try {
      const proxy = window.pyodide.globals.get("get_state")();
      const data = proxy.toJs({ dict_converter: Object.fromEntries });
      if (proxy.destroy) proxy.destroy();
      let v = data;
      for (const key of path.split(".")) v = v == null ? undefined : v[key];
      return typeof v === "number" && isFinite(v) ? v : null;
    } catch (err) { return null; }
  }
  button.addEventListener("click", async function () {
    const API = "https://noyvjgames.fastapicloud.dev";
    button.disabled = true;
    result.textContent = "Loading...";
    try {
      const res = await fetch(API + "/stats/games/continuum");
      if (!res.ok) throw new Error("status " + res.status);
      const summary = await res.json();
      if (summary.suppressed) {
        result.textContent = "Not enough players yet for an anonymous comparison (needs " + summary.min_bucket + "+).";
        return;
      }
      const rows = [];
      for (const [field, label] of FIELDS) {
        const info = summary.fields && summary.fields[field];
        const mine = mineFor(field);
        if (!info || mine === null || typeof info.mean !== "number") continue;
        let pct = "";
        try {
          const p = await (await fetch(API + "/stats/games/continuum/percentile?field=" + field + "&value=" + encodeURIComponent(mine))).json();
          if (!p.suppressed && typeof p.percentile === "number") pct = " · " + Math.round(p.percentile) + "th percentile";
        } catch (err) { /* the average still shows */ }
        rows.push(label + ": you " + mine.toFixed(2) + " · community average " + info.mean.toFixed(2) + pct);
      }
      result.textContent = rows.length ? rows.join("\n") : "Not enough players yet for an anonymous comparison.";
    } catch (err) {
      result.textContent = "Community comparison isn't available yet. Check back later.";
    } finally {
      button.disabled = false;
    }
  });
})();
