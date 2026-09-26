/*
 * Shared "community index" line (planning/TODO.md E9, I17, D9): a read-only
 * sentence built from the cross-game aggregate stats the backend already
 * publishes at /stats/games/<game> (app/stats.py; only whitelisted numeric
 * save fields, never fewer than MIN_BUCKET saves, never any individual save).
 *
 * One script tag per line, after the element exists:
 *   <p id="community-index" class="comparison-message" hidden></p>
 *   <script src="../../shared/community-index.js" data-game-id="drift"
 *     data-target="#community-index"
 *     data-template="Average regional wellbeing across {count} players: {wellbeing_score:mean}."></script>
 *
 * Template placeholders: {count} (that game's save count), {<field>:mean} and
 * {<field>:p10|p25|p50|p75|p90} using the field's summary. A "[...]" group is
 * kept only if every placeholder inside it has data, so a partly-suppressed
 * game still shows the parts that can be shown. If nothing usable is left the
 * element stays hidden. Every failure (network, shape, missing element) fails
 * soft. The result is written with textContent.
 */
(function () {
  const script = document.currentScript;
  if (!script) return;
  const game = script.dataset.gameId;
  const template = script.dataset.template;
  const target = document.querySelector(script.dataset.target || "#community-index");
  if (!game || !template || !target) return;
  const API_BASE = "https://noyvjgames.fastapicloud.dev";

  function formatNumber(value) {
    if (typeof value !== "number" || !Number.isFinite(value)) return null;
    return String(Math.round(value * 10) / 10);
  }

  function lookup(summary, name) {
    if (name === "count") return formatNumber(summary.save_count);
    const [field, stat] = name.split(":");
    const entry = summary.fields && summary.fields[field];
    if (!entry || !stat) return null;
    if (stat === "mean") return formatNumber(entry.mean);
    return entry.percentiles ? formatNumber(entry.percentiles[stat]) : null;
  }

  // Fills one piece of the template; null if any placeholder has no data.
  function fill(piece, summary) {
    let missing = false;
    const text = piece.replace(/\{([^}]+)\}/g, (_, name) => {
      const value = lookup(summary, name);
      if (value === null) { missing = true; return ""; }
      return value;
    });
    return missing ? null : text;
  }

  function build(summary) {
    if (!summary || summary.suppressed) return "";
    let out = "";
    let ok = true;
    const parts = template.split(/(\[[^\]]*\])/);
    for (const part of parts) {
      if (part.startsWith("[") && part.endsWith("]")) {
        const filled = fill(part.slice(1, -1), summary);
        if (filled !== null) out += filled;
      } else {
        const filled = fill(part, summary);
        if (filled === null) { ok = false; break; }
        out += filled;
      }
    }
    return ok ? out.replace(/\s+/g, " ").trim() : "";
  }

  fetch(`${API_BASE}/stats/games/${encodeURIComponent(game)}`)
    .then((r) => (r.ok ? r.json() : null))
    .then((summary) => {
      const text = build(summary);
      if (text) {
        target.textContent = text;
        target.hidden = false;
      }
    })
    .catch(() => { /* leave the line hidden */ });
})();
