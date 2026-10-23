/*
 * Shared "next up" achievement chip (planning/TODO.md H-24): one small line that shows the closest achievement the player
 * has not earned yet and how far along it is, e.g. "Next up: Ten Lit, 3 of 10". It never decides anything about a game:
 * the game hands it the achievement list it already has, and the chip only picks one and draws it.
 *
 *   <link rel="stylesheet" href="../../shared/next-achievement.css">   (optional: the script links it itself)
 *   <script src="../../shared/next-achievement.js"></script>
 *   <div id="next-up-chip"></div>
 *
 *   // after every redraw (the newer games already have this list in their view):
 *   if (window.NoyvjNextUp) window.NoyvjNextUp.show("#next-up-chip", view.achievements);
 *
 * The list: an array of {id, label (or name or title), description?, earned?, have?, need?, hidden?, locked?}. An entry is
 * left out when it is earned (earned true, or have >= need), hidden (never spoil a secret) or locked (locked true or
 * available false). The closest one is the highest have/need; a tie goes to the fewest still needed, then to the list
 * order (the game's own order). An entry without numbers counts as 0 progress, so with no progress anywhere the first
 * unearned one in the game's order is shown. The count ("3 of 10") and the bar appear only when need is more than 1.
 *
 *   NoyvjNextUp.show(target, list, opts)  -> the chip handle (mounts on first use, then only updates; a selector or element)
 *   NoyvjNextUp.mount(target, opts)       -> {update(list), entry(), element, destroy()}
 *       opts: {title: "Next up", opens: "#achievements-toggle-button" (the chip becomes a button that clicks it),
 *              doneText: "Every achievement earned."}
 *   NoyvjNextUp.pick(list)                -> the chosen entry {id, label, description, have, need} or null
 *   NoyvjNextUp.text(entry, title)        -> "Next up: Ten Lit, 3 of 10" (plain text, the same words the chip shows)
 *
 * The chip is hidden while the list is missing or empty, says doneText when every entry is earned (hidden ones too), and
 * fires document event "noyvj-nextup-change" ({id, previous}) when the chosen achievement changes. Text is written with
 * textContent only; the DOM is touched only when what it shows changes; no timers, no storage, no network.
 * See planning/SHARED-COMPONENTS.md ("Next-up achievement chip").
 */
(function () {
  "use strict";
  if (window.NoyvjNextUp) return;

  var CSS_FILE = "next-achievement.css";
  var DEFAULT_TITLE = "Next up";
  var DEFAULT_DONE = "Every achievement earned.";
  var mounts = [];

  function ensureStylesheet() {
    if (typeof document === "undefined" || document.querySelector('link[href*="' + CSS_FILE + '"]')) return;
    var own = document.currentScript || Array.prototype.slice.call(document.scripts).filter(function (s) {
      return /next-achievement\.js/.test(s.src || "");
    })[0];
    if (!own || !own.src) return;
    var link = document.createElement("link");
    link.rel = "stylesheet";
    link.href = own.src.replace(/next-achievement\.js(\?.*)?$/, CSS_FILE);
    document.head.appendChild(link);
  }
  ensureStylesheet();

  function num(value) {
    var n = typeof value === "string" && value.trim() !== "" ? Number(value) : value;
    return typeof n === "number" && isFinite(n) ? n : null;
  }

  function str(value) {
    return typeof value === "string" ? value.replace(/\s+/g, " ").trim() : (typeof value === "number" ? String(value) : "");
  }

  // One entry in a plain shape, or null when it cannot be shown at all.
  function normalise(raw) {
    if (!raw || typeof raw !== "object") return null;
    var id = str(raw.id);
    var label = str(raw.label) || str(raw.name) || str(raw.title) || id;
    if (!label) return null;
    var need = num(raw.need);
    var have = num(raw.have);
    if (need !== null && need <= 0) need = null;
    if (need === null) have = null;
    else have = Math.max(0, Math.min(have === null ? 0 : have, need));
    var earned = raw.earned === true || (need !== null && have >= need);
    return {
      id: id, label: label, description: str(raw.description), have: have, need: need, earned: earned,
      hidden: raw.hidden === true, locked: raw.locked === true || raw.available === false,
    };
  }

  function candidates(list) {
    var out = [];
    (Array.isArray(list) ? list : []).forEach(function (raw, index) {
      var e = normalise(raw);
      if (e && !e.earned && !e.hidden && !e.locked) { e.index = index; out.push(e); }
    });
    return out;
  }

  function pick(list) {
    var open = candidates(list);
    if (!open.length) return null;
    open.sort(function (a, b) {
      var ra = a.need ? a.have / a.need : 0;
      var rb = b.need ? b.have / b.need : 0;
      if (ra !== rb) return rb - ra;
      var la = a.need ? a.need - a.have : Infinity;
      var lb = b.need ? b.need - b.have : Infinity;
      if (la !== lb) return la < lb ? -1 : 1;
      return a.index - b.index;
    });
    var best = open[0];
    return { id: best.id, label: best.label, description: best.description, have: best.have, need: best.need };
  }

  function countText(entry) {
    return entry && entry.need > 1 ? entry.have + " of " + entry.need : "";
  }

  function text(entry, title) {
    if (!entry) return "";
    var count = countText(entry);
    return (title || DEFAULT_TITLE) + ": " + entry.label + (count ? ", " + count : "");
  }

  function resolve(target) {
    if (typeof target === "string") return document.querySelector(target);
    return target && target.nodeType === 1 ? target : null;
  }

  function el(tag, cls) {
    var node = document.createElement(tag);
    if (cls) node.className = cls;
    return node;
  }

  function mount(target, opts) {
    var host = resolve(target);
    if (!host) return null;
    for (var i = 0; i < mounts.length; i++) if (mounts[i].host === host) return mounts[i].api;
    opts = opts || {};
    var title = str(opts.title) || DEFAULT_TITLE;
    var doneText = str(opts.doneText) || DEFAULT_DONE;
    var opens = opts.opens || null;

    var root = el(opens ? "button" : "div", "noyvj-nextup");
    if (opens) {
      root.type = "button";
      root.addEventListener("click", function () {
        var other = resolve(opens);
        if (other && typeof other.click === "function") other.click();
      });
    }
    var label = el("span", "noyvj-nextup-title");
    var name = el("span", "noyvj-nextup-name");
    var count = el("span", "noyvj-nextup-count");
    var bar = el("progress", "noyvj-nextup-bar");
    var desc = el("span", "noyvj-nextup-desc");
    root.appendChild(label);
    root.appendChild(name);
    root.appendChild(count);
    root.appendChild(bar);
    root.appendChild(desc);
    root.hidden = true;
    host.appendChild(root);

    var shownSig = null;
    var shownId = null;
    var current = null;

    function update(list) {
      var entries = Array.isArray(list) ? list : [];
      current = pick(entries);
      var state = current ? "next" : (entries.length ? "done" : "empty");
      var sig = JSON.stringify([state, current]);
      if (sig === shownSig) return api;
      shownSig = sig;
      root.hidden = state === "empty";
      root.setAttribute("data-state", state);
      if (current) {
        root.setAttribute("data-achievement-id", current.id);
        label.textContent = title + ":";
        name.textContent = current.label;
        count.textContent = countText(current);
        count.hidden = !count.textContent;
        bar.hidden = !(current.need > 1);
        bar.max = current.need || 1;
        bar.value = current.have || 0;
        bar.setAttribute("aria-label", current.label + ": " + (countText(current) || "not yet"));
        desc.textContent = current.description;
        desc.hidden = !current.description;
        if (opens) root.setAttribute("aria-label", text(current, title) + ". Open the achievements.");
      } else {
        root.removeAttribute("data-achievement-id");
        label.textContent = state === "done" ? "" : title + ":";
        name.textContent = state === "done" ? doneText : "";
        count.textContent = "";
        count.hidden = true;
        bar.hidden = true;
        desc.textContent = "";
        desc.hidden = true;
        if (opens) root.setAttribute("aria-label", (state === "done" ? doneText : title) + " Open the achievements.");
      }
      label.hidden = !label.textContent;
      var id = current ? current.id : null;
      if (id !== shownId) {
        var previous = shownId;
        shownId = id;
        try {
          document.dispatchEvent(new CustomEvent("noyvj-nextup-change", { detail: { id: id, previous: previous } }));
        } catch (e) { /* an old browser without CustomEvent: the chip still draws */ }
      }
      return api;
    }

    function destroy() {
      if (root.parentNode) root.parentNode.removeChild(root);
      mounts = mounts.filter(function (m) { return m.host !== host; });
    }

    var api = { update: update, entry: function () { return current; }, element: root, destroy: destroy };
    mounts.push({ host: host, api: api });
    return api;
  }

  function show(target, list, opts) {
    var handle = mount(target, opts);
    if (handle) handle.update(list);
    return handle;
  }

  window.NoyvjNextUp = { show: show, mount: mount, pick: pick, text: text };
})();
