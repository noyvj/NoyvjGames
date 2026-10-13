(function () {
  "use strict";
  var list = document.getElementById("letters-list");
  if (!list) return;

  function init() {
    var items = list.querySelectorAll(".letters-list li");
    for (var i = 0; i < items.length; i++) {
      var item = items[i];
      if (item.dataset.mobileLettersInit) continue;
      item.dataset.mobileLettersInit = "true";

      var inner = document.createElement("div");
      inner.className = "letter-card-inner";

      var front = document.createElement("div");
      front.className = "letter-card-front";
      front.innerHTML = '<span class="tap-hint">Tap to read</span>';

      var back = document.createElement("div");
      back.className = "letter-card-back";
      while (item.firstChild) {
        back.appendChild(item.firstChild);
      }

      inner.appendChild(front);
      inner.appendChild(back);
      item.appendChild(inner);

      var startX = 0;
      var isDragging = false;

      item.addEventListener("touchstart", function (e) {
        startX = e.touches[0].clientX;
        isDragging = false;
      }, { passive: true });

      item.addEventListener("touchmove", function (e) {
        if (!isDragging && Math.abs(e.touches[0].clientX - startX) > 10) {
          isDragging = true;
        }
        if (isDragging) {
          var diff = e.touches[0].clientX - startX;
          this.style.transform = "translateX(" + diff + "px)";
          this.style.opacity = Math.max(0, 1 - Math.abs(diff) / 200);
        }
      }, { passive: true });

      item.addEventListener("touchend", function () {
        var diff = parseFloat(this.style.transform.replace("translateX(", "").replace("px)", "")) || 0;
        if (Math.abs(diff) > 80) {
          this.classList.add("dismissed");
          setTimeout(function () { this.remove(); }.bind(this), 300);
        } else {
          this.style.transform = "";
          this.style.opacity = "";
          if (!isDragging) {
            this.classList.toggle("flipped");
          }
        }
        isDragging = false;
      });
    }
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }

  window.lighthouseRefreshLetters = init;
})();
(function () {
  "use strict";
  var list = document.getElementById("letters-list");
  if (!list) return;

  function init() {
    var items = list.querySelectorAll(".letters-list li");
    for (var i = 0; i < items.length; i++) {
      var item = items[i];
      if (item.dataset.mobileLettersInit) continue;
      item.dataset.mobileLettersInit = "true";

      var inner = document.createElement("div");
      inner.className = "letter-card-inner";

      var front = document.createElement("div");
      front.className = "letter-card-front";
      front.innerHTML = '<span class="tap-hint">Tap to read</span>';

      var back = document.createElement("div");
      back.className = "letter-card-back";
      while (item.firstChild) {
        back.appendChild(item.firstChild);
      }

      inner.appendChild(front);
      inner.appendChild(back);
      item.appendChild(inner);

      var startX = 0;
      var isDragging = false;

      item.addEventListener("touchstart", function (e) {
        startX = e.touches[0].clientX;
        isDragging = false;
      }, { passive: true });

      item.addEventListener("touchmove", function (e) {
        if (!isDragging && Math.abs(e.touches[0].clientX - startX) > 10) {
          isDragging = true;
        }
        if (isDragging) {
          var diff = e.touches[0].clientX - startX;
          this.style.transform = "translateX(" + diff + "px)";
          this.style.opacity = Math.max(0, 1 - Math.abs(diff) / 200);
        }
      }, { passive: true });

      item.addEventListener("touchend", function () {
        var diff = parseFloat(this.style.transform.replace("translateX(", "").replace("px)", "")) || 0;
        if (Math.abs(diff) > 80) {
          this.classList.add("dismissed");
          setTimeout(function () { this.remove(); }.bind(this), 300);
        } else {
          this.style.transform = "";
          this.style.opacity = "";
          if (!isDragging) {
            this.classList.toggle("flipped");
          }
        }
        isDragging = false;
      });
    }
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }

  window.lighthouseRefreshLetters = init;
})();
