/* Signal, part 4 of 4 (loads last): user actions, wire(), the hold-to-aim magnifier, init() and window.SignalApp. */
(function () {
  "use strict";

  var A = window.SignalPage;
  var $ = A.$, GAME = A.GAME, LS_STATE = A.LS_STATE, LS_VIEW = A.LS_VIEW, SLOW_MODES = A.SLOW_MODES, act = A.act,
      applyResponse = A.applyResponse, defaultView = A.defaultView, el = A.el, focusCursor = A.focusCursor,
      isCachedValid = A.isCachedValid, jsonParse = A.jsonParse, label = A.label,
      loadCachedView = A.loadCachedView, lsGet = A.lsGet, lsRemove = A.lsRemove, openArchive = A.openArchive,
      render = A.render, renderAchievements = A.renderAchievements, renderBoard = A.renderBoard,
      renderCalendar = A.renderCalendar, renderResult = A.renderResult, renderStatus = A.renderStatus,
      renderTabs = A.renderTabs, requestStats = A.requestStats, restoreResumeState = A.restoreResumeState,
      saveResumeState = A.saveResumeState, send = A.send, setMessage = A.setMessage, startEngine = A.startEngine,
      timings = A.timings, utcToday = A.utcToday;
  var jump = { col: null, row: "" };

  // ---- user actions ---------------------------------------------------------------------
  function doTool(r, c, forceMark) {
    if (A.view.status !== "inprogress") { setMessage("This puzzle is finished. Open another from the tabs or the archive."); return; }
    A.cursor = { r: r, c: c };
    saveResumeState();
    if (forceMark || A.tool === "mark") act({ action: "mark", r: r, c: c });
    else act({ action: "ping", r: r, c: c });
  }

  function confirmThen(id, message, confirmLabel, allowSkip, fn) {
    if (window.ConfirmDialog) window.ConfirmDialog.ask({ id: id, message: message, confirmLabel: confirmLabel, allowSkip: allowSkip, onConfirm: fn });
    else fn();
  }

  function wire() {
    var boardEl = $("board");

    // ---- radial menu (mobile long-press) ------------------------------
    var rMenu = null, rTimer = null, rTarget = null, rPos = { x: 0, y: 0 };
    if (window.innerWidth <= 600) {
      rMenu = document.createElement("div");
      rMenu.id = "radial-menu";
      rMenu.innerHTML = '<button data-action="ping">Ping</button><button data-action="mark">Mark</button><button data-action="clear">Clear</button>';
      document.body.appendChild(rMenu);

      function showRMenu(x, y) {
        hideMagnifier();
        var rect = rMenu.getBoundingClientRect();
        var left = x + 10;
        var top = y - 60;
        if (left + rect.width > window.innerWidth) left = x - rect.width - 10;
        if (top < 0) top = y + 20;
        rMenu.style.left = left + "px";
        rMenu.style.top = top + "px";
        rMenu.style.display = "flex";
      }
      function hideRMenu() { rMenu.style.display = "none"; rTimer = null; rTarget = null; }

      boardEl.addEventListener("pointerdown", function (ev) {
        if (ev.pointerType !== "touch") return;
        var btn = ev.target.closest(".cell");
        if (!btn || !A.view || A.view.status !== "inprogress") return;
        rTarget = btn;
        rPos = { x: ev.clientX, y: ev.clientY };
        clearTimeout(rTimer);
        rTimer = setTimeout(function () { showRMenu(ev.clientX, ev.clientY); }, 400);
      });
      boardEl.addEventListener("pointermove", function (ev) {
        if (!rTarget || !rTimer) return;
        if (Math.abs(ev.clientX - rPos.x) > 20 || Math.abs(ev.clientY - rPos.y) > 20) { clearTimeout(rTimer); rTimer = null; }
      });
      boardEl.addEventListener("pointerup", function () { if (rTimer) { clearTimeout(rTimer); rTimer = null; } });
      document.addEventListener("pointerdown", function (ev) { if (!rMenu.contains(ev.target)) hideRMenu(); });

      rMenu.addEventListener("click", function (ev) {
        var btn = ev.target.closest("button");
        if (!btn || !rTarget) return;
        var r = parseInt(rTarget.getAttribute("data-r"), 10);
        var c = parseInt(rTarget.getAttribute("data-c"), 10);
        var action = btn.getAttribute("data-action");
        hideRMenu();
        if (action === "ping") doTool(r, c, false);
        else if (action === "mark") doTool(r, c, true);
        else if (action === "clear") act({ action: "clear_marks" });
      });
    }

    boardEl.addEventListener("click", function (ev) {
      var btn = ev.target.closest(".cell");
      if (!btn) return;
      doTool(parseInt(btn.getAttribute("data-r"), 10), parseInt(btn.getAttribute("data-c"), 10), ev.shiftKey);
    });
    boardEl.addEventListener("contextmenu", function (ev) {
      var btn = ev.target.closest(".cell");
      if (!btn) return;
      ev.preventDefault();
      doTool(parseInt(btn.getAttribute("data-r"), 10), parseInt(btn.getAttribute("data-c"), 10), true);
    });
    boardEl.addEventListener("keydown", function (ev) {
      var btn = ev.target.closest(".cell");
      if (!btn || ev.ctrlKey || ev.metaKey || ev.altKey) return;
      var n = A.view.board.n;
      var r = parseInt(btn.getAttribute("data-r"), 10);
      var c = parseInt(btn.getAttribute("data-c"), 10);
      var moved = true;
      if (ev.key === "ArrowUp") r = Math.max(0, r - 1);
      else if (ev.key === "ArrowDown") r = Math.min(n - 1, r + 1);
      else if (ev.key === "ArrowLeft") c = Math.max(0, c - 1);
      else if (ev.key === "ArrowRight") c = Math.min(n - 1, c + 1);
      else moved = false;
      if (moved) {
        ev.preventDefault();
        A.cursor = { r: r, c: c };
        saveResumeState();
        renderBoard();
        focusCursor();
        return;
      }
      if (ev.key === "Enter") { ev.preventDefault(); doTool(r, c, false); return; }
      if (ev.key === " " || ev.key === "Spacebar") { ev.preventDefault(); doTool(r, c, true); return; }
      // Type a column letter then a row number (D4) to jump the cursor.
      if (/^[a-zA-Z]$/.test(ev.key)) {
        var col = ev.key.toUpperCase().charCodeAt(0) - 65;
        if (col < n) { jump = { col: col, row: "" }; A.cursor = { r: A.cursor.r, c: col }; renderBoard(); focusCursor(); ev.preventDefault(); }
      } else if (/^[0-9]$/.test(ev.key) && jump.col !== null) {
        var next = jump.row + ev.key;
        var row = parseInt(next, 10);
        if (row < 1 || row > n) { next = ev.key; row = parseInt(next, 10); }
        if (row >= 1 && row <= n) { jump.row = next; A.cursor = { r: row - 1, c: jump.col }; renderBoard(); focusCursor(); }
        ev.preventDefault();
      }
    });

    $("tool-toggle-button").addEventListener("click", function () {
      A.tool = A.tool === "ping" ? "mark" : "ping";
      saveResumeState();
      renderStatus();
    });
    $("mobile-ping-button").addEventListener("click", function () { A.tool = "ping"; renderStatus(); });
    $("mobile-mark-button").addEventListener("click", function () { A.tool = "mark"; renderStatus(); });

    document.querySelectorAll("[data-mode-tab]").forEach(function (tab) {
      tab.addEventListener("click", function () {
        var t = tab.getAttribute("data-mode-tab");
        if (t === "archive") { $("archive-panel").hidden = false; openArchive(); return; }
        if (t === "practice") {
          $("practice-controls").hidden = false;
          var code = A.currentState && A.currentState.practice && A.currentState.practice.code;
          if (A.view.session.type !== "practice") {
            if (code) act({ action: "practice", code: code });
            else act({ action: "practice", mode: $("practice-preset").value }, { slow: !!SLOW_MODES[$("practice-preset").value] });
          }
          renderTabs();
          return;
        }
        $("practice-controls").hidden = true;
        act({ action: "open", date: utcToday(), mode: t });
      });
    });

    $("today-button").addEventListener("click", function () {
      act({ action: "open", date: utcToday(), mode: "easy" });
    });

    $("practice-new-button").addEventListener("click", function () {
      var mode = $("practice-preset").value;
      var go = function () { act({ action: "practice", mode: mode }, { slow: !!SLOW_MODES[mode] }); };
      if (A.view.session.type === "practice" && A.view.status === "inprogress" && A.view.pings.length) {
        confirmThen("signal-new-practice", "Leave this practice puzzle unfinished and start a new one?", "New puzzle", true, go);
      } else go();
    });
    $("practice-load-button").addEventListener("click", function () {
      var code = $("practice-code").value.trim();
      if (!code) { setMessage("Type a practice code first, for example P-H4K2Q7."); return; }
      act({ action: "practice", code: code }, { slow: true });
    });
    $("practice-code").addEventListener("keydown", function (ev) { if (ev.key === "Enter") $("practice-load-button").click(); });

    $("commit-button").addEventListener("click", function () {
      confirmThen("signal-commit", "Commit these " + A.view.board.k + " markers? You only get one answer.", "Commit", true, function () { act({ action: "commit" }); });
    });
    $("clear-marks-button").addEventListener("click", function () { act({ action: "clear_marks" }); });
    $("give-up-button").addEventListener("click", function () {
      confirmThen("signal-give-up", "Give up and reveal the transmitters? This counts as a loss.", "Give up", false, function () { act({ action: "give_up" }); });
    });
    $("share-button").addEventListener("click", async function () {
      if (!A.engineReady) { setMessage("Receiver warming up..."); return; }
      await act({ action: "share" });
      if (A.lastShareText && navigator.clipboard && navigator.clipboard.writeText) {
        try { await navigator.clipboard.writeText(A.lastShareText); setMessage("Result copied to the clipboard."); } catch (e) { setMessage("Copy the result from the box below."); }
      } else setMessage("Copy the result from the box below.");
    });

    // panels backed by engine or static data
    $("archive-toggle-button").addEventListener("click", function () {
      var panel = $("archive-panel");
      panel.hidden = !panel.hidden;
      if (!panel.hidden) openArchive();
    });
    $("cal-prev-button").addEventListener("click", function () { A.cal.m -= 1; if (A.cal.m < 0) { A.cal.m = 11; A.cal.y -= 1; } renderCalendar(); });
    $("cal-next-button").addEventListener("click", function () { A.cal.m += 1; if (A.cal.m > 11) { A.cal.m = 0; A.cal.y += 1; } renderCalendar(); });
    $("stats-toggle-button").addEventListener("click", function () {
      var panel = $("stats-panel");
      panel.hidden = !panel.hidden;
      if (!panel.hidden) { startEngine(); requestStats(); }
    });
    $("achievements-toggle-button").addEventListener("click", function () {
      var panel = $("achievements-panel");
      panel.hidden = !panel.hidden;
      if (!panel.hidden) { renderAchievements(); if (window.applyAchievementStats) window.applyAchievementStats(); }
    });
    $("changelog-toggle-button").addEventListener("click", function () { $("changelog-panel").hidden = !$("changelog-panel").hidden; });
    $("info-page-toggle-button").addEventListener("click", function () { $("info-page-panel").hidden = !$("info-page-panel").hidden; });

    // settings that live in the save (engine-side)
    function engineSetting(key, value) {
      if (A.engineReady) act({ action: "settings", [key]: value });
      else { A.pendingSettings[key] = value; startEngine(); }
    }
    $("assist-checkbox").addEventListener("change", function (ev) { engineSetting("assist_shading", ev.target.checked); });
    $("ascii-checkbox").addEventListener("change", function (ev) { engineSetting("ascii_share", ev.target.checked); });
    $("streak-checkbox").addEventListener("change", function (ev) { engineSetting("show_streaks", ev.target.checked); requestStats(); });
    $("theme-setting-button").addEventListener("click", function () { if (window.NoyvjTheme) window.NoyvjTheme.toggle(); });
    $("reset-progress-button").addEventListener("click", function () {
      confirmThen("signal-reset", "Erase ALL Signal progress in this browser (streaks, archive results, achievements)? A save code you already made can still restore it.", "Erase everything", false, async function () {
        if (!A.engineReady) { setMessage("Wait for the receiver to warm up first."); return; }
        lsRemove(LS_STATE);
        lsRemove(LS_VIEW);
        var resp = send({ action: "reset" });
        A.lastShareText = "";
        applyResponse(resp, { action: "reset" });
        setMessage("Progress erased.");
      });
    });

    // feedback (plain JS, same shape as the other games)
    var answer = null;
    function pick(value) {
      answer = value;
      $("feedback-yes-button").classList.toggle("selected", value === "yes");
      $("feedback-no-button").classList.toggle("selected", value === "no");
      $("feedback-submit-button").disabled = false;
    }
    $("feedback-yes-button").addEventListener("click", function () { pick("yes"); });
    $("feedback-no-button").addEventListener("click", function () { pick("no"); });
    $("feedback-submit-button").addEventListener("click", async function () {
      if (!answer) return;
      var comment = $("feedback-comment").value.trim();
      $("feedback-submit-button").disabled = true;
      try {
        var res = await fetch("https://noyvjgames.fastapicloud.dev/ratings", {
          method: "POST", headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ game_slug: GAME, response: comment ? answer + " — " + comment : answer }),
        });
        if (!res.ok) throw new Error("status " + res.status);
        $("feedback-status").textContent = "Thanks for the feedback!";
      } catch (e) {
        $("feedback-status").textContent = "Feedback submission failed, try again.";
        $("feedback-submit-button").disabled = false;
      }
    });

    // day rollover: only checked when the page becomes visible again
    function checkRollover() {
      if (!A.engineReady || !A.view || document.hidden) return;
      if (utcToday() !== A.view.today) {
        var resp = send({ action: "boot" });
        applyResponse(resp, { action: "boot" });
        setMessage("A new UTC day: fresh puzzles are on the air.");
      } else {
        renderResult();
      }
    }
    document.addEventListener("visibilitychange", checkRollover);
    window.addEventListener("focus", checkRollover);

    // kick the engine off on the first sign of interaction, and after first paint
    var kick = function () { startEngine(); };
    document.addEventListener("pointerdown", kick, { once: true });
    document.addEventListener("keydown", kick, { once: true });

    wireMagnifier(boardEl);
  }

  // ---- hold-to-aim magnifier (R4-SIMO-1, phone only) -------------------------------------------------------
  // Holding a tile with a finger shows a bubble ABOVE the finger naming the tile (and what is already known about it), so the
  // thumb never hides what is about to be tapped. It never pings by itself: lifting the finger is the ordinary tap. Moving
  // the finger more than a few pixels, a second finger (pinch) or the radial menu cancels it. Per-device setting, on by default.
  var MAGNIFIER_KEY = "signal-magnifier";
  var MAGNIFIER_HOLD_MS = 180;
  var magnifier = null;
  var magTimer = null;
  var magOrigin = null;
  function magnifierWanted() {
    return lsGet(MAGNIFIER_KEY) !== "off" && Boolean(window.matchMedia) && window.matchMedia("(max-width: 600px)").matches;
  }
  function hideMagnifier() {
    if (magTimer) { clearTimeout(magTimer); magTimer = null; }
    magOrigin = null;
    if (magnifier) magnifier.classList.remove("visible");
  }
  function showMagnifier() {
    magTimer = null;
    if (!magOrigin || !A.view) return;
    var r = parseInt(magOrigin.btn.getAttribute("data-r"), 10);
    var c = parseInt(magOrigin.btn.getAttribute("data-c"), 10);
    var known = "Not pinged yet";
    A.view.pings.forEach(function (p) { if (p.r === r && p.c === c) known = "Reading " + p.v + " " + p.glyph; });
    if (A.pendingCells[r + "," + c]) known = "Ping queued";
    A.view.marks.forEach(function (m) { if (m[0] === r && m[1] === c) known = known === "Not pinged yet" ? "Marked" : known + ", marked"; });
    if (!magnifier) {
      magnifier = el("div", "magnifier-bubble");
      magnifier.setAttribute("aria-hidden", "true");   // the tile's own label already says all of this
      magnifier.appendChild(el("span", "mag-coord"));
      magnifier.appendChild(el("span", "mag-state"));
      document.body.appendChild(magnifier);
    }
    magnifier.querySelector(".mag-coord").textContent = label(r, c);
    magnifier.querySelector(".mag-state").textContent = known;
    magnifier.classList.add("visible");
    var width = magnifier.offsetWidth || 90;
    var left = Math.max(8, Math.min(window.innerWidth - width - 8, magOrigin.x - width / 2));
    magnifier.style.left = left + "px";
    magnifier.style.top = Math.max(8, magOrigin.y - 56) + "px";
  }
  function wireMagnifier(boardEl) {
    boardEl.addEventListener("pointerdown", function (ev) {
      hideMagnifier();
      if (ev.pointerType !== "touch" || !ev.isPrimary || !magnifierWanted() || !A.view || A.view.status !== "inprogress") return;
      var btn = ev.target.closest(".cell");
      if (!btn) return;
      magOrigin = { btn: btn, x: ev.clientX, y: ev.clientY };
      magTimer = setTimeout(showMagnifier, MAGNIFIER_HOLD_MS);
    });
    boardEl.addEventListener("pointermove", function (ev) {
      if (!magOrigin) return;
      if (Math.abs(ev.clientX - magOrigin.x) > 12 || Math.abs(ev.clientY - magOrigin.y) > 12) hideMagnifier();
    });
    ["pointerup", "pointercancel", "pointerleave"].forEach(function (name) { boardEl.addEventListener(name, hideMagnifier); });
    document.addEventListener("pointerdown", function (ev) { if (!ev.isPrimary || !boardEl.contains(ev.target)) hideMagnifier(); });
  }

  function init() {
    A.tool = "ping";
    A.currentState = jsonParse(lsGet(LS_STATE) || "null");
    var cached = loadCachedView();
    A.cachedValid = isCachedValid(cached);
    A.view = cached || defaultView();
    if (cached && !A.cachedValid) {
      setMessage("Tuning in to today's puzzle... (showing your last board)");
    } else if (!cached) {
      setMessage("Tap a tile to ping it. The receiver is warming up in the background.");
    } else {
      setMessage("Welcome back. Your board is shown while the receiver warms up.");
    }
    A.cursor = { r: Math.floor(A.view.board.n / 2), c: Math.floor(A.view.board.n / 2) };
    restoreResumeState();
    wire();
    render();
    renderAchievements();
    var d = new Date();
    A.cal = { y: d.getUTCFullYear(), m: d.getUTCMonth() };

    // Start the engine right after the shell is painted into the DOM. A timer
    // (not requestAnimationFrame) so a tab opened in the background still warms up.
    setTimeout(startEngine, 0);
  }

  // Mobile pinch-to-zoom & double-tap reset (max-width: 600px)
  (function () {
    if (window.innerWidth > 600) return;
    var board = document.getElementById("board");
    if (!board) return;
    var wrap = board.parentElement;
    if (!wrap) return;
    // Respect reduced motion
    if (document.documentElement.getAttribute("data-reduced-motion") === "true" ||
        window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;

    var SCALE_KEY = "signal-zoom-scale";
    var PAN_X_KEY = "signal-zoom-x";
    var PAN_Y_KEY = "signal-zoom-y";
    var MIN_S = 0.5, MAX_S = 3;

    function getScale() {
      var v = parseFloat(localStorage.getItem(SCALE_KEY));
      return isFinite(v) && v >= MIN_S && v <= MAX_S ? v : 1;
    }
    function setScale(s) {
      s = Math.max(MIN_S, Math.min(MAX_S, s));
      localStorage.setItem(SCALE_KEY, s);
      applyTransform();
    }
    function getPX() { return parseFloat(localStorage.getItem(PAN_X_KEY)) || 0; }
    function setPX(x) { localStorage.setItem(PAN_X_KEY, x); applyTransform(); }
    function getPY() { return parseFloat(localStorage.getItem(PAN_Y_KEY)) || 0; }
    function setPY(y) { localStorage.setItem(PAN_Y_KEY, y); applyTransform(); }

    function applyTransform() {
      var s = getScale();
      var x = getPX();
      var y = getPY();
      board.style.transform = "translate(" + x + "px, " + y + "px) scale(" + s + ")";
    }

    var lastPinchDist = null;
    wrap.addEventListener("touchstart", function (e) {
      if (e.touches.length === 2) {
        var dx = e.touches[0].clientX - e.touches[1].clientX;
        var dy = e.touches[0].clientY - e.touches[1].clientY;
        lastPinchDist = Math.sqrt(dx * dx + dy * dy);
      }
    }, { passive: true });

    wrap.addEventListener("touchmove", function (e) {
      if (e.touches.length === 2 && lastPinchDist !== null) {
        var dx = e.touches[0].clientX - e.touches[1].clientX;
        var dy = e.touches[0].clientY - e.touches[1].clientY;
        var dist = Math.sqrt(dx * dx + dy * dy);
        setScale(getScale() + (dist - lastPinchDist) / 200);
        lastPinchDist = dist;
      }
    }, { passive: true });

    wrap.addEventListener("touchend", function () { lastPinchDist = null; });

    var lastTapTime = 0;
    board.addEventListener("touchend", function (e) {
      if (e.changedTouches.length !== 1) return;
      var now = Date.now();
      if (now - lastTapTime < 300) {
        setScale(1);
        setPX(0);
        setPY(0);
        localStorage.removeItem(PAN_X_KEY);
        localStorage.removeItem(PAN_Y_KEY);
        applyTransform();
        lastTapTime = 0;
      } else {
        lastTapTime = now;
      }
    });

    applyTransform();
  })();

  window.SignalApp = { timings: timings, act: act, getView: function () { return A.view; }, startEngine: startEngine };
  window.SignalTimings = timings;

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init);
  else init();
})();
