/*
 * Hub "Today" strip (TODO Y-2), loaded on index.html after script.js.
 *
 * One compact block above the lobby with only things that are true right now, each read from the
 * place that owns it:
 *   - Daily games: whether today's daily puzzle is done. Signal keeps its own state in
 *     localStorage["signal:state"] (days["<UTC date>:<mode>"], kind "daily"); any other game that
 *     records dailies through shared/seed.js uses localStorage["noyvj-daily-v1"] (runs and
 *     streaks). Both are read, never written.
 *   - Your daily streak, from the same two records (Signal: consecutive daily wins; seed.js:
 *     its own streak counter). It never punishes: no streak is just a sentence saying so.
 *   - The weekly challenge, from the admin-edited feed today.json (schema in today-feed.md).
 *     Shipped content is a SAMPLE schedule and is labelled as one on the page.
 *   - The seasonal event that is on today (shared/seasonal-events.js, dates from
 *     shared/seasonal-dates.json, copy and badge mark from events.json) or the next one, plus
 *     whether its badge is earned on this device.
 * Daily puzzles and the streak are read from the games' own saved data, so (GN-15) they are shown only when
 * the player has turned that on: settings.html "Show my daily puzzles and streak in the Today strip", stored
 * as localStorage["hub_today_track_dailies"] = "1" on this device. Off (the default) the strip never opens
 * those records at all and says so, with a button to turn it on. The weekly challenge and the seasonal event
 * do not depend on any game's data and always show.
 * Nothing here calls the backend. Every missing piece gets an honest sentence, not a placeholder.
 * "Today" for dailies is the UTC date (Signal resets at UTC midnight). ?event-date=YYYY-MM-DD
 * overrides the date for testing, the same switch the seasonal events use.
 *
 * window.HubToday: sanitizeFeed, weeklyFor, signalDaily, signalStreak, dailyRecord, utcDate,
 * addDays, render().
 */
(function () {
  "use strict";

  const FEED_URL = "today.json";
  const DAILY_KEY = "noyvj-daily-v1";
  const SIGNAL_KEY = "signal:state";
  const DONE_KEY = "hub_today_weekly_done";
  const TRACK_KEY = "hub_today_track_dailies";
  const SIGNAL_MODES = [["easy", "Easy"], ["hard", "Hard"]];
  const DATE_RE = /^\d{4}-\d{2}-\d{2}$/;
  const SLUG_RE = /^[a-z0-9-]{1,40}$/;

  function lsGet(k) { try { return localStorage.getItem(k); } catch (e) { return null; } }
  function lsSet(k, v) { try { localStorage.setItem(k, v); } catch (e) { /* convenience only */ } }
  function jsonOf(text) { try { return JSON.parse(text); } catch (e) { return null; } }
  function trackingOn() { return lsGet(TRACK_KEY) === "1"; }

  // ---- dates ------------------------------------------------------------------------------------

  function realDate(text) {
    if (typeof text !== "string" || !DATE_RE.test(text)) return false;
    const d = new Date(text + "T00:00:00Z");
    return !isNaN(d.getTime()) && d.toISOString().slice(0, 10) === text;
  }
  function dayNumber(iso) { return Math.round(new Date(iso + "T00:00:00Z").getTime() / 86400000); }
  function addDays(iso, n) { return new Date((dayNumber(iso) + n) * 86400000).toISOString().slice(0, 10); }
  function utcDate(now) {
    try {
      const forced = new URLSearchParams(location.search).get("event-date");
      if (forced && realDate(forced)) return forced;
    } catch (e) { /* no URL */ }
    return (now instanceof Date ? now : new Date()).toISOString().slice(0, 10);
  }
  function longDate(iso) {
    return new Date(iso + "T00:00:00Z").toLocaleDateString(undefined, { weekday: "short", day: "numeric", month: "short", timeZone: "UTC" });
  }
  function shortDate(iso) {
    return new Date(iso + "T00:00:00Z").toLocaleDateString(undefined, { day: "numeric", month: "short", timeZone: "UTC" });
  }

  // ---- the feed ---------------------------------------------------------------------------------

  function cleanText(v, max) { return typeof v === "string" ? v.trim().slice(0, max) : ""; }

  /** Keeps only well-formed parts of today.json; anything else is dropped, never trusted. */
  function sanitizeFeed(raw) {
    const out = { sample: false, updated: "", note: "", daily: [], weekly: [], repeat: false };
    if (!raw || typeof raw !== "object" || raw.version !== 1) return out;
    out.sample = raw.sample === true;
    out.updated = realDate(raw.updated) ? raw.updated : "";
    out.note = cleanText(raw.note, 240);
    out.repeat = raw.repeat === true;
    if (Array.isArray(raw.daily)) {
      raw.daily.forEach((d) => {
        if (d && typeof d === "object" && SLUG_RE.test(String(d.game || ""))) out.daily.push({ game: d.game, label: cleanText(d.label, 60) });
      });
    }
    if (Array.isArray(raw.weekly)) {
      raw.weekly.forEach((w) => {
        if (!w || typeof w !== "object" || !realDate(w.start) || !SLUG_RE.test(String(w.game || ""))) return;
        const title = cleanText(w.title, 80);
        if (!title) return;
        out.weekly.push({ start: w.start, game: w.game, title, text: cleanText(w.text, 240), sample: w.sample === true });
      });
      out.weekly.sort((a, b) => (a.start < b.start ? -1 : 1));
    }
    return out;
  }

  /** { entry, weekStart, weekEnd, repeating } for the challenge covering `iso`, or null. */
  function weeklyFor(feed, iso) {
    const list = feed && feed.weekly ? feed.weekly : [];
    if (!list.length || !realDate(iso)) return null;
    const day = dayNumber(iso);
    for (let i = list.length - 1; i >= 0; i -= 1) {
      const s = dayNumber(list[i].start);
      if (s <= day && day < s + 7) return { entry: list[i], weekStart: list[i].start, weekEnd: addDays(list[i].start, 6), repeating: false };
    }
    if (feed.repeat) {
      const first = dayNumber(list[0].start);
      if (day >= first) {
        const weeks = Math.floor((day - first) / 7);
        const start = addDays(list[0].start, weeks * 7);
        return { entry: list[weeks % list.length], weekStart: start, weekEnd: addDays(start, 6), repeating: true };
      }
    }
    return null;
  }

  // ---- daily records ----------------------------------------------------------------------------

  /** Reads noyvj-daily-v1 (shared/seed.js format) for `iso`: { runs, streaks } already validated. */
  function dailyRecord(raw, iso) {
    const out = { runs: {}, streaks: {} };
    if (!raw || typeof raw !== "object" || raw.version !== 1) return out;
    if (raw.runs && typeof raw.runs === "object" && raw.date === iso) {
      Object.keys(raw.runs).forEach((g) => {
        const r = raw.runs[g];
        if (SLUG_RE.test(g) && r && typeof r === "object") out.runs[g] = { text: cleanText(r.text, 120) };
      });
    }
    if (raw.streaks && typeof raw.streaks === "object") {
      Object.keys(raw.streaks).forEach((g) => {
        const s = raw.streaks[g];
        if (SLUG_RE.test(g) && s && typeof s === "object" && realDate(s.last) && Number.isSafeInteger(s.count) && s.count >= 0) {
          const alive = s.last === iso || s.last === addDays(iso, -1);
          out.streaks[g] = { count: alive ? s.count : 0, best: Number.isSafeInteger(s.best) && s.best >= s.count ? s.best : s.count };
        }
      });
    }
    return out;
  }

  /** Signal's per-mode result for the UTC date: [{ mode, label, status: "won"|"lost"|"inprogress"|"none", pings }]. */
  function signalDaily(state, iso) {
    const days = state && typeof state === "object" && state.days && typeof state.days === "object" ? state.days : {};
    return SIGNAL_MODES.map(([mode, label]) => {
      const rec = days[iso + ":" + mode];
      if (!rec || typeof rec !== "object" || rec.kind !== "daily") return { mode, label, status: "none", pings: 0 };
      const pings = Array.isArray(rec.pings) ? rec.pings.length : (Number.isFinite(rec.pings_used) ? rec.pings_used : 0);
      const status = rec.result === "won" || rec.result === "lost" ? rec.result : "inprogress";
      return { mode, label, status, pings };
    });
  }

  /** Signal's daily win streak, the same rule as game.py's _streaks: { count, best } across modes. */
  function signalStreak(state, iso) {
    const days = state && typeof state === "object" && state.days && typeof state.days === "object" ? state.days : {};
    let count = 0; let best = 0;
    SIGNAL_MODES.forEach(([mode]) => {
      const wins = new Set();
      let lostToday = false;
      Object.keys(days).forEach((key) => {
        const parts = key.split(":");
        const rec = days[key];
        if (parts.length !== 2 || parts[1] !== mode || !realDate(parts[0]) || !rec || rec.kind !== "daily") return;
        if (rec.result === "won") wins.add(dayNumber(parts[0]));
        else if (rec.result === "lost" && parts[0] === iso) lostToday = true;
      });
      if (!wins.size) return;
      const ordered = Array.from(wins).sort((a, b) => a - b);
      let run = 1; let modeBest = 1;
      for (let i = 1; i < ordered.length; i += 1) {
        run = ordered[i] === ordered[i - 1] + 1 ? run + 1 : 1;
        modeBest = Math.max(modeBest, run);
      }
      best = Math.max(best, modeBest);
      if (lostToday) return;
      const today = dayNumber(iso);
      const anchor = wins.has(today) ? today : wins.has(today - 1) ? today - 1 : null;
      if (anchor === null) return;
      let length = 0;
      while (wins.has(anchor - length)) length += 1;
      count = Math.max(count, length);
    });
    return { count, best };
  }

  // ---- small DOM helpers ------------------------------------------------------------------------

  function el(tag, className, text) {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (text !== undefined) node.textContent = text;
    return node;
  }
  function item(label) {
    const li = el("li", "today-item");
    li.appendChild(el("span", "today-label", label));
    return li;
  }
  function plural(n, word) { return n + " " + word + (n === 1 ? "" : "s"); }

  function gameNames() {
    const names = {};
    document.querySelectorAll(".title-card").forEach((card) => {
      const w = card.querySelector(".review-widget");
      const n = card.querySelector(".title-card-name");
      if (w && n) names[w.dataset.gameSlug] = n.textContent.trim();
    });
    return names;
  }
  function gameLink(slug, names, text) {
    const a = el("a", "today-link", text || names[slug] || slug);
    a.href = "games/" + slug + "/index.html";
    return a;
  }

  // ---- sections ---------------------------------------------------------------------------------

  function dailyItems(feed, iso, names) {
    const games = feed && feed.daily.length ? feed.daily : [{ game: "signal", label: "" }];
    const signal = jsonOf(lsGet(SIGNAL_KEY));
    const record = dailyRecord(jsonOf(lsGet(DAILY_KEY)), iso);
    return games.map((g) => {
      const label = g.label || (names[g.game] || g.game) + " daily puzzle";
      const li = item(label);
      const body = el("span", "today-body");
      let line;
      if (g.game === "signal") {
        const modes = signalDaily(signal, iso);
        const finished = modes.filter((m) => m.status === "won" || m.status === "lost");
        const headline = finished.length === modes.length ? "Done today" : finished.length ? "Partly done" : "Not played yet";
        const parts = modes.map((m) => {
          if (m.status === "won") return m.label + " won" + (m.pings ? " in " + plural(m.pings, "ping") : "");
          if (m.status === "lost") return m.label + " lost";
          if (m.status === "inprogress") return m.label + " in progress";
          return m.label + " not played";
        });
        line = (finished.length === modes.length ? "✓ " : "○ ") + headline + ": " + parts.join(", ") + ".";
      } else if (record.runs[g.game]) {
        const t = record.runs[g.game].text;
        line = "✓ Done today" + (t ? ": " + t : "") + ".";
      } else {
        line = "○ Not played yet.";
      }
      body.appendChild(document.createTextNode(line + " "));
      body.appendChild(gameLink(g.game, names, "Play"));
      li.appendChild(body);
      return li;
    });
  }

  /** GN-15: the one item shown in place of the daily puzzles and the streak while tracking is off. */
  function trackingOffItem() {
    const li = item("Daily puzzles and streak");
    const body = el("span", "today-body");
    body.appendChild(document.createTextNode("Not tracking. The Today strip is not reading your games' daily puzzles or streaks. "));
    const on = el("button", "secondary today-track-button", "Turn on daily tracking");
    on.type = "button";
    on.addEventListener("click", () => { lsSet(TRACK_KEY, "1"); render(); });
    body.appendChild(on);
    body.appendChild(document.createTextNode(" "));
    const settings = el("a", "today-link", "Settings");
    settings.href = "settings.html#today-tracking";
    body.appendChild(settings);
    li.appendChild(body);
    return li;
  }

  function streakItem(feed, iso, names) {
    const li = item("Daily streak");
    const body = el("span", "today-body");
    const record = dailyRecord(jsonOf(lsGet(DAILY_KEY)), iso);
    const candidates = [];
    const sig = signalStreak(jsonOf(lsGet(SIGNAL_KEY)), iso);
    candidates.push({ game: "signal", count: sig.count, best: sig.best });
    Object.keys(record.streaks).forEach((g) => candidates.push({ game: g, count: record.streaks[g].count, best: record.streaks[g].best }));
    candidates.sort((a, b) => b.count - a.count || b.best - a.best);
    const top = candidates[0];
    if (top && top.count > 0) {
      body.textContent = plural(top.count, "day") + " in a row in " + (names[top.game] || top.game) + (top.best > top.count ? " (best " + top.best + ")" : "") + ".";
    } else if (top && top.best > 0) {
      body.textContent = "No streak running. Your best is " + plural(top.best, "day") + ". Finish a daily puzzle to start a new one.";
    } else {
      body.textContent = "No streak yet. Finish a daily puzzle to start one; missing a day just starts again at one.";
    }
    li.appendChild(body);
    return li;
  }

  function weeklyItem(feedState, iso, names) {
    const li = item("Weekly challenge");
    const body = el("span", "today-body");
    li.appendChild(body);
    if (feedState.error) {
      body.textContent = "The weekly challenge could not be loaded right now.";
      return li;
    }
    const found = weeklyFor(feedState.feed, iso);
    if (!found) {
      body.textContent = "No weekly challenge is scheduled this week.";
      return li;
    }
    const w = found.entry;
    const sample = feedState.feed.sample || w.sample;
    const head = el("span", "today-challenge-title", w.title);
    body.appendChild(head);
    if (sample) {
      const flag = el("span", "today-sample", "Sample");
      flag.title = "A placeholder challenge to show how the weekly slot works. The owner has not published a real schedule yet.";
      body.append(" ", flag);
    }
    if (w.text) body.appendChild(el("span", "today-challenge-text", w.text));
    const meta = el("span", "today-meta");
    meta.append("Week of " + shortDate(found.weekStart) + ". ");
    meta.appendChild(gameLink(w.game, names, "Play " + (names[w.game] || w.game)));
    body.appendChild(meta);
    const key = found.weekStart + "|" + w.game + "|" + w.title;
    const label = el("label", "today-check");
    const box = document.createElement("input");
    box.type = "checkbox";
    box.checked = lsGet(DONE_KEY) === key;
    box.addEventListener("change", () => { if (box.checked) lsSet(DONE_KEY, key); else if (lsGet(DONE_KEY) === key) lsSet(DONE_KEY, ""); });
    label.append(box, " I did this one (your own tick, kept on this device only)");
    body.appendChild(label);
    return li;
  }

  async function fetchJson(url) {
    try {
      const res = await fetch(url);
      return res.ok ? await res.json() : null;
    } catch (e) { return null; }
  }

  function earnedBadgeIds() {
    const parsed = jsonOf(lsGet("event_badges_v1"));
    const ids = new Set();
    if (parsed && parsed.version === 1 && Array.isArray(parsed.badges)) parsed.badges.forEach((b) => { if (b && typeof b.id === "string") ids.add(b.id); });
    return ids;
  }

  let eventData = null;

  function nextEvent(S, dates, iso) {
    for (let n = 1; n <= 400; n += 1) {
      const found = S.activeEvents(addDays(iso, n), { dates });
      if (found.length) return { event: found[0], inDays: n };
    }
    return null;
  }

  async function eventItem(iso) {
    const li = item("Seasonal event");
    const body = el("span", "today-body");
    li.appendChild(body);
    const S = window.NoyvjSeasonal;
    if (!eventData) eventData = Promise.all([fetchJson("shared/seasonal-dates.json"), fetchJson("events.json")]);
    const [dates, copyList] = await eventData;
    if (!dates) eventData = null; // try again next render (offline then back online)
    if (!S || !dates) {
      body.textContent = "The event calendar could not be loaded right now.";
      return li;
    }
    S.setDates(dates);
    const copy = {};
    if (copyList && Array.isArray(copyList.events)) copyList.events.forEach((c) => { copy[c.id] = c; });
    const active = S.activeEvents(iso, { dates });
    const links = el("span", "today-meta");
    const eventsLink = el("a", "today-link", "All events");
    eventsLink.href = "events.html";
    if (active.length) {
      const earned = earnedBadgeIds();
      active.forEach((event) => {
        const c = copy[event.id] || {};
        const row = el("span", "today-event");
        const mark = el("span", "today-medal", c.mark || event.name.slice(0, 2));
        mark.setAttribute("aria-hidden", "true");
        if (c.accent && /^#[0-9a-fA-F]{6}$/.test(c.accent)) mark.style.borderColor = c.accent;
        row.appendChild(mark);
        const text = el("span", "today-event-text");
        const badge = S.badgeLabel(event, null, event.year);
        const got = earned.has(S.badgeId(event));
        text.appendChild(el("strong", "", event.name));
        text.append(" is on until " + shortDate(event.end) + ". Badge: " + badge + (got ? " (earned on this device)." : " (not earned yet)."));
        const hosted = c.host && c.host.status === "live";
        text.appendChild(el("span", "today-meta", hosted ? "Play it in " + c.host.name + "." : "No game hosts this event yet, so the badge cannot be earned yet."));
        row.appendChild(text);
        body.appendChild(row);
      });
    } else {
      const next = nextEvent(S, dates, iso);
      body.textContent = next
        ? "No event today. Next: " + next.event.name + " opens in " + plural(next.inDays, "day") + " (" + shortDate(next.event.start) + ")."
        : "No event today, and the next date is not published yet.";
    }
    links.appendChild(eventsLink);
    body.appendChild(links);
    return li;
  }

  // ---- render -----------------------------------------------------------------------------------

  let feedState = null;

  async function render() {
    const strip = document.getElementById("today-strip");
    const list = document.getElementById("today-items");
    if (!strip || !list) return;
    const iso = utcDate();
    const names = gameNames();
    if (!feedState) {
      const raw = await fetchJson(FEED_URL);
      feedState = raw ? { feed: sanitizeFeed(raw), error: false } : { feed: sanitizeFeed(null), error: true };
    }
    const dateEl = document.getElementById("today-date");
    if (dateEl) dateEl.textContent = longDate(iso) + " (UTC)";
    const events = await eventItem(iso);
    list.textContent = "";
    if (trackingOn()) {
      dailyItems(feedState.feed, iso, names).forEach((li) => list.appendChild(li));
      list.appendChild(streakItem(feedState.feed, iso, names));
    } else {
      list.appendChild(trackingOffItem());
    }
    list.appendChild(weeklyItem(feedState, iso, names));
    list.appendChild(events);
    const status = document.getElementById("today-status");
    if (status) {
      status.textContent = feedState.error
        ? "The weekly feed could not be loaded; daily status and events below still come from this device."
        : feedState.feed.sample ? "The weekly challenge is a sample schedule until a real one is published." + (trackingOn() ? " Daily puzzles reset at midnight UTC." : "")
          : (trackingOn() ? "Daily puzzles reset at midnight UTC." : "");
    }
    window.dispatchEvent(new CustomEvent("hub-today-rendered"));
  }

  window.HubToday = { sanitizeFeed, weeklyFor, signalDaily, signalStreak, dailyRecord, utcDate, addDays, render, trackingOn, TRACK_KEY };

  function start() {
    render();
    // A finished daily in another tab, or coming back to this one after midnight UTC.
    document.addEventListener("visibilitychange", () => { if (!document.hidden) render(); });
    window.addEventListener("storage", (ev) => { if (ev.key === SIGNAL_KEY || ev.key === DAILY_KEY || ev.key === TRACK_KEY) render(); });
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", start);
  else start();
})();
