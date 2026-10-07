/*
 * Shared seasonal-events front end (planning/TODO.md W-4, Round 3 section N).
 * The browser twin of shared/seasonal_events.py: the same date rules (fixed
 * dates, Easter, nth-weekday holidays, sourced tables for moving holidays) plus
 * what a game needs on screen: flavour overrides, a dismissible banner, and a
 * badge grant that lands where the hub already looks. No backend. Full guide:
 * planning/SHARED-COMPONENTS.md; event list and rationale:
 * planning/SEASONAL-EVENTS.md.
 *
 *   <link rel="stylesheet" href="../../shared/seasonal-events.css">  (optional: linked
 *                                      automatically when missing)
 *   <script src="../../shared/seasonal-events.js"></script>
 *   const events = NoyvjSeasonal.init({
 *     game: "aftermath",
 *     events: { halloween: { text: "Night of Storms", task: "Survive one run with resources left",
 *                            goal: 1, unit: "run" } },        // the event ids THIS game hosts
 *     progress: (id) => currentCount,                         // number | { count, goal } | null
 *     onGrant: (badge, all) => saveIntoMyState(all),          // optional mirror into the save
 *   });
 *   events.refresh();            // call after state changes (cheap: update in place)
 *
 * Dates: nothing is hardcoded. "Today" is, in order, init({ today }) (a Date, a
 * "YYYY-MM-DD" string or a function), the URL parameter ?event-date=YYYY-MM-DD,
 * then the browser's local date. Moving-holiday tables come from init({ dates })
 * or init({ datesUrl }) (default: shared/seasonal-dates.json next to this
 * script); a year a table lacks never counts as active. A custom event table
 * ({ id, name, when }, same schema as seasonal_events.DEFAULT_EVENTS) goes in
 * init({ calendar }).
 *
 * Badges follow the hub contract R2-Z23b (planning/ACHIEVEMENTS-SYSTEM-DESIGN.md
 * section 8): { id: "halloween-2026", label: "Halloween 2026", earned_at }.
 * Ids are lowercase slugs with hyphens (so the Python event id new_year gives
 * new-year-2027; seasonal_events.hub_badge_id is the Python equivalent). A grant
 * is written to localStorage "event_badges_v1" (merged with what is there; pass
 * localBadges:false to skip) and handed to onGrant(badge, allBadges) so the game
 * can also put the list in save_data.event_badges, which travels with the
 * account. Text is written with textContent only.
 */
(function (root) {
  "use strict";

  const DEFAULT_EVENTS = [
    { id: "new_year", name: "New Year", when: { kind: "fixed", month: 1, day: 1, before: 2, after: 3 } },
    { id: "valentines", name: "Valentine's Day", when: { kind: "fixed", month: 2, day: 14, before: 3, after: 1 } },
    { id: "lunar_new_year", name: "Lunar New Year", when: { kind: "table", table: "lunar_new_year", before: 1, after: 5 } },
    { id: "easter", name: "Easter", when: { kind: "easter", before: 3, after: 1 } },
    { id: "independence_day", name: "4th of July", when: { kind: "fixed", month: 7, day: 4, before: 3, after: 1 } },
    { id: "halloween", name: "Halloween", when: { kind: "fixed", month: 10, day: 31, before: 6, after: 1 } },
    { id: "diwali", name: "Diwali", when: { kind: "table", table: "diwali", before: 3, after: 2 } },
    { id: "thanksgiving", name: "Thanksgiving", when: { kind: "nth_weekday", month: 11, weekday: 3, n: 4, before: 3, after: 1 } },
    { id: "hanukkah", name: "Hanukkah", when: { kind: "table", table: "hanukkah" } },
    { id: "christmas", name: "Christmas", when: { kind: "fixed", month: 12, day: 25, before: 7, after: 1 } },
  ];

  // Decorative only (aria-hidden); a game can pass its own `icon`.
  const DEFAULT_ICONS = {
    new_year: "✨", valentines: "❤", lunar_new_year: "❀", easter: "✿", independence_day: "★",
    halloween: "☾", diwali: "✸", thanksgiving: "❦", hanukkah: "✡", christmas: "❄",
  };

  const BADGES_KEY = "event_badges_v1";
  const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
  let sharedDates = null;
  let counter = 0;

  // ---- dates (whole days, UTC arithmetic so DST never shifts a window) -----

  function toDay(year, month, day) {
    const ms = Date.UTC(year, month - 1, day);
    const d = new Date(ms);
    if (d.getUTCFullYear() !== year || d.getUTCMonth() !== month - 1 || d.getUTCDate() !== day) return null;
    return Math.round(ms / 86400000);
  }
  function fromDay(n) {
    const d = new Date(n * 86400000);
    const p = (v, w) => String(v).padStart(w, "0");
    return p(d.getUTCFullYear(), 4) + "-" + p(d.getUTCMonth() + 1, 2) + "-" + p(d.getUTCDate(), 2);
  }
  function parseIso(text) {
    const m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(String(text));
    return m ? toDay(Number(m[1]), Number(m[2]), Number(m[3])) : null;
  }
  function yearOf(dayNumber) { return new Date(dayNumber * 86400000).getUTCFullYear(); }
  function mod(a, b) { return ((a % b) + b) % b; }

  function easterSunday(year) {
    const a = year % 19;
    const b = Math.floor(year / 100); const c = year % 100;
    const d = Math.floor(b / 4); const e = b % 4;
    const f = Math.floor((b + 8) / 25);
    const g = Math.floor((b - f + 1) / 3);
    const h = (19 * a + b - d - g + 15) % 30;
    const i = Math.floor(c / 4); const k = c % 4;
    const l = (32 + 2 * e + 2 * i - h - k) % 7;
    const m = Math.floor((a + 11 * h + 22 * l) / 451);
    const total = h + l - 7 * m + 114;
    return toDay(year, Math.floor(total / 31), (total % 31) + 1);
  }

  // Monday = 0, like Python's date.weekday().
  function weekdayOf(dayNumber) { return mod(new Date(dayNumber * 86400000).getUTCDay() + 6, 7); }

  function nthWeekday(year, month, weekday, n) {
    if (n === -1) {
      const lastDay = month === 12 ? toDay(year + 1, 1, 1) - 1 : toDay(year, month + 1, 1) - 1;
      return lastDay - mod(weekdayOf(lastDay) - weekday, 7);
    }
    const first = toDay(year, month, 1);
    return first + mod(weekday - weekdayOf(first), 7) + 7 * (n - 1);
  }

  function asDay(value) {
    if (typeof value === "number") return value;
    if (value instanceof Date) return toDay(value.getFullYear(), value.getMonth() + 1, value.getDate());
    return parseIso(value);
  }

  // [startDay, endDay] of an event in `year`, or null.
  function eventWindowDays(event, year, dates) {
    const when = event && typeof event === "object" ? event.when : null;
    if (!when || typeof when !== "object") return null;
    const before = Number.isFinite(Number(when.before)) ? Math.trunc(Number(when.before)) : 0;
    const after = Number.isFinite(Number(when.after)) ? Math.trunc(Number(when.after)) : 0;
    let start; let end;
    if (when.kind === "fixed") {
      start = end = toDay(year, Math.trunc(Number(when.month)), Math.trunc(Number(when.day)));
    } else if (when.kind === "easter") {
      start = end = easterSunday(year);
    } else if (when.kind === "nth_weekday") {
      start = end = nthWeekday(year, Math.trunc(Number(when.month)), Math.trunc(Number(when.weekday)), Math.trunc(Number(when.n)));
    } else if (when.kind === "table") {
      const source = dates || sharedDates || {};
      const table = source[when.table];
      const entry = table && table.years ? table.years[String(year)] : undefined;
      if (Array.isArray(entry) && entry.length === 2) { start = parseIso(entry[0]); end = parseIso(entry[1]); }
      else { start = end = parseIso(entry); }
    } else {
      return null;
    }
    if (start === null || end === null || start === undefined || end === undefined || Number.isNaN(start) || Number.isNaN(end)) return null;
    return [start - before, end + after];
  }

  function eventWindow(event, year, dates) {
    const w = eventWindowDays(event, year, dates);
    return w ? { start: fromDay(w[0]), end: fromDay(w[1]) } : null;
  }

  // The events whose window includes `today` (a Date, ISO string or day number).
  function activeEvents(today, options) {
    const o = options || {};
    const events = Array.isArray(o.events) ? o.events : DEFAULT_EVENTS;
    const day = asDay(today);
    if (day === null || day === undefined) return [];
    const found = [];
    events.forEach((event) => {
      const y = yearOf(day);
      for (const year of [y - 1, y, y + 1]) {
        const w = eventWindowDays(event, year, o.dates);
        if (w && w[0] <= day && day <= w[1]) {
          found.push(Object.assign({}, event, { year, start: fromDay(w[0]), end: fromDay(w[1]) }));
          break;
        }
      }
    });
    return found;
  }

  // Hub-safe slug: lowercase, hyphens (the hub rejects underscores).
  function badgeId(event, year) {
    const y = year === undefined || year === null ? event.year : year;
    return (String(event.id) + "-" + y).toLowerCase().replace(/[^a-z0-9-]+/g, "-").slice(0, 64);
  }
  function badgeLabel(event, flavour, year) {
    const y = year === undefined || year === null ? event.year : year;
    const base = (flavour && (flavour.badgeLabel || flavour.badge_label)) || (event.name + " " + y);
    return String(base).slice(0, 60);
  }

  function formatDay(iso) {
    const day = parseIso(iso);
    if (day === null) return "";
    const d = new Date(day * 86400000);
    return d.getUTCDate() + " " + MONTHS[d.getUTCMonth()];
  }

  function localDay(now) { return toDay(now.getFullYear(), now.getMonth() + 1, now.getDate()); }

  // Where "today" comes from: explicit option, ?event-date=, then the real local date.
  function resolveToday(todayOption) {
    let value = todayOption;
    if (typeof value === "function") { try { value = value(); } catch (e) { value = undefined; } }
    if (value !== undefined && value !== null) {
      const day = asDay(value);
      if (day !== null && day !== undefined) return { day, iso: fromDay(day), source: "option" };
    }
    try {
      const raw = new URLSearchParams(root.location && root.location.search || "").get("event-date");
      const day = raw ? parseIso(raw) : null;
      if (day !== null) return { day, iso: fromDay(day), source: "url" };
    } catch (e) { /* no URL */ }
    const day = localDay(new Date());
    return { day, iso: fromDay(day), source: "clock" };
  }

  // ---- badge storage (hub contract) ----------------------------------------

  function sanitizeBadges(list) {
    if (!Array.isArray(list)) return [];
    const seen = new Set();
    const out = [];
    list.forEach((b) => {
      if (!b || typeof b.id !== "string" || !/^[a-z0-9-]{1,64}$/.test(b.id) || seen.has(b.id)) return;
      if (typeof b.label !== "string" || !b.label.trim() || b.label.length > 60) return;
      if (b.earned_at !== undefined && (typeof b.earned_at !== "string" || b.earned_at.length > 32)) return;
      seen.add(b.id);
      out.push({ id: b.id, label: b.label.trim(), earned_at: b.earned_at || "" });
    });
    return out;
  }
  function readLocalBadges() {
    try {
      const parsed = JSON.parse(root.localStorage.getItem(BADGES_KEY) || "null");
      return parsed && parsed.version === 1 ? sanitizeBadges(parsed.badges) : [];
    } catch (e) { return []; }
  }
  function writeLocalBadges(list) {
    try { root.localStorage.setItem(BADGES_KEY, JSON.stringify({ version: 1, badges: list })); } catch (e) { /* convenience only */ }
  }

  // ---- styles --------------------------------------------------------------

  function ensureStylesheet() {
    if (typeof document === "undefined" || document.querySelector('link[href*="seasonal-events.css"]')) return;
    const own = document.currentScript || Array.from(document.scripts).find((s) => /seasonal-events\.js/.test(s.src || ""));
    if (!own || !own.src) return;
    const link = document.createElement("link");
    link.rel = "stylesheet";
    link.href = own.src.replace(/seasonal-events\.js(\?.*)?$/, "seasonal-events.css");
    document.head.append(link);
  }
  ensureStylesheet();
  const OWN_SCRIPT_SRC = typeof document !== "undefined" && document.currentScript ? document.currentScript.src : "";

  function loadDates(url) {
    const target = url || (OWN_SCRIPT_SRC ? OWN_SCRIPT_SRC.replace(/seasonal-events\.js(\?.*)?$/, "seasonal-dates.json") : "../../shared/seasonal-dates.json");
    return fetch(target, { cache: "no-cache" })
      .then((r) => (r.ok ? r.json() : null))
      .then((data) => { if (data && typeof data === "object") sharedDates = data; return sharedDates; })
      .catch(() => sharedDates);
  }
  function setDates(data) { sharedDates = data && typeof data === "object" ? data : null; }

  // ---- the controller ------------------------------------------------------

  function init(config) {
    const cfg = config || {};
    const game = cfg.game || "game";
    const hosted = cfg.events && typeof cfg.events === "object" && !Array.isArray(cfg.events) ? cfg.events : null;
    const calendar = Array.isArray(cfg.calendar) ? cfg.calendar : DEFAULT_EVENTS;
    const uid = "noyvj-se-" + (++counter);
    let dates = cfg.dates && typeof cfg.dates === "object" ? cfg.dates : null;
    let todayInfo = resolveToday(cfg.today);
    let badges = sanitizeBadges(cfg.badges);
    const useLocal = cfg.localBadges !== false;
    if (useLocal) {
      readLocalBadges().forEach((b) => { if (!badges.some((x) => x.id === b.id)) badges.push(b); });
    }
    const dismissKey = (id) => "seasonal-dismissed:" + game + ":" + id;
    const dismissedMemory = new Set();
    const banners = new Map();   // badge id -> element bundle
    let stack = null; let toastRegion = null; let destroyed = false;

    function isDismissed(id) {
      if (dismissedMemory.has(id)) return true;
      if (cfg.rememberDismiss === false) return false;
      try { return root.localStorage.getItem(dismissKey(id)) === "1"; } catch (e) { return false; }
    }

    function flavourFor(eventId) {
      const f = hosted && hosted[eventId] && typeof hosted[eventId] === "object" ? hosted[eventId] : {};
      return f;
    }

    function activeHosted() {
      return activeEvents(todayInfo.day, { events: calendar, dates: dates || undefined })
        .filter((e) => !hosted || Object.prototype.hasOwnProperty.call(hosted, e.id))
        .map((e) => {
          const flavour = flavourFor(e.id);
          return Object.assign({}, e, {
            badgeId: badgeId(e),
            badgeLabel: badgeLabel(e, flavour),
            flavour: Object.assign({ icon: DEFAULT_ICONS[e.id] || "★", name: e.name }, flavour),
          });
        });
    }

    function hasBadge(id) { return badges.some((b) => b.id === id); }

    function readProgress(event) {
      let value = null;
      if (typeof cfg.progress === "function") {
        try { value = cfg.progress(event.id, { event, badgeId: event.badgeId, today: todayInfo.iso, flavour: event.flavour }); } catch (e) { value = null; }
      }
      let count = null; let goal = Number.isFinite(event.flavour.goal) ? event.flavour.goal : null;
      if (typeof value === "number" && Number.isFinite(value)) count = value;
      else if (value && typeof value === "object") {
        if (Number.isFinite(value.count)) count = value.count;
        if (Number.isFinite(value.goal)) goal = value.goal;
      }
      let qualifies = false;
      if (typeof cfg.qualifies === "function") {
        try { qualifies = Boolean(cfg.qualifies(event.id, { event, badgeId: event.badgeId, today: todayInfo.iso, flavour: event.flavour })); } catch (e) { qualifies = false; }
      }
      if (!qualifies && count !== null && goal !== null && goal > 0 && count >= goal) qualifies = true;
      return { count, goal, qualifies };
    }

    function grantBadge(event) {
      if (hasBadge(event.badgeId)) return { granted: false, badge: badges.find((b) => b.id === event.badgeId) };
      const badge = { id: event.badgeId, label: event.badgeLabel, earned_at: todayInfo.iso };
      badges.push(badge);
      if (useLocal) {
        const merged = readLocalBadges();
        if (!merged.some((b) => b.id === badge.id)) merged.push(badge);
        writeLocalBadges(merged);
      }
      if (typeof cfg.onGrant === "function") { try { cfg.onGrant(Object.assign({}, badge), badges.map((b) => Object.assign({}, b))); } catch (e) { /* game callback */ } }
      toast("Badge earned: " + badge.label);
      return { granted: true, badge };
    }

    function ensureStack() {
      if (stack && stack.isConnected) return stack;
      const target = cfg.container ? (typeof cfg.container === "string" ? document.querySelector(cfg.container) : cfg.container) : null;
      stack = document.createElement("div");
      stack.className = "noyvj-se-stack" + (target ? " noyvj-se-stack--inline" : "");
      stack.id = uid;
      (target || document.body).append(stack);
      return stack;
    }

    function ensureToast() {
      if (toastRegion && toastRegion.isConnected) return toastRegion;
      toastRegion = document.createElement("div");
      toastRegion.className = "noyvj-se-toasts";
      toastRegion.setAttribute("role", "status");
      toastRegion.setAttribute("aria-live", "polite");
      document.body.append(toastRegion);
      return toastRegion;
    }

    function toast(text) {
      if (typeof document === "undefined") return;
      const region = ensureToast();
      const item = document.createElement("p");
      item.className = "noyvj-se-toast";
      item.textContent = "✓ " + text;
      region.append(item);
      setTimeout(() => item.remove(), cfg.toastMs || 7000);
    }

    function buildBanner(event) {
      const el = document.createElement("aside");
      el.className = "noyvj-se";
      el.dataset.event = event.id;
      el.setAttribute("role", "region");
      const icon = document.createElement("span");
      icon.className = "noyvj-se-icon";
      icon.setAttribute("aria-hidden", "true");
      const body = document.createElement("div");
      body.className = "noyvj-se-body";
      const title = document.createElement("p");
      title.className = "noyvj-se-title";
      const text = document.createElement("p");
      text.className = "noyvj-se-text";
      const task = document.createElement("p");
      task.className = "noyvj-se-task";
      const prog = document.createElement("p");
      prog.className = "noyvj-se-progress";
      const meter = document.createElement("progress");
      meter.className = "noyvj-se-meter";
      meter.setAttribute("aria-hidden", "true");
      const stateLine = document.createElement("p");
      stateLine.className = "noyvj-se-state";
      body.append(title, text, task, prog, meter, stateLine);
      const dismiss = document.createElement("button");
      dismiss.type = "button";
      dismiss.className = "noyvj-se-dismiss";
      dismiss.textContent = "Dismiss";
      dismiss.addEventListener("click", () => dismissEvent(event.badgeId));
      el.append(icon, body, dismiss);
      const bundle = { el, icon, title, text, task, prog, meter, stateLine, dismiss };
      banners.set(event.badgeId, bundle);
      ensureStack().append(el);
      return bundle;
    }

    function paintBanner(event, p) {
      const b = banners.get(event.badgeId) || buildBanner(event);
      const f = event.flavour;
      const earned = hasBadge(event.badgeId);
      b.el.setAttribute("aria-label", "Seasonal event: " + (f.title || f.name));
      b.el.dataset.state = earned ? "earned" : "open";
      b.icon.textContent = f.icon;
      b.title.textContent = (f.title || f.name) + (earned ? " — badge earned" : "");
      b.text.textContent = f.text || (f.name + " is on for a few days. A small task is open for a badge.");
      b.text.hidden = earned && !f.text;
      b.task.textContent = f.task ? "Task: " + f.task : "";
      b.task.hidden = !f.task || earned;
      const showProgress = !earned && p.count !== null;
      b.prog.hidden = !showProgress;
      b.meter.hidden = !(showProgress && p.goal);
      if (showProgress) {
        b.prog.textContent = "Progress: " + p.count + (p.goal ? " of " + p.goal : "") + (f.unit ? " " + f.unit + (p.goal === 1 ? "" : "s") : "");
        if (p.goal) { b.meter.max = p.goal; b.meter.value = Math.min(p.count, p.goal); }
      }
      b.stateLine.textContent = earned
        ? "✓ Badge earned: " + event.badgeLabel
        : "Open until " + formatDay(event.end) + " · badge: " + event.badgeLabel;
      b.el.hidden = isDismissed(event.badgeId);
    }

    function refresh() {
      if (destroyed || typeof document === "undefined") return [];
      const active = activeHosted();
      const live = new Set();
      const result = [];
      active.forEach((event) => {
        const p = readProgress(event);
        if (p.qualifies && cfg.autoGrant !== false) grantBadge(event);
        live.add(event.badgeId);
        if (cfg.banner !== false) paintBanner(event, p);
        result.push({ id: event.id, badgeId: event.badgeId, name: event.name, start: event.start, end: event.end, year: event.year, earned: hasBadge(event.badgeId), progress: { count: p.count, goal: p.goal } });
      });
      banners.forEach((b, id) => { if (!live.has(id)) { b.el.remove(); banners.delete(id); } });
      if (stack && !cfg.container) {
        const wn = document.getElementById("whats-new-banner");
        stack.style.top = wn && !wn.hidden ? Math.max(0, Math.round(wn.getBoundingClientRect().bottom)) + "px" : "";
      }
      reserveSpace();
      return result;
    }

    // The default strip is fixed, so it would sit on top of the game's own header;
    // push the page down by its height (html padding, which every body layout
    // respects) and give the space back when no banner is showing.
    function reserveSpace() {
      if (cfg.container || cfg.reserveSpace === false || typeof document === "undefined") return;
      const html = document.documentElement;
      const showing = stack && Array.from(stack.children).some((c) => !c.hidden);
      if (!showing || destroyed) {
        html.classList.remove("noyvj-se-reserve");
        html.style.removeProperty("--se-reserve");
        return;
      }
      html.style.setProperty("--se-reserve", Math.ceil(stack.getBoundingClientRect().bottom) + "px");
      html.classList.add("noyvj-se-reserve");
    }
    if (typeof root.addEventListener === "function") root.addEventListener("resize", reserveSpace);

    function dismissEvent(id) {
      dismissedMemory.add(id);
      if (cfg.rememberDismiss !== false) { try { root.localStorage.setItem(dismissKey(id), "1"); } catch (e) { /* convenience only */ } }
      const b = banners.get(id);
      if (b) b.el.hidden = true;
      reserveSpace();
      if (typeof cfg.onDismiss === "function") { try { cfg.onDismiss(id); } catch (e) { /* game callback */ } }
    }

    const api = {
      refresh,
      active: () => activeHosted().map((e) => ({ id: e.id, badgeId: e.badgeId, name: e.name, start: e.start, end: e.end, year: e.year, earned: hasBadge(e.badgeId) })),
      today: () => todayInfo.iso,
      todaySource: () => todayInfo.source,
      setToday(value) { todayInfo = resolveToday(value); return refresh(); },
      setDates(data) { dates = data && typeof data === "object" ? data : null; return refresh(); },
      grant(eventId) {
        const event = activeHosted().find((e) => e.id === eventId);
        if (!event) return { granted: false, badge: null, reason: "not-active" };
        const out = grantBadge(event);
        refresh();
        return out;
      },
      badges: () => badges.map((b) => Object.assign({}, b)),
      hasBadge,
      // Merge badges read from a save (e.g. save_data.event_badges) into this device's list.
      adoptBadges(list) {
        sanitizeBadges(list).forEach((b) => { if (!hasBadge(b.id)) badges.push(b); });
        if (useLocal) {
          const merged = readLocalBadges();
          badges.forEach((b) => { if (!merged.some((m) => m.id === b.id)) merged.push(b); });
          writeLocalBadges(merged);
        }
        return refresh();
      },
      dismiss: dismissEvent,
      destroy() {
        destroyed = true;
        if (stack) stack.remove();
        if (toastRegion) toastRegion.remove();
        banners.clear();
        reserveSpace();
        if (typeof root.removeEventListener === "function") root.removeEventListener("resize", reserveSpace);
      },
    };

    if (!dates && !sharedDates && cfg.datesUrl !== false && typeof fetch === "function" && typeof document !== "undefined") {
      // Moving-holiday tables arrive asynchronously; refresh once they do.
      loadDates(typeof cfg.datesUrl === "string" ? cfg.datesUrl : undefined).then(() => refresh());
    }
    if (typeof document !== "undefined") {
      if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", () => refresh());
      else refresh();
    }
    return api;
  }

  root.NoyvjSeasonal = {
    DEFAULT_EVENTS, DEFAULT_ICONS, init, loadDates, setDates,
    easterSunday: (y) => fromDay(easterSunday(y)),
    nthWeekday: (y, m, wd, n) => fromDay(nthWeekday(y, m, wd, n)),
    eventWindow, activeEvents, badgeId, badgeLabel, resolveToday, sanitizeBadges,
    badgeEntry: (event, earnedAt, flavour) => ({ id: badgeId(event), label: badgeLabel(event, flavour), earned_at: earnedAt || "" }),
  };
})(typeof window !== "undefined" ? window : globalThis);
