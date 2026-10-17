// R4-THMO-4: a vibration that grows each time the global temperature crosses a warming milestone upward, on phones
// that allow it (navigator.vibrate; iOS Safari does not, so nothing happens there). Milestones: +10 (permafrost starts
// to melt), +15 (thaw becomes a global driver), then +20, +25 and +30. A crossing is read from the "Global temperature"
// line itself (any unit: C, F or K), once per upward crossing, and never for a jump that was not a player action (a
// save loading, a new game). Off with Settings > "No vibration...", with Reduce motion, lite mode or the OS setting.
(function () {
  "use strict";
  if (typeof navigator === "undefined" || typeof navigator.vibrate !== "function") return;
  var el = document.getElementById("temperature-display");
  if (!el) return;

  // Milestone (degrees C of rise) -> vibration pattern in ms (buzz, pause, buzz ...). Each one is longer than the last.
  var MILESTONES = [
    [10, [120]],
    [15, [120, 80, 160]],
    [20, [120, 80, 160, 80, 200]],
    [25, [140, 80, 180, 80, 220, 80, 260]],
    [30, [160, 80, 200, 80, 240, 80, 280, 80, 320]],
  ];

  function suppressed() {
    var root = document.documentElement;
    if (root.getAttribute("data-no-haptics") === "true") return true;
    if (root.getAttribute("data-reduced-motion") === "true" || root.getAttribute("data-lite") === "true") return true;
    try {
      return Boolean(window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches);
    } catch (e) {
      return false;
    }
  }

  // The readout's rise in degrees C, whatever unit the player chose (F is 1.8 times C, K is the same size as C).
  function riseFrom(text) {
    var match = /([+-]?\d+(?:\.\d+)?)/.exec(text || "");
    if (!match) return null;
    var value = parseFloat(match[1]);
    if (isNaN(value)) return null;
    return /°\s*F/.test(text) ? value / 1.8 : value;
  }

  function playerAction() {
    // A save loading or a new game is not the player pushing the temperature up: only buzz during a recent gesture.
    var activation = navigator.userActivation;
    return !activation || activation.isActive;
  }

  var last = riseFrom(el.textContent);

  function check() {
    var now = riseFrom(el.textContent);
    if (now === null) return;
    var before = last;
    last = now;
    // A round raises the temperature by a few degrees at most: a bigger jump is a save loading or a new game.
    if (before === null || now <= before || now - before > 5 || suppressed() || !playerAction()) return;
    var pattern = null;
    MILESTONES.forEach(function (milestone) {
      if (before < milestone[0] && now >= milestone[0]) pattern = milestone[1];  // the highest one crossed this time
    });
    if (!pattern) return;
    try {
      navigator.vibrate(pattern);
    } catch (e) {
      return;
    }
    el.classList.remove("threshold-crossed-pulse");
    void el.offsetWidth;
    el.classList.add("threshold-crossed-pulse");
    window.setTimeout(function () { el.classList.remove("threshold-crossed-pulse"); }, 900);
  }

  new MutationObserver(check).observe(el, { characterData: true, childList: true, subtree: true });
})();
