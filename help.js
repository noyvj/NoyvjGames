/*
 * help.html (Y-15): searchable FAQ built from help-data.json, plus the lobby's own game list
 * (read from index.html through hub-games.js, so there is no second copy of game names, blurbs or
 * tags) so a search for a game name or topic ("climate", "language") also lists matching games.
 *
 * Matching is the same plain rule the lobby search uses: every word typed must appear somewhere in
 * the item's text (question, answer, topic label) or the game's text (name, blurb, tags).
 */
(function () {
  "use strict";

  const $ = (id) => document.getElementById(id);
  const searchInput = $("faq-search");
  const listEl = $("faq-list");
  const statusEl = $("faq-status");
  const topicsEl = $("faq-topics");
  const gamesSection = $("faq-games-section");
  const gamesEl = $("faq-games");

  let data = null;
  let games = [];
  let activeTopic = "";
  const els = []; // { item, details, text }

  function words(query) {
    return query.toLowerCase().split(/\s+/).filter(Boolean);
  }
  function matches(text, terms) {
    return terms.every((t) => text.includes(t));
  }

  function buildItem(item, topicLabel) {
    const details = document.createElement("details");
    details.className = "faq-item";
    details.id = `faq-${item.id}`;
    const summary = document.createElement("summary");
    summary.textContent = item.q;
    details.appendChild(summary);
    const answer = document.createElement("p");
    answer.textContent = item.a;
    details.appendChild(answer);
    if (item.links && item.links.length) {
      const more = document.createElement("p");
      more.className = "hub-note";
      more.appendChild(document.createTextNode("See: "));
      item.links.forEach((link, i) => {
        if (i) more.appendChild(document.createTextNode(", "));
        const a = document.createElement("a");
        a.href = link.href;
        a.textContent = link.label;
        more.appendChild(a);
      });
      details.appendChild(more);
    }
    return { item, details, text: `${item.q} ${item.a} ${topicLabel}`.toLowerCase() };
  }

  function render() {
    const terms = words(searchInput.value);
    let shown = 0;
    els.forEach((entry) => {
      const visible = (!activeTopic || entry.item.topic === activeTopic) && matches(entry.text, terms);
      entry.details.hidden = !visible;
      // While searching, open the matches so the answer is visible straight away.
      if (terms.length) entry.details.open = visible;
      if (visible) shown += 1;
    });

    gamesEl.textContent = "";
    if (terms.length && games.length) {
      games
        .filter((g) => matches(`${g.name} ${g.blurb} ${g.tags.join(" ").replace(/-/g, " ")}`.toLowerCase(), terms))
        .forEach((g) => {
          const li = document.createElement("li");
          const a = document.createElement("a");
          a.href = g.href;
          a.textContent = g.name;
          li.appendChild(a);
          li.appendChild(document.createTextNode(` — ${g.blurb.length > 140 ? g.blurb.slice(0, 137).trimEnd() + "…" : g.blurb}`));
          gamesEl.appendChild(li);
        });
    }
    gamesSection.hidden = !gamesEl.children.length;

    if (!shown && !gamesEl.children.length) {
      statusEl.textContent = "Nothing matches that. Try fewer or different words, or ask through the feedback box.";
    } else if (!shown) {
      const n = gamesEl.children.length;
      statusEl.textContent = `No help answers match, but ${n} game${n === 1 ? "" : "s"} do.`;
    } else if (terms.length || activeTopic) {
      statusEl.textContent = `${shown} answer${shown === 1 ? "" : "s"} shown.`;
    } else {
      statusEl.textContent = `${els.length} questions.`;
    }
  }

  function buildTopics() {
    const make = (id, label) => {
      const b = document.createElement("button");
      b.type = "button";
      b.className = "faq-topic";
      b.textContent = label;
      b.dataset.topic = id;
      b.setAttribute("aria-pressed", String(id === activeTopic));
      b.addEventListener("click", () => {
        activeTopic = id === activeTopic ? "" : id;
        topicsEl.querySelectorAll(".faq-topic").forEach((el) => {
          el.setAttribute("aria-pressed", String(el.dataset.topic === activeTopic && activeTopic !== ""));
        });
        render();
      });
      return b;
    };
    data.topics.forEach((t) => topicsEl.appendChild(make(t.id, t.label)));
  }

  function openFromHash() {
    const id = location.hash.replace(/^#/, "");
    if (!id.startsWith("faq-")) return;
    const target = document.getElementById(id);
    if (target && target.tagName === "DETAILS") {
      target.open = true;
      target.scrollIntoView();
    }
  }

  async function boot() {
    try {
      const res = await fetch("help-data.json");
      if (!res.ok) throw new Error(`status ${res.status}`);
      data = await res.json();
      if (!data || !Array.isArray(data.items) || !Array.isArray(data.topics)) throw new Error("bad shape");
    } catch (err) {
      console.error("help.js: could not load help-data.json", err);
      statusEl.textContent = "The help could not be loaded. Check your connection and reload, or use the feedback box on the hub.";
      return;
    }
    const labels = {};
    data.topics.forEach((t) => { labels[t.id] = t.label; });
    data.items.forEach((item) => {
      const entry = buildItem(item, labels[item.topic] || "");
      els.push(entry);
      listEl.appendChild(entry.details);
    });
    buildTopics();
    searchInput.addEventListener("input", render);
    render();
    openFromHash();
    // The game list only matters once someone searches; load it without blocking the FAQ.
    window.HubGames.load().then((list) => { games = list; if (searchInput.value) render(); });
  }

  window.addEventListener("hashchange", openFromHash);
  boot();
})();
