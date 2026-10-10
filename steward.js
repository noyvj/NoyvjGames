/*
 * Climate Steward (planning/TODO.md B-23): one portrait of how the signed-in player's eight climate worlds stand,
 * read from the most recent save of each game (GET /users/me/saves, the same list the hub already uses).
 *
 * Each game may carry an optional `summary` list in its save: [{label, value, unit, note?}]. This file validates it
 * (at most 4 items, label 1 to 40 characters, value a finite number, unit up to 12 characters, note up to 80) and
 * ignores anything malformed. Canopy has no summary list, so its numbers are read from fields it already saves.
 *
 * Read-only: nothing is sent anywhere except the one GET, every string reaches the page through textContent, and
 * there is no score, ranking or comparison with other players.
 */
(function () {
  "use strict";

  const API_BASE = "https://noyvjgames.fastapicloud.dev";
  const MAX_SHOWN = 3;
  const GAMES = [
    { slug: "canopy", name: "Canopy", theme: "forest value and community trust" },
    { slug: "grid", name: "Grid", theme: "clean power" },
    { slug: "tide", name: "Tide", theme: "the coastline" },
    { slug: "aftermath", name: "Aftermath", theme: "resilience" },
    { slug: "herd", name: "Herd", theme: "farm methane" },
    { slug: "thaw", name: "Thaw", theme: "permafrost warming" },
    { slug: "loop", name: "Loop", theme: "circular supply" },
    { slug: "drift", name: "Drift", theme: "newcomers and services" },
  ];

  function isNum(v) {
    return typeof v === "number" && Number.isFinite(v);
  }
  function isObj(v) {
    return v !== null && typeof v === "object" && !Array.isArray(v);
  }

  // One summary list from a save's data; [] if absent or entirely malformed. Bad items are dropped one by one.
  function sanitiseSummary(raw) {
    if (!Array.isArray(raw)) return [];
    const out = [];
    for (const item of raw.slice(0, 4)) {
      if (!isObj(item)) continue;
      const label = typeof item.label === "string" ? item.label.trim() : "";
      if (label.length < 1 || label.length > 40) continue;
      if (!isNum(item.value)) continue;
      const unit = item.unit === undefined || item.unit === null ? "" : item.unit;
      if (typeof unit !== "string" || unit.length > 12) continue;
      const clean = { label, value: item.value, unit };
      if (typeof item.note === "string" && item.note.trim() && item.note.length <= 80) clean.note = item.note.trim();
      out.push(clean);
    }
    return out;
  }

  // Canopy keeps these as plain fields in its save (no summary list).
  function canopySummary(data) {
    if (!isObj(data)) return [];
    const out = [];
    if (isNum(data.standing_value) && data.standing_value >= 0) {
      out.push({ label: "Standing forest value", value: data.standing_value, unit: "" });
    }
    if (isNum(data.community_relations) && data.community_relations >= 0 && data.community_relations <= 100) {
      out.push({ label: "Community relations", value: data.community_relations, unit: "of 100" });
    }
    if (isNum(data.total_replants) && data.total_replants >= 0) {
      out.push({ label: "Plots replanted", value: data.total_replants, unit: "" });
    }
    if (out.length < MAX_SHOWN && isNum(data.total_recoveries) && data.total_recoveries >= 0) {
      out.push({ label: "Plots recovered", value: data.total_recoveries, unit: "" });
    }
    return out;
  }

  // The summary shown for one game's save data: its own list if valid, else (Canopy only) the plain fields.
  function summaryFor(slug, data) {
    if (!isObj(data)) return [];
    const own = sanitiseSummary(data.summary);
    if (own.length) return own.slice(0, MAX_SHOWN);
    if (slug === "canopy") return canopySummary(data).slice(0, MAX_SHOWN);
    return [];
  }

  function saveTime(s) {
    return new Date(s.updated_at || s.created_at).getTime() || 0;
  }
  // Same rule as the hub's mostRecentSaveForGame: the newest save of that game wins.
  function mostRecent(saves, slug) {
    let best = null;
    saves.forEach((s) => {
      if (!isObj(s) || s.game_id !== slug) return;
      if (!best || saveTime(s) > saveTime(best)) best = s;
    });
    return best;
  }

  function formatValue(v) {
    return v.toLocaleString("en-US", { maximumFractionDigits: 1 });
  }
  // "5 of 6", "42%", "1.2°C", "1,234".
  function formatItem(item) {
    const unit = item.unit || "";
    const num = formatValue(item.value);
    if (!unit) return num;
    if (unit === "%" || unit.charAt(0) === "°") return num + unit;
    return num + " " + unit;
  }
  // 0..1 when the number is a fraction of a known total (then a small bar can sit beside the number), else null.
  function fraction(item) {
    const unit = item.unit || "";
    if (unit === "%") return Math.min(1, Math.max(0, item.value / 100));
    const m = /^of (\d+(?:\.\d+)?)$/.exec(unit);
    if (m && Number(m[1]) > 0) return Math.min(1, Math.max(0, item.value / Number(m[1])));
    return null;
  }

  function dateText(save) {
    const t = saveTime(save);
    if (!t) return "";
    const d = new Date(t);
    const pad = (n) => String(n).padStart(2, "0");
    return d.getFullYear() + "-" + pad(d.getMonth() + 1) + "-" + pad(d.getDate());
  }

  const api = { sanitiseSummary, canopySummary, summaryFor, mostRecent, formatItem, fraction, GAMES };
  window.Steward = api;
  if (typeof document === "undefined" || !document.getElementById("steward-grid")) return;

  const summaryEl = document.getElementById("steward-summary");
  const portraitEl = document.getElementById("steward-portrait");
  const gridEl = document.getElementById("steward-grid");

  function el(tag, className, text) {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (text !== undefined) node.textContent = text;
    return node;
  }

  function card(game, status) {
    const li = el("li", "steward-card");
    li.id = game.slug;
    li.dataset.state = status.kind;
    li.appendChild(el("h2", "steward-card-name", game.name));
    if (status.items && status.items.length) {
      const dl = el("dl", "steward-stats");
      status.items.forEach((item) => {
        const row = el("div", "steward-stat");
        row.appendChild(el("dt", "steward-stat-label", item.label));
        const dd = el("dd", "steward-stat-value");
        dd.appendChild(el("span", "steward-stat-number", formatItem(item)));
        const frac = fraction(item);
        if (frac !== null) {
          const bar = el("span", "steward-bar");
          bar.setAttribute("aria-hidden", "true");
          const fill = el("span", "steward-bar-fill");
          fill.style.width = Math.round(frac * 100) + "%";
          bar.appendChild(fill);
          dd.appendChild(bar);
        }
        if (item.note) dd.appendChild(el("span", "steward-stat-note", item.note));
        row.appendChild(dd);
        dl.appendChild(row);
      });
      li.appendChild(dl);
    }
    if (status.message) li.appendChild(el("p", "steward-card-message", status.message));
    if (status.when) li.appendChild(el("p", "steward-card-when", "Read from your save of " + status.when + "."));
    const link = el("a", "steward-card-link", (status.kind === "ready" ? "Open " : "Play ") + game.name);
    link.href = game.href;
    li.appendChild(link);
    return li;
  }

  async function fetchSaves(token) {
    try {
      const res = await fetch(API_BASE + "/users/me/saves", { headers: { Authorization: "Bearer " + token } });
      if (!res.ok) return null;
      const body = await res.json();
      return Array.isArray(body) ? body : null;
    } catch (e) {
      return null;
    }
  }

  function listNames(names) {
    if (names.length <= 1) return names.join("");
    return names.slice(0, -1).join(", ") + " and " + names[names.length - 1];
  }

  async function main() {
    const hubGames = window.HubGames ? await window.HubGames.load() : [];
    const games = GAMES.map((g) => {
      const info = hubGames.find((h) => h.slug === g.slug);
      return Object.assign({}, g, { name: info && info.name ? info.name : g.name, href: info && info.href ? info.href : "games/" + g.slug + "/index.html" });
    });
    const token = typeof hubGetBearerToken === "function" ? hubGetBearerToken() : null;
    const saves = token ? await fetchSaves(token) : null;

    gridEl.textContent = "";
    if (!token || !saves) {
      if (!token) {
        summaryEl.textContent = "Sign in on the hub to see your Climate Steward portrait.";
        portraitEl.textContent = "This page reads your own saves, so it has nothing to show until you are signed in. The eight climate worlds are listed below.";
      } else {
        summaryEl.textContent = "Your saves could not be read right now.";
        portraitEl.textContent = "Try again in a moment. Nothing was changed; this page only reads.";
      }
      games.forEach((g) => gridEl.appendChild(card(g, {
        kind: "locked",
        message: token ? "Could not read this game's save." : "Not read yet (signed out).",
      })));
      return;
    }

    const tended = [];
    const waiting = [];
    games.forEach((g) => {
      const save = mostRecent(saves, g.slug);
      if (!save) {
        waiting.push(g.name);
        gridEl.appendChild(card(g, { kind: "empty", message: "No save yet. When you play, this card fills in." }));
        return;
      }
      tended.push(g.name);
      const items = summaryFor(g.slug, save.save_data);
      if (!items.length) {
        gridEl.appendChild(card(g, {
          kind: "ready", when: dateText(save),
          message: "This save does not carry summary numbers yet. Play a round and save again.",
        }));
      } else {
        gridEl.appendChild(card(g, { kind: "ready", items, when: dateText(save) }));
      }
    });

    summaryEl.textContent = "You are tending " + tended.length + " of " + games.length + " climate worlds.";
    if (tended.length) {
      let text = "You have a save in " + listNames(tended) + ".";
      if (waiting.length) text += " Still waiting for you: " + listNames(waiting) + ".";
      else text += " Every climate world has a save.";
      portraitEl.textContent = text;
    } else {
      portraitEl.textContent = "None of the climate worlds has a save yet. Start any of them and this portrait fills in as you play.";
    }
  }

  main();
})();
