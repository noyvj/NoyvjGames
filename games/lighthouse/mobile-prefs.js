/*
 * Lighthouse -- the phone touches' switches (R4-LHMO-1, 2, 4, 6, 8, 9).
 *
 * Every phone-only extra is optional and off until the player switches it on in Settings ("On a phone"). The choices are
 * per-device display choices, like settings.js's: they live in localStorage, never in get_state()/load_state(), and
 * "Reset display settings" puts them back. Each choice becomes an attribute on <html> that style.css and the other
 * mobile-*.js files read; nothing here touches the engine.
 */
(function () {
  "use strict";
  var root = document.documentElement;
  var DEFS = {
    lamp: { key: "lighthouse-phone-lamp", attr: "data-phone-lamp", control: "phone-lamp-select", kind: "select", values: ["off", "slider", "rail"], dflt: "off" },
    crank: { key: "lighthouse-phone-crank", attr: "data-phone-crank", control: "phone-crank-checkbox", kind: "box", dflt: "off" },
    cards: { key: "lighthouse-phone-cards", attr: "data-phone-cards", control: "phone-cards-checkbox", kind: "box", dflt: "off" },
    edge: { key: "lighthouse-phone-edge", attr: "data-phone-edge", control: "phone-edge-checkbox", kind: "box", dflt: "off" },
    saver: { key: "lighthouse-battery-saver", attr: "data-battery-saver", control: "battery-saver-checkbox", kind: "box", dflt: "off" }
  };

  function lsGet(k) { try { return window.localStorage.getItem(k); } catch (e) { return null; } }
  function lsSet(k, v) { try { window.localStorage.setItem(k, v); } catch (e) { /* a convenience only */ } }
  function lsRemove(k) { try { window.localStorage.removeItem(k); } catch (e) { /* a convenience only */ } }

  function valid(def, value) {
    if (def.kind === "box") return value === "on" || value === "off";
    return def.values.indexOf(value) !== -1;
  }
  function read(def) {
    var stored = lsGet(def.key);
    return valid(def, stored) ? stored : def.dflt;
  }
  function apply(name, value) {
    var def = DEFS[name];
    root.setAttribute(def.attr, value);
    var control = document.getElementById(def.control);
    if (control) {
      if (def.kind === "box") control.checked = value === "on"; else control.value = value;
    }
  }
  function get(name) { return root.getAttribute(DEFS[name].attr) || DEFS[name].dflt; }
  function announceChange(name) {
    document.dispatchEvent(new CustomEvent("lighthouse-phone-pref", { detail: { name: name, value: get(name) } }));
  }

  Object.keys(DEFS).forEach(function (name) {
    var def = DEFS[name];
    apply(name, read(def));
    var control = document.getElementById(def.control);
    if (!control) return;
    control.addEventListener("change", function () {
      var value = def.kind === "box" ? (control.checked ? "on" : "off") : control.value;
      if (!valid(def, value)) value = def.dflt;
      lsSet(def.key, value);
      apply(name, value);
      announceChange(name);
    });
  });

  var reset = document.getElementById("display-reset-button");
  if (reset) {
    reset.addEventListener("click", function () {
      Object.keys(DEFS).forEach(function (name) {
        lsRemove(DEFS[name].key);
        apply(name, DEFS[name].dflt);
        announceChange(name);
      });
    });
  }

  window.LighthousePhonePrefs = { get: get, names: Object.keys(DEFS) };
})();
