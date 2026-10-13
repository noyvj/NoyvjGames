(function () {
  "use strict";
  var ctx = null;

  function ensureCtx() {
    if (!ctx) {
      try { ctx = new (window.AudioContext || window.webkitAudioContext)(); } catch (e) { return false; }
    }
    if (ctx.state === "suspended") { ctx.resume().catch(function(){}); }
    return true;
  }

  function playTone(freq, dur, type) {
    if (!ensureCtx()) return;
    var osc = ctx.createOscillator();
    var gain = ctx.createGain();
    osc.type = type || "sine";
    osc.frequency.value = freq;
    gain.gain.setValueAtTime(0.15, ctx.currentTime);
    gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + dur);
    osc.connect(gain);
    gain.connect(ctx.destination);
    osc.start();
    osc.stop(ctx.currentTime + dur);
  }

  window.RobotSound = {
    tick: function () {
      if (document.documentElement.dataset.reducedMotion === "true" || document.documentElement.dataset.effects === "off") return;
      playTone(800, 0.05, "square");
    },
    buzz: function () {
      if (document.documentElement.dataset.reducedMotion === "true" || document.documentElement.dataset.effects === "off") return;
      playTone(150, 0.4, "sawtooth");
    }
  };
})();
