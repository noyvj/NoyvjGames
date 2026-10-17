/* Chronicle, part 5 of 5 (loads last): wiring (clicks and keys), the save-loaded hook, copy result, init. */
(function () {
  "use strict";

  var A = window.ChronicleApp;
  var $ = A.$, LS_STATE = A.LS_STATE, LS_VIEW = A.LS_VIEW, MODE_IDS = A.MODE_IDS, MODE_KEYS = A.MODE_KEYS,
      act = A.act, announce = A.announce, answerAccount = A.answerAccount, answerReview = A.answerReview,
      applyResponse = A.applyResponse, buildReport = A.buildReport, catalog = A.catalog,
      currentMode = A.currentMode, jsonParse = A.jsonParse, lsGet = A.lsGet, lsRemove = A.lsRemove,
      onCard = A.onCard, onSlot = A.onSlot, onWebCard = A.onWebCard, openArchive = A.openArchive,
      openInfo = A.openInfo, persistState = A.persistState, pickDecision = A.pickDecision,
      placeCard = A.placeCard, render = A.render, renderAchievements = A.renderAchievements,
      renderWeb = A.renderWeb, send = A.send, setStatus = A.setStatus, showToast = A.showToast,
      sortClaim = A.sortClaim, startEngine = A.startEngine, switchMode = A.switchMode,
      unplaceSlot = A.unplaceSlot;
  A.getView = function () { return A.view; };
  A.isReady = function () { return A.engineReady; };

  // ---- wiring -----------------------------------------------------------------------------------------------------
  function togglePanel(btnId, panelId, onOpen) {
    $(btnId).addEventListener("click", function () {
      var panel = $(panelId);
      panel.hidden = !panel.hidden;
      $(btnId).setAttribute("aria-expanded", String(!panel.hidden));
      if (!panel.hidden) {
        if (onOpen) onOpen();
        if (!A.engineReady) startEngine();
      }
    });
  }

  function wire() {
    togglePanel("archive-toggle-button", "archive-panel", function () { if (A.engineReady) openArchive(); });
    togglePanel("achievements-toggle-button", "achievements-panel", renderAchievements);
    togglePanel("changelog-toggle-button", "changelog-panel");
    togglePanel("info-page-toggle-button", "info-page-panel", function () { if (A.engineReady) openInfo(); });

    $("slots").addEventListener("click", function (ev) {
      var b = ev.target.closest(".slot");
      if (b) onSlot(parseInt(b.getAttribute("data-slot"), 10));
    });
    $("slots").addEventListener("dragover", function (ev) { if (ev.target.closest(".slot")) ev.preventDefault(); });
    $("slots").addEventListener("drop", function (ev) {
      var b = ev.target.closest(".slot");
      if (!b) return;
      ev.preventDefault();
      var id = ev.dataTransfer.getData("text/plain");
      if (id && A.view && A.view.puzzle.status === "playing" && !A.view.puzzle.slots[parseInt(b.getAttribute("data-slot"), 10)].locked) placeCard(id, parseInt(b.getAttribute("data-slot"), 10));
    });
    $("tray").addEventListener("click", function (ev) {
      var c = ev.target.closest(".card");
      if (c) { onCard(c.getAttribute("data-card")); return; }
      if (A.selected && A.selected.slot !== null) unplaceSlot(A.selected.slot);
    });
    $("tray").addEventListener("dragover", function (ev) { ev.preventDefault(); });
    $("tray").addEventListener("drop", function (ev) {
      ev.preventDefault();
      var id = ev.dataTransfer.getData("text/plain");
      if (!id || !A.view) return;
      var s = A.view.puzzle.slots.filter(function (x) { return x.card === id && !x.locked; })[0];
      if (s) unplaceSlot(s.index);
    });
    $("return-button").addEventListener("click", function () { if (A.selected && A.selected.slot !== null) unplaceSlot(A.selected.slot); });

    $("check-button").addEventListener("click", function () {
      if (!A.view) return;
      if (!A.view.puzzle.all_placed) { $("message-line").textContent = "Fill every slot before checking."; announce("Fill every slot before checking."); return; }
      A.selected = null;
      var resp = act({ action: "check" });
      if (resp && resp.ok) announce(A.view.puzzle.message);
      if (A.view.result) $("result-panel").scrollIntoView({ block: "nearest" });
    });
    $("show-answer-button").addEventListener("click", function () {
      var go = function () { A.selected = null; act({ action: "show_answer" }); };
      if (window.ConfirmDialog) window.ConfirmDialog.ask({ id: "chronicle-show-answer", message: "Show the answer? Nothing from this puzzle will be added to your archive.", confirmLabel: "Show the answer", allowSkip: true, onConfirm: go });
      else go();
    });
    $("next-button").addEventListener("click", function () { A.selected = null; act({ action: "next" }); $("puzzle-panel").scrollIntoView({ block: "nearest" }); });

    $("sections").addEventListener("click", function (ev) {
      var b = ev.target.closest(".section-card");
      if (!b) return;
      var kind = b.getAttribute("data-kind");
      if (b.getAttribute("aria-disabled") === "true") {
        var why = (kind ? "That chapter" : "That section") + " is locked. " + b.querySelectorAll(".sc-meta")[0].textContent + ".";
        var line = { web: "web-message", myth: "myth-message", account: "account-message", decision: "decision-message" }[kind] || "message-line";
        $(line).textContent = why;
        announce(why);
        return;
      }
      A.selected = null; A.webPick = null;
      if (kind === "web") act({ action: "web_start", chapter: b.getAttribute("data-chapter") });
      else if (kind === "myth") act({ action: "myth_start", chapter: b.getAttribute("data-chapter") });
      else if (kind === "account") act({ action: "account_start", account: b.getAttribute("data-chapter") });
      else if (kind === "decision") act({ action: "decision_start", decision: b.getAttribute("data-chapter") });
      else act({ action: "start", section: b.getAttribute("data-section") });
    });

    // mode tabs (a tablist: arrow keys, Home and End move between the three)
    var tabs = MODE_IDS;
    tabs.forEach(function (id) {
      $("mode-" + id + "-button").addEventListener("click", function () { switchMode(id); });
      $("mode-" + id + "-button").addEventListener("keydown", function (ev) {
        var i = tabs.indexOf(id), j = null;
        if (ev.key === "ArrowRight" || ev.key === "ArrowDown") j = (i + 1) % tabs.length;
        else if (ev.key === "ArrowLeft" || ev.key === "ArrowUp") j = (i + tabs.length - 1) % tabs.length;
        else if (ev.key === "Home") j = 0;
        else if (ev.key === "End") j = tabs.length - 1;
        if (j === null) return;
        ev.preventDefault();
        $("mode-" + tabs[j] + "-button").focus();
        switchMode(tabs[j]);
        $("mode-" + tabs[j] + "-button").focus();
      });
    });

    // cause web
    $("web-cards").addEventListener("click", function (ev) {
      var b = ev.target.closest(".web-card");
      if (b) onWebCard(b.getAttribute("data-wcard"));
    });
    $("web-cancel-button").addEventListener("click", function () { A.webPick = null; renderWeb(); announce("Put the card down."); });
    $("web-show-button").addEventListener("click", function () {
      var go = function () { A.webPick = null; act({ action: "web_show" }); };
      if (window.ConfirmDialog) window.ConfirmDialog.ask({ id: "chronicle-web-show", message: "Show the links? Nothing from this puzzle will be added to your archive.", confirmLabel: "Show the links", allowSkip: true, onConfirm: go });
      else go();
    });
    $("web-next-button").addEventListener("click", function () { A.webPick = null; act({ action: "web_next" }); $("web-panel").scrollIntoView({ block: "nearest" }); });

    // myth or record
    $("myth-cards").addEventListener("click", function (ev) {
      var b = ev.target.closest(".bin-btn");
      if (!b || b.getAttribute("aria-disabled") === "true") return;
      sortClaim(b.getAttribute("data-claim"), b.getAttribute("data-bin"));
    });
    $("myth-check-button").addEventListener("click", function () {
      if (!A.view || !A.view.myth) return;
      if (!A.view.myth.all_sorted) { $("myth-message").textContent = "Sort every statement before checking."; announce("Sort every statement before checking."); return; }
      var resp = act({ action: "myth_check" });
      if (resp && resp.ok) announce(A.view.myth.message);
      if (A.view.myth && A.view.myth.result) $("myth-result").scrollIntoView({ block: "nearest" });
    });
    $("myth-show-button").addEventListener("click", function () {
      var go = function () { act({ action: "myth_show" }); };
      if (window.ConfirmDialog) window.ConfirmDialog.ask({ id: "chronicle-myth-show", message: "Show the answer? Nothing from this puzzle will be added to your archive.", confirmLabel: "Show the answer", allowSkip: true, onConfirm: go });
      else go();
    });
    $("myth-next-button").addEventListener("click", function () { act({ action: "myth_next" }); $("myth-panel").scrollIntoView({ block: "nearest" }); });
    // whose account?
    $("account-questions").addEventListener("click", function (ev) {
      var b = ev.target.closest(".opt-btn");
      if (!b || b.getAttribute("aria-disabled") === "true") return;
      answerAccount(b.getAttribute("data-q"), b.getAttribute("data-opt"));
    });
    $("account-check-button").addEventListener("click", function () {
      if (!A.view || !A.view.account) return;
      if (!A.view.account.all_answered) { $("account-message").textContent = "Answer every question before checking."; announce("Answer every question before checking."); return; }
      var resp = act({ action: "account_check" });
      if (resp && resp.ok) announce(A.view.account.message);
      if (A.view.account && A.view.account.result) $("account-result").scrollIntoView({ block: "nearest" });
    });
    $("account-show-button").addEventListener("click", function () {
      var go = function () { act({ action: "account_show" }); };
      if (window.ConfirmDialog) window.ConfirmDialog.ask({ id: "chronicle-account-show", message: "Show the answers? Nothing from this puzzle will be added to your archive.", confirmLabel: "Show the answers", allowSkip: true, onConfirm: go });
      else go();
    });
    $("account-next-button").addEventListener("click", function () { act({ action: "account_next" }); $("account-panel").scrollIntoView({ block: "nearest" }); });

    // decision points
    $("decision-options").addEventListener("click", function (ev) {
      var b = ev.target.closest(".opt-btn");
      if (!b || b.getAttribute("aria-disabled") === "true") return;
      pickDecision(b.getAttribute("data-opt"));
    });

    // review
    $("review-question").addEventListener("click", function (ev) {
      var b = ev.target.closest(".opt-btn");
      if (b) answerReview(b.getAttribute("data-key"), b.getAttribute("data-opt"));
    });
    $("review-next-button").addEventListener("click", function () { act({ action: "review_next" }); var first = document.querySelector("#review-question .opt-btn"); if (first) first.focus(); });
    $("review-day-button").addEventListener("click", function () {
      var resp = act({ action: "review_day" });
      if (resp && resp.ok) announce("A day passed. It is now day " + A.view.review.day + ".");
    });

    $("set-select").addEventListener("change", function (ev) { A.selected = null; act({ action: "choose_set", set: ev.target.value }); });

    $("report-build-button").addEventListener("click", buildReport);
    $("report-copy-button").addEventListener("click", function () {
      var text = $("report-payload").textContent;
      if (navigator.clipboard && navigator.clipboard.writeText) navigator.clipboard.writeText(text).then(function () { $("report-notice").textContent = "Report text copied."; }, function () { $("report-notice").textContent = "Select the text above and copy it by hand."; });
      else $("report-notice").textContent = "Select the text above and copy it by hand.";
    });
    $("report-dialog").addEventListener("close", function () { if (A.currentReport && A.currentReport.opener && document.body.contains(A.currentReport.opener)) A.currentReport.opener.focus(); });

    $("hints-checkbox").addEventListener("change", function (ev) { act({ action: "settings", hints: ev.target.checked }); });
    $("reset-progress-button").addEventListener("click", function () {
      var go = function () {
        lsRemove(LS_STATE); lsRemove(LS_VIEW);
        A.selected = null;
        if (act({ action: "reset" })) { persistState(); showToast("Progress erased."); }
      };
      if (window.ConfirmDialog) window.ConfirmDialog.ask({ id: "chronicle-reset", message: "Erase ALL Chronicle progress in this browser (archive, solved puzzles, achievements)? A save code you already made can still restore it.", confirmLabel: "Erase everything", allowSkip: false, onConfirm: go });
      else go();
    });

    document.addEventListener("keydown", onKey);
    var kick = function () { startEngine(); };
    document.addEventListener("pointerdown", kick, { once: true });
    document.addEventListener("keydown", kick, { once: true });
  }

  function onKey(ev) {
    if (ev.ctrlKey || ev.metaKey || ev.altKey || !A.view || A.view.empty) return;
    var tag = (ev.target && ev.target.tagName) || "";
    if (tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT") return;
    if (ev.target.closest && ev.target.closest("dialog[open]")) return;
    var mode = currentMode();
    if (mode === "web") {
      if (ev.key === "Escape" && A.webPick) { A.webPick = null; renderWeb(); announce("Put the card down."); return; }
      if (/^[1-9]$/.test(ev.key) && A.view.web && !A.view.web.locked && A.view.web.status === "playing") {
        var wc = A.view.web.cards[parseInt(ev.key, 10) - 1];
        if (wc) { ev.preventDefault(); onWebCard(wc.id); }
        return;
      }
    } else if (mode === "account") {
      var aq = ev.target.closest && ev.target.closest(".acct-q");
      if (/^[1-5]$/.test(ev.key) && aq && A.view.account && !A.view.account.locked) {
        ev.preventDefault();
        var qrow = A.view.account.questions.filter(function (x) { return x.id === aq.getAttribute("data-q"); })[0];
        if (qrow && !qrow.locked && qrow.options[parseInt(ev.key, 10) - 1]) answerAccount(qrow.id, qrow.options[parseInt(ev.key, 10) - 1].id);
        return;
      }
    } else if (mode === "decision") {
      if (/^[1-4]$/.test(ev.key) && A.view.decision && !A.view.decision.locked && !A.view.decision.decided) {
        var dopt = A.view.decision.options[parseInt(ev.key, 10) - 1];
        if (dopt) { ev.preventDefault(); pickDecision(dopt.id); }
        return;
      }
    } else if (mode === "review") {
      if (/^[1-4]$/.test(ev.key) && A.view.review && A.view.review.question) {
        var ropt = A.view.review.question.options[parseInt(ev.key, 10) - 1];
        if (ropt) { ev.preventDefault(); answerReview(A.view.review.question.key, ropt.id); }
        return;
      }
    } else if (mode === "myth") {
      var card = ev.target.closest && ev.target.closest(".myth-card");
      if (/^[1-3]$/.test(ev.key) && card && A.view.myth && !A.view.myth.locked) {
        ev.preventDefault();
        var claimId = card.getAttribute("data-claim");
        var bins = A.view.myth.bins;
        var row = A.view.myth.claims.filter(function (c) { return c.id === claimId; })[0];
        if (row && !row.locked) sortClaim(claimId, bins[parseInt(ev.key, 10) - 1].id);
        return;
      }
    }
    if (!(ev.target.closest && ev.target.closest(".myth-card, .web-card")) && /^[twmadr]$/i.test(ev.key)) {
      ev.preventDefault();
      switchMode(MODE_KEYS[ev.key.toLowerCase()]);
      return;
    }
    if (ev.key === "Escape" && A.selected) { A.selected = null; render(); announce("Put the card down."); return; }
    if (mode === "timeline" && /^[1-8]$/.test(ev.key) && A.selected) {
      var n = parseInt(ev.key, 10) - 1;
      if (n < A.view.puzzle.size) { ev.preventDefault(); onSlot(n); }
      return;
    }
    if ((ev.key === "Delete" || ev.key === "Backspace") && ev.target.classList && ev.target.classList.contains("slot")) {
      var i = parseInt(ev.target.getAttribute("data-slot"), 10);
      var s = A.view.puzzle.slots[i];
      if (s && s.card && !s.locked && A.view.puzzle.status === "playing") { ev.preventDefault(); unplaceSlot(i); }
      return;
    }
    if (ev.target.classList && ev.target.classList.contains("slot") && /^Arrow/.test(ev.key)) {
      var cur = parseInt(ev.target.getAttribute("data-slot"), 10);
      var next = (ev.key === "ArrowRight" || ev.key === "ArrowDown") ? cur + 1 : cur - 1;
      var t = document.querySelector('[data-slot="' + next + '"]');
      if (t) { ev.preventDefault(); t.focus(); }
    }
  }

  // Called by game.py's load_state() after the save widget loads a save.
  window.chronicleOnStateLoaded = function () {
    if (!A.engineReady) return;
    A.selected = null; A.webPick = null;
    applyResponse(send({ action: "boot" }));
    persistState();
    showToast("Save loaded.");
  };

  // Z-20: the shared "Copy result" button under the archive, filled from the figures the meter shows.
  function mountCopyResult() {
    if (!window.NoyvjCopyResult || !$("archive-copy-result")) return;
    window.NoyvjCopyResult.mountButton("#archive-copy-result", {
      getResult: function () {
        if (!A.view || !A.view.set) return {};
        var earned = (A.view.achievements_earned || []).length;
        return {
          game: "Chronicle",
          score: A.view.set.percent + "% of the " + (A.view.set.title || "set") + " archive",
          stats: [A.view.set.found + " of " + A.view.set.total + " found", earned + " of " + catalog.ach.length + " achievements"]
        };
      }
    });
  }

  function init() {
    wire();
    mountCopyResult();
    var cached = jsonParse(lsGet(LS_VIEW) || "null");
    if (cached && cached.puzzle && cached.set) {
      A.view = cached;
      render();
      setStatus("Warming up the archive... (showing where you left off)");
    } else {
      setStatus("Warming up the archive...");
      renderStaticPlaceholder();
    }
    setTimeout(startEngine, 0);
  }

  function renderStaticPlaceholder() {
    $("puzzle-meta").textContent = "The first puzzle appears when the archive has warmed up.";
    $("check-button").setAttribute("aria-disabled", "true");
    $("show-answer-button").hidden = true;
  }


  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init);
  else init();
})();
