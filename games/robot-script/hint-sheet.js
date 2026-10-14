/* Robot Script -- R4-RSMO-10: on a phone the hint button opens a bottom sheet that shows the hints so far and reveals one
 * more line (nudge, then hint, then answer) for each long press of its button. Keyboard and screen-reader players press
 * Enter or Space on the same button instead of holding it. The ladder itself is the engine's own `hint` action, asked
 * for through app.js (robotScriptHintRequest); hints are free and never touch a medal. Wide screens keep the inline hints. */
(function () {
  "use strict";
  var HOLD_MS = 500;
  var sheet, lines, reveal, answerBtn, note;
  var last = null;
  var holdTimer = null;
  var held = false;

  function isPhone() {
    return Boolean(window.matchMedia && window.matchMedia("(max-width: 600px)").matches);
  }

  function render(h) {
    last = h;
    if (!sheet) return;
    lines.textContent = "";
    var rows = [];
    if (h.nudge) rows.push("Nudge: " + h.nudge);
    if (h.hint) rows.push("Hint: " + h.hint);
    if (h.answer) rows.push("Answer: " + h.answer.lines.join(" / "));
    if (!rows.length) rows.push("No hints yet. They are free and never touch a medal.");
    rows.forEach(function (text) {
      var p = document.createElement("p");
      p.className = "hint-sheet-line";
      p.textContent = text;
      lines.appendChild(p);
    });
    var more = h.rung < h.max;
    reveal.hidden = !more;
    if (more) reveal.textContent = "Hold to reveal the next line (" + (h.next || "more") + ")";
    answerBtn.hidden = !h.answer;
    if (h.max < 3 && !more) note.textContent = "Hard has no answer step: that is every hint there is.";
    else note.textContent = "";
  }

  function ask() {
    document.dispatchEvent(new CustomEvent("robotScriptHintRequest"));
  }

  function open() {
    sheet.hidden = false;
    if (last) render(last);
    (reveal.hidden ? sheet.querySelector("#hint-sheet-close") : reveal).focus();
  }
  function close() {
    sheet.hidden = true;
    var btn = document.getElementById("hint-button");
    if (btn && !btn.hidden) btn.focus();
  }

  function build() {
    sheet = document.createElement("div");
    sheet.id = "hint-sheet";
    sheet.className = "hint-sheet";
    sheet.setAttribute("role", "region");   // not "dialog": app.js stops the F/L/R shortcuts while a dialog exists
    sheet.setAttribute("aria-label", "Hints");
    sheet.hidden = true;
    var head = document.createElement("div");
    head.className = "hint-sheet-head";
    var title = document.createElement("strong");
    title.textContent = "Hints";
    var closeBtn = document.createElement("button");
    closeBtn.type = "button";
    closeBtn.id = "hint-sheet-close";
    closeBtn.textContent = "Close";
    closeBtn.addEventListener("click", close);
    head.appendChild(title);
    head.appendChild(closeBtn);
    lines = document.createElement("div");
    lines.id = "hint-sheet-lines";
    lines.setAttribute("aria-live", "polite");
    reveal = document.createElement("button");
    reveal.type = "button";
    reveal.id = "hint-sheet-reveal";
    reveal.className = "primary";
    answerBtn = document.createElement("button");
    answerBtn.type = "button";
    answerBtn.id = "hint-sheet-answer";
    answerBtn.textContent = "Put the answer in my list";
    answerBtn.hidden = true;
    answerBtn.addEventListener("click", function () {
      document.dispatchEvent(new CustomEvent("robotScriptHintAnswer"));
      close();
    });
    note = document.createElement("p");
    note.className = "note";
    note.id = "hint-sheet-note";
    note.setAttribute("aria-live", "polite");
    sheet.appendChild(head);
    sheet.appendChild(lines);
    sheet.appendChild(reveal);
    sheet.appendChild(answerBtn);
    sheet.appendChild(note);
    document.body.appendChild(sheet);

    reveal.addEventListener("pointerdown", function () {
      held = false;
      clearTimeout(holdTimer);
      holdTimer = setTimeout(function () { held = true; ask(); }, HOLD_MS);
    });
    ["pointerup", "pointercancel", "pointerleave"].forEach(function (name) {
      reveal.addEventListener(name, function () { clearTimeout(holdTimer); });
    });
    reveal.addEventListener("contextmenu", function (e) { e.preventDefault(); });   // a long press must not open the menu
    reveal.addEventListener("click", function (e) {
      if (e.detail === 0) { ask(); return; }                  // Enter or Space on the focused button
      if (held) { held = false; return; }                      // the long press already asked
      note.textContent = "Press and hold the button to reveal the next line.";
    });
    sheet.addEventListener("keydown", function (e) { if (e.key === "Escape") { e.stopPropagation(); close(); } });
  }

  document.addEventListener("DOMContentLoaded", function () {
    build();
    document.addEventListener("robotScriptHints", function (e) { render(e.detail); });
    // capture phase: on a phone the hint button opens the sheet instead of climbing a rung at once
    document.addEventListener("click", function (e) {
      var btn = e.target.closest && e.target.closest("#hint-button");
      if (!btn || !isPhone()) return;
      e.preventDefault();
      e.stopImmediatePropagation();
      open();
    }, true);
  });
})();
