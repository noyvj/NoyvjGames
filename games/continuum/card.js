/*
 * Continuum -- K20: the shareable settlement infographic card.
 *
 * Draws a 1200x630 card (stats on the left, the 3D-scene image on the right)
 * onto a plain 2D canvas and downloads it as a PNG. Pure browser code with no
 * Python or Three.js dependency: game.py hands it a JSON string
 * {title, lines[], thumb, filename}. Everything is drawn as text and shapes
 * (nothing is encoded by colour alone), and any failure (bad JSON, a tainted
 * canvas, no image) degrades to a card without the picture or to no download,
 * never to an error the player sees.
 */
(function () {
  "use strict";

  const W = 1200;
  const H = 630;

  function fitText(ctx, text, maxWidth) {
    let out = String(text);
    while (out.length > 1 && ctx.measureText(out).width > maxWidth) out = out.slice(0, -2) + "…";
    return out;
  }

  function draw(payload, image, extras) {
    extras = extras || {};
    const canvas = document.createElement("canvas");
    canvas.width = W;
    canvas.height = H;
    const ctx = canvas.getContext("2d");
    const grad = ctx.createLinearGradient(0, 0, 0, H);
    grad.addColorStop(0, "#2b2233");
    grad.addColorStop(1, "#1a1410");
    ctx.fillStyle = grad;
    ctx.fillRect(0, 0, W, H);
    ctx.strokeStyle = "#e0b374";
    ctx.lineWidth = 6;
    ctx.strokeRect(12, 12, W - 24, H - 24);

    // Picture, right side.
    const px = 640, py = 70, pw = 500, ph = 400;
    ctx.fillStyle = "#120d09";
    ctx.fillRect(px, py, pw, ph);
    if (image) {
      const scale = Math.max(pw / image.width, ph / image.height);
      const sw = pw / scale, sh = ph / scale;
      ctx.drawImage(image, (image.width - sw) / 2, (image.height - sh) / 2, sw, sh, px, py, pw, ph);
    } else {
      ctx.fillStyle = "#8a7355";
      ctx.font = "26px sans-serif";
      ctx.textAlign = "center";
      ctx.fillText("No 3D picture for this card", px + pw / 2, py + ph / 2);
      ctx.textAlign = "left";
    }
    ctx.strokeStyle = "#e0b374";
    ctx.lineWidth = 3;
    ctx.strokeRect(px, py, pw, ph);

    // Text, left side.
    ctx.fillStyle = "#f6e6c8";
    ctx.font = "bold 84px Georgia, serif";
    ctx.fillText(fitText(ctx, payload.title || "Continuum", 540), 60, 150);
    ctx.fillStyle = "#e0b374";
    ctx.font = "26px sans-serif";
    ctx.fillText("A settlement carried across the ages", 60, 195);
    const lines = Array.isArray(payload.lines) ? payload.lines.slice(0, 8) : [];
    ctx.fillStyle = "#f6e6c8";
    lines.forEach(function (line, i) {
      ctx.font = i === 0 ? "bold 36px sans-serif" : "30px sans-serif";
      ctx.fillText(fitText(ctx, line, 540), 60, 262 + i * 50);
    });
    // K-20: the cosmetic skyline flourish along the bottom of the picture, and the banner cloth hung
    // from the top-right corner. Both are drawn from stand-alone SVG strings; labels are written as
    // text too, so the card never depends on the pictures to say what they are.
    if (extras.flourish) {
      try { ctx.drawImage(extras.flourish, px, py + ph - 70, pw, 70); } catch (err) { /* decoration only */ }
    }
    if (extras.banner) {
      try { ctx.drawImage(extras.banner, W - 150, 14, 110, 154); } catch (err) { /* decoration only */ }
    }
    ctx.fillStyle = "#8a7355";
    ctx.font = "24px sans-serif";
    const cosmetics = [payload.banner_label, payload.flourish_label].filter(function (t) { return t && !/^(Plain Cloth|No flourish)$/.test(t); });
    if (cosmetics.length) ctx.fillText(fitText(ctx, cosmetics.join(" · "), 560), 640, H - 44);
    ctx.fillText("Continuum · NoyvjGames", 60, H - 44);
    return canvas;
  }

  function finish(payload, image, extras) {
    try {
      const canvas = draw(payload, image, extras);
      const link = document.createElement("a");
      const name = String(payload.filename || "continuum-card.png").replace(/[^A-Za-z0-9._-]/g, "-");
      link.download = name;
      link.href = canvas.toDataURL("image/png");
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
    } catch (err) {
      console.warn("Continuum card: export failed.", err);
    }
  }

  function download(json) {
    let payload;
    try {
      payload = JSON.parse(json);
    } catch (err) {
      return;
    }
    if (!payload || typeof payload !== "object") return;
    // Load the picture and the two optional cosmetic SVGs, then draw once all have settled
    // (a failed or missing image is simply left out).
    const jobs = [
      ["thumb", typeof payload.thumb === "string" && payload.thumb.indexOf("data:image/jpeg;base64,") === 0 ? payload.thumb : ""],
      ["banner", svgSource(payload.banner_svg)],
      ["flourish", svgSource(payload.flourish_svg)],
    ];
    const found = {};
    let pending = jobs.length;
    function settle() {
      pending -= 1;
      if (pending === 0) finish(payload, found.thumb || null, { banner: found.banner || null, flourish: found.flourish || null });
    }
    jobs.forEach(function (job) {
      if (!job[1]) { settle(); return; }
      const img = new Image();
      img.onload = function () { found[job[0]] = img; settle(); };
      img.onerror = function () { settle(); };
      img.src = job[1];
    });
  }

  // A stand-alone SVG string from game.py -> a data URL, only when it really is a plain <svg> with no script.
  function svgSource(markup) {
    if (typeof markup !== "string" || markup.indexOf("<svg") !== 0 || markup.length > 20000 || /<script|onload|onerror|href=/i.test(markup)) return "";
    return "data:image/svg+xml;charset=utf-8," + encodeURIComponent(markup);
  }

  // K-18: downloads plain text (CSV or JSON) as a file. game.py hands it a JSON
  // string {text, filename, mime}; the file is built in the browser and never
  // leaves the device. Any failure (bad JSON, no Blob support) does nothing.
  function downloadText(json) {
    let payload;
    try {
      payload = JSON.parse(json);
    } catch (err) {
      return;
    }
    if (!payload || typeof payload.text !== "string") return;
    try {
      const mime = payload.mime === "application/json" ? "application/json" : "text/csv";
      // A byte-order mark makes a spreadsheet open UTF-8 CSV with the right accents.
      const body = mime === "text/csv" ? "\ufeff" + payload.text : payload.text;
      const blob = new Blob([body], { type: mime + ";charset=utf-8" });
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.download = String(payload.filename || "continuum-export.txt").replace(/[^A-Za-z0-9._-]/g, "-");
      link.href = url;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      setTimeout(function () { URL.revokeObjectURL(url); }, 4000);
    } catch (err) {
      console.warn("Continuum export: download failed.", err);
    }
  }

  window.ContinuumCard = { download: download, downloadText: downloadText };
})();
