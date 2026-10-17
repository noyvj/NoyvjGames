// R4-THMO-2: on phones, a bar for splitting Region A's funds. The bar is the funds laid out as a strip: Output, then
// Preservation, then Monitoring, then whatever is left over. Two handles drag the Output and Preservation edges, the big
// plus and minus buttons change one category by one unit, and "Invest the plan" makes the investments by pressing the game's
// own Invest buttons (so every rule, render and achievement is the game's). The plan lives only on this page: nothing is
// spent, saved or lost until that button, and Clear plan drops it. Costs and funds are read from the page, not copied.
(function () {
  "use strict";
  var details = document.getElementById("mobile-invest-details");
  var track = document.getElementById("mobile-invest-track");
  if (!details || !track) return;
  var CATS = ["output", "preserve", "monitor"];
  var NAMES = { output: "Output", preserve: "Preservation", monitor: "Monitoring" };
  var FALLBACK_COST = { output: 20, preserve: 25, monitor: 20 };
  var plan = { output: 0, preserve: 0, monitor: 0 };

  var fills = {};
  CATS.forEach(function (cat) { fills[cat] = track.querySelector(".mobile-invest-fill--" + cat); });
  var handleA = document.getElementById("mobile-invest-handle-a");
  var handleB = document.getElementById("mobile-invest-handle-b");
  var summary = document.getElementById("mobile-invest-summary");
  var applyButton = document.getElementById("mobile-invest-apply");
  var clearButton = document.getElementById("mobile-invest-clear");
  var segs = {};
  Array.prototype.forEach.call(details.querySelectorAll(".mobile-invest-seg"), function (seg) { segs[seg.getAttribute("data-cat")] = seg; });
  var fundsEl = document.getElementById("funds-display");

  function funds() {
    var digits = fundsEl ? fundsEl.textContent.replace(/[^0-9]/g, "") : "";
    return digits ? parseInt(digits, 10) : 0;
  }

  function cost(cat) {
    var button = document.getElementById(cat + "-invest-button");
    var digits = button ? (button.textContent.match(/\((\d+)\)/) || [])[1] : null;
    var value = digits ? parseInt(digits, 10) : FALLBACK_COST[cat];
    return value > 0 ? value : FALLBACK_COST[cat];
  }

  function spent() {
    return CATS.reduce(function (sum, cat) { return sum + plan[cat] * cost(cat); }, 0);
  }

  // The most more units of `cat` the rest of the plan leaves room for.
  function room(cat) {
    return Math.max(0, Math.floor((funds() - spent()) / cost(cat)));
  }

  function fit() {
    // Funds went down (an Invest button elsewhere, a new game): shrink the plan from the right until it is affordable.
    ["monitor", "preserve", "output"].forEach(function (cat) {
      while (plan[cat] > 0 && spent() > funds()) plan[cat] -= 1;
    });
  }

  function percent(amount, total) {
    return total > 0 ? Math.min(100, (amount / total) * 100) : 0;
  }

  function describe() {
    var parts = CATS.filter(function (cat) { return plan[cat] > 0; }).map(function (cat) { return plan[cat] + " " + NAMES[cat]; });
    if (!parts.length) return "No plan yet. You have " + funds() + " funds. Drag a handle or press a plus.";
    return "Plan: " + parts.join(", ") + " for " + spent() + " of " + funds() + " funds. Nothing is spent until you press Invest the plan.";
  }

  function render() {
    var total = funds();
    var edge = 0;
    var edges = {};
    CATS.forEach(function (cat) {
      var width = percent(plan[cat] * cost(cat), total);
      fills[cat].style.left = edge + "%";
      fills[cat].style.width = width + "%";
      edge += width;
      edges[cat] = edge;
      var seg = segs[cat];
      seg.querySelector(".mobile-invest-count").textContent = String(plan[cat]);
      seg.querySelector("[data-dir='-1']").disabled = plan[cat] <= 0;
      seg.querySelector("[data-dir='1']").disabled = room(cat) < 1;
    });
    handleA.style.left = edges.output + "%";
    handleB.style.left = edges.preserve + "%";
    [[handleA, "output"], [handleB, "preserve"]].forEach(function (pair) {
      var cat = pair[1];
      pair[0].setAttribute("aria-valuemin", "0");
      pair[0].setAttribute("aria-valuemax", String(plan[cat] + room(cat)));
      pair[0].setAttribute("aria-valuenow", String(plan[cat]));
      pair[0].setAttribute("aria-valuetext", NAMES[cat] + ": " + plan[cat] + " units, " + plan[cat] * cost(cat) + " funds");
    });
    summary.textContent = describe();
    var any = spent() > 0;
    applyButton.disabled = !any;
    clearButton.disabled = !any;
  }

  function setPlan(cat, units) {
    plan[cat] = Math.max(0, Math.min(plan[cat] + room(cat), units));
    render();
  }

  // Dragging a handle: the pointer's place on the strip, as funds, becomes that edge.
  function fraction(event) {
    var rect = track.getBoundingClientRect();
    return rect.width > 0 ? Math.max(0, Math.min(1, (event.clientX - rect.left) / rect.width)) : 0;
  }

  function onDrag(handle, event) {
    var target = fraction(event) * funds();
    if (handle === handleA) {
      setPlan("output", Math.round(target / cost("output")));
    } else {
      setPlan("preserve", Math.round((target - plan.output * cost("output")) / cost("preserve")));
    }
  }

  [handleA, handleB].forEach(function (handle) {
    var active = false;
    handle.addEventListener("pointerdown", function (event) {
      active = true;
      try { handle.setPointerCapture(event.pointerId); } catch (e) { /* the drag still works on the handle */ }
      event.preventDefault();
    });
    handle.addEventListener("pointermove", function (event) { if (active) onDrag(handle, event); });
    ["pointerup", "pointercancel"].forEach(function (name) {
      handle.addEventListener(name, function () { active = false; });
    });
    handle.addEventListener("keydown", function (event) {
      var cat = handle === handleA ? "output" : "preserve";
      var next = null;
      if (event.key === "ArrowRight" || event.key === "ArrowUp") next = plan[cat] + 1;
      else if (event.key === "ArrowLeft" || event.key === "ArrowDown") next = plan[cat] - 1;
      else if (event.key === "Home") next = 0;
      if (next === null) return;
      event.preventDefault();
      setPlan(cat, next);
    });
  });

  Array.prototype.forEach.call(details.querySelectorAll(".mobile-invest-step"), function (button) {
    button.addEventListener("click", function () {
      var cat = button.closest(".mobile-invest-seg").getAttribute("data-cat");
      setPlan(cat, plan[cat] + parseInt(button.getAttribute("data-dir"), 10));
    });
  });

  clearButton.addEventListener("click", function () {
    CATS.forEach(function (cat) { plan[cat] = 0; });
    render();
  });

  applyButton.addEventListener("click", function () {
    var made = [];
    CATS.forEach(function (cat) {
      var button = document.getElementById(cat + "-invest-button");
      var count = 0;
      while (button && plan[cat] > 0 && !button.disabled) {
        button.click();
        plan[cat] -= 1;
        count += 1;
      }
      if (count) made.push(count + " " + NAMES[cat]);
    });
    fit();
    render();
    if (made.length) summary.textContent = "Invested: " + made.join(", ") + ". " + describe();
  });

  if (fundsEl) {
    // The game redraws Funds after every round and every investment: keep the bar honest about what is affordable now.
    new MutationObserver(function () { fit(); render(); }).observe(fundsEl, { childList: true, characterData: true, subtree: true });
  }
  render();
})();
