/*
 * sources.html (SR-1, SR-2): one shared page, one data file per game.
 *
 *   sources.html?game=<slug>   that game's Sources page, read from games/<slug>/sources.json
 *   sources.html               the hub-wide index: every game's sources together, with a filter box
 *
 * SCHEMA of games/<slug>/sources.json (adding a source is adding one line to one list):
 *
 *   {
 *     "game": "<slug>",                      required, must equal the folder name
 *     "updated": "YYYY-MM-DD",               required, when the list last changed
 *     "research": [                          papers, datasets, reports, pages read live
 *       { "title": "...",                    required, non-empty
 *         "by": "...",                       required: the publisher or author
 *         "url": "https://...",              optional, https only (anything else is shown as plain text)
 *         "read": "YYYY-MM-DD",              optional: the date the page or data was read (live pages)
 *         "note": "..." }                    required, non-empty: what the game took from it
 *     ],
 *     "inspiration": [                       games, shows, books or other media
 *       { "title": "...",                    required
 *         "kind": "game|show|book|film|other",   required
 *         "by": "...",                       optional: the creator or studio
 *         "note": "..." }                    required: what was taken (a mechanic, a mood, a structure)
 *     ],
 *     "other": [                             tools, libraries, how the maths or rules were derived
 *       { "title": "...",                    required
 *         "by": "...",                       required
 *         "url": "https://...",              optional, https only
 *         "note": "..." }                    required
 *     ]
 *   }
 *
 * An empty list is fine (the page says so in a sentence). A game without a file gets a friendly
 * "No sources file yet" message. Everything from a file is data: it is put on the page with
 * textContent only, a link is only made for an https address and always opens with
 * rel="noopener noreferrer", and nothing in a file is ever run. The tests in scripts/tests/ check
 * every committed file against this schema.
 *
 * The game list and names come from the lobby itself (hub-games.js reads index.html's title cards),
 * plus any slug in game-manifest.json that the lobby does not list.
 */
(function () {
  "use strict";

  const GROUPS = [
    { key: "research", title: "Research",
      blurb: "Papers, datasets, reports and pages read live.",
      empty: "No research sources are listed for this game yet." },
    { key: "inspiration", title: "Inspiration",
      blurb: "Games, shows, books and other media this game drew on.",
      empty: "No inspirations are listed for this game yet." },
    { key: "other", title: "Other credits",
      blurb: "Tools, libraries and how the maths or rules were worked out.",
      empty: "No other credits are listed for this game yet." },
  ];
  const KINDS = { game: "Game", show: "TV show", book: "Book", film: "Film", other: "Other" };
  const SLUG_RE = /^[a-z0-9][a-z0-9-]{0,48}$/;

  function str(v) { return typeof v === "string" ? v.trim() : ""; }

  // An https address or "": anything else is never made into a link.
  function safeUrl(v) {
    const raw = str(v);
    if (!raw) return null;
    try {
      const u = new URL(raw);
      return u.protocol === "https:" ? u : null;
    } catch (e) { return null; }
  }

  function domainOf(u) { return u.hostname.replace(/^www\./, ""); }

  // Reads a parsed file into clean entries. Never throws; entries without a title are dropped.
  function normalise(data) {
    const out = { game: "", updated: "", research: [], inspiration: [], other: [], dropped: 0 };
    if (!data || typeof data !== "object" || Array.isArray(data)) return out;
    out.game = str(data.game);
    out.updated = /^\d{4}-\d{2}-\d{2}$/.test(str(data.updated)) ? str(data.updated) : "";
    GROUPS.forEach((g) => {
      const list = Array.isArray(data[g.key]) ? data[g.key] : [];
      list.forEach((e) => {
        if (!e || typeof e !== "object" || !str(e.title)) { out.dropped += 1; return; }
        const kind = str(e.kind).toLowerCase();
        out[g.key].push({
          title: str(e.title),
          by: str(e.by),
          url: str(e.url),
          read: /^\d{4}-\d{2}-\d{2}$/.test(str(e.read)) ? str(e.read) : "",
          kind: g.key === "inspiration" ? (KINDS[kind] ? kind : "other") : "",
          note: str(e.note),
        });
      });
    });
    return out;
  }

  function countOf(n) { return n.research.length + n.inspiration.length + n.other.length; }

  function el(tag, className, text) {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (text !== undefined) node.textContent = text;
    return node;
  }

  function buildEntry(entry, groupKey) {
    const li = el("li", "src-item");
    li.dataset.srcText = [entry.title, entry.by, entry.note, entry.kind, entry.url].join(" ").toLowerCase();
    const head = el("div", "src-item-title");
    const link = safeUrl(entry.url);
    if (link) {
      const a = el("a", "", entry.title);
      a.href = link.href;
      a.target = "_blank";
      a.rel = "noopener noreferrer";
      head.appendChild(a);
      head.appendChild(el("span", "visually-hidden", " (opens in a new tab)"));
      head.appendChild(el("span", "src-domain", ` ${domainOf(link)}`));
    } else {
      head.appendChild(el("span", "", entry.title));
      if (entry.url) head.appendChild(el("span", "src-domain", ` ${entry.url}`));
    }
    li.appendChild(head);
    const meta = [];
    if (groupKey === "inspiration") meta.push(KINDS[entry.kind]);
    if (entry.by) meta.push(groupKey === "inspiration" ? `by ${entry.by}` : entry.by);
    if (entry.read) meta.push(`read ${entry.read}`);
    if (meta.length) li.appendChild(el("div", "src-item-meta", meta.join(" · ")));
    if (entry.note) li.appendChild(el("p", "src-item-note", entry.note));
    return li;
  }

  // Appends the three groups to `into`. headingTag is "h2" on a game's own page, "h3" in the index.
  function renderGroups(into, data, headingTag) {
    const n = data && Array.isArray(data.research) && typeof data.game === "string" && "dropped" in data ? data : normalise(data);
    GROUPS.forEach((g) => {
      const section = el("section", "src-group");
      section.dataset.group = g.key;
      const heading = el(headingTag || "h2", "src-group-h", `${g.title} (${n[g.key].length})`);
      section.appendChild(heading);
      section.appendChild(el("p", "hub-note src-group-blurb", g.blurb));
      if (!n[g.key].length) {
        section.appendChild(el("p", "src-empty", g.empty));
      } else {
        const ul = el("ul", "src-list");
        n[g.key].forEach((entry) => ul.appendChild(buildEntry(entry, g.key)));
        section.appendChild(ul);
      }
      into.appendChild(section);
    });
    return n;
  }

  // ---- page wiring -----------------------------------------------------------------------

  function prettify(slug) { return slug.replace(/-/g, " ").replace(/\b\w/g, (c) => c.toUpperCase()); }

  function fetchJson(url) {
    return fetch(url).then((res) => {
      if (res.status === 404) return { missing: true };
      if (!res.ok) return { error: true };
      return res.json().then((data) => ({ data }), () => ({ error: true }));
    }).catch(() => ({ error: true }));
  }

  function loadGameList() {
    const hub = window.HubGames ? window.HubGames.load() : Promise.resolve([]);
    const manifest = fetch("game-manifest.json").then((r) => (r.ok ? r.json() : {})).catch(() => ({}));
    return Promise.all([hub, manifest]).then(([games, man]) => {
      const list = games.map((g) => ({ slug: g.slug, name: g.name }));
      const seen = new Set(list.map((g) => g.slug));
      (Array.isArray(man.achievements) ? man.achievements : []).forEach((slug) => {
        if (typeof slug === "string" && SLUG_RE.test(slug) && !seen.has(slug)) {
          seen.add(slug);
          list.push({ slug, name: prettify(slug) });
        }
      });
      return list;
    });
  }

  function link(href, text, className) {
    const a = el("a", className || "", text);
    a.href = href;
    return a;
  }

  function setPage(title, tagline) {
    const h1 = document.getElementById("sources-title");
    if (h1) h1.textContent = title;
    const tag = document.getElementById("hub-tagline");
    if (tag && tagline) tag.textContent = tagline;
  }

  function showMessage(root, heading, text, links) {
    root.textContent = "";
    const card = el("section", "hub-card src-message");
    card.appendChild(el("h2", "", heading));
    card.appendChild(el("p", "", text));
    if (links && links.length) {
      const p = el("p");
      links.forEach((l, i) => {
        if (i) p.appendChild(document.createTextNode(" · "));
        p.appendChild(link(l.href, l.text));
      });
      card.appendChild(p);
    }
    root.appendChild(card);
  }

  function renderGamePage(root, slug, games) {
    const known = games.find((g) => g.slug === slug);
    const name = known ? known.name : prettify(slug);
    document.title = `Sources: ${name} — NoyvjGames`;
    setPage(`Sources: ${name}`, "The research this game used, what inspired it, and the tools and credits behind it.");
    const legacy = document.getElementById("src-legacy");
    if (legacy) legacy.hidden = true;
    const back = [
      { href: `games/${slug}/index.html`, text: `← Back to ${name}` },
      { href: "sources.html", text: "All games' sources" },
      { href: "index.html", text: "Hub" },
    ];
    return fetchJson(`games/${slug}/sources.json`).then((res) => {
      if (res.missing) {
        if (!known) {
          document.title = "Sources \u2014 NoyvjGames";
          setPage("Sources & Credits");
          showMessage(root, "No game called that",
            `There is no game "${slug}" on the hub, so there is nothing to list here.`, back.slice(1));
        } else {
          showMessage(root, "No sources file yet",
            `${name} does not have a sources list yet. When it does, the research it used, what inspired it and its other credits will appear here.`,
            back);
        }
        return;
      }
      if (res.error) {
        showMessage(root, "Could not load the sources",
          `${name}'s sources file could not be read just now. Try again in a moment.`, back);
        return;
      }
      root.textContent = "";
      const nav = el("p", "src-back");
      back.forEach((l, i) => {
        if (i) nav.appendChild(document.createTextNode(" · "));
        nav.appendChild(link(l.href, l.text));
      });
      root.appendChild(nav);
      const body = el("div", "hub-card src-game-body");
      const n = normalise(res.data);
      const summary = `${countOf(n)} source${countOf(n) === 1 ? "" : "s"}` + (n.updated ? ` · list updated ${n.updated}` : "");
      body.appendChild(el("p", "hub-note src-summary", summary));
      renderGroups(body, n, "h2");
      root.appendChild(body);
    });
  }

  function renderIndex(root, games) {
    document.title = "Sources & Credits — NoyvjGames";
    setPage("Sources & Credits",
      "What every game used: research with the date it was read, the games and media that inspired it, and the tools behind it.");
    return Promise.all(games.map((g) => fetchJson(`games/${g.slug}/sources.json`))).then((results) => {
      root.textContent = "";
      const tools = el("div", "src-tools");
      const label = el("label", "visually-hidden", "Filter the sources");
      label.htmlFor = "src-filter";
      const input = el("input", "faq-search src-filter");
      input.type = "search";
      input.id = "src-filter";
      input.setAttribute("data-hub-search", "");
      input.autocomplete = "off";
      input.placeholder = "Filter by game, publisher or title\u2026";
      const toggle = el("button", "src-toggle", "Expand all");
      toggle.type = "button";
      toggle.setAttribute("aria-pressed", "false");
      tools.appendChild(label);
      tools.appendChild(input);
      tools.appendChild(toggle);
      root.appendChild(tools);
      const status = el("p", "hub-note src-status");
      status.setAttribute("role", "status");
      root.appendChild(status);
      const listEl = el("div", "src-index");
      root.appendChild(listEl);

      const cards = [];
      let total = 0;
      let withFile = 0;
      games.forEach((g, i) => {
        const res = results[i];
        const card = el("section", "hub-card src-game");
        card.dataset.slug = g.slug;
        const h2 = el("h2", "src-game-h");
        h2.appendChild(link(`sources.html?game=${encodeURIComponent(g.slug)}`, g.name));
        card.appendChild(h2);
        let n = null;
        if (res.data) {
          n = normalise(res.data);
          withFile += 1;
          total += countOf(n);
          const counts = el("p", "src-counts");
          GROUPS.forEach((grp) => counts.appendChild(el("span", "src-count", `${n[grp.key].length} ${grp.title.toLowerCase()}`)));
          card.appendChild(counts);
          const details = el("details", "src-details");
          details.appendChild(el("summary", "", `Show the ${countOf(n)} source${countOf(n) === 1 ? "" : "s"}`));
          renderGroups(details, n, "h3");
          card.appendChild(details);
        } else {
          card.appendChild(el("p", "src-empty", res.error ? "This game's sources file could not be read just now." : "No sources file yet."));
        }
        listEl.appendChild(card);
        cards.push({ card, name: g.name.toLowerCase(), slug: g.slug, details: card.querySelector("details"), loaded: !!n });
      });

      function words(q) { return q.toLowerCase().split(/\s+/).filter(Boolean); }
      function apply() {
        const terms = words(input.value);
        let shown = 0;
        cards.forEach((c) => {
          const nameHit = terms.every((t) => c.name.includes(t) || c.slug.includes(t));
          const items = Array.from(c.card.querySelectorAll(".src-item"));
          let hits = 0;
          items.forEach((li) => {
            const hit = terms.length === 0 || nameHit || terms.every((t) => (li.dataset.srcText || "").includes(t));
            li.hidden = !hit;
            if (hit) hits += 1;
          });
          const visible = terms.length === 0 || nameHit || hits > 0;
          c.card.hidden = !visible;
          if (visible) shown += 1;
          if (c.details && terms.length) c.details.open = visible && (hits > 0);
          c.card.querySelectorAll(".src-group").forEach((grp) => {
            const any = Array.from(grp.querySelectorAll(".src-item")).some((li) => !li.hidden);
            grp.hidden = terms.length > 0 && !any;
          });
        });
        status.textContent = terms.length
          ? `Showing ${shown} of ${cards.length} games.`
          : `${total} sources listed across ${withFile} of ${cards.length} games.` +
            (withFile < cards.length ? ` ${cards.length - withFile} still to come.` : "");
        const none = shown === 0;
        let msg = listEl.querySelector(".src-nomatch");
        if (none && !msg) {
          msg = el("p", "src-empty src-nomatch", "No source matches that filter. Try fewer words.");
          listEl.appendChild(msg);
        } else if (!none && msg) {
          msg.remove();
        }
      }
      input.addEventListener("input", apply);
      toggle.addEventListener("click", () => {
        const open = toggle.getAttribute("aria-pressed") !== "true";
        toggle.setAttribute("aria-pressed", String(open));
        toggle.textContent = open ? "Collapse all" : "Expand all";
        cards.forEach((c) => { if (c.details && !c.card.hidden) c.details.open = open; });
      });
      apply();
    });
  }

  window.NoyvjSources = { GROUPS, KINDS, normalise, renderGroups, safeUrl };

  function start() {
    const root = document.getElementById("sources-root");
    if (!root) return;
    const param = new URLSearchParams(location.search).get("game");
    const slug = param === null ? "" : param.trim().toLowerCase();
    loadGameList().then((games) => {
      if (slug && SLUG_RE.test(slug)) return renderGamePage(root, slug, games);
      if (slug) {
        document.title = "Sources — NoyvjGames";
        setPage("Sources & Credits");
        const legacy = document.getElementById("src-legacy");
        if (legacy) legacy.hidden = true;
        showMessage(root, "No game called that", "That is not a game name this page knows.",
          [{ href: "sources.html", text: "All games' sources" }, { href: "index.html", text: "Hub" }]);
        return null;
      }
      return renderIndex(root, games);
    }).catch(() => {
      showMessage(root, "Could not load the sources", "Something went wrong reading the sources. Try reloading the page.",
        [{ href: "index.html", text: "Hub" }]);
    });
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", start, { once: true });
  else start();
})();
