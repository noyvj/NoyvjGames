/*
 * profile.html (TODO Y-1): a player's public profile, and for its owner the one switch that makes it
 * public (off by default), the favourite-game picker and a share link.
 *
 *   profile.html?u=name   public view of "name" (only exists while its owner has it switched on)
 *   profile.html          your own page when signed in
 *
 * Data: GET /profiles/{name} (public, 404 for "no such player" and "not public" alike, so the page can
 * never tell a visitor whether an account exists) and, for the signed-in owner, GET/PUT
 * /users/me/profile. Everything is written with textContent. Nothing here counts or records visitors.
 */
(function () {
  "use strict";
  const API_BASE = "https://noyvjgames.fastapicloud.dev";
  const $ = (id) => document.getElementById(id);

  const FALLBACK_NAMES = {
    sol: "SOL", canopy: "Canopy", grid: "Grid", tide: "Tide", aftermath: "Aftermath", herd: "Herd",
    thaw: "Thaw", loop: "Loop", drift: "Drift", "trade-empire": "Trade Empire", continuum: "Continuum",
    "champ-de-mots": "Le Champ de Mots", signal: "Signal", lexis: "Lexis",
    "heist-committee": "Heist Committee",
    "lighthouse": "Lighthouse",
    "pocket-bazaar": "Pocket Bazaar",
    "dead-reckoning": "Dead Reckoning",
    "logic-gates": "Logic Gates",
    "robot-script": "Robot Script",
    "hull-repair": "Hull Repair",
    "station-medic": "Station Medic",
  };
  let games = [];                       // [{slug, name, href}] from the lobby page
  let ownData = null;                   // the owner's own profile data, when viewing it
  let shown = null;                     // the data on screen

  const token = () => { try { return typeof hubGetBearerToken === "function" ? hubGetBearerToken() : null; } catch (e) { return null; } };
  const authHeaders = () => (token() ? { Authorization: "Bearer " + token() } : {});

  function gameName(slug) {
    const found = games.find((g) => g.slug === slug);
    if (found) return found.name;
    if (FALLBACK_NAMES[slug]) return FALLBACK_NAMES[slug];
    return slug.replace(/-/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
  }
  function gameHref(slug) {
    const found = games.find((g) => g.slug === slug);
    return found ? found.href : "games/" + encodeURIComponent(slug) + "/index.html";
  }

  async function api(path, options) {
    try {
      const res = await fetch(API_BASE + path, Object.assign({ cache: "no-store" }, options || {}));
      let body = null;
      try { body = await res.json(); } catch (e) { body = null; }
      return { ok: res.ok, status: res.status, body };
    } catch (e) {
      return { ok: false, status: 0, body: null };
    }
  }

  function setStatus(text) { const el = $("pf-status"); el.textContent = text; el.hidden = !text; }

  function showMessage(heading, text, actions) {
    $("pf-card").hidden = true;
    $("pf-owner").hidden = true;
    $("pf-message").hidden = false;
    $("pf-message-h").textContent = heading;
    $("pf-message-text").textContent = text;
    const box = $("pf-message-actions");
    box.textContent = "";
    (actions || []).forEach((a, i) => {
      if (i) box.append(" ");
      const link = document.createElement("a");
      link.href = a.href;
      link.textContent = a.label;
      box.append(link);
    });
    setStatus("");
  }

  function memberSince(iso) {
    if (!iso) return "not known";
    const date = new Date(iso + "T00:00:00Z");
    if (Number.isNaN(date.getTime())) return "not known";
    return date.toLocaleDateString(undefined, { month: "long", year: "numeric", timeZone: "UTC" });
  }

  function timeText(seconds, gameCount) {
    if (!seconds) return "none recorded yet";
    const minutes = Math.round(seconds / 60);
    const span = minutes < 90 ? minutes + " minute" + (minutes === 1 ? "" : "s")
      : "about " + Math.round(seconds / 3600) + " hour" + (Math.round(seconds / 3600) === 1 ? "" : "s");
    return span + " across " + gameCount + " game" + (gameCount === 1 ? "" : "s");
  }

  function listItem(glyph, title, sub, count, extraClass) {
    const li = document.createElement("li");
    if (extraClass) li.className = extraClass;
    const g = document.createElement("span");
    g.className = "pf-glyph";
    g.setAttribute("aria-hidden", "true");
    g.textContent = glyph;
    const main = document.createElement("span");
    main.append(title);
    if (sub) {
      const s = document.createElement("span");
      s.className = "pf-sub";
      s.textContent = sub;
      main.append(s);
    }
    li.append(g, main);
    if (count) {
      const c = document.createElement("span");
      c.className = "pf-count";
      c.textContent = count;
      li.append(c);
    }
    return li;
  }

  function emptyItem(text) {
    const li = document.createElement("li");
    li.className = "pf-empty";
    li.textContent = text;
    return li;
  }

  function renderCard(data, isOwner) {
    shown = data;
    $("pf-card").hidden = false;
    $("pf-message").hidden = true;
    $("pf-name").textContent = data.username;
    $("pf-what-others-see").hidden = !isOwner;
    $("pf-since").textContent = memberSince(data.member_since);
    const fav = $("pf-fav");
    if (data.favourite_game) {
      fav.textContent = "";
      const link = document.createElement("a");
      link.href = gameHref(data.favourite_game);
      link.textContent = gameName(data.favourite_game);
      fav.append(link, data.favourite_is_most_played ? " (the one played most)" : "");
    } else {
      fav.textContent = "not chosen yet";
    }
    $("pf-time").textContent = timeText(data.total_seconds, data.games_played || (data.games || []).length);

    const badges = $("pf-badges");
    badges.textContent = "";
    if (!data.badges.length) {
      badges.append(emptyItem(isOwner ? "No badges yet. They appear as you earn achievements, try games and play on." : "No badges yet."));
    }
    data.badges.forEach((b) => {
      const event = b.kind === "event";
      badges.append(listItem(event ? "✦" : "★", b.label, (event ? "Seasonal badge. " : "") + (b.kind === "event" ? "" : b.detail || ""), "",
        event ? "pf-badge-event" : ""));
    });

    const list = $("pf-games");
    list.textContent = "";
    if (!data.games.length) {
      list.append(emptyItem(isOwner
        ? "Nothing recorded yet. Achievement counts appear here after you play a game while signed in and it saves."
        : "No achievements recorded yet."));
    }
    data.games.forEach((g) => {
      const li = listItem("▶", "", "", g.achievements + " achievement" + (g.achievements === 1 ? "" : "s"));
      const link = document.createElement("a");
      link.href = gameHref(g.game);
      link.textContent = gameName(g.game);
      li.children[1].append(link);
      list.append(li);
    });

    const streaks = $("pf-streaks");
    streaks.textContent = "";
    $("pf-streaks-wrap").hidden = !data.streaks.length;
    data.streaks.forEach((s) => {
      streaks.append(listItem("→", gameName(s.game), s.label.replace(/_/g, " "), String(s.value)));
    });
  }

  // ---- owner controls -----------------------------------------------------------------------
  function shareLink(username) {
    return new URL("profile.html?u=" + encodeURIComponent(username), location.href).href;
  }

  function renderOwner(data) {
    ownData = data;
    $("pf-owner").hidden = false;
    const isPublic = Boolean(data.is_public);
    $("pf-public").checked = isPublic;
    $("pf-state").textContent = isPublic
      ? "Your profile is public. Anyone with the link can see it."
      : "Your profile is private. Only you can see this page.";
    $("pf-private-note").hidden = isPublic;
    $("pf-share").hidden = !isPublic;
    $("pf-link").value = shareLink(data.username);
    const select = $("pf-favourite");
    select.textContent = "";
    const auto = document.createElement("option");
    auto.value = "";
    auto.textContent = "The one I play most (automatic)";
    select.append(auto);
    const slugs = games.length ? games.map((g) => g.slug) : Object.keys(FALLBACK_NAMES);
    slugs.forEach((slug) => {
      const o = document.createElement("option");
      o.value = slug;
      o.textContent = gameName(slug);
      select.append(o);
    });
    if (data.favourite_game_choice && !slugs.includes(data.favourite_game_choice)) {
      const o = document.createElement("option");
      o.value = data.favourite_game_choice;
      o.textContent = gameName(data.favourite_game_choice);
      select.append(o);
    }
    select.value = data.favourite_game_choice || "";
    renderCard(data, true);
  }

  async function putProfile(body) {
    const status = $("pf-owner-status");
    status.textContent = "Saving…";
    const res = await api("/users/me/profile", {
      method: "PUT",
      headers: Object.assign({ "Content-Type": "application/json" }, authHeaders()),
      body: JSON.stringify(body),
    });
    if (!res.ok || !res.body) {
      status.textContent = res.status === 401
        ? "You have been signed out. Sign in on the hub and try again."
        : "That did not save (the server may be asleep). Nothing changed; try again in a moment.";
      renderOwner(ownData);                      // put the controls back to what is really stored
      return;
    }
    status.textContent = "Saved.";
    renderOwner(res.body);
  }

  function copyLink() {
    const input = $("pf-link");
    const status = $("pf-owner-status");
    const done = () => { status.textContent = "Link copied."; };
    const fallback = () => {
      input.focus();
      input.select();
      let ok = false;
      try { ok = document.execCommand("copy"); } catch (e) { ok = false; }
      status.textContent = ok ? "Link copied." : "Press Ctrl or Cmd + C to copy the selected link.";
    };
    if (navigator.clipboard && navigator.clipboard.writeText) navigator.clipboard.writeText(input.value).then(done, fallback);
    else fallback();
  }

  // ---- start --------------------------------------------------------------------------------
  async function start() {
    const params = new URLSearchParams(location.search);
    const wanted = (params.get("u") || "").trim();
    const loadedGames = window.HubGames ? window.HubGames.load() : Promise.resolve([]);
    games = (await loadedGames.catch(() => [])) || [];

    let own = null;
    if (token()) {
      const res = await api("/users/me/profile", { headers: authHeaders() });
      if (res.ok && res.body) own = res.body;
    }
    if (!wanted && own) {
      try { history.replaceState(null, "", "profile.html?u=" + encodeURIComponent(own.username)); } catch (e) { /* cosmetic */ }
    }
    if (own && (!wanted || wanted.toLowerCase() === own.username.toLowerCase())) {
      setStatus("");
      document.title = own.username + " — Profile — NoyvjGames";
      renderOwner(own);
      return;
    }
    if (!wanted) {
      showMessage("Whose profile?", token()
        ? "Your profile could not be loaded right now. Try again in a moment."
        : "A profile address looks like profile.html?u=name. Sign in on the hub to see and share your own.",
        [{ href: "index.html#account-section", label: "Go to the hub to sign in" }]);
      return;
    }
    const res = await api("/profiles/" + encodeURIComponent(wanted));
    if (res.ok && res.body) {
      setStatus("");
      document.title = res.body.username + " — Profile — NoyvjGames";
      renderCard(res.body, false);
      return;
    }
    if (res.status === 404) {
      showMessage("No public profile here",
        "There is no public profile with that name. Either the player has not switched theirs on (it is private by default) or the name is wrong.",
        [{ href: "index.html", label: "Back to the games" }]);
    } else if (res.status === 429) {
      showMessage("Too many looks", "Please wait a little and try again.", []);
    } else {
      showMessage("The profile could not be loaded", "The server did not answer (it may be asleep or you may be offline). Try again in a moment.",
        [{ href: location.href, label: "Try again" }]);
    }
  }

  $("pf-public").addEventListener("change", (event) => putProfile({ is_public: event.target.checked }));
  $("pf-favourite").addEventListener("change", (event) => putProfile({ favourite_game: event.target.value || null }));
  $("pf-copy").addEventListener("click", copyLink);
  start();
})();
