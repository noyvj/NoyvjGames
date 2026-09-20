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

  function draw(payload, image) {
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
    ctx.fillStyle = "#8a7355";
    ctx.font = "24px sans-serif";
    ctx.fillText("Continuum · NoyvjGames", 60, H - 44);
    return canvas;
  }

  function finish(payload, image) {
    try {
      const canvas = draw(payload, image);
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
    if (typeof payload.thumb === "string" && payload.thumb.indexOf("data:image/jpeg;base64,") === 0) {
      const image = new Image();
      image.onload = function () { finish(payload, image); };
      image.onerror = function () { finish(payload, null); };
      image.src = payload.thumb;
    } else {
      finish(payload, null);
    }
  }

  window.ContinuumCard = { download: download };
})();
