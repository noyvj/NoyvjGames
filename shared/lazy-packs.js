/*
 * Shared lazy content-pack loader (planning/TODO.md LZ-2 and LZ-3). A game boots with only its core; a level,
 * chapter, scenario or mode "loads in" the first time the player opens it, behind a small loading card, and
 * works offline once it has been downloaded. This file is the whole loader: no build step, no dependencies,
 * no timers, no backend.
 *
 *   <link rel="stylesheet" href="../../shared/lazy-packs.css">   (optional: the script links it itself)
 *   <script src="../../shared/lazy-packs.js" data-game-id="canopy" data-manifest="modules.json"></script>
 *
 * A game lists its optional packs in games/<slug>/modules.json:
 *   { "version": 1, "game": "canopy", "packs": [
 *       { "id": "wetland", "label": "Wetland Forest", "kind": "python", "url": "packs/wetland.py",
 *         "bytes": 24300, "modes": "Wetland Forest level", "needs": ["highland"], "exec": true } ] }
 *   id      lower-case letters, digits, "-" or "_" (1 to 48), unique on the page
 *   label   what the loading card says ("Loading Wetland Forest (about 24 KB)...")
 *   kind    "python" | "json" | "script" | "css"
 *   url     where the file is, relative to the PAGE (the game folder; "../../shared/x.js" is fine). Same origin only.
 *   bytes   approximate size in bytes, shown on the card and used for the cap (not an integrity check)
 *   length  optional EXACT decoded byte length; when present a different length is refused ("integrity by length")
 *   modes   text (or a list of texts) naming the modes/levels that need the pack: documentation for people, shown nowhere else
 *   needs   list of pack ids that must be loaded first (loaded automatically, in order). A plain text note is ignored.
 *   exec    python only: also run the source in Pyodide's main namespace (for a piece cut out of a monolithic game.py).
 *           Without it the file is only written into Pyodide's file system, ready for `import`.
 *   path    python only: file name inside Pyodide's file system (default: the file name of url)
 *
 * Python games call it through shared/lazy_packs.py (await lazy_packs.require("id")); see that file's header for the pattern.
 *
 * What a pack kind does on load (each is fetched ONCE, however many times it is asked for):
 *   python  pyodide.FS.writeFile(path, text); importlib.invalidate_caches(); optional exec; resolves with the source text
 *   json    resolves with the parsed object (kept in memory: loading again returns the same object, no second fetch)
 *   script  inserted once as an inline <script data-noyvj-pack="id"> (the exact bytes that passed the checks); resolves with the element
 *   css     inserted once as a <style data-noyvj-pack="id">; resolves with the element. Keep url(...) out of pack CSS
 *           (an inline style resolves relative urls against the page, not the css file).
 *
 * window.NoyvjPacks
 *   register(config)  config: { game, packs: [...] and/or manifest: "modules.json", baseUrl, onLoaded(id, text, pack),
 *                     maxBytes (default 6 MB), ui (default true), getPyodide() }. Packs given inline are known at once;
 *                     returns a promise that settles once a manifest (if any) has been read. Never rejects.
 *   ready()           the promise of the latest register()
 *   has(id)           true once the pack finished loading on THIS page
 *   known(id)         true if the id is registered
 *   load(id, { onProgress, ui, onLoaded })  -> promise (see "what a pack kind does"). Loading twice at once or twice in a
 *                     row is harmless and does one fetch. Rejections are Errors with .code, .packId and a plain-words message.
 *   requires(ids, { onProgress, ui, soft })  -> promise: loads every id not loaded yet, one after another. For a load_state
 *                     flow: `await NoyvjPacks.requires(save.packs_used)` before restoring. With soft:true it never rejects and
 *                     resolves { loaded: [ids], failed: [{ id, code, message }] } so a game can keep the save and show a notice.
 *   requiresSoft(ids, opts)  same as requires(ids, {soft: true}): what Python code (shared/lazy_packs.py) calls
 *   missing(ids)      the ids (of those asked) that are NOT loaded yet, unknown ones included
 *   unknown(ids)      the ids that are not registered at all (a save from a newer or older game version)
 *   used()            ids loaded on this page, in load order: store it in the game's own state as `packs_used`
 *   info(id), list()  { id, label, kind, bytes, modes, needs, state: "idle"|"loading"|"loaded", loaded }
 *   downloaded(game)  [{ id, bytes, at }] recorded in localStorage["packs:<game>"] (default: this page's game);
 *                     downloadedAll() -> { <game>: [...] } for every game on this device. A record is a note that the pack
 *                     was fetched here, not proof it is still in Cache Storage (the hub offline page checks that).
 *   clearRecord(game, id?)  forget one pack's record or the game's whole record (the hub's Remove button)
 *   problems          manifest entries that were skipped, as text, for tests and the console
 * Events on document: "noyvj-pack-loaded" {game, id, bytes}, "noyvj-pack-failed" {game, id, code}.
 *
 * The loading card: one role="status" box at the bottom of the page. Each pack shows "Loading <label> (about N KB)...",
 * a progress bar when the size is known and a percentage, never a spinner alone. On failure the same row says what went
 * wrong in plain words and offers "Try again" (the load promise simply stays pending and resumes) and "Not now" (the
 * promise rejects). ui:false loads silently and rejects at once. Text is written with textContent only. There is no
 * animation, so reduced motion needs no special case.
 *
 * Offline: the fetch goes through the service worker, which already keeps every same-origin GET it sees in
 * site-cache-v<N> and answers from there when the network is gone. Without a worker (or a worker that does not control
 * the page yet) the loader also looks in Cache Storage itself when the network fails, and, when no worker controls the
 * page, stores a fresh pack in the newest site-cache-v<N> so it is there next time.
 */
(function () {
  "use strict";
  if (window.NoyvjPacks) return;

  const VERSION = 1;
  const CSS_FILE = "lazy-packs.css";
  const KINDS = ["python", "json", "script", "css"];
  const ID_RE = /^[a-z0-9][a-z0-9_-]{0,47}$/;
  const DEFAULT_MAX_BYTES = 6 * 1024 * 1024;
  const LIVE_CACHE_RE = /^site-cache-v(\d+)$/;
  const NOT_RETRYABLE = { unknown: 1, "too-big": 1, "bad-url": 1, dependency: 1 };

  const packs = new Map();          // id -> pack record
  const order = [];                 // ids in the order they finished loading
  const problems = [];
  let readyPromise = Promise.resolve({ game: null, ids: [] });
  let currentGame = null;
  let card = null;                  // { root } created on first use
  let manifestPending = false;      // a modules.json is being read: load() of a not-yet-known id waits for it

  const ownScript = document.currentScript || Array.from(document.scripts).find((s) => /lazy-packs\.js/.test(s.src || ""));

  // ---- small helpers ------------------------------------------------------------------------------

  function lsGet(k) { try { return localStorage.getItem(k); } catch (e) { return null; } }
  function lsSet(k, v) { try { localStorage.setItem(k, v); } catch (e) { /* convenience only */ } }

  function ensureCss() {
    if (document.querySelector('link[href*="' + CSS_FILE + '"]')) return;
    if (!ownScript || !ownScript.src) return;
    const link = document.createElement("link");
    link.rel = "stylesheet";
    link.href = ownScript.src.replace(/lazy-packs\.js(\?.*)?$/, CSS_FILE);
    (document.head || document.documentElement).appendChild(link);
  }

  function gameFromLocation() {
    const m = /\/games\/([a-z0-9-]+)\//.exec(location.pathname);
    return m ? m[1] : null;
  }

  function sizeText(bytes) {
    if (!(bytes > 0)) return "";
    if (bytes >= 1024 * 1024 * 0.95) return (bytes / (1024 * 1024)).toFixed(1) + " MB";
    return Math.max(1, Math.round(bytes / 1024)) + " KB";
  }

  function makeError(code, pack, extra) {
    const label = pack ? pack.label : "This content";
    let message;
    switch (code) {
      case "offline": message = "You are offline, and " + label + " has not been downloaded on this device yet. Connect to the internet once to load it."; break;
      case "network": message = label + " could not be loaded. Check your connection and try again."; break;
      case "http": message = (extra && extra.status === 404)
        ? label + " was not found on the server (404). If the site was just updated, reload the page."
        : label + " could not be loaded (the server answered " + (extra && extra.status) + "). Try again in a moment."; break;
      case "too-big": message = label + " is larger than this page allows" + (extra && extra.size ? " (" + extra.size + ")" : "") + ", so it was not loaded."; break;
      case "length": case "empty": case "parse": message = label + " arrived damaged or incomplete. Try again."; break;
      case "no-runtime": message = "The game engine is not ready yet, so " + label + " cannot start. Wait a moment and try again."; break;
      case "import": message = label + " downloaded but could not start. Reload the page and try again."; break;
      case "bad-url": message = label + " has an address this page does not accept."; break;
      case "unknown": message = "This game has no content pack called \"" + (extra && extra.id) + "\"."; break;
      case "dependency": message = label + " needs another pack that could not be loaded first."; break;
      default: message = label + " could not be loaded.";
    }
    const err = new Error(message);
    err.code = code;
    err.packId = pack ? pack.id : (extra && extra.id) || null;
    if (extra && extra.status) err.status = extra.status;
    return err;
  }

  function safeCall(fn, arg) { try { fn(arg); } catch (e) { /* a listener's bug must not break loading */ } }

  // ---- registration -------------------------------------------------------------------------------

  function cleanPack(raw, cfg) {
    if (!raw || typeof raw !== "object") { problems.push("a pack entry is not an object"); return null; }
    if (typeof raw.id !== "string" || !ID_RE.test(raw.id)) { problems.push("bad pack id: " + String(raw.id).slice(0, 60)); return null; }
    if (KINDS.indexOf(raw.kind) < 0) { problems.push(raw.id + ": unknown kind " + String(raw.kind).slice(0, 20)); return null; }
    if (typeof raw.url !== "string" || !raw.url || raw.url.length > 300) { problems.push(raw.id + ": missing url"); return null; }
    const modes = Array.isArray(raw.modes) ? raw.modes.map(String).join(", ") : (typeof raw.modes === "string" ? raw.modes : "");
    return {
      id: raw.id,
      label: typeof raw.label === "string" && raw.label.trim() ? raw.label.trim().slice(0, 80) : raw.id,
      kind: raw.kind,
      url: raw.url,
      bytes: Number.isFinite(raw.bytes) && raw.bytes >= 0 ? raw.bytes : 0,
      length: Number.isInteger(raw.length) && raw.length >= 0 ? raw.length : null,
      modes: modes.slice(0, 300),
      needs: Array.isArray(raw.needs) ? raw.needs.filter((n) => typeof n === "string" && ID_RE.test(n)) : [],
      exec: raw.exec === true,
      path: typeof raw.path === "string" && raw.path ? raw.path.slice(0, 120) : null,
      state: "idle",
      session: null,
      result: undefined,
      cfg: cfg,
    };
  }

  function addPacks(list, cfg) {
    const ids = [];
    (Array.isArray(list) ? list : []).forEach((raw) => {
      const pack = cleanPack(raw, cfg);
      if (!pack) return;
      const have = packs.get(pack.id);
      if (have && (have.state === "loaded" || have.state === "loading")) { ids.push(pack.id); return; }
      packs.set(pack.id, pack);
      ids.push(pack.id);
    });
    return ids;
  }

  function register(config) {
    const cfg = Object.assign({ game: null, ui: true, maxBytes: DEFAULT_MAX_BYTES, baseUrl: null, onLoaded: null, getPyodide: null }, config || {});
    cfg.game = (typeof cfg.game === "string" && /^[a-z0-9-]{1,40}$/.test(cfg.game)) ? cfg.game : (currentGame || gameFromLocation());
    if (cfg.game) currentGame = cfg.game;
    if (!(cfg.maxBytes > 0)) cfg.maxBytes = DEFAULT_MAX_BYTES;
    ensureCss();
    let ids = addPacks(cfg.packs, cfg);
    if (typeof cfg.manifest === "string" && cfg.manifest) {
      manifestPending = true;
      readyPromise = readManifest(cfg).then((list) => {
        ids = ids.concat(addPacks(list, cfg));
        manifestPending = false;
        return { game: cfg.game, ids: ids };
      }, () => { manifestPending = false; return { game: cfg.game, ids: ids }; });
    } else {
      readyPromise = Promise.resolve({ game: cfg.game, ids: ids });
    }
    return readyPromise;
  }

  async function readManifest(cfg) {
    const url = new URL(cfg.manifest, cfg.baseUrl || document.baseURI).href;
    let response = null;
    try { response = await fetch(url, { cache: "no-cache", credentials: "same-origin" }); } catch (e) { response = await cachedResponse(url); }
    if (!response || !response.ok) { problems.push("modules.json not read"); return []; }
    let data = null;
    try { data = await response.json(); } catch (e) { problems.push("modules.json is not valid JSON"); return []; }
    if (data && !cfg.game && typeof data.game === "string" && /^[a-z0-9-]{1,40}$/.test(data.game)) {
      cfg.game = data.game;
      currentGame = data.game;
    }
    return data && Array.isArray(data.packs) ? data.packs : (Array.isArray(data) ? data : []);
  }

  // ---- fetching -----------------------------------------------------------------------------------

  async function cachedResponse(url) {
    try {
      if (typeof caches === "undefined" || typeof caches.match !== "function") return null;
      return (await caches.match(url)) || null;
    } catch (e) { return null; }
  }

  async function liveCacheName() {
    try {
      const names = await caches.keys();
      let best = null;
      names.forEach((n) => {
        const m = LIVE_CACHE_RE.exec(n);
        if (m && (!best || Number(m[1]) > best.v)) best = { name: n, v: Number(m[1]) };
      });
      return best ? best.name : null;
    } catch (e) { return null; }
  }

  async function cachePut(url, response) {
    try {
      if (typeof caches === "undefined") return;
      if (navigator.serviceWorker && navigator.serviceWorker.controller) return;   // the worker caches it by itself
      const name = await liveCacheName();
      if (!name) return;
      const cache = await caches.open(name);
      await cache.put(url, response);
    } catch (e) { /* best effort */ }
  }

  function absoluteUrl(pack) {
    let url;
    try { url = new URL(pack.url, pack.cfg.baseUrl || document.baseURI); } catch (e) { throw makeError("bad-url", pack); }
    if (url.origin !== location.origin || !/^https?:$/.test(url.protocol)) throw makeError("bad-url", pack);
    return url.href;
  }

  async function readBody(response, cap, onBytes, pack) {
    const reader = response.body && response.body.getReader ? response.body.getReader() : null;
    if (!reader) {
      const buf = new Uint8Array(await response.arrayBuffer());
      if (buf.length > cap) throw makeError("too-big", pack, { size: sizeText(buf.length) });
      onBytes(buf.length);
      return buf;
    }
    const chunks = [];
    let total = 0;
    for (;;) {
      const step = await reader.read();
      if (step.done) break;
      total += step.value.length;
      if (total > cap) {
        try { await reader.cancel(); } catch (e) { /* already closed */ }
        throw makeError("too-big", pack, { size: sizeText(total) });
      }
      chunks.push(step.value);
      onBytes(total);
    }
    const out = new Uint8Array(total);
    let at = 0;
    chunks.forEach((c) => { out.set(c, at); at += c.length; });
    return out;
  }

  async function fetchPack(pack, sess) {
    const cfg = pack.cfg;
    const cap = cfg.maxBytes;
    if (pack.bytes > cap) throw makeError("too-big", pack, { size: sizeText(pack.bytes) });
    const url = absoluteUrl(pack);
    let response = null;
    let fromCache = false;
    try {
      response = await fetch(url, { cache: "no-cache", credentials: "same-origin" });
    } catch (e) {
      response = await cachedResponse(url);
      if (!response) throw makeError(navigator.onLine === false ? "offline" : "network", pack);
      fromCache = true;
    }
    if (!response.ok && response.status >= 500) {
      const held = await cachedResponse(url);
      if (held) { response = held; fromCache = true; }
    }
    if (!response.ok) throw makeError("http", pack, { status: response.status });

    const header = Number(response.headers.get("content-length"));
    if (header > cap) {
      try { if (response.body) await response.body.cancel(); } catch (e) { /* ignore */ }
      throw makeError("too-big", pack, { size: sizeText(header) });
    }
    const encoded = Boolean(response.headers.get("content-encoding"));
    const toCache = !fromCache && typeof caches !== "undefined" ? response.clone() : null;
    const total = header > 0 ? header : (pack.bytes > 0 ? pack.bytes : null);
    const bytes = await readBody(response, cap, (n) => sess.progress("fetch", n, total), pack);

    if (bytes.length === 0) throw makeError("empty", pack);
    if (!encoded && header > 0 && bytes.length !== header) throw makeError("length", pack);
    if (pack.length !== null && bytes.length !== pack.length) throw makeError("length", pack);
    // A listed size that is wildly smaller than what arrived means the list is stale or the file is wrong.
    if (pack.bytes > 0 && bytes.length > pack.bytes * 3 + 32768) throw makeError("too-big", pack, { size: sizeText(bytes.length) });
    if (toCache) cachePut(url, toCache);
    return { text: new TextDecoder("utf-8").decode(bytes), size: bytes.length, url: url };
  }

  // ---- installing each kind -----------------------------------------------------------------------

  function fileName(pack) {
    if (pack.path) return pack.path;
    return pack.url.split("?")[0].split("#")[0].split("/").pop();
  }

  async function install(pack, got, extraOnLoaded) {
    const cfg = pack.cfg;
    if (pack.kind === "json") {
      try { return JSON.parse(got.text); } catch (e) { throw makeError("parse", pack); }
    }
    if (pack.kind === "script" || pack.kind === "css") {
      const have = document.querySelector('[data-noyvj-pack="' + pack.id + '"]');
      if (have) return have;
      const el = document.createElement(pack.kind === "script" ? "script" : "style");
      el.setAttribute("data-noyvj-pack", pack.id);
      el.textContent = pack.kind === "script" ? got.text + "\n//# sourceURL=" + got.url : got.text;
      try { (pack.kind === "script" ? document.body || document.documentElement : document.head || document.documentElement).appendChild(el); }
      catch (e) { throw makeError("import", pack); }
      return el;
    }
    // python
    const py = (typeof cfg.getPyodide === "function" ? cfg.getPyodide() : null) || window.pyodide;
    if (!py || !py.FS || typeof py.FS.writeFile !== "function") throw makeError("no-runtime", pack);
    const name = fileName(pack);
    try {
      const slash = name.lastIndexOf("/");
      if (slash > 0 && typeof py.FS.mkdirTree === "function") py.FS.mkdirTree(name.slice(0, slash));
      py.FS.writeFile(name, got.text, { encoding: "utf8" });
      if (typeof py.runPython === "function") {
        try { py.runPython("import importlib\nimportlib.invalidate_caches()"); } catch (e) { /* nothing cached yet */ }
      }
      if (pack.exec) {
        if (typeof py.runPythonAsync === "function") await py.runPythonAsync(got.text);
        else if (typeof py.runPython === "function") py.runPython(got.text);
      }
      if (typeof cfg.onLoaded === "function") await cfg.onLoaded(pack.id, got.text, info(pack));
      if (typeof extraOnLoaded === "function") await extraOnLoaded(pack.id, got.text, info(pack));
    } catch (e) {
      if (e && e.code) throw e;
      throw makeError("import", pack);
    }
    return got.text;
  }

  // ---- the loading card ---------------------------------------------------------------------------

  function ensureCard() {
    if (card && card.root.isConnected) return card;
    const root = document.createElement("div");
    root.className = "noyvj-pack-card";
    root.id = "noyvj-pack-card";
    root.setAttribute("role", "status");
    root.setAttribute("aria-live", "polite");
    root.setAttribute("data-testid", "pack-card");
    root.hidden = true;
    (document.body || document.documentElement).appendChild(root);
    card = { root: root };
    return card;
  }

  function makeRow(pack) {
    const c = ensureCard();
    const row = document.createElement("div");
    row.className = "noyvj-pack-row";
    row.setAttribute("data-pack", pack.id);
    const text = document.createElement("p");
    text.className = "noyvj-pack-text";
    const size = sizeText(pack.bytes);
    text.textContent = "Loading " + pack.label + (size ? " (about " + size + ")" : "") + "…";
    const meter = document.createElement("div");
    meter.className = "noyvj-pack-meter";
    const bar = document.createElement("progress");
    bar.className = "noyvj-pack-bar";
    bar.max = 100;
    bar.value = 0;
    bar.hidden = !(pack.bytes > 0);
    bar.setAttribute("aria-label", pack.label + " download progress");
    const pct = document.createElement("span");
    pct.className = "noyvj-pack-pct";
    pct.setAttribute("aria-hidden", "true");
    pct.hidden = bar.hidden;
    pct.textContent = "0%";
    meter.hidden = bar.hidden;
    meter.appendChild(bar);
    meter.appendChild(pct);
    const actions = document.createElement("div");
    actions.className = "noyvj-pack-actions";
    actions.hidden = true;
    row.appendChild(text);
    row.appendChild(meter);
    row.appendChild(actions);
    c.root.appendChild(row);
    c.root.hidden = false;
    return { row: row, text: text, bar: bar, pct: pct, meter: meter, actions: actions, label: pack.label, size: size, previousFocus: null };
  }

  function rowLoading(view) {
    view.row.classList.remove("noyvj-pack-failed");
    view.text.textContent = "Loading " + view.label + (view.size ? " (about " + view.size + ")" : "") + "…";
    view.meter.hidden = view.bar.hidden;
    view.actions.hidden = true;
    while (view.actions.firstChild) view.actions.removeChild(view.actions.firstChild);
  }

  function rowProgress(view, fraction) {
    if (fraction === null) return;
    const pct = Math.max(0, Math.min(100, Math.round(fraction * 100)));
    view.bar.hidden = false;
    view.pct.hidden = false;
    view.meter.hidden = false;
    view.bar.value = pct;
    view.pct.textContent = pct + "%";
  }

  function rowFailed(view, err, retryable) {
    view.row.classList.add("noyvj-pack-failed");
    view.text.textContent = err.message;
    view.meter.hidden = true;
    view.actions.hidden = false;
    while (view.actions.firstChild) view.actions.removeChild(view.actions.firstChild);
    return new Promise((resolve) => {
      let first = null;
      if (retryable) {
        const retry = document.createElement("button");
        retry.type = "button";
        retry.className = "noyvj-pack-retry";
        retry.textContent = "Try again";
        retry.addEventListener("click", () => resolve("retry"));
        view.actions.appendChild(retry);
        first = retry;
      }
      const close = document.createElement("button");
      close.type = "button";
      close.className = "noyvj-pack-close";
      close.textContent = retryable ? "Not now" : "Close";
      close.addEventListener("click", () => resolve("cancel"));
      view.actions.appendChild(close);
      if (!first) first = close;
      view.previousFocus = document.activeElement && document.activeElement !== document.body ? document.activeElement : null;
      try { first.focus(); } catch (e) { /* not focusable yet */ }
    });
  }

  function dropRow(view) {
    const prev = view.previousFocus;
    if (view.row.parentNode) view.row.parentNode.removeChild(view.row);
    if (card && !card.root.querySelector(".noyvj-pack-row")) card.root.hidden = true;
    if (prev && prev.isConnected && typeof prev.focus === "function") { try { prev.focus(); } catch (e) { /* gone */ } }
  }

  // ---- sessions (one per pack being loaded) -------------------------------------------------------

  function info(pack) {
    return { id: pack.id, label: pack.label, kind: pack.kind, bytes: pack.bytes, modes: pack.modes, needs: pack.needs.slice(),
             state: pack.state, loaded: pack.state === "loaded", url: pack.url };
  }

  function startSession(pack, opts) {
    const sess = {
      listeners: [],
      ui: opts.ui !== undefined ? opts.ui : pack.cfg.ui !== false,
      onLoaded: opts.onLoaded || null,
      chain: opts._chain || [],
      progress: function (phase, loaded, total) {
        const fraction = total ? Math.min(1, loaded / total) : null;
        const event = { id: pack.id, label: pack.label, phase: phase, loaded: loaded, total: total || null, fraction: fraction };
        if (sess.view) rowProgress(sess.view, fraction);
        sess.listeners.forEach((fn) => safeCall(fn, event));
      },
      view: null,
    };
    if (typeof opts.onProgress === "function") sess.listeners.push(opts.onProgress);
    pack.state = "loading";
    sess.promise = runSession(pack, sess).then(
      (value) => { pack.state = "loaded"; pack.result = value; pack.session = null; return value; },
      (err) => { pack.state = "idle"; pack.session = null; throw err; }
    );
    pack.session = sess;
    return sess;
  }

  async function runSession(pack, sess) {
    try {
      for (const dep of pack.needs) {
        if (dep === pack.id) continue;
        try { await load(dep, { ui: sess.ui, _chain: (sess.chain || []).concat(pack.id) }); }
        catch (e) { const wrapped = makeError("dependency", pack); wrapped.cause = e; throw wrapped; }
      }
      if (sess.ui) sess.view = makeRow(pack);
      for (;;) {
        try {
          sess.progress("fetch", 0, pack.bytes || null);
          const got = await fetchPack(pack, sess);
          sess.progress("install", got.size, got.size);
          const value = await install(pack, got, sess.onLoaded);
          recordDownload(pack, got.size);
          sess.progress("done", got.size, got.size);
          order.push(pack.id);
          if (pack.cfg.game) document.dispatchEvent(new CustomEvent("noyvj-pack-loaded", { detail: { game: pack.cfg.game, id: pack.id, bytes: got.size } }));
          return value;
        } catch (e) {
          const err = e && e.code ? e : makeError("network", pack);
          document.dispatchEvent(new CustomEvent("noyvj-pack-failed", { detail: { game: pack.cfg.game, id: pack.id, code: err.code } }));
          if (!sess.ui || !sess.view) throw err;
          const choice = await rowFailed(sess.view, err, !NOT_RETRYABLE[err.code]);
          if (choice !== "retry") { err.dismissed = true; throw err; }
          rowLoading(sess.view);
        }
      }
    } finally {
      if (sess.view) { dropRow(sess.view); sess.view = null; }
    }
  }

  function load(id, opts) {
    opts = opts || {};
    if (!packs.has(id) && manifestPending) return readyPromise.then(() => load(id, opts));
    const pack = packs.get(id);
    if (!pack) return Promise.reject(makeError("unknown", null, { id: String(id).slice(0, 60) }));
    if (pack.state === "loaded") return Promise.resolve(pack.result);
    if (opts._chain && opts._chain.indexOf(id) >= 0) return Promise.reject(makeError("dependency", pack));
    if (pack.session) {
      if (typeof opts.onProgress === "function") pack.session.listeners.push(opts.onProgress);
      return pack.session.promise;
    }
    return startSession(pack, opts).promise;
  }

  async function requires(ids, opts) {
    opts = opts || {};
    const list = Array.isArray(ids) ? ids.filter((x) => typeof x === "string") : [];
    const seen = {};
    const unique = list.filter((x) => (seen[x] ? false : (seen[x] = true)));
    const loaded = [];
    const failed = [];
    for (const id of unique) {
      if (has(id)) continue;
      try { await load(id, { ui: opts.ui, onProgress: opts.onProgress }); loaded.push(id); }
      catch (e) {
        if (!opts.soft) throw e;
        failed.push({ id: id, code: e && e.code || "network", message: e && e.message || "Could not load " + id });
      }
    }
    return opts.soft ? { loaded: loaded, failed: failed } : loaded;
  }

  function has(id) { const p = packs.get(id); return Boolean(p && p.state === "loaded"); }
  function known(id) { return packs.has(id); }
  function missing(ids) { return (Array.isArray(ids) ? ids : []).filter((id) => typeof id === "string" && !has(id)); }
  function unknown(ids) { return (Array.isArray(ids) ? ids : []).filter((id) => typeof id === "string" && !packs.has(id)); }
  function used() { return order.filter(has); }
  function infoOf(id) { const p = packs.get(id); return p ? info(p) : null; }
  function list() { return Array.from(packs.values()).map(info); }

  // ---- the record of what was fetched on this device (LZ-3) ----------------------------------------

  function recordKey(game) { return "packs:" + game; }

  function readRecord(game) {
    try {
      const raw = JSON.parse(lsGet(recordKey(game)) || "{}");
      const out = {};
      if (raw && typeof raw === "object" && !Array.isArray(raw)) {
        Object.keys(raw).forEach((id) => {
          const r = raw[id];
          if (ID_RE.test(id) && r && typeof r === "object" && Number.isFinite(r.bytes)) {
            out[id] = { bytes: r.bytes, at: typeof r.at === "string" ? r.at.slice(0, 10) : "" };
          }
        });
      }
      return out;
    } catch (e) { return {}; }
  }

  function recordDownload(pack, bytes) {
    const game = pack.cfg.game;
    if (!game) return;
    const rec = readRecord(game);
    rec[pack.id] = { bytes: bytes, at: new Date().toISOString().slice(0, 10) };
    lsSet(recordKey(game), JSON.stringify(rec));
  }

  function downloaded(game) {
    const slug = game || currentGame || gameFromLocation();
    if (!slug) return [];
    const rec = readRecord(slug);
    return Object.keys(rec).sort().map((id) => ({ id: id, bytes: rec[id].bytes, at: rec[id].at }));
  }

  function downloadedAll() {
    const out = {};
    try {
      for (let i = 0; i < localStorage.length; i++) {
        const key = localStorage.key(i);
        const m = /^packs:([a-z0-9-]{1,40})$/.exec(key || "");
        if (m) { const l = downloaded(m[1]); if (l.length) out[m[1]] = l; }
      }
    } catch (e) { /* storage blocked */ }
    return out;
  }

  function clearRecord(game, id) {
    const slug = game || currentGame || gameFromLocation();
    if (!slug) return;
    if (!id) { try { localStorage.removeItem(recordKey(slug)); } catch (e) { /* ignore */ } return; }
    const rec = readRecord(slug);
    delete rec[id];
    lsSet(recordKey(slug), JSON.stringify(rec));
  }

  // ---- go -----------------------------------------------------------------------------------------

  window.NoyvjPacks = {
    version: VERSION,
    register: register,
    ready: function () { return readyPromise; },
    has: has,
    known: known,
    load: load,
    requires: requires,
    requiresSoft: function (ids, opts) { return requires(ids, Object.assign({}, opts, { soft: true })); },
    missing: missing,
    unknown: unknown,
    used: used,
    info: infoOf,
    list: list,
    downloaded: downloaded,
    downloadedAll: downloadedAll,
    clearRecord: clearRecord,
    problems: problems,
  };

  if (ownScript && ownScript.getAttribute) {
    const manifest = ownScript.getAttribute("data-manifest");
    const game = ownScript.getAttribute("data-game-id");
    if (manifest || game) {
      const cfg = { game: game || undefined, manifest: manifest || undefined };
      if (ownScript.getAttribute("data-no-ui") === "true") cfg.ui = false;
      const max = Number(ownScript.getAttribute("data-max-bytes"));
      if (max > 0) cfg.maxBytes = max;
      register(cfg);
    }
  }
})();
