/*
 * Shared generated sound (planning/TODO.md AU-1): short, soft sound cues made in code with the browser's
 * Web Audio API. There are no audio files, no downloads and no libraries, and nothing here calls the network.
 *
 *   <script src="../../shared/sfx.js"></script>      (the script links shared/sfx.css itself, like night-mode.js)
 *
 * The rules this file keeps, so a game never has to:
 *   - Off by default. Nothing is created or played until the player turns sound on (localStorage "sfx_enabled").
 *   - Never autoplays. The AudioContext is created lazily, on the first tap, click or key press AFTER sound
 *     is on, and play() before that is a silent no-op that returns false.
 *   - Nothing is ever communicated by sound alone: every cue is decoration for something the page also shows.
 *   - Quiet by construction: sine/triangle voices only, short envelopes, a conservative master gain, a low-pass
 *     filter and a hard compressor/limiter at the end of the chain. The loudest cue's summed peak is bounded.
 *   - The hidden tab is muted (context suspended, hum stopped) and comes back when the tab is visible again.
 *   - "Reduce sounds" (sfx_reduce) halves the level, shortens every cue, keeps at most two voices of it and
 *     switches the ambient hum off.
 *
 * Settings (localStorage, read fresh on every call, so the hub Settings page and a game in another tab agree):
 *   sfx_enabled   "true" when on; absent or anything else = off
 *   sfx_volume    "0".."1", default 0.5, mapped to a low master gain (see masterGain)
 *   sfx_reduce    "true" when "reduce sounds" is on
 *
 * API (window.NoyvjSfx):
 *   play(name, {pitch, gain, delay}) -> boolean      true when sound was actually scheduled
 *       names: tap, confirm, soft_error, success, level_complete, unlock, bell, click_low, click_high,
 *       hum_start, hum_stop (the hum is a faint continuous bed; hum_start remembers the wish, so it begins as
 *       soon as sound is on and the player has tapped; hum_stop fades it out)
 *       pitch = semitones (-12..12), gain = 0..1 multiplier, delay = seconds
 *   enabled() / volume() / reduce() and setEnabled(bool) / setVolume(0..1) / setReduce(bool)
 *   control(opts) -> HTMLElement   an accessible on/off + volume + reduce control to mount in a Settings panel
 *   onChange(fn) -> unsubscribe    fn({enabled, volume, reduce}); the same data fires "noyvj-sfx-change" on document
 *   supported(), stopAll(), cueNames()
 *   _testing    the pure tone tables and envelope math, plus a status() snapshot (for tests only)
 * Text is written with textContent only.
 */
(function () {
  "use strict";
  var root = typeof window !== "undefined" ? window : this;
  if (root.NoyvjSfx) return;

  var KEYS = { enabled: "sfx_enabled", volume: "sfx_volume", reduce: "sfx_reduce" };
  var DEFAULT_VOLUME = 0.5;
  var MAX_MASTER = 0.5;          // master gain at volume 1; volume 0.5 is about 0.18
  var VOLUME_CURVE = 1.5;
  var ENV_FLOOR = 0.001;         // an envelope decays to peak * ENV_FLOOR (-60 dB) at the end of its voice
  var REDUCE_GAIN = 0.5;
  var REDUCE_TIME = 0.6;
  var REDUCE_MAX_VOICES = 2;
  var MAX_PEAK_SUM = 0.9;        // the summed peaks of one cue never exceed this (before the master gain)
  var MAX_LIVE_VOICES = 10;
  var MIN_GAP_MS = 45;           // the same cue twice inside this is dropped (no machine-gun)
  var LOWPASS_HZ = 3800;
  var CSS_FILE = "sfx.css";

  // Notes (Hz) from a calm C major / A minor pentatonic-ish set.
  var N = { G3: 196.0, C4: 261.63, E4: 329.63, G4: 392.0, A4: 440.0, C5: 523.25, E5: 659.25, G5: 783.99, A5: 880.0, C6: 1046.5 };

  function tone(wave, freq, at, dur, attack, peak, glide) {
    var v = { wave: wave, freq: freq, at: at, dur: dur, attack: attack, peak: peak };
    if (glide) v.glide = glide;
    return v;
  }

  // Every voice: {wave, freq, glide?, at, dur, attack, peak}. Times in seconds, peak is a gain 0..1.
  var CUES = {
    tap: { kind: "tone", voices: [tone("sine", 520, 0, 0.07, 0.004, 0.32, 470)] },
    confirm: { kind: "tone", voices: [tone("sine", N.G4, 0, 0.16, 0.006, 0.28), tone("sine", N.C5, 0.075, 0.24, 0.006, 0.28)] },
    soft_error: { kind: "tone", voices: [tone("triangle", 196, 0, 0.2, 0.012, 0.3, 160)] },
    success: { kind: "tone", voices: [tone("sine", N.C5, 0, 0.3, 0.006, 0.24), tone("sine", N.E5, 0.09, 0.3, 0.006, 0.24), tone("sine", N.G5, 0.18, 0.46, 0.006, 0.24)] },
    level_complete: {
      kind: "tone",
      voices: [tone("sine", N.G4, 0, 0.36, 0.008, 0.22), tone("sine", N.C5, 0.12, 0.36, 0.008, 0.22), tone("sine", N.E5, 0.24, 0.4, 0.008, 0.22),
        tone("sine", N.G5, 0.36, 0.75, 0.008, 0.22), tone("sine", N.C6, 0.36, 0.85, 0.008, 0.1)],
    },
    unlock: { kind: "tone", voices: [tone("sine", N.E5, 0, 0.5, 0.008, 0.22, 700), tone("sine", N.A5, 0.11, 0.62, 0.008, 0.18)] },
    bell: {
      kind: "tone",
      voices: [tone("sine", N.C5, 0, 1.4, 0.006, 0.26), tone("sine", 1444, 0, 0.7, 0.006, 0.08), tone("sine", N.C4, 0, 1.0, 0.01, 0.12)],
    },
    click_low: { kind: "tone", voices: [tone("sine", 170, 0, 0.055, 0.002, 0.4, 105)] },
    click_high: { kind: "tone", voices: [tone("sine", 1000, 0, 0.04, 0.002, 0.22, 800)] },
    // A faint bed: a low fifth plus a slightly detuned twin (a slow beat), faded in over seconds and swelling
    // very gently. Never started in reduce mode.
    hum_start: {
      kind: "hum",
      fade_in: 3,
      lfo: { freq: 0.11, depth: 0.2 },
      voices: [tone("sine", 146.83, 0, 0, 0, 0.06), tone("sine", 147.6, 0, 0, 0, 0.05), tone("sine", 220.0, 0, 0, 0, 0.04), tone("sine", 293.66, 0, 0, 0, 0.015)],
    },
    hum_stop: { kind: "hum_stop", fade_out: 2, voices: [] },
  };

  // ---------- pure math (no audio, no DOM): exposed through _testing ----------

  function clamp(x, lo, hi) { return x < lo ? lo : x > hi ? hi : x; }

  /** Volume 0..1 to master gain: quadratic-ish curve, so the middle of the slider is already quiet. */
  function masterGain(volume) {
    var v = clamp(Number(volume), 0, 1);
    if (!isFinite(v)) v = DEFAULT_VOLUME;
    return MAX_MASTER * Math.pow(v, VOLUME_CURVE);
  }

  /** Gain of one voice t seconds after the voice starts: linear attack to peak, then exponential decay to peak * ENV_FLOOR. */
  function envelope(voice, t) {
    var d = voice.dur;
    var a = Math.max(voice.attack || 0.005, 1e-4);
    if (!(d > 0) || t <= 0 || t >= d) return 0;
    if (t < a) return voice.peak * (t / a);
    return voice.peak * Math.pow(ENV_FLOOR, (t - a) / Math.max(d - a, 1e-4));
  }

  function cueDuration(voices) {
    var end = 0;
    voices.forEach(function (v) { end = Math.max(end, v.at + v.dur); });
    return end;
  }

  /** The highest summed gain of a list of voices at any moment (sampled every 5 ms). */
  function peakSum(voices) {
    var peak = 0;
    var end = cueDuration(voices);
    for (var t = 0; t <= end; t += 0.005) {
      var sum = 0;
      for (var i = 0; i < voices.length; i++) sum += envelope(voices[i], t - voices[i].at);
      if (sum > peak) peak = sum;
    }
    return peak;
  }

  function copyVoice(v) {
    var out = {};
    Object.keys(v).forEach(function (k) { out[k] = v[k]; });
    return out;
  }

  /** The "reduce sounds" version of a tone cue: at most two voices, quieter, shorter. A hum becomes nothing. */
  function reduceCue(cue) {
    if (!cue || cue.kind !== "tone") return null;
    return {
      kind: "tone",
      voices: cue.voices.slice(0, REDUCE_MAX_VOICES).map(function (v) {
        var out = copyVoice(v);
        out.peak = v.peak * REDUCE_GAIN;
        out.dur = v.dur * REDUCE_TIME;
        out.at = v.at * REDUCE_TIME;
        out.attack = Math.min(v.attack, out.dur / 2);
        return out;
      }),
    };
  }

  /** What would actually be scheduled for a cue name: a list of voices (or null for a hum / unknown / silent cue). */
  function planCue(name, opts) {
    opts = opts || {};
    var cue = CUES[name];
    if (!cue || cue.kind !== "tone") return null;
    if (opts.reduce) cue = reduceCue(cue);
    var ratio = Math.pow(2, clamp(Number(opts.pitch) || 0, -12, 12) / 12);
    var gain = opts.gain === undefined ? 1 : clamp(Number(opts.gain), 0, 1);
    if (!isFinite(gain)) gain = 1;
    return cue.voices.map(function (v) {
      var out = copyVoice(v);
      out.freq = v.freq * ratio;
      if (v.glide) out.glide = v.glide * ratio;
      out.peak = v.peak * gain;
      return out;
    });
  }

  // ---------- settings ----------

  var memory = {};
  function read(key) {
    try { return root.localStorage.getItem(key); } catch (e) { return memory[key] === undefined ? null : memory[key]; }
  }
  function write(key, value) {
    memory[key] = value;
    try { root.localStorage.setItem(key, value); } catch (e) { /* blocked storage: the choice lasts this page */ }
  }
  function remove(key) {
    delete memory[key];
    try { root.localStorage.removeItem(key); } catch (e) { /* ignore */ }
  }
  function truthy(v) { return v === "true" || v === "1"; }

  function enabled() { return truthy(read(KEYS.enabled)); }
  function reduce() { return truthy(read(KEYS.reduce)); }
  function volume() {
    var v = parseFloat(read(KEYS.volume));
    return isFinite(v) ? clamp(v, 0, 1) : DEFAULT_VOLUME;
  }
  function snapshot() { return { enabled: enabled(), volume: volume(), reduce: reduce() }; }

  var listeners = [];
  function onChange(fn) {
    if (typeof fn !== "function") return function () {};
    listeners.push(fn);
    return function () { var i = listeners.indexOf(fn); if (i >= 0) listeners.splice(i, 1); };
  }
  function changed() {
    syncAudio();
    var state = snapshot();
    listeners.slice().forEach(function (fn) { try { fn(state); } catch (e) { /* a listener must not break the page */ } });
    try { root.document.dispatchEvent(new root.CustomEvent("noyvj-sfx-change", { detail: state })); } catch (e) { /* no DOM */ }
  }
  function setEnabled(on) {
    if (on) write(KEYS.enabled, "true"); else remove(KEYS.enabled);
    changed();
    return enabled();
  }
  function setReduce(on) {
    if (on) write(KEYS.reduce, "true"); else remove(KEYS.reduce);
    changed();
    return reduce();
  }
  function setVolume(v) {
    var x = parseFloat(v);
    if (!isFinite(x)) return volume();
    write(KEYS.volume, String(Math.round(clamp(x, 0, 1) * 100) / 100));
    changed();
    return volume();
  }

  // ---------- audio graph (created lazily, only after sound is on and the player has acted) ----------

  var ctx = null;
  var chain = null;
  var gestureSeen = false;
  var humWanted = false;
  var hum = null;
  var live = [];
  var lastPlayed = {};

  function contextClass() { return root.AudioContext || root.webkitAudioContext || null; }
  function supported() { return Boolean(contextClass()); }
  function hidden() { return Boolean(root.document && root.document.hidden); }

  function setParam(param, value, time) {
    if (!param) return;
    try {
      if (typeof param.setValueAtTime === "function") param.setValueAtTime(value, time === undefined ? 0 : time);
      else param.value = value;
    } catch (e) { try { param.value = value; } catch (e2) { /* ignore */ } }
  }
  function call(obj, method) {
    var args = Array.prototype.slice.call(arguments, 2);
    try { if (obj && typeof obj[method] === "function") obj[method].apply(obj, args); } catch (e) { /* ignore */ }
  }

  function ensureContext() {
    if (ctx) return ctx;
    if (!gestureSeen || !enabled() || hidden()) return null;
    var C = contextClass();
    if (!C) return null;
    try {
      ctx = new C();
      var master = ctx.createGain();
      var filter = ctx.createBiquadFilter();
      var comp = ctx.createDynamicsCompressor();
      filter.type = "lowpass";
      setParam(filter.frequency, LOWPASS_HZ);
      setParam(filter.Q, 0.5);
      // A hard limiter in effect: low threshold, high ratio, fast attack.
      setParam(comp.threshold, -18);
      setParam(comp.knee, 8);
      setParam(comp.ratio, 20);
      setParam(comp.attack, 0.003);
      setParam(comp.release, 0.2);
      master.connect(filter);
      filter.connect(comp);
      comp.connect(ctx.destination);
      chain = { input: master, master: master };
    } catch (e) {
      ctx = null;
      chain = null;
      return null;
    }
    return ctx;
  }

  function resumeContext() {
    if (ctx && ctx.state === "suspended" && !hidden() && enabled()) {
      try { var p = ctx.resume(); if (p && p.catch) p.catch(function () {}); } catch (e) { /* ignore */ }
    }
  }

  function applyMasterGain() {
    if (!ctx || !chain) return;
    var g = enabled() ? masterGain(volume()) : 0;
    call(chain.master.gain, "cancelScheduledValues", 0);
    setParam(chain.master.gain, g, ctx.currentTime || 0);
  }

  function startHum() {
    if (hum || !humWanted || !enabled() || reduce() || hidden() || !gestureSeen) return false;
    var c = ensureContext();
    if (!c) return false;
    resumeContext();
    try {
      var spec = CUES.hum_start;
      var now = c.currentTime || 0;
      var bed = c.createGain();
      var breath = c.createGain();
      setParam(bed.gain, 0.0001, now);
      call(bed.gain, "linearRampToValueAtTime", 1, now + spec.fade_in);
      setParam(breath.gain, 1 - spec.lfo.depth, now);
      bed.connect(breath);
      breath.connect(chain.input);
      var oscs = [];
      spec.voices.forEach(function (v) {
        var osc = c.createOscillator();
        var g = c.createGain();
        osc.type = v.wave;
        setParam(osc.frequency, v.freq, now);
        setParam(g.gain, v.peak, now);
        osc.connect(g);
        g.connect(bed);
        osc.start(now);
        oscs.push(osc);
      });
      var lfo = c.createOscillator();
      var depth = c.createGain();
      lfo.type = "sine";
      setParam(lfo.frequency, spec.lfo.freq, now);
      setParam(depth.gain, spec.lfo.depth, now);
      lfo.connect(depth);
      depth.connect(breath.gain);
      lfo.start(now);
      oscs.push(lfo);
      hum = { bed: bed, oscs: oscs };
      return true;
    } catch (e) {
      hum = null;
      return false;
    }
  }

  function stopHum(fadeSeconds) {
    if (!hum) return false;
    var h = hum;
    hum = null;
    try {
      var fade = fadeSeconds === undefined ? CUES.hum_stop.fade_out : fadeSeconds;
      var now = ctx ? ctx.currentTime || 0 : 0;
      call(h.bed.gain, "cancelScheduledValues", now);
      var level = h.bed.gain && h.bed.gain.value > 0 ? h.bed.gain.value : 1;
      setParam(h.bed.gain, level, now);
      call(h.bed.gain, "linearRampToValueAtTime", 0.0001, now + fade);
      h.oscs.forEach(function (osc) { call(osc, "stop", now + fade + 0.05); });
    } catch (e) { /* ignore */ }
    return true;
  }

  /** Brings the audio graph in line with the settings and the tab: called after every setting change and visibility change. */
  function syncAudio() {
    if (!enabled() || hidden()) {
      stopHum(enabled() ? 0.15 : 0.1);
      if (ctx && ctx.state === "running" && hidden()) { try { var p = ctx.suspend(); if (p && p.catch) p.catch(function () {}); } catch (e) { /* ignore */ } }
      if (ctx && !enabled()) applyMasterGain();
      return;
    }
    if (ctx) { resumeContext(); applyMasterGain(); }
    if (reduce()) stopHum(0.3); else startHum();
  }

  function markGesture() {
    gestureSeen = true;
    if (enabled() && !hidden()) {
      ensureContext();
      resumeContext();
      applyMasterGain();
      startHum();
    }
  }

  function scheduleVoice(c, v, base, out) {
    var t0 = base + v.at;
    var t1 = t0 + v.dur;
    var osc = c.createOscillator();
    var g = c.createGain();
    osc.type = v.wave;
    setParam(osc.frequency, v.freq, t0);
    if (v.glide) call(osc.frequency, "exponentialRampToValueAtTime", v.glide, t1);
    setParam(g.gain, 0.0001, t0);
    call(g.gain, "linearRampToValueAtTime", v.peak, t0 + v.attack);
    call(g.gain, "exponentialRampToValueAtTime", Math.max(v.peak * ENV_FLOOR, 1e-5), t1);
    osc.connect(g);
    g.connect(chain.input);
    osc.start(t0);
    osc.stop(t1 + 0.03);
    osc.onended = function () { try { osc.disconnect(); g.disconnect(); } catch (e) { /* ignore */ } };
    out.push(t1 + 0.03);
  }

  function play(name, opts) {
    var cue = CUES[name];
    if (!cue) return false;
    if (name === "hum_start") { humWanted = true; return startHum(); }
    if (name === "hum_stop") { humWanted = false; return stopHum(); }
    if (!enabled() || hidden() || !gestureSeen) return false;
    var c = ensureContext();
    if (!c || !chain) return false;
    resumeContext();
    var nowMs = root.performance && root.performance.now ? root.performance.now() : 0;
    if (lastPlayed[name] !== undefined && nowMs - lastPlayed[name] < MIN_GAP_MS) return false;
    opts = opts || {};
    var voices = planCue(name, { reduce: reduce(), pitch: opts.pitch, gain: opts.gain });
    if (!voices || !voices.length) return false;
    var now = c.currentTime || 0;
    live = live.filter(function (end) { return end > now; });
    if (live.length + voices.length > MAX_LIVE_VOICES) return false;
    lastPlayed[name] = nowMs;
    applyMasterGain();
    var base = now + 0.01 + Math.max(0, Number(opts.delay) || 0);
    try {
      voices.forEach(function (v) { scheduleVoice(c, v, base, live); });
    } catch (e) { return false; }
    return true;
  }

  function stopAll() {
    humWanted = false;
    stopHum(0.1);
    live = [];
    if (ctx && ctx.state === "running") { try { var p = ctx.suspend(); if (p && p.catch) p.catch(function () {}); } catch (e) { /* ignore */ } }
  }

  // ---------- the small control a game mounts in its Settings panel ----------

  var controls = [];
  var controlCount = 0;

  function ensureStylesheet() {
    var doc = root.document;
    if (!doc || doc.querySelector('link[href*="' + CSS_FILE + '"]') || !ownSrc) return;
    var link = doc.createElement("link");
    link.rel = "stylesheet";
    link.href = ownSrc.replace(/sfx\.js(\?.*)?$/, CSS_FILE);
    doc.head.appendChild(link);
  }

  function element(tag, className, text) {
    var node = root.document.createElement(tag);
    if (className) node.className = className;
    if (text !== undefined) node.textContent = text;
    return node;
  }

  function control(opts) {
    opts = opts || {};
    ensureStylesheet();
    controlCount += 1;
    var id = (opts.idPrefix || "noyvj-sfx") + "-" + controlCount;
    var wrap = element("div", "noyvj-sfx-control");
    wrap.setAttribute("data-testid", "sfx-control");

    var rowOn = element("div", "noyvj-sfx-row");
    var on = element("input");
    on.type = "checkbox";
    on.id = id + "-on";
    on.setAttribute("data-testid", "sfx-enabled");
    var onLabel = element("label", "", opts.label || "Sound effects made in code (off by default)");
    onLabel.setAttribute("for", on.id);
    rowOn.appendChild(on);
    rowOn.appendChild(onLabel);

    var rowVol = element("div", "noyvj-sfx-row");
    var volLabel = element("label", "", "Volume");
    var vol = element("input");
    vol.type = "range";
    vol.min = "0";
    vol.max = "100";
    vol.step = "5";
    vol.id = id + "-volume";
    vol.setAttribute("data-testid", "sfx-volume");
    volLabel.setAttribute("for", vol.id);
    var volOut = element("output", "noyvj-sfx-out");
    volOut.setAttribute("for", vol.id);
    rowVol.appendChild(volLabel);
    rowVol.appendChild(vol);
    rowVol.appendChild(volOut);

    var rowReduce = element("div", "noyvj-sfx-row");
    var red = element("input");
    red.type = "checkbox";
    red.id = id + "-reduce";
    red.setAttribute("data-testid", "sfx-reduce");
    var redLabel = element("label", "", "Reduce sounds (quieter, shorter, no ambient hum)");
    redLabel.setAttribute("for", red.id);
    rowReduce.appendChild(red);
    rowReduce.appendChild(redLabel);

    var rowTest = element("div", "noyvj-sfx-row");
    var test = element("button", "noyvj-sfx-test", "Play a sample");
    test.type = "button";
    test.id = id + "-test";
    test.setAttribute("data-testid", "sfx-test");
    rowTest.appendChild(test);

    var note = element("p", "noyvj-sfx-note");
    note.id = id + "-note";
    note.setAttribute("role", "status");
    note.setAttribute("aria-live", "polite");
    on.setAttribute("aria-describedby", note.id);

    wrap.appendChild(rowOn);
    wrap.appendChild(rowVol);
    wrap.appendChild(rowReduce);
    wrap.appendChild(rowTest);
    wrap.appendChild(note);

    function refresh() {
      var s = snapshot();
      if (root.document.activeElement !== on) on.checked = s.enabled;
      if (root.document.activeElement !== vol) vol.value = String(Math.round(s.volume * 100));
      if (root.document.activeElement !== red) red.checked = s.reduce;
      volOut.textContent = Math.round(s.volume * 100) + "%";
      vol.setAttribute("aria-valuetext", Math.round(s.volume * 100) + " percent");
      if (!supported()) {
        on.disabled = vol.disabled = red.disabled = test.disabled = true;
        note.textContent = "This browser cannot make sound. The game works exactly the same without it.";
        return;
      }
      vol.disabled = !s.enabled;
      red.disabled = !s.enabled;
      note.textContent = !s.enabled
        ? "Sound is off. Nothing plays until you turn it on, and nothing in the game depends on it."
        : "Sound is on at " + Math.round(s.volume * 100) + "%." + (s.reduce ? " Reduced: quieter, shorter, and no ambient hum." : "") + " Sound pauses while this tab is hidden.";
    }

    on.addEventListener("change", function () {
      markGesture();
      setEnabled(on.checked);
      if (on.checked) play("tap");
    });
    vol.addEventListener("input", function () { setVolume(Number(vol.value) / 100); });
    vol.addEventListener("change", function () { play("tap"); });
    red.addEventListener("change", function () { setReduce(red.checked); });
    test.addEventListener("click", function () {
      markGesture();
      if (!enabled()) { note.textContent = "Turn sound on first, then play the sample."; return; }
      play("confirm");
    });

    var off = onChange(refresh);
    refresh();
    var entry = { element: wrap, off: off };
    controls.push(entry);
    wrap.refresh = refresh;
    wrap.destroy = function () { off(); var i = controls.indexOf(entry); if (i >= 0) controls.splice(i, 1); if (wrap.parentNode) wrap.parentNode.removeChild(wrap); };
    return wrap;
  }

  // ---------- wiring (cheap listeners; no audio object exists until sound is on and the player has acted) ----------

  var ownSrc = root.document && root.document.currentScript && root.document.currentScript.src || "";

  if (root.document) {
    ["pointerup", "click", "keydown", "touchend"].forEach(function (type) {
      root.document.addEventListener(type, markGesture, { capture: true, passive: true });
    });
    root.document.addEventListener("visibilitychange", function () { syncAudio(); if (!hidden()) markGestureIfSeen(); });
    root.addEventListener("storage", function (event) {
      if (!event.key || event.key === KEYS.enabled || event.key === KEYS.volume || event.key === KEYS.reduce) changed();
    });
    root.addEventListener("pagehide", function () { stopHum(0.05); });
  }
  function markGestureIfSeen() { if (gestureSeen) { resumeContext(); applyMasterGain(); startHum(); } }

  root.NoyvjSfx = {
    play: play,
    enabled: enabled,
    volume: volume,
    reduce: reduce,
    setEnabled: setEnabled,
    setVolume: setVolume,
    setReduce: setReduce,
    control: control,
    onChange: onChange,
    supported: supported,
    stopAll: stopAll,
    cueNames: function () { return Object.keys(CUES); },
    _testing: {
      KEYS: KEYS,
      CUES: CUES,
      MAX_MASTER: MAX_MASTER,
      MAX_PEAK_SUM: MAX_PEAK_SUM,
      MAX_LIVE_VOICES: MAX_LIVE_VOICES,
      ENV_FLOOR: ENV_FLOOR,
      masterGain: masterGain,
      envelope: envelope,
      peakSum: peakSum,
      cueDuration: cueDuration,
      reduceCue: reduceCue,
      planCue: planCue,
      status: function () { return { gestureSeen: gestureSeen, contextCreated: Boolean(ctx), contextState: ctx ? ctx.state : null, humRunning: Boolean(hum), humWanted: humWanted, live: live.length }; },
    },
  };
}).call(this);
