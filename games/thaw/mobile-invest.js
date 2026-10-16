// R4-THMO-2: Mobile investment bar for splitting funds on small screens.
(function () {
  const track = document.getElementById("mobile-invest-track");
  if (!track) return;
  const fill = track.querySelector(".mobile-invest-fill");
  const handles = Array.from(track.querySelectorAll(".mobile-invest-handle"));
  const segs = document.querySelectorAll(".mobile-invest-seg");
  let dragging = null;
  let posA = 0.33, posB = 0.66;

  function update() {
    const w = track.clientWidth || 1;
    fill.style.left = (posA * 100) + "%";
    fill.style.width = ((posB - posA) * 100) + "%";
    handles[0].style.left = (posA * 100) + "%";
    handles[1].style.left = (posB * 100) + "%";
    
    const fundsEl = document.getElementById("funds-display");
    const funds = fundsEl ? parseInt(fundsEl.textContent.replace(/\D/g, ""), 10) || 0 : 0;
    const totalSegs = posB - posA;
    const outPct = posA;
    const monPct = 1 - posB;
    const avgCost = 20; 
    
    segs.forEach((seg, i) => {
      let pct = 0;
      if (i === 0) pct = outPct;
      else if (i === 1) pct = totalSegs;
      else pct = monPct;
      const count = Math.max(0, Math.floor((funds * pct) / avgCost));
      seg.querySelector(".mobile-invest-count").textContent = count;
    });
  }

  function onDown(e) {
    dragging = e.target.closest(".mobile-invest-handle");
    if (!dragging) return;
    e.preventDefault();
    document.addEventListener("pointermove", onMove);
    document.addEventListener("pointerup", onUp);
  }

  function onMove(e) {
    if (!dragging) return;
    const rect = track.getBoundingClientRect();
    let x = (e.clientX - rect.left) / rect.width;
    x = Math.max(0, Math.min(1, x));
    if (dragging === handles[0]) {
      posA = Math.min(x, posB - 0.05);
    } else {
      posB = Math.max(x, posA + 0.05);
    }
    update();
  }

  function onUp() {
    dragging = null;
    document.removeEventListener("pointermove", onMove);
    document.removeEventListener("pointerup", onUp);
  }

  track.addEventListener("pointerdown", onDown);

  segs.forEach((seg) => {
    seg.addEventListener("click", (e) => {
      if (dragging) return;
      const cat = seg.dataset.cat;
      const investFn = window.pyodide && window.pyodide.globals.get("invest");
      if (investFn) {
        try { investFn(cat); } catch (_) {}
      }
    });
  });

  document.querySelectorAll(".mobile-invest-step").forEach(btn => {
    btn.addEventListener("click", () => {
      const cat = btn.closest(".mobile-invest-seg").dataset.cat;
      const investFn = window.pyodide && window.pyodide.globals.get("invest");
      if (investFn) {
        try { investFn(cat); } catch (_) {}
      }
    });
  });

  update();
})();
