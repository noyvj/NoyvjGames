/*
 * Shared translations (TODO Z-13): t("key") for the strings the shared components put on screen
 * (save widget, confirm dialog, tutorial card, achievements panel). English is the default and is
 * always the fallback:
 *
 *   NoyvjI18n.t("confirm.cancel", "Cancel")             -> "Cancel", or "Cancelar" when Spanish is chosen
 *   NoyvjI18n.t("tutorial.step", "Step {n} of {total}", { n: 2, total: 5 })
 *   t("save.copied")                                     -> the same lookup through the global shortcut
 *
 * The second argument is the English text. Components pass it so they look exactly the same when
 * this script is not on the page, when the language is English, when a language file has not loaded
 * yet, and when a key is missing from a language file. English never fetches anything.
 *
 * Languages live in shared/strings/<code>.json: a flat {"key": "text"} object, "{name}" marks a
 * value the component fills in. shared/strings/en.json is the full list of keys with their English
 * text (the source the translations follow; a test keeps it equal to what the components pass);
 * es.json and fr.json hold the translations. The chosen language is stored on this device only, in
 * localStorage["hub_lang"] (the hub Settings page has the chooser). It is not synced to the account
 * the way the theme is: that would need a new setting on the server.
 *
 * When a language file arrives the page gets a "noyvj-i18n-change" event on document ({lang}); the
 * components listen and relabel what is already on screen. Nothing here ever throws or blocks: a
 * blocked localStorage, a failed fetch or a bad file leaves the English text.
 *
 *   NoyvjI18n.LANGS            [{code, name}] the languages offered (names are written in that language)
 *   NoyvjI18n.lang()           the current code ("en" unless another one is stored and supported)
 *   NoyvjI18n.setLang(code)    store + load + announce; false for an unsupported code
 *   NoyvjI18n.t(key, english, vars)
 *   NoyvjI18n.ready            promise, resolved once the current language has loaded (or failed)
 */
(function () {
  if (window.NoyvjI18n) return;

  const KEY = "hub_lang";
  const LANGS = [
    { code: "en", name: "English" },
    { code: "es", name: "Español" },
    { code: "fr", name: "Français" },
  ];
  const SCRIPT = document.currentScript;
  const BASE = SCRIPT && SCRIPT.src ? new URL("strings/", SCRIPT.src).href : "shared/strings/";

  function lsGet(k) { try { return localStorage.getItem(k); } catch (e) { return null; } }
  function lsSet(k, v) { try { localStorage.setItem(k, v); return true; } catch (e) { return false; } }
  function supported(code) { return LANGS.some((l) => l.code === code); }

  let current = (() => { const v = lsGet(KEY); return supported(v) ? v : "en"; })();
  const dicts = {};           // code -> {key: text}, only for languages that loaded
  const loading = {};         // code -> promise

  function fill(text, vars) {
    if (!vars) return text;
    return text.replace(/\{(\w+)\}/g, (m, name) => (Object.prototype.hasOwnProperty.call(vars, name) ? String(vars[name]) : m));
  }

  function t(key, english, vars) {
    const dict = dicts[current];
    const own = dict && typeof dict[key] === "string" ? dict[key] : null;
    const text = own !== null ? own : typeof english === "string" ? english : key;
    return fill(text, vars);
  }

  function load(code) {
    if (code === "en" || !supported(code)) return Promise.resolve(false);
    if (dicts[code]) return Promise.resolve(true);
    if (loading[code]) return loading[code];
    loading[code] = fetch(BASE + code + ".json")
      .then((res) => (res.ok ? res.json() : null))
      .then((data) => {
        if (!data || typeof data !== "object" || Array.isArray(data)) return false;
        const clean = {};
        Object.keys(data).forEach((k) => { if (typeof data[k] === "string") clean[k] = data[k]; });
        dicts[code] = clean;
        return true;
      })
      .catch(() => false)
      .then((ok) => { delete loading[code]; return ok; });
    return loading[code];
  }

  function announce() {
    try { document.dispatchEvent(new CustomEvent("noyvj-i18n-change", { detail: { lang: current } })); } catch (e) { /* old browser */ }
  }

  const api = {
    LANGS,
    t,
    lang() { return current; },
    setLang(code) {
      if (!supported(code)) return false;
      lsSet(KEY, code);
      current = code;
      api.ready = load(code).then(() => { announce(); return true; });
      if (code === "en") announce();
      return true;
    },
    load,
    ready: Promise.resolve(true),
  };
  window.NoyvjI18n = api;
  if (typeof window.t === "undefined") window.t = t;

  if (current !== "en") api.ready = load(current).then((ok) => { if (ok) announce(); return ok; });
})();
