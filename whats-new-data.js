/*
 * The What's New feed's data layer, shared by whats-new.html (the public feed with its "was this
 * helpful?" thumbs) and the owner's stats page (to put readable names to the vote tallies). It reads
 * BCM114-DEV-LOG.md (individual game content) and BCM206-DEV-LOG.md (site infrastructure) live; there
 * is no build step, so an entry appended to a log shows up on the next load.
 *
 * Every entry gets a stable id, "<game|site>-<date>-<8 hex>", where the hex is a hash of the
 * entry's full "Did" text. The logs are append-only, so an id never changes once the entry exists, and
 * the server accepts only ids of exactly this shape (app/account_data.py ENTRY_ID_RE).
 */
(function () {
  "use strict";

  const LOG_SOURCES = [
    { path: "BCM114-DEV-LOG.md", label: "Game content", key: "game" },
    { path: "BCM206-DEV-LOG.md", label: "Site infrastructure", key: "site" },
  ];

  function truncate(text, maxLength) {
    if (text.length <= maxLength) return text;
    const cut = text.slice(0, maxLength);
    const lastSpace = cut.lastIndexOf(" ");
    return `${cut.slice(0, lastSpace > 0 ? lastSpace : maxLength)}…`;
  }

  // FNV-1a, 32 bit: small, dependency-free and good enough to tell entries on one day apart.
  function hash8(text) {
    let h = 0x811c9dc5;
    for (let i = 0; i < text.length; i++) {
      h ^= text.charCodeAt(i);
      h = Math.imul(h, 0x01000193) >>> 0;
    }
    return h.toString(16).padStart(8, "0");
  }

  // Every dev log entry starts with "### YYYY-MM-DD" and always includes a "**Did:** ..." line; BCM114
  // entries also carry "**Game:** ...". Only date + a trimmed one-line slice of "Did" is surfaced.
  function parseLogEntries(text, source) {
    const entries = [];
    text.split(/\n(?=### \d{4}-\d{2}-\d{2})/).forEach((block) => {
      const dateMatch = block.match(/^### (\d{4}-\d{2}-\d{2})/);
      const didMatch = block.match(/\*\*Did:\*\*\s*([\s\S]*?)(?:\n\*\*|\n---|\n##|$)/);
      if (!dateMatch || !didMatch) return;
      // Warframe tracker work is kept off the public feed.
      if (/warframe/i.test(block.split("\n")[0])) return;
      const gameMatch = block.match(/\*\*Game:\*\*\s*(.+)/);
      const oneLine = didMatch[1].replace(/\s+/g, " ").trim();
      entries.push({
        id: `${source.key}-${dateMatch[1]}-${hash8(oneLine)}`,
        date: dateMatch[1],
        label: source.label,
        game: gameMatch ? gameMatch[1].trim() : null,
        summary: truncate(oneLine, 180),
      });
    });
    return entries;
  }

  function groupByDate(entries) {
    const byDate = new Map();
    entries.forEach((entry) => {
      if (!byDate.has(entry.date)) byDate.set(entry.date, []);
      byDate.get(entry.date).push(entry);
    });
    return [...byDate.entries()].sort((a, b) => (a[0] < b[0] ? 1 : -1));
  }

  async function loadEntries() {
    const results = await Promise.all(
      LOG_SOURCES.map(async (source) => {
        const res = await fetch(source.path, { cache: "no-cache" });
        if (!res.ok) throw new Error(`status ${res.status}`);
        return parseLogEntries(await res.text(), source);
      })
    );
    return results.flat();
  }

  window.WhatsNewData = { LOG_SOURCES, parseLogEntries, groupByDate, loadEntries, truncate, hash8 };
})();
