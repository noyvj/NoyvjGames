/*
 * Lighthouse -- R4-LHMO-6: open the letters drawer with a swipe from the left edge (phones, when "Swipe from the left
 * edge for letters" is switched on under Settings > On a phone). It does exactly what the Letters toolbar button does
 * (that button stays, and is the keyboard and screen-reader way in): it clicks that button, and the CSS then draws the
 * panel as a drawer. A Close button, Escape, a swipe back to the left, or a tap outside the drawer closes it the same way.
 * Off by default because a swipe from the very edge is also the back gesture on some phones.
 */
(function () {
  "use strict";
  var strip = document.getElementById("edge-strip");
  var panel = document.getElementById("letters-panel");
  var toggle = document.getElementById("letters-toggle-button");
  var closeBtn = document.getElementById("letters-close-button");
  if (!strip || !panel || !toggle || !closeBtn) return;

  function wanted() { return window.LighthousePhonePrefs && window.LighthousePhonePrefs.get("edge") === "on"; }
  function phone() { return Boolean(window.matchMedia && window.matchMedia("(max-width: 600px)").matches); }
  function isOpen() { return !panel.hidden; }
  function drawerMode() { return wanted() && phone(); }

  var openedAt = 0;
  function open() {
    if (isOpen() || toggle.hidden) return;
    openedAt = Date.now();
    toggle.click();
    try { closeBtn.focus({ preventScroll: true }); } catch (err) { /* fine */ }
  }
  function close() {
    if (!isOpen()) return;
    toggle.click();
    toggle.focus({ preventScroll: true });
  }

  function paint() {
    strip.hidden = !(drawerMode() && !toggle.hidden && !isOpen());
    document.documentElement.setAttribute("data-letters-open", String(isOpen()));
  }

  var x0 = null;
  strip.addEventListener("pointerdown", function (e) { x0 = e.clientX; try { strip.setPointerCapture(e.pointerId); } catch (err) { /* fine */ } });
  strip.addEventListener("pointermove", function (e) { if (x0 !== null && e.clientX - x0 > 40) { x0 = null; open(); } });
  strip.addEventListener("pointerup", function () { x0 = null; });
  strip.addEventListener("pointercancel", function () { x0 = null; });

  var d0 = null;
  panel.addEventListener("pointerdown", function (e) { if (drawerMode() && isOpen()) d0 = e.clientX; });
  panel.addEventListener("pointermove", function (e) { if (d0 !== null && d0 - e.clientX > 80) { d0 = null; close(); } });
  panel.addEventListener("pointerup", function () { d0 = null; });
  panel.addEventListener("pointercancel", function () { d0 = null; });

  closeBtn.addEventListener("click", close);
  document.addEventListener("keydown", function (e) { if (e.key === "Escape" && drawerMode() && isOpen()) close(); });
  document.addEventListener("click", function (e) {
    if (!drawerMode() || !isOpen()) return;
    // the click that ends the very swipe which opened the drawer lands on the edge strip: it is not a tap outside
    if (Date.now() - openedAt < 600) return;
    // the path is read from the event, not the DOM: a button inside the drawer may already have been redrawn away
    var path = e.composedPath ? e.composedPath() : [];
    if (path.indexOf(panel) !== -1 || path.indexOf(toggle) !== -1) return;
    if (e.target.closest && e.target.closest("[role='dialog']:not([hidden])")) return;
    close();
  });

  // follow the panel however it was opened or closed (the toolbar button, the Desktop menu, a settings change)
  new MutationObserver(paint).observe(panel, { attributes: true, attributeFilter: ["hidden"] });
  new MutationObserver(paint).observe(toggle, { attributes: true, attributeFilter: ["hidden"] });
  document.addEventListener("lighthouse-phone-pref", function (e) { if (e.detail.name === "edge") paint(); });
  window.addEventListener("resize", paint);
  paint();
})();
