/*
 * SOL: "compare my run" (TODO A21). Plain JS, no Pyodide dependency: Python
 * hands over a JSON object of {field: value} and this file asks the site's
 * public aggregate-stats backend (app/stats.py, GET /stats/games/sol/percentile)
 * where each value ranks, then writes plain text into #compare-run-results.
 *
 * Only ever runs on an explicit button click (never at page load), so a
 * backend that isn't deployed yet costs nothing until the player asks, and
 * every failure path (network error, 404, suppressed bucket) degrades to
 * one calm sentence rather than an error.
 */
(function () {
  "use strict";

  const API_BASE = "https://noyvjgames.fastapicloud.dev";
  const LABELS = {
    prestige_level: "Prestige level",
    total_ticks: "Time played",
    total_manual_clicks: "Manual clicks",
    lifetime_generators_built: "Generators built",
    lifetime_recyclers_built: "Recyclers built",
    lifetime_trade_routes_built: "Trade routes built",
    lifetime_sky_cities_built: "Sky cities built",
    governor_purchase_count: "Governor purchases",
  };

  function setText(text) {
    const el = document.getElementById("compare-run-results");
    if (el) {
      el.textContent = text;
    }
    return el;
  }

  async function fetchOne(field, value) {
    const url = API_BASE + "/stats/games/sol/percentile?field=" + encodeURIComponent(field) +
      "&value=" + encodeURIComponent(value);
    const response = await fetch(url);
    if (!response.ok) {
      throw new Error("status " + response.status);
    }
    return response.json();
  }

  async function run(valuesJson) {
    let values;
    try {
      values = JSON.parse(valuesJson);
    } catch (e) {
      setText("Comparison isn't available right now.");
      return;
    }
    setText("Comparing...");
    const lines = [];
    let sawSuppressed = false;
    try {
      for (const field of Object.keys(values)) {
        const result = await fetchOne(field, values[field]);
        if (result.suppressed || result.percentile === null || result.percentile === undefined) {
          sawSuppressed = true;
          continue;
        }
        const pct = Math.round(result.percentile);
        lines.push((LABELS[field] || field) + ": higher than " + pct + "% of players");
      }
    } catch (e) {
      setText("Comparison isn't available yet. Check back once more players have shared runs.");
      return;
    }
    if (!lines.length) {
      setText(sawSuppressed
        ? "Not enough players yet to compare against without identifying anyone. Check back later."
        : "Comparison isn't available yet.");
      return;
    }
    setText(lines.join("\n"));
  }

  window.SolCompare = { run: run };
})();
