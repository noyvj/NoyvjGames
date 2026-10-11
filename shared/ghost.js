/*
 * Shared ghost-run line, browser side (planning/TODO.md Z-3b). The Python twin is shared/ghost.py:
 * the SAME trace format, cleaning, turn reading, comparison and summary sentence, pinned together by
 * shared/tests/test_ghost.py and shared/tests/test_ghost_browser.py. Notes and an example:
 * planning/SHARED-COMPONENTS.md, section "Ghost runs".
 *
 *   <script src="../../shared/ghost.js"></script>
 *
 * A trace is { v: 1, turns: 40, values: [...], label: "Run 3" } (one number per turn, at most 120
 * numbers; a longer run is thinned evenly). A game's Python side records it with ghost.Recorder and
 * saves it; this file only READS a trace (it cleans anything it is given) and draws it.
 *
 * window.NoyvjGhost:
 *   draw(svg, opts)      a faint dashed, labelled line laid BEHIND the chart's own lines. Returns a
 *                        controller { show(), hide(), toggle([on]), isOn(), update(opts), summary(),
 *                        text(), destroy(), element }.
 *     opts.trace         the stored trace (cleaned here; nothing usable = nothing drawn)
 *     opts.live          the live run's per-turn numbers (for the spoken summary)
 *     opts.turns         how many turns the chart's x axis spans (default: live length, else the trace's)
 *     opts.x             { left, right } pixels in the svg's own coordinates, or a function turn -> x
 *     opts.y             { top, bottom, min, max } (min at bottom), or a function value -> y
 *     opts.label         legend text on the line (default: the trace's label, else "Best run")
 *     opts.who           how the summary names the ghost (default "your best run")
 *     opts.higherIsBetter (default true)   opts.unit (e.g. "%")   opts.on (default true)
 *     opts.summaryEl     an element that receives the summary sentence (textContent; give it
 *                        role="status" / aria-live in the page if it should be announced)
 *     opts.testId        data-testid for the group (default "ghost-line")
 *   bindToggle(input, ghost[, { storageKey }])   wire a checkbox to show/hide; remembers the choice
 *                        in localStorage when storageKey is given (wrapped in try/catch)
 *   sanitise / load / valueAt / liveSeries / compare / summary / formatNumber / cleanNumber / cleanLabel
 *                        the same functions as ghost.py (snake_case aliases exist)
 *
 * The line is never colour alone: it is dashed, labelled in text, and the group has a title and an
 * aria-label with the summary. It ignores the pointer, so it never blocks the chart's own tooltips.
 * Text is only ever written with textContent / setAttribute. Nothing here calls the network.
 */
(function () {
  "use strict";

  const TRACE_VERSION = 1;
  const MAX_LEN = 120;
  const MIN_POINTS = 2;
  const MAX_TURNS = 100000;
  const HARD_INPUT_LIMIT = 5000;
  const MAX_ABS = 1e12;
  const DIGITS = 2;
  const SCALE = Math.pow(10, DIGITS);
  const LABEL_MAX = 40;
  const LEVEL_EPSILON = 0.005;
  const MAX_DRAWN_POINTS = 400;
  const SVG_NS = "http://www.w3.org/2000/svg";

  // ---- numbers (identical rules to ghost.py) -----------------------------------------------------
  function round(x) { return Math.floor(x * SCALE + 0.5) / SCALE; }

  function cleanNumber(value) {
    if (typeof value !== "number" || !isFinite(value)) return null;
    let x = Math.max(-MAX_ABS, Math.min(MAX_ABS, value));
    x = round(x);
    return x === 0 ? 0 : x;
  }

  function thin(values, limit) {
    const n = values.length;
    if (n <= limit) return values.slice();
    if (limit === 1) return [values[n - 1]];
    const out = [];
    for (let i = 0; i < limit; i++) out.push(values[Math.floor(i * (n - 1) / (limit - 1) + 0.5)]);
    return out;
  }

  function sanitise(raw, maxLen) {
    if (!Array.isArray(raw) || raw.length > HARD_INPUT_LIMIT) return [];
    const out = [];
    for (const item of raw) {
      const x = cleanNumber(item);
      if (x !== null) out.push(x);
    }
    return thin(out, Math.max(1, Math.trunc(maxLen === undefined ? MAX_LEN : maxLen)));
  }

  const CONTROL = /[\u0000-\u001f\u007f-\u009f\u2028\u2029]/g;
  const SPACE = /[ \t\r\n\f\v\u00a0\u2000-\u200b\u202f\u205f\u3000\ufeff]+/g;

  function cleanLabel(label) {
    if (typeof label !== "string") return "";
    const text = label.replace(CONTROL, " ").replace(SPACE, " ").replace(/^ +| +$/g, "");
    return Array.from(text).slice(0, LABEL_MAX).join("").replace(/ +$/, "");
  }

  // ---- the trace ---------------------------------------------------------------------------------
  function isObject(x) { return x !== null && typeof x === "object" && !Array.isArray(x); }

  function load(data) {
    if (!isObject(data)) return null;
    let values = sanitise(data.values);
    if (values.length < MIN_POINTS) return null;
    let turns = data.turns;
    if (typeof turns !== "number" || !isFinite(turns)) {
      turns = values.length;
    } else {
      turns = Math.trunc(turns);
      if (turns < 1) turns = values.length;
    }
    turns = Math.min(turns, MAX_TURNS);
    if (turns < values.length) {
      values = thin(values, Math.max(MIN_POINTS, turns));
      turns = Math.max(turns, values.length);
    }
    if (turns < MIN_POINTS) return null;
    return { v: TRACE_VERSION, turns: turns, values: values, label: cleanLabel(data.label) };
  }

  function makeTrace(values, turns, label) {
    if (!Array.isArray(values) || values.length > HARD_INPUT_LIMIT) return null;
    if (turns === undefined || turns === null) turns = values.filter((v) => cleanNumber(v) !== null).length;
    return load({ v: TRACE_VERSION, turns: turns, values: values, label: label || "" });
  }

  function valueAt(trace, turn) {
    const t = load(trace);
    if (t === null || typeof turn !== "number" || !isFinite(turn)) return null;
    turn = Math.trunc(turn);
    const n = t.values.length;
    const total = t.turns;
    if (turn < 1 || turn > total) return null;
    if (total <= n) return t.values[turn - 1];
    return t.values[Math.floor((turn - 1) * (n - 1) / (total - 1) + 0.5)];
  }

  // ---- comparing ---------------------------------------------------------------------------------
  function liveSeries(live) {
    if (!Array.isArray(live) || !live.length || live.length > HARD_INPUT_LIMIT) return null;
    const out = [];
    let last = 0;
    for (const item of live) {
      const x = cleanNumber(item);
      if (x !== null) last = x;
      out.push(last);
    }
    return out;
  }

  function compare(live, trace, higherIsBetter) {
    const t = load(trace);
    if (t === null) return null;
    const nums = liveSeries(live);
    if (nums === null) return null;
    const sign = higherIsBetter === false ? -1 : 1;
    let bestTurn = null;
    let bestGap = 0;
    for (let i = 1; i <= nums.length; i++) {
      const g = valueAt(t, i);
      if (g === null) continue;
      const behindBy = sign * (g - nums[i - 1]);
      if (behindBy > bestGap) { bestTurn = i; bestGap = round(behindBy); }
    }
    const turn = nums.length;
    const mine = nums[turn - 1];
    const ghost = valueAt(t, turn);
    if (ghost === null) {
      return { turn: turn, live: mine, ghost: null, gap: null, status: "ended", lead: 0, best_turn: bestTurn, best_gap: bestGap };
    }
    const gap = round(mine - ghost);
    let lead = round(sign * gap);
    let status;
    if (Math.abs(lead) < LEVEL_EPSILON) { status = "level"; lead = 0; }
    else if (lead > 0) { status = "ahead"; }
    else { status = "behind"; lead = round(-lead); }
    return { turn: turn, live: mine, ghost: ghost, gap: gap, status: status, lead: lead, best_turn: bestTurn, best_gap: bestGap };
  }

  function formatNumber(x) {
    x = round(x);
    if (x === Math.trunc(x)) return String(x === 0 ? 0 : x);
    return x.toFixed(2).replace(/0+$/, "").replace(/\.$/, "");
  }

  function summary(result, label, unit) {
    if (!result) return "ghost: no earlier run to race yet";
    const who = typeof label === "string" && label.trim() ? label.trim() : "your best run";
    const turn = result.turn;
    if (result.status === "ended") return "ghost: " + who + " ended before turn " + turn;
    if (result.status === "level") return "ghost: level with " + who + " at turn " + turn;
    const amount = formatNumber(result.lead) + (typeof unit === "string" ? unit : "");
    if (result.status === "ahead") return "ghost: you are " + amount + " ahead of " + who + " at turn " + turn;
    return "ghost: " + who + " was " + amount + " ahead at turn " + turn;
  }

  // ---- drawing -----------------------------------------------------------------------------------
  function svgEl(name, attrs) {
    const node = document.createElementNS(SVG_NS, name);
    for (const k in attrs) node.setAttribute(k, attrs[k]);
    return node;
  }

  function xMapper(x, turns) {
    if (typeof x === "function") return x;
    if (!x || typeof x.left !== "number" || typeof x.right !== "number") return null;
    return (turn) => (turns <= 1 ? x.left : x.left + (turn - 1) * (x.right - x.left) / (turns - 1));
  }

  function yMapper(y) {
    if (typeof y === "function") return y;
    if (!y || ![y.top, y.bottom, y.min, y.max].every((n) => typeof n === "number" && isFinite(n))) return null;
    return (value) => {
      if (y.max === y.min) return (y.top + y.bottom) / 2;
      const f = (value - y.min) / (y.max - y.min);
      return Math.max(Math.min(y.top, y.bottom), Math.min(Math.max(y.top, y.bottom), y.bottom - f * (y.bottom - y.top)));
    };
  }

  function draw(svg, options) {
    if (!svg || typeof svg.insertBefore !== "function") return null;
    let opts = Object.assign({}, options || {});
    let on = opts.on !== false;
    let group = null;
    let target = svg;

    function build() {
      if (group && group.parentNode) group.parentNode.removeChild(group);
      group = null;
      const trace = load(opts.trace);
      const live = liveSeries(opts.live);
      const result = trace && live ? compare(live, trace, opts.higherIsBetter) : null;
      const name = cleanLabel(opts.label) || (trace && trace.label) || "Best run";
      const unit = typeof opts.unit === "string" ? opts.unit : "";
      const sentence = trace ? summary(result, opts.who || "", unit) : summary(null);
      ctl.text = sentence;
      if (opts.summaryEl) opts.summaryEl.textContent = on ? sentence : "";
      if (!trace) return;
      const turns = Math.max(1, Math.trunc(opts.turns || (live ? live.length : trace.turns)));
      const mapX = xMapper(opts.x, turns);
      const mapY = yMapper(opts.y);
      if (!mapX || !mapY) return;
      const last = Math.min(trace.turns, turns);
      const count = Math.min(last, MAX_DRAWN_POINTS);
      const points = [];
      let end = null;
      for (let k = 0; k < count; k++) {
        const turn = count === 1 ? 1 : 1 + Math.floor(k * (last - 1) / (count - 1));
        const px = mapX(turn);
        const py = mapY(valueAt(trace, turn));
        if (typeof px === "number" && typeof py === "number" && isFinite(px) && isFinite(py)) {
          points.push(px.toFixed(1) + "," + py.toFixed(1));
          end = [px, py];
        }
      }
      group = svgEl("g", {
        "class": "noyvj-ghost", "data-noyvj-ghost": "", "data-testid": opts.testId || "ghost-line",
        "pointer-events": "none", "role": "img", "aria-label": sentence,
      });
      const title = svgEl("title", {});
      title.textContent = sentence;
      group.appendChild(title);
      if (points.length >= 2) {
        group.appendChild(svgEl("polyline", {
          "class": "noyvj-ghost-line", "points": points.join(" "), "fill": "none",
          "stroke": "var(--ghost-color, #9aa4c8)", "stroke-width": "2", "stroke-dasharray": "6 4",
          "stroke-linecap": "round", "stroke-linejoin": "round", "opacity": "0.6",
        }));
        const text = svgEl("text", {
          "class": "noyvj-ghost-label", "x": (end[0] - 4).toFixed(1), "y": (end[1] - 6).toFixed(1),
          "text-anchor": "end", "font-size": "11", "fill": "var(--ghost-color, #9aa4c8)",
          "stroke": "var(--ghost-halo, rgba(10,12,24,0.8))", "stroke-width": "3", "paint-order": "stroke",
          "opacity": "0.9",
        });
        text.textContent = "Ghost: " + name;
        group.appendChild(text);
      }
      group.style.display = on ? "" : "none";
      group.setAttribute("aria-hidden", on ? "false" : "true");
      target.insertBefore(group, target.firstChild);
    }

    function setOn(next) {
      on = !!next;
      if (group) {
        group.style.display = on ? "" : "none";
        group.setAttribute("aria-hidden", on ? "false" : "true");
      }
      if (opts.summaryEl) opts.summaryEl.textContent = on ? ctl.text : "";
      if (typeof opts.onChange === "function") opts.onChange(on);
      return on;
    }

    const ctl = {
      text: "",
      show() { return setOn(true); },
      hide() { return setOn(false); },
      toggle(next) { return setOn(next === undefined ? !on : next); },
      isOn() { return on; },
      /** Redraw with changed options (e.g. a new svg after the game re-rendered, new live numbers). */
      update(more) {
        if (more && more.svg) { target = more.svg; }
        opts = Object.assign(opts, more || {});
        delete opts.svg;
        build();
        return ctl;
      },
      summary() { return ctl.text; },
      destroy() {
        if (group && group.parentNode) group.parentNode.removeChild(group);
        group = null;
        if (opts.summaryEl) opts.summaryEl.textContent = "";
      },
      get element() { return group; },
    };
    build();
    return ctl;
  }

  function bindToggle(input, ghost, options) {
    if (!input || !ghost) return null;
    const key = options && options.storageKey;
    if (key) {
      try {
        const saved = window.localStorage.getItem(key);
        if (saved === "1") ghost.show();
        else if (saved === "0") ghost.hide();
      } catch (e) { /* storage blocked: the default stands */ }
    }
    input.checked = ghost.isOn();
    const onChange = () => {
      ghost.toggle(!!input.checked);
      if (key) { try { window.localStorage.setItem(key, input.checked ? "1" : "0"); } catch (e) { /* ignore */ } }
      if (input.checked && window.NoyvjAnnounce && typeof window.NoyvjAnnounce.say === "function") {
        window.NoyvjAnnounce.say(ghost.summary());
      }
    };
    input.addEventListener("change", onChange);
    return { destroy() { input.removeEventListener("change", onChange); } };
  }

  window.NoyvjGhost = {
    TRACE_VERSION: TRACE_VERSION, MAX_LEN: MAX_LEN, MAX_TURNS: MAX_TURNS, HARD_INPUT_LIMIT: HARD_INPUT_LIMIT,
    draw: draw, bindToggle: bindToggle,
    sanitise: sanitise, load: load, makeTrace: makeTrace, valueAt: valueAt, liveSeries: liveSeries,
    compare: compare, summary: summary, formatNumber: formatNumber, cleanNumber: cleanNumber, cleanLabel: cleanLabel,
    make_trace: makeTrace, value_at: valueAt, live_series: liveSeries, format_number: formatNumber,
    clean_number: cleanNumber, clean_label: cleanLabel,
  };
})();
