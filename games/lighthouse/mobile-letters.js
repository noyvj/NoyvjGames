/*
 * Lighthouse -- R4-LHMO-4: letters as paper cards (phones, when "Letters as paper cards" is switched on under
 * Settings > On a phone). A closed card shows who it is from; Read turns it over to the letter, and a swipe sideways (or
 * the File away button, which does the same without any gesture) files a read letter out of the pile. Filing hides a
 * letter and nothing else: "Filed letters" brings it back, the engine's letter, its gifts and its replies are untouched,
 * and an unread letter cannot be filed. Which letters are filed is a per-device choice in localStorage, never the save.
 */
(function () {
  "use strict";
  var list = document.getElementById("letters-list");
  var filedToggle = document.getElementById("letters-filed-toggle");
  if (!list || !filedToggle) return;
  var KEY = "lighthouse-letters-filed";
  var SWIPE = 90;

  var filed = {};
  var opened = {};
  var showFiled = false;

  try {
    var stored = JSON.parse(window.localStorage.getItem(KEY));
    if (Array.isArray(stored)) stored.forEach(function (id) { if (typeof id === "string" && id.length < 60) filed[id] = true; });
  } catch (err) { /* nothing stored, or not readable: nothing is filed */ }

  function save() { try { window.localStorage.setItem(KEY, JSON.stringify(Object.keys(filed))); } catch (err) { /* convenience only */ } }
  function wanted() { return window.LighthousePhonePrefs && window.LighthousePhonePrefs.get("cards") === "on"; }
  function phone() { return Boolean(window.matchMedia && window.matchMedia("(max-width: 600px)").matches); }
  function api() { return window.lighthouseApi; }
  function say(text) { if (api()) api().announce(text); }
  function flip(card) {
    card.classList.remove("flip");
    void card.offsetWidth;   // restart the short turn-over animation
    card.classList.add("flip");
  }

  function countFiled() {
    return Object.keys(filed).filter(function (id) { return list.querySelector('li[data-letter-id="' + id + '"]'); }).length;
  }
  function paintToggle() {
    var n = countFiled();
    filedToggle.hidden = n === 0 || !wanted();
    filedToggle.setAttribute("aria-pressed", String(showFiled));
    filedToggle.textContent = "Filed letters (" + n + "): " + (showFiled ? "hide" : "show");
    list.setAttribute("data-show-filed", String(showFiled));
  }

  function paint(card) {
    var id = card.dataset.letterId;
    var isOpen = Boolean(opened[id]);
    var isFiled = Boolean(filed[id]);
    var read = card.dataset.read === "true";
    card.dataset.open = String(isOpen);
    card.dataset.filed = String(isFiled);
    var readBtn = card.querySelector(".card-read");
    var fileBtn = card.querySelector(".card-file");
    if (readBtn) {
      readBtn.textContent = isOpen ? "Fold" : "Read";
      readBtn.setAttribute("aria-expanded", String(isOpen));
      readBtn.hidden = !read;   // an unread letter has its own "Open the letter" button
    }
    if (fileBtn) {
      fileBtn.textContent = isFiled ? "Take out" : "File away";
      fileBtn.setAttribute("aria-disabled", String(!read));
      fileBtn.title = read ? "" : "Open the letter first";
    }
  }

  function setFiled(card, on) {
    var id = card.dataset.letterId;
    if (on && card.dataset.read !== "true") return false;
    if (on) filed[id] = true; else delete filed[id];
    save();
    card.style.transform = "";
    card.style.opacity = "";
    paint(card);
    paintToggle();
    say(on ? "Letter filed. Filed letters brings it back." : "Letter taken out of the file.");
    return true;
  }

  function enhance() {
    Array.prototype.forEach.call(list.children, function (card) {
      if (card.tagName !== "LI" || !card.dataset.letterId || card.classList.contains("paper-card")) return;
      card.classList.add("paper-card");
      var head = card.querySelector(".letter-head");
      var bar = document.createElement("div");
      bar.className = "card-actions";
      var read = document.createElement("button");
      read.type = "button"; read.className = "card-read";
      var file = document.createElement("button");
      file.type = "button"; file.className = "card-file";
      bar.appendChild(read);
      bar.appendChild(file);
      if (head && head.nextSibling) card.insertBefore(bar, head.nextSibling); else card.appendChild(bar);
      read.addEventListener("click", function () {
        opened[card.dataset.letterId] = !opened[card.dataset.letterId];
        paint(card);
        flip(card);
      });
      file.addEventListener("click", function () {
        if (file.getAttribute("aria-disabled") === "true") { say("Open the letter first."); return; }
        setFiled(card, !filed[card.dataset.letterId]);
      });
      swipeable(card);
      paint(card);
    });
    paintToggle();
  }

  function swipeable(card) {
    var x0 = null;
    var dx = 0;
    card.addEventListener("pointerdown", function (e) {
      if (!wanted() || !phone() || e.target.closest("button, a, input, select, textarea")) return;
      x0 = e.clientX; dx = 0;
    });
    card.addEventListener("pointermove", function (e) {
      if (x0 === null) return;
      dx = e.clientX - x0;
      if (Math.abs(dx) < 12) return;
      try { card.setPointerCapture(e.pointerId); } catch (err) { /* fine without */ }
      card.style.transform = "translateX(" + Math.round(dx) + "px)";
      card.style.opacity = String(Math.max(0.3, 1 - Math.abs(dx) / 260));
    });
    function end() {
      if (x0 === null) return;
      var far = Math.abs(dx) >= SWIPE;
      x0 = null;
      card.style.transform = ""; card.style.opacity = "";
      if (far) {
        if (!setFiled(card, !filed[card.dataset.letterId])) say("Open the letter first.");
      }
    }
    card.addEventListener("pointerup", end);
    card.addEventListener("pointercancel", function () { x0 = null; card.style.transform = ""; card.style.opacity = ""; });
  }

  // An unread letter's own "Open the letter" button asks the engine; keep that card open when it comes back read.
  list.addEventListener("click", function (e) {
    var b = e.target.closest("button");
    var card = b && b.closest("li[data-letter-id]");
    if (card && !b.classList.contains("card-read") && !b.classList.contains("card-file") && b.parentNode === card) opened[card.dataset.letterId] = true;
  });

  filedToggle.addEventListener("click", function () { showFiled = !showFiled; paintToggle(); });
  new MutationObserver(enhance).observe(list, { childList: true });
  document.addEventListener("lighthouse-phone-pref", function (e) { if (e.detail.name === "cards") paintToggle(); });
  enhance();
})();
