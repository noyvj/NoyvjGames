/*
 * Lighthouse -- R4-LHMO-2: wind the clockwork by drawing circles on a crank (phones, night only, when "Wind crank" is
 * switched on under Settings > On a phone). One full turn of the handle, either way round, sends the same {action: "wind"}
 * the "Wind it" button and the W key send. The plain "Wind it" button beside the crank does the same without any
 * drawing, so the gesture is never the only way. Nothing is timed: the handle stays wherever you leave it.
 */
(function () {
  "use strict";
  var wrap = document.getElementById("crank-wrap");
  var svg = document.getElementById("crank-svg");
  var handle = document.getElementById("crank-handle");
  var button = document.getElementById("crank-button");
  if (!wrap || !svg || !handle || !button) return;

  var dragging = false;
  var lastPointerAngle = 0;
  var handleAngle = 0;   // where the handle is drawn, in degrees
  var turned = 0;        // signed degrees since the last wind

  function wanted() { return window.LighthousePhonePrefs && window.LighthousePhonePrefs.get("crank") === "on"; }
  function api() { return window.lighthouseApi; }
  function reduced() { return document.documentElement.getAttribute("data-reduced-motion") === "true"; }

  function draw() { handle.setAttribute("transform", "rotate(" + handleAngle.toFixed(1) + " 50 50)"); }

  function pointerAngle(e) {
    var r = svg.getBoundingClientRect();
    return Math.atan2(e.clientY - (r.top + r.height / 2), e.clientX - (r.left + r.width / 2)) * 180 / Math.PI;
  }

  // One wind, the same message the button would give. Returns true when the engine wound it.
  function wind() {
    var a = api();
    var v = a && a.view();
    if (!v || v.phase !== "night") return false;
    if (v.clockwork.left >= v.clockwork.max - 1) {
      a.toast("The clockwork is already wound.");
      a.announce("The clockwork is already wound.");
      return false;
    }
    var res = a.send({ action: "wind" });
    if (res) {
      a.announce("You wind the clockwork.");
      if (navigator.vibrate && !reduced()) { try { navigator.vibrate(15); } catch (err) { /* not everywhere */ } }
    }
    return Boolean(res);
  }

  svg.addEventListener("pointerdown", function (e) {
    dragging = true;
    lastPointerAngle = pointerAngle(e);
    try { svg.setPointerCapture(e.pointerId); } catch (err) { /* fine without */ }
    e.preventDefault();
  });
  svg.addEventListener("pointermove", function (e) {
    if (!dragging) return;
    var angle = pointerAngle(e);
    var delta = angle - lastPointerAngle;
    if (delta > 180) delta -= 360;
    if (delta < -180) delta += 360;
    lastPointerAngle = angle;
    handleAngle += delta;
    turned += delta;
    draw();
    while (Math.abs(turned) >= 360) {
      turned -= turned > 0 ? 360 : -360;
      wind();
    }
    e.preventDefault();
  });
  function release() { dragging = false; turned = 0; }
  svg.addEventListener("pointerup", release);
  svg.addEventListener("pointercancel", release);

  button.addEventListener("click", function () { if (wind()) { handleAngle += 360; draw(); } });

  function sync(v) {
    v = v || (api() && api().view());
    wrap.hidden = !(Boolean(v) && v.phase === "night" && wanted());
  }
  document.addEventListener("lighthouse-view", function (e) { sync(e.detail); });
  document.addEventListener("lighthouse-phone-pref", function (e) { if (e.detail.name === "crank") sync(); });
  sync();
})();
