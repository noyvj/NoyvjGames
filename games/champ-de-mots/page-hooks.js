// Browser-side helpers game.py (the Python side) calls through `js.window`: speech, per-browser prefs, the real date,
// the Faux Amis fetch, downloads and the answer-report sender. Python decides what to do; this file owns the one external thing.
// L7a: the real calendar date (device-local, YYYY-MM-DD) for the study
// calendar. game.py may not touch a clock itself, so it asks here.
// L9: French speech via the browser's own voices; no audio files.
window.champSpeechAvailable = function () {
  return "speechSynthesis" in window && typeof SpeechSynthesisUtterance === "function";
};
window.champSpeak = function (text, slow) {
  if (!window.champSpeechAvailable()) return;
  try {
    window.speechSynthesis.cancel();
    const utterance = new SpeechSynthesisUtterance(String(text));
    utterance.lang = "fr-FR";
    const voice = window.speechSynthesis.getVoices().find((v) => (v.lang || "").toLowerCase().startsWith("fr"));
    if (voice) utterance.voice = voice;
    utterance.rate = slow ? 0.6 : 0.9;
    window.speechSynthesis.speak(utterance);
  } catch (e) { /* speech is a nicety; never break the game */ }
};
// Per-browser preferences (the Always multiple choice setting and every
// minigame's difficulty). Not part of the save code; failures are silent.
window.champPrefGet = function (key) {
  try { return window.localStorage.getItem(String(key)); } catch (e) { return null; }
};
window.champPrefSet = function (key, value) {
  try { window.localStorage.setItem(String(key), String(value)); } catch (e) { /* a nicety */ }
};
window.studyToday = function () {
  const d = new Date();
  const pad = (n) => String(n).padStart(2, "0");
  return d.getFullYear() + "-" + pad(d.getMonth() + 1) + "-" + pad(d.getDate());
};
window.championFetchText = function (url) {
  // Faux Amis: reads the live public list (a GET only; nothing is ever sent).
  return fetch(url, { credentials: "omit" }).then(function (r) {
    if (!r.ok) throw new Error("HTTP " + r.status);
    return r.text();
  });
};
window.championDownload = function (filename, text, mime) {
  try {
    const blob = new Blob([text], { type: mime + ";charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    a.remove();
    setTimeout(function () { URL.revokeObjectURL(url); }, 1000);
  } catch (e) { /* a download is a nicety; never break the game */ }
};
window.submitAnswerReport = function (jsonPayload) {
  fetch("https://noyvjgames.fastapicloud.dev/answer-reports", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: jsonPayload,
  }).catch(function () {});
};
