/*
 * Shared skill-tree component (planning/TODO.md W-3, from your Round 3 answer
 * "where a game has meta-progression, build it as a skill tree"). First users:
 * Canopy's Seed Vault and ranger crews (GB-10, GB-26); the shape also fits Trade
 * Empire's existing charter perk tree (O-1) without changes. Full guide:
 * planning/SHARED-COMPONENTS.md.
 *
 *   <link rel="stylesheet" href="../../shared/skill-tree.css">   (optional: the
 *                              script links it itself when it is missing)
 *   <script src="../../shared/skill-tree.js"></script>
 *
 * A tree is plain data (ship it as JSON, or build it in Python and pass it in):
 *   { id, title, currency: "seed points",
 *     branches: [{ id, title, blurb }],                 // optional
 *     nodes: [{ id, branch, cost, label, description,   // description = effect text
 *               effect,                                  // effect id, default = id
 *               requires: [ids],                         // ALL must be owned
 *               tier }] }                                // optional, default = depth
 * Player state is only a list of owned node ids plus `earned`, the total points
 * ever given (balance = earned - spent, so it cannot drift; null = unlimited).
 *
 * Pure functions (same names, camelCase, and rules as shared/skill_tree.py; no
 * randomness, never mutate their arguments):
 *   validate, tierOf, spent, pointsLeft, sanitizeOwned, missingRequirements,
 *   status, canBuy, buy, canRefund, refund, refundAll, effects, hasEffect, totals
 * Renderer:
 *   const tree = NoyvjSkillTree.render(container, { tree, owned, earned,
 *     onBuy(id, node), onRefund(id, node), onRefundAll(), refundNodes: false });
 *   tree.update({ owned, earned });   // after the game changed its state
 *   tree.focus(id) / tree.announce(text) / tree.destroy()
 * The renderer never changes state itself: it calls the callbacks, the game
 * decides (confirm dialog, save, apply effects) and then calls update().
 * Text is written with textContent only.
 */
(function (root) {
  "use strict";

  const STATUS = { OWNED: "owned", AVAILABLE: "available", UNAFFORDABLE: "unaffordable", LOCKED: "locked" };

  // ---- pure rules ---------------------------------------------------------

  const isInt = (v) => typeof v === "number" && Number.isInteger(v);
  const isStr = (v) => typeof v === "string";

  function nodesOf(tree) {
    const nodes = tree && Array.isArray(tree.nodes) ? tree.nodes : [];
    return nodes.filter((n) => n && typeof n === "object" && isStr(n.id));
  }
  function nodeMap(tree) {
    const map = new Map();
    nodesOf(tree).forEach((n) => { if (!map.has(n.id)) map.set(n.id, n); });
    return map;
  }
  function requiresOf(node) { return Array.isArray(node.requires) ? node.requires.filter(isStr) : []; }
  function costOf(node) { return isInt(node.cost) && node.cost >= 0 ? node.cost : 0; }
  function effectOf(node) { return isStr(node.effect) && node.effect ? node.effect : node.id; }
  function uniq(list) { return Array.from(new Set(Array.isArray(list) ? list : [])); }

  function validate(tree) {
    const errors = [];
    const raw = tree && Array.isArray(tree.nodes) ? tree.nodes : null;
    if (!raw || !raw.length) return ["tree has no nodes"];
    const seen = new Set();
    raw.forEach((n) => {
      if (!n || typeof n !== "object" || !isStr(n.id) || !n.id) { errors.push("a node has no string id"); return; }
      if (seen.has(n.id)) errors.push("duplicate node id " + n.id);
      seen.add(n.id);
      if (!isInt(n.cost) || n.cost < 1) errors.push("node " + n.id + " needs an integer cost of at least 1");
      if (!isStr(n.label) || !n.label) errors.push("node " + n.id + " needs a label");
      if (n.requires !== undefined && (!Array.isArray(n.requires) || n.requires.some((r) => !isStr(r)))) {
        errors.push("node " + n.id + " requires must be a list of ids");
      }
    });
    raw.forEach((n) => {
      if (!n || !isStr(n.id)) return;
      requiresOf(n).forEach((r) => {
        if (r === n.id) errors.push("node " + n.id + " requires itself");
        else if (!seen.has(r)) errors.push("node " + n.id + " requires unknown node " + r);
      });
    });
    if (!errors.length) {
      const remaining = new Map(raw.map((n) => [n.id, new Set(requiresOf(n))]));
      while (remaining.size) {
        const ready = Array.from(remaining.keys()).filter((i) => !Array.from(remaining.get(i)).some((r) => remaining.has(r)));
        if (!ready.length) { errors.push("prerequisites form a cycle: " + Array.from(remaining.keys()).sort().join(", ")); break; }
        ready.forEach((i) => remaining.delete(i));
      }
    }
    return errors;
  }

  function tierOf(tree, id) {
    const nodes = nodeMap(tree);
    function depth(i, trail) {
      const node = nodes.get(i);
      if (!node || trail.has(i)) return 0;
      if (isInt(node.tier) && node.tier >= 1) return node.tier;
      const next = new Set(trail); next.add(i);
      let best = 0;
      requiresOf(node).forEach((r) => { best = Math.max(best, depth(r, next)); });
      return 1 + best;
    }
    return nodes.has(id) ? Math.max(depth(id, new Set()), 1) : 0;
  }

  function spent(tree, owned) {
    const nodes = nodeMap(tree);
    return uniq(owned).reduce((sum, i) => sum + (isStr(i) && nodes.has(i) ? costOf(nodes.get(i)) : 0), 0);
  }
  function pointsLeft(tree, owned, earned) {
    return earned === null || earned === undefined ? null : earned - spent(tree, owned);
  }

  function prune(nodes, owned) {
    let out = owned.slice();
    let changed = true;
    while (changed) {
      changed = false;
      out.slice().forEach((i) => {
        if (requiresOf(nodes.get(i)).some((r) => !out.includes(r))) { out = out.filter((x) => x !== i); changed = true; }
      });
    }
    return out;
  }

  function sanitizeOwned(tree, owned, earned, overspend) {
    const nodes = nodeMap(tree);
    let out = [];
    (Array.isArray(owned) ? owned : []).forEach((i) => { if (isStr(i) && nodes.has(i) && !out.includes(i)) out.push(i); });
    out = prune(nodes, out);
    if (earned !== null && earned !== undefined && spent(tree, out) > earned) {
      if (overspend !== "trim") return [];
      while (out.length && spent(tree, out) > earned) { out.pop(); out = prune(nodes, out); }
    }
    return out;
  }

  function missingRequirements(tree, owned, id) {
    const node = nodeMap(tree).get(id);
    if (!node) return [];
    const have = new Set(owned || []);
    return requiresOf(node).filter((r) => !have.has(r));
  }

  function status(tree, owned, id, earned) {
    const node = nodeMap(tree).get(id);
    if (!node) return STATUS.LOCKED;
    if ((owned || []).includes(id)) return STATUS.OWNED;
    if (missingRequirements(tree, owned, id).length) return STATUS.LOCKED;
    if (earned !== null && earned !== undefined && pointsLeft(tree, owned, earned) < costOf(node)) return STATUS.UNAFFORDABLE;
    return STATUS.AVAILABLE;
  }

  function canBuy(tree, owned, id, earned) {
    return isStr(id) && status(tree, owned, id, earned) === STATUS.AVAILABLE;
  }

  function buy(tree, owned, id, earned) {
    const current = Array.isArray(owned) ? owned.slice() : [];
    const known = isStr(id) && nodeMap(tree).has(id);
    const state = known ? status(tree, current, id, earned) : STATUS.LOCKED;
    let reason = "";
    if (state === STATUS.AVAILABLE) current.push(id);
    else if (!known) reason = "unknown";
    else if (state === STATUS.OWNED) reason = "owned";
    else if (state === STATUS.LOCKED) reason = "locked";
    else reason = "points";
    return { ok: state === STATUS.AVAILABLE && known, owned: current, spent: spent(tree, current), pointsLeft: pointsLeft(tree, current, earned), reason };
  }

  function canRefund(tree, owned, id) {
    const nodes = nodeMap(tree);
    if (!nodes.has(id) || !(owned || []).includes(id)) return false;
    return !owned.some((i) => i !== id && nodes.has(i) && requiresOf(nodes.get(i)).includes(id));
  }

  function refund(tree, owned, id) {
    const current = Array.isArray(owned) ? owned.slice() : [];
    if (!nodeMap(tree).has(id)) return { ok: false, owned: current, refunded: 0, reason: "unknown" };
    if (!current.includes(id)) return { ok: false, owned: current, refunded: 0, reason: "not-owned" };
    if (!canRefund(tree, current, id)) return { ok: false, owned: current, refunded: 0, reason: "needed" };
    return { ok: true, owned: current.filter((i) => i !== id), refunded: costOf(nodeMap(tree).get(id)), reason: "" };
  }

  function refundAll(tree, owned) {
    return { ok: true, owned: [], refunded: spent(tree, owned), reason: "" };
  }

  function effects(tree, owned) {
    const have = new Set(owned || []);
    return nodesOf(tree).filter((n) => have.has(n.id)).map(effectOf);
  }
  function hasEffect(tree, owned, effect) { return effects(tree, owned).includes(effect); }

  function totals(tree, owned, earned) {
    const nodes = nodesOf(tree);
    const have = new Set(owned || []);
    const byBranch = {};
    let totalCost = 0; let spentNow = 0; let ownedCount = 0;
    nodes.forEach((n) => {
      const key = n.branch || "";
      const slot = byBranch[key] || (byBranch[key] = { owned: 0, nodes: 0, spent: 0, cost: 0 });
      slot.nodes += 1; slot.cost += costOf(n); totalCost += costOf(n);
      if (have.has(n.id)) { slot.owned += 1; slot.spent += costOf(n); spentNow += costOf(n); ownedCount += 1; }
    });
    return {
      ownedCount, nodeCount: nodes.length, spent: spentNow, totalCost, remainingCost: totalCost - spentNow,
      pointsLeft: earned === null || earned === undefined ? null : earned - spentNow,
      complete: nodes.length > 0 && ownedCount === nodes.length, byBranch,
    };
  }

  // ---- renderer -----------------------------------------------------------

  const GLYPH = { owned: "✓", available: "◆", unaffordable: "◇", locked: "▪" };
  const STATE_WORD = { owned: "Owned", available: "Available", unaffordable: "Not enough points", locked: "Locked" };
  let counter = 0;

  function ensureStylesheet() {
    if (typeof document === "undefined" || document.querySelector('link[href*="skill-tree.css"]')) return;
    const own = document.currentScript || Array.from(document.scripts).find((s) => /skill-tree\.js/.test(s.src || ""));
    if (!own || !own.src) return;
    const link = document.createElement("link");
    link.rel = "stylesheet";
    link.href = own.src.replace(/skill-tree\.js(\?.*)?$/, "skill-tree.css");
    document.head.append(link);
  }
  ensureStylesheet();

  function plural(n, word) { return n + " " + (n === 1 ? word.replace(/s$/, "") : word); }

  function render(container, options) {
    const opts = options || {};
    let tree = opts.tree || { nodes: [] };
    let owned = sanitizeList(opts.owned);
    let earned = opts.earned === undefined ? null : opts.earned;
    const uid = "noyvj-st-" + (++counter);
    const els = {};      // node id -> { li, button, state, refund }
    let currentId = null;
    let announceEnabled = opts.announceChanges !== false;

    function sanitizeList(list) { return Array.isArray(list) ? uniq(list).filter(isStr) : []; }

    const rootEl = document.createElement("section");
    rootEl.className = "noyvj-st";
    const head = document.createElement("div");
    head.className = "noyvj-st-head";
    const title = document.createElement("h3");
    title.className = "noyvj-st-title";
    title.id = uid + "-title";
    const points = document.createElement("p");
    points.className = "noyvj-st-points";
    const refundAllBtn = document.createElement("button");
    refundAllBtn.type = "button";
    refundAllBtn.className = "noyvj-st-refund-all";
    refundAllBtn.textContent = "Refund all";
    refundAllBtn.addEventListener("click", () => {
      if (refundAllBtn.getAttribute("aria-disabled") === "true") { say("Nothing to refund."); return; }
      if (typeof opts.onRefundAll === "function") opts.onRefundAll();
    });
    if (opts.showRefundAll !== false && typeof opts.onRefundAll === "function") head.append(title, points, refundAllBtn);
    else head.append(title, points);
    const help = document.createElement("p");
    help.className = "noyvj-st-help";
    help.id = uid + "-help";
    help.textContent = "Up and down move within a branch, left and right switch branch. Enter or Space buys an available perk." +
      (opts.refundNodes ? " R refunds the focused perk if nothing else needs it." : "");
    const live = document.createElement("p");
    live.className = "noyvj-st-live";
    live.setAttribute("role", "status");
    live.setAttribute("aria-live", "polite");
    const branchesEl = document.createElement("div");
    branchesEl.className = "noyvj-st-branches";
    branchesEl.setAttribute("role", "group");
    branchesEl.setAttribute("aria-labelledby", uid + "-title");
    branchesEl.setAttribute("aria-describedby", uid + "-help");
    rootEl.append(head, help, branchesEl, live);

    let branchLists = [];  // arrays of node ids per branch, in display order

    function say(text) {
      live.textContent = "";
      // A second tick so an identical message is announced again.
      setTimeout(() => { live.textContent = text; }, 20);
    }

    function currency() { return isStr(tree.currency) && tree.currency ? tree.currency : "points"; }

    function build() {
      Object.keys(els).forEach((k) => delete els[k]);
      branchesEl.textContent = "";
      title.textContent = opts.heading || tree.title || "Skill tree";
      const all = nodesOf(tree);
      const order = [];
      const declared = Array.isArray(tree.branches) ? tree.branches.filter((b) => b && isStr(b.id)) : [];
      declared.forEach((b) => order.push({ id: b.id, title: b.title || b.id, blurb: b.blurb || "" }));
      all.forEach((n) => {
        const key = n.branch || "";
        if (!order.some((b) => b.id === key)) order.push({ id: key, title: key || "Perks", blurb: "" });
      });
      branchLists = [];
      order.forEach((branch) => {
        const members = all
          .map((n, index) => ({ n, index }))
          .filter((m) => (m.n.branch || "") === branch.id)
          .sort((a, b) => tierOf(tree, a.n.id) - tierOf(tree, b.n.id) || a.index - b.index)
          .map((m) => m.n);
        if (!members.length) return;
        const section = document.createElement("section");
        section.className = "noyvj-st-branch";
        section.dataset.branch = branch.id;
        const h = document.createElement("h4");
        h.className = "noyvj-st-branch-title";
        h.id = uid + "-b-" + branchLists.length;
        h.textContent = branch.title;
        const count = document.createElement("span");
        count.className = "noyvj-st-branch-count";
        count.dataset.branchCount = branch.id;
        h.append(" ", count);
        section.append(h);
        if (branch.blurb) {
          const blurb = document.createElement("p");
          blurb.className = "noyvj-st-branch-blurb";
          blurb.textContent = branch.blurb;
          section.append(blurb);
        }
        const list = document.createElement("ol");
        list.className = "noyvj-st-nodes";
        list.setAttribute("aria-labelledby", h.id);
        members.forEach((node) => list.append(buildNode(node)));
        section.append(list);
        branchesEl.append(section);
        branchLists.push(members.map((n) => n.id));
      });
      if (!currentId || !els[currentId]) currentId = branchLists.length ? branchLists[0][0] : null;
    }

    function buildNode(node) {
      const li = document.createElement("li");
      li.className = "noyvj-st-node";
      li.dataset.node = node.id;
      const button = document.createElement("button");
      button.type = "button";
      button.className = "noyvj-st-btn";
      button.dataset.node = node.id;
      const glyph = document.createElement("span");
      glyph.className = "noyvj-st-glyph";
      glyph.setAttribute("aria-hidden", "true");
      const label = document.createElement("span");
      label.className = "noyvj-st-label";
      label.textContent = node.label || node.id;
      const meta = document.createElement("span");
      meta.className = "noyvj-st-meta";
      meta.textContent = "Tier " + tierOf(tree, node.id) + " · Cost " + plural(costOf(node), currency());
      button.append(glyph, label, meta);
      const desc = document.createElement("p");
      desc.className = "noyvj-st-desc";
      desc.id = uid + "-d-" + node.id;
      desc.textContent = node.description || "";
      const needs = document.createElement("p");
      needs.className = "noyvj-st-needs";
      needs.id = uid + "-n-" + node.id;
      const state = document.createElement("p");
      state.className = "noyvj-st-state";
      state.id = uid + "-s-" + node.id;
      button.setAttribute("aria-describedby", [desc.id, needs.id, state.id].join(" "));
      button.tabIndex = -1;
      button.addEventListener("click", () => activate(node.id));
      button.addEventListener("focus", () => setCurrent(node.id));
      button.addEventListener("keydown", (event) => onKey(event, node.id));
      li.append(button, desc);
      if (requiresOf(node).length) li.append(needs);
      li.append(state);
      let refundBtn = null;
      if (opts.refundNodes) {
        refundBtn = document.createElement("button");
        refundBtn.type = "button";
        refundBtn.className = "noyvj-st-refund";
        refundBtn.tabIndex = -1;
        refundBtn.textContent = "Refund";
        refundBtn.setAttribute("aria-label", "Refund " + (node.label || node.id));
        refundBtn.addEventListener("click", () => doRefund(node.id));
        li.append(refundBtn);
      }
      els[node.id] = { li, button, glyph, state, needs, refund: refundBtn, node };
      return li;
    }

    function labelOf(id) { const n = nodeMap(tree).get(id); return n ? (n.label || n.id) : id; }

    function paint() {
      const left = pointsLeft(tree, owned, earned);
      points.textContent = earned === null
        ? "Spent: " + plural(spent(tree, owned), currency())
        : plural(left, currency()) + " left of " + earned;
      const t = totals(tree, owned, earned);
      points.title = t.ownedCount + " of " + t.nodeCount + " perks owned";
      const canAny = owned.length > 0;
      refundAllBtn.setAttribute("aria-disabled", canAny ? "false" : "true");
      Object.keys(els).forEach((id) => {
        const e = els[id];
        const st = status(tree, owned, id, earned);
        const cost = costOf(e.node);
        e.li.className = "noyvj-st-node noyvj-st-node--" + st;
        e.li.dataset.status = st;
        e.glyph.textContent = GLYPH[st];
        e.button.setAttribute("aria-disabled", st === STATUS.AVAILABLE ? "false" : "true");
        let text = STATE_WORD[st];
        if (st === STATUS.AVAILABLE) text += ": buy for " + plural(cost, currency());
        else if (st === STATUS.UNAFFORDABLE) text += ": " + plural(cost - left, "more " + currency()) + " needed";
        else if (st === STATUS.LOCKED) text += ": needs " + missingRequirements(tree, owned, id).map(labelOf).join(" and ");
        e.state.textContent = text;
        const reqs = requiresOf(e.node);
        if (reqs.length) e.needs.textContent = "Needs: " + reqs.map((r) => labelOf(r) + (owned.includes(r) ? " (owned)" : "")).join(", ");
        if (e.refund) {
          e.refund.hidden = st !== STATUS.OWNED;
          e.refund.setAttribute("aria-disabled", canRefund(tree, owned, id) ? "false" : "true");
        }
      });
      Array.from(branchesEl.querySelectorAll("[data-branch-count]")).forEach((el) => {
        const slot = t.byBranch[el.dataset.branchCount] || { owned: 0, nodes: 0 };
        el.textContent = "(" + slot.owned + "/" + slot.nodes + ")";
      });
      Object.keys(els).forEach((id) => { els[id].button.tabIndex = id === currentId ? 0 : -1; });
    }

    function setCurrent(id) {
      if (!els[id]) return;
      currentId = id;
      Object.keys(els).forEach((k) => { els[k].button.tabIndex = k === id ? 0 : -1; });
    }

    function activate(id) {
      const st = status(tree, owned, id, earned);
      const e = els[id];
      if (st === STATUS.AVAILABLE) {
        if (typeof opts.onBuy === "function") opts.onBuy(id, e.node);
      } else {
        say(labelOf(id) + ". " + e.state.textContent);
      }
    }

    function doRefund(id) {
      if (!canRefund(tree, owned, id)) { say(labelOf(id) + " cannot be refunded while another owned perk needs it."); return; }
      if (typeof opts.onRefund === "function") opts.onRefund(id, els[id].node);
    }

    function focusId(id) { if (els[id]) { setCurrent(id); els[id].button.focus(); } }

    function onKey(event, id) {
      if (event.altKey || event.metaKey) return;
      let b = -1; let r = -1;
      branchLists.forEach((list, bi) => { const ri = list.indexOf(id); if (ri >= 0) { b = bi; r = ri; } });
      if (b < 0) return;
      let target = null;
      const list = branchLists[b];
      switch (event.key) {
        case "ArrowDown": target = list[Math.min(r + 1, list.length - 1)]; break;
        case "ArrowUp": target = list[Math.max(r - 1, 0)]; break;
        case "ArrowRight": if (b + 1 < branchLists.length) target = branchLists[b + 1][Math.min(r, branchLists[b + 1].length - 1)]; break;
        case "ArrowLeft": if (b > 0) target = branchLists[b - 1][Math.min(r, branchLists[b - 1].length - 1)]; break;
        case "Home": target = event.ctrlKey ? branchLists[0][0] : list[0]; break;
        case "End": target = event.ctrlKey ? branchLists[branchLists.length - 1].slice(-1)[0] : list[list.length - 1]; break;
        case "r": case "R":
          if (opts.refundNodes && owned.includes(id) && !event.ctrlKey) { event.preventDefault(); doRefund(id); }
          return;
        default: return;
      }
      event.preventDefault();
      if (target) focusId(target);
    }

    function update(next) {
      const n = next || {};
      const before = owned.slice();
      if (n.tree) { tree = n.tree; build(); }
      if (n.owned !== undefined) owned = sanitizeList(n.owned);
      if (n.earned !== undefined) earned = n.earned;
      paint();
      if (announceEnabled && n.owned !== undefined) {
        const added = owned.filter((i) => !before.includes(i));
        const removed = before.filter((i) => !owned.includes(i));
        if (added.length === 1 && !removed.length) {
          const left = pointsLeft(tree, owned, earned);
          say("Bought " + labelOf(added[0]) + "." + (left === null ? "" : " " + plural(left, currency()) + " left."));
        } else if (removed.length === 1 && !added.length) say("Refunded " + labelOf(removed[0]) + ".");
        else if (!owned.length && removed.length > 1) say("All perks refunded.");
      }
    }

    build();
    paint();
    container.textContent = "";
    container.append(rootEl);

    return {
      element: rootEl,
      update,
      focus: (id) => focusId(id || currentId),
      announce: say,
      current: () => currentId,
      destroy() { rootEl.remove(); },
    };
  }

  root.NoyvjSkillTree = {
    STATUS, validate, tierOf, spent, pointsLeft, sanitizeOwned, missingRequirements, status,
    canBuy, buy, canRefund, refund, refundAll, effects, hasEffect, totals, render,
  };
})(typeof window !== "undefined" ? window : globalThis);
