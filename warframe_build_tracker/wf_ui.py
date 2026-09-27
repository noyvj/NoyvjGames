"""Rendering and event handling for the batch B planners ("5. Deeper planners").

Runs inside the same Pyodide interpreter as game.py but is handed everything it needs through
one `ctx` object (built by game.py's setup()), rather than importing game.py, so it works both
in the browser (where game.py runs as __main__) and under the test fakes. The logic itself lives
in the pure modules wf_relics, wf_crafting, wf_forma, wf_plans, wf_insight and wf_tips; this file
only turns their results into DOM nodes and clicks into calls. All UI state (open tab, chosen
build, last import's owned-item names) lives on the Planner instance, never at module level.

ctx fields used: document, create_proxy, state, el, button, fill, say, by_id, active_proxies,
calculate, render, active_rows, all_combos, part_category, recipes, refinery_plan, refinery_recipes,
location_places, resource_names, blueprint_owned, resource_usage, build_names, add_timer, now_ms, now_stamp.
"""

import wf_crafting
import wf_forma
import wf_insight
import wf_plans
import wf_relics
import wf_store
import wf_tips
from wf_util import norm

ADV_KEYS = ("meta", "session", "relics", "crafts", "forma", "pets", "diff", "audit", "ready", "tips")


class Planner:
    def __init__(self, ctx):
        self.ctx = ctx
        self.ui = {"tab": "meta", "meta": "", "seen": None, "tails": set()}

    # --- small helpers -----------------------------------------------------

    def _val(self, element_id):
        return str(self.ctx.by_id(element_id).value or "")

    def _int(self, element_id, limit):
        """A typed whole number 0..limit, or None when blank or not a number."""
        text = self._val(element_id).strip()
        if not text:
            return None
        try:
            return max(0, min(limit, int(float(text))))
        except (ValueError, OverflowError):
            return None

    def _clear(self, *ids):
        for element_id in ids:
            self.ctx.by_id(element_id).value = ""

    def _wire(self, element_id, event, handler):
        self.ctx.by_id(element_id).addEventListener(event, self.ctx.create_proxy(handler))

    def _proxy(self, handler):
        proxy = self.ctx.create_proxy(handler)
        self.ctx.active_proxies.append(proxy)
        return proxy

    def _check(self, text, checked, handler, aria):
        label = self.ctx.el("label", class_="mini-text")
        box = self.ctx.el("input", type="checkbox", aria_label=aria)
        box.checked = checked
        box.addEventListener("change", self._proxy(lambda _e, b=box: handler(bool(b.checked))))
        label.appendChild(box)
        label.appendChild(self.ctx.el("span", text=" " + text))
        return label

    def _lines(self, container_id, lines):
        box = self.ctx.by_id(container_id)
        box.innerHTML = ""
        for line in lines:
            box.appendChild(self.ctx.el("p", class_="sync adv-line", text=line))

    def _bar(self, percent, label):
        wrap = self.ctx.el("div", class_="cat-progress")
        wrap.appendChild(self.ctx.el("span", class_="cat-progress-label", text=label))
        track = self.ctx.el("div", class_="progress small", role="progressbar", aria_valuemin="0",
                            aria_valuemax="100", aria_valuenow=str(percent), aria_label=f"{label} progress")
        fill = self.ctx.el("div", class_="progress-fill")
        fill.style.width = f"{percent}%"
        track.appendChild(fill)
        wrap.appendChild(track)
        wrap.appendChild(self.ctx.el("span", class_="cat-progress-count", text=f"{percent}%"))
        return wrap

    def _options(self, element_id, values):
        box = self.ctx.by_id(element_id)
        box.innerHTML = ""
        for value in values:
            box.appendChild(self.ctx.el("option", value=value))

    def _after(self, message_id, result, *clear_ids):
        ok, message = result
        self.ctx.say(message_id, message)
        if ok:
            self._clear(*clear_ids)
        self.ctx.render()
        return ok

    # --- tabs --------------------------------------------------------------

    def select_tab(self, key):
        if key not in ADV_KEYS:
            return
        self.ui["tab"] = key
        for k in ADV_KEYS:
            self.ctx.by_id(f"adv-{k}").hidden = k != key
            button = self.ctx.by_id(f"adv-btn-{k}")
            button.className = "tab-btn selected" if k == key else "tab-btn"
            button.setAttribute("aria-selected", "true" if k == key else "false")

    # --- render ------------------------------------------------------------

    def render(self, components, resources):
        self._render_meta(components)
        self._render_session(resources)
        self._render_relics()
        self._render_crafts()
        self._render_forma()
        self._render_pets()
        self.ctx.by_id("diff-text").textContent = wf_insight.diff_text(self.ctx.state["imports"])
        self._render_audit(resources)
        self._render_ready(components)
        self._render_tips()

    def _render_meta(self, components):
        c = self.ctx
        combos = c.all_combos()
        names = [x["name"] for x in combos]
        if self.ui["meta"] not in names:
            self.ui["meta"] = names[0] if names else ""
        select = c.by_id("meta-select")
        select.innerHTML = ""
        for combo in combos:
            select.appendChild(c.el("option", value=combo["name"], text=f"{combo['name']} ({combo['category']}, {combo['source']})"))
        select.value = self.ui["meta"]
        bar, text = c.by_id("meta-bar"), c.by_id("meta-text")
        bar.innerHTML = ""
        if not combos:
            text.textContent = "No builds to plan yet. Add a combo in the Build comparison box."
            return
        combo = next(x for x in combos if x["name"] == self.ui["meta"])
        plan = wf_plans.meta_plan(combo, components, c.state["inventory"], c.recipes, c.refinery_plan)
        bar.appendChild(self._bar(plan["percent"], combo["name"]))
        text.textContent = wf_plans.meta_text(plan)

    def _render_session(self, resources):
        c = self.ctx
        session = wf_plans.farm_session(c.active_rows(resources), c.location_places)
        c.by_id("session-text").textContent = "\n".join(wf_plans.session_lines(session))

    def _render_relics(self):
        c = self.ctx
        rel = c.state["relics"]
        c.by_id("relic-source").textContent = wf_relics.SOURCE_NOTE
        self._options("relic-part-list", wf_relics.known_parts(rel))
        self._options("relic-name-list", wf_relics.relic_names(rel))
        plan = wf_relics.build_plan(rel)
        rows = []
        for want, line in zip(plan["wants"], wf_relics.plan_lines(plan)):
            rows.append(c.mini_row(line, [c.button("Remove", lambda _e, p=want["part"]: self._remove_want(p),
                                                   aria=f"Remove wanted part {want['part']}")]))
        if plan["steps"]:
            rows.append(c.el("h3", text=f"Order to open or farm ({plan['owned_total']} relic(s) owned that carry a wanted part)"))
            for number, step in enumerate(plan["steps"], 1):
                rows.append(c.el("p", class_="sync adv-line", text=wf_relics.step_text(step, number)))
        if rel["custom"]:
            rows.append(c.el("h3", text="Relics you added"))
            for custom in rel["custom"]:
                rows.append(c.el("p", class_="sync adv-line", text=(
                    f"{custom['n']} ({'unvaulted' if custom['v'] else 'vaulted'}): {', '.join(custom['p'])}"
                    + (f". You own {rel['owned'][custom['n']]}." if custom["n"] in rel["owned"] else ""))))
        c.fill("relic-plan", rows, "Nothing listed yet. Add a prime part you want, for example Braton Prime Barrel.")

    def _remove_want(self, part):
        ok, message = wf_relics.remove_want(self.ctx.state["relics"], part)
        self.ctx.say("relic-message", message)
        self.ctx.render()

    def _render_crafts(self):
        c = self.ctx
        seen = self.ui["seen"]
        c.by_id("craft-import-note").textContent = (
            "No import has run this session, so nothing is marked from a file yet." if seen is None else
            f"The last import this session saw {seen} owned item(s) in the file's equipment lists; crafting items whose "
            "name matches one are marked owned (import). Anything else, tick by hand.")
        self._options("craft-name-list", [x["n"] for x in c.state["crafts"]])
        rows = []
        for craft in c.state["crafts"]:
            info = wf_crafting.craft_progress(craft, c.state["inventory"], c.resource_names)
            card = c.el("div", class_="adv-card")
            head = c.el("div", class_="mini-row")
            head.appendChild(c.el("strong", class_="mini-text", text=f"{craft['n']} ({wf_crafting.CRAFT_KIND_LABELS[craft['k']]})"))
            head.appendChild(self._check("owned" + (f" ({info['source']})" if info["source"] else ""), info["owned"],
                                         lambda flag, n=craft["n"]: self._set_owned(n, flag), f"Owned: {craft['n']}"))
            head.appendChild(c.button("Remove item", lambda _e, n=craft["n"]: self._remove_craft(n), aria=f"Remove {craft['n']}"))
            card.appendChild(head)
            card.appendChild(self._bar(info["pct"], craft["n"]))
            status = ("Owned." if info["owned"] else "Every component is on hand: ready to craft." if info["ready"]
                      else "Components still short." if info["needs"] else "No components listed yet.")
            card.appendChild(c.el("p", class_="sync adv-line", text=status))
            for index, need in enumerate(info["needs"]):
                row = c.el("div", class_="mini-row")
                row.appendChild(c.el("span", class_="mini-text", text=(
                    f"{need['n']}: {need['have']}/{need['q']}" + (" (from your inventory)" if need["linked"] else "")
                    + (f", short {need['short']}" if need["short"] else ""))))
                if not need["linked"]:
                    box = c.el("input", type="number", min="0", class_="craft-have-input", aria_label=f"Have of {need['n']}")
                    box.value = str(craft["needs"][index]["h"])
                    box.addEventListener("change", self._proxy(lambda _e, n=craft["n"], i=index, b=box: self._set_have(n, i, b)))
                    row.appendChild(box)
                row.appendChild(c.button("Remove", lambda _e, n=craft["n"], i=index: self._remove_need(n, i),
                                         aria=f"Remove component {need['n']}"))
                card.appendChild(row)
            rows.append(card)
        c.fill("craft-list", rows, "No items yet. Add a weapon, warframe or companion you are crafting.")

    def _set_owned(self, name, flag):
        craft = wf_crafting.find_craft(self.ctx.state["crafts"], name)
        if craft:
            wf_crafting.set_owned(craft, flag)
        self.ctx.render()

    def _remove_craft(self, name):
        wf_crafting.remove_craft(self.ctx.state["crafts"], name)
        wf_store.prune(self.ctx.state, self.ctx.build_names())
        self.ctx.render()

    def _set_have(self, name, index, box):
        craft = wf_crafting.find_craft(self.ctx.state["crafts"], name)
        try:
            value = max(0, min(wf_crafting.QTY_MAX, int(float(str(box.value or "0")))))
        except (ValueError, OverflowError):
            value = 0
        if craft:
            wf_crafting.set_have(craft, index, value)
        self.ctx.render()

    def _remove_need(self, name, index):
        craft = wf_crafting.find_craft(self.ctx.state["crafts"], name)
        if craft and 0 <= index < len(craft["needs"]):
            del craft["needs"][index]
        self.ctx.render()

    def _render_forma(self):
        c = self.ctx
        forma = c.state["forma"]
        c.by_id("forma-have-input").value = str(forma["have"]) if forma["have"] else ""
        c.by_id("forma-used-input").value = str(forma["used"]) if forma["used"] else ""
        c.by_id("forma-total").textContent = wf_forma.totals_text(forma)
        relics = wf_relics.forma_relics()
        c.by_id("forma-note").textContent = (
            f"{len(relics)} of the embedded unvaulted relics list a Forma Blueprint (Void relics tab; data read "
            f"{wf_relics.SOURCE_DATE}). A Forma resets an item to Unranked and needs it at max rank "
            f"(Warframe Wiki, Forma page, read {wf_forma.FACTS_DATE}).")
        self._options("forma-target-list", wf_store.plan_targets(c.state, c.build_names()))
        rows = []
        for plan in forma["plans"]:
            card = c.el("div", class_="adv-card")
            head = c.el("div", class_="mini-row")
            head.appendChild(c.el("strong", class_="mini-text", text=f"{plan['n']}: {len(wf_forma.steps(plan))} Forma"))
            head.appendChild(self._check("active", plan["on"], lambda flag, n=plan["n"]: self._set_plan_active(n, flag),
                                         f"Include {plan['n']} in the running total"))
            head.appendChild(c.button("Remove", lambda _e, n=plan["n"]: self._remove_plan(n), aria=f"Remove Forma plan {plan['n']}"))
            card.appendChild(head)
            card.appendChild(c.el("p", class_="sync adv-line", text="Slots now: " + ", ".join(plan["cur"]) + ". Wanted: " + ", ".join(plan["want"]) + "."))
            card.appendChild(c.el("p", class_="sync adv-line", text=wf_forma.step_text(plan)))
            links = c.el("div", class_="adv-links")
            for label, url in wf_forma.overframe_links(plan["n"], self._category(plan["n"])):
                links.appendChild(c.el("a", href=url, target="_blank", rel="noopener", text=label + " ↗"))
            card.appendChild(links)
            rows.append(card)
        if rows:
            rows.append(c.el("p", class_="sync", text=wf_forma.LINK_NOTE))
        c.fill("forma-list", rows, "No Forma plans yet.")

    def _category(self, name):
        c = self.ctx
        if name in c.part_category:
            return c.part_category[name]
        combo = next((x for x in c.all_combos() if x["name"] == name), None)
        if combo:
            return combo["category"]
        craft = wf_crafting.find_craft(c.state["crafts"], name)
        return craft["k"] if craft else None

    def _set_plan_active(self, name, flag):
        wf_forma.set_active(self.ctx.state["forma"], name, flag)
        self.ctx.render()

    def _remove_plan(self, name):
        wf_forma.remove_plan(self.ctx.state["forma"], name)
        self.ctx.render()

    def _render_pets(self):
        c = self.ctx
        facts = c.by_id("pet-facts")
        facts.innerHTML = ""
        for text, url in wf_crafting.PET_FACTS:
            line = c.el("p", class_="sync adv-line", text=text + " ")
            line.appendChild(c.el("a", href=url, target="_blank", rel="noopener", text=f"Wiki, read {wf_crafting.PET_FACTS_DATE} ↗"))
            facts.appendChild(line)
        rows = []
        for pet in c.state["pets"]:
            imprint = c.button("+1 imprint", lambda _e, n=pet["n"]: self._bump(n), aria=f"Log one more imprint for {pet['n']}")
            timer = c.button("Imprint timer (1.5 h)", lambda _e, n=pet["n"]: self._imprint_timer(n),
                             aria=f"Add a 1.5 hour imprint timer for {pet['n']}")
            remove = c.button("Remove", lambda _e, n=pet["n"]: self._remove_pet(n), aria=f"Remove {pet['n']}")
            rows.append(c.mini_row(wf_crafting.pet_line(pet), [imprint, timer, remove]))
        c.fill("pet-list", rows, "No pets logged yet.")

    def _bump(self, name):
        ok, message = wf_crafting.bump_imprint(self.ctx.state["pets"], name)
        self.ctx.say("pet-message", message)
        self.ctx.render()

    def _imprint_timer(self, name):
        ok, message = self.ctx.add_timer(f"Imprint {name}", start_ms=self.ctx.now_ms(),
                                         duration_min=round(wf_crafting.IMPRINT_HOURS * 60))
        self.ctx.say("pet-message", message if not ok else f"Added a 1.5 hour imprint timer for {name} (Foundry timers tab).")
        self.ctx.render()

    def _remove_pet(self, name):
        wf_crafting.remove_pet(self.ctx.state["pets"], name)
        self.ctx.render()

    def _render_audit(self, resources):
        c = self.ctx
        audit = wf_insight.waste_audit(resources, c.state["inventory"], c.resource_names, c.refinery_recipes,
                                       c.blueprint_owned, c.resource_usage)
        self._lines("audit-list", wf_insight.audit_lines(audit))

    def _render_ready(self, components):
        c = self.ctx
        result = wf_insight.readiness(components, c.state["forma"]["used"], c.state["readiness"]["mods"])
        c.by_id("ready-score").textContent = f"Endgame readiness: {result['score']} / 100 ({result['title']})"
        self._lines("ready-breakdown", wf_insight.readiness_lines(result))
        rows = []
        for mod in c.state["readiness"]["mods"]:
            rows.append(c.mini_row(f"{mod['n']}: rank {mod['r']}/{mod['m']}",
                                   [c.button("Remove", lambda _e, n=mod["n"]: self._remove_mod(n), aria=f"Remove mod {mod['n']}")]))
        c.fill("ready-mod-list", rows, "No mods typed yet.")

    def _remove_mod(self, name):
        wf_insight.remove_mod(self.ctx.state["readiness"]["mods"], name)
        self.ctx.render()

    def _render_tips(self):
        c = self.ctx
        c.by_id("tips-summary").textContent = wf_tips.summary_text()
        rows = []
        for entry in wf_tips.all_tips():
            row = c.el("div", class_="adv-card")
            row.appendChild(c.el("strong", text=entry["resource"]))
            row.appendChild(c.el("p", class_="sync adv-line", text=(
                f"{entry['section']}: {entry['text']}" if entry["text"] else entry["note"])))
            row.appendChild(c.el("a", href=entry["url"], target="_blank", rel="noopener", text=f"Source: Warframe Wiki, read {entry['date']} ↗"))
            rows.append(row)
        c.fill("tips-list", rows)

    # --- events ------------------------------------------------------------

    def _on_meta(self, _event=None):
        self.ui["meta"] = self._val("meta-select")
        self.ctx.render()

    def _on_want_add(self, _event=None):
        self._after("relic-message", wf_relics.add_want(self.ctx.state["relics"], self._val("relic-want-input")), "relic-want-input")

    def _on_want_remove(self, _event=None):
        self._after("relic-message", wf_relics.remove_want(self.ctx.state["relics"], self._val("relic-want-input")), "relic-want-input")

    def _on_owned_set(self, _event=None):
        count = self._int("relic-owned-count-input", wf_relics.OWNED_MAX)
        result = (wf_relics.set_owned(self.ctx.state["relics"], self._val("relic-owned-name-input"), count) if count is not None
                  else (False, "Type how many you own (0 removes it)."))
        self._after("relic-message", result, "relic-owned-name-input", "relic-owned-count-input")

    def _on_custom_add(self, _event=None):
        result = wf_relics.add_custom(self.ctx.state["relics"], self._val("relic-custom-name-input"),
                                      self._val("relic-custom-parts-input"), bool(self.ctx.by_id("relic-custom-unvaulted-check").checked))
        self._after("relic-message", result, "relic-custom-name-input", "relic-custom-parts-input")

    def _on_custom_remove(self, _event=None):
        self._after("relic-message", wf_relics.remove_custom(self.ctx.state["relics"], self._val("relic-custom-name-input")),
                    "relic-custom-name-input")

    def _on_craft_add(self, _event=None):
        c = self.ctx
        name = self._val("craft-name-input")
        result = wf_crafting.add_craft(c.state["crafts"], name, self._val("craft-kind-select"))
        if result[0] and self.ui["tails"]:
            craft = wf_crafting.find_craft(c.state["crafts"], name)
            craft["imp"] = norm(craft["n"]) in self.ui["tails"]
        self._after("craft-message", result, "craft-name-input")

    def _on_need_add(self, _event=None):
        qty = self._int("craft-need-qty-input", wf_crafting.QTY_MAX)
        c = self.ctx
        result = (wf_crafting.add_need(c.state["crafts"], self._val("craft-need-item-input"), self._val("craft-need-name-input"),
                                       qty, c.resource_names) if qty else (False, "Type how many of the component you need."))
        self._after("craft-message", result, "craft-need-name-input", "craft-need-qty-input")

    def _on_forma_add(self, _event=None):
        c = self.ctx
        result = wf_forma.add_plan(c.state["forma"], self._val("forma-build-input"), self._val("forma-current-input"),
                                   self._val("forma-wanted-input"), wf_store.plan_targets(c.state, c.build_names()))
        self._after("forma-message", result, "forma-build-input", "forma-current-input", "forma-wanted-input")

    def _on_forma_counts(self, _event=None):
        forma = self.ctx.state["forma"]
        forma["have"] = self._int("forma-have-input", wf_forma.COUNT_MAX) or 0
        forma["used"] = self._int("forma-used-input", wf_forma.COUNT_MAX) or 0
        self.ctx.render()

    def _on_pet_add(self, _event=None):
        imprints = self._int("pet-imprints-input", wf_crafting.IMPRINT_MAX)
        result = wf_crafting.add_pet(self.ctx.state["pets"], self._val("pet-name-input"), self._val("pet-kind-select"),
                                     imprints or 0, self._val("pet-mods-input"), self._val("pet-note-input"))
        self._after("pet-message", result, "pet-name-input", "pet-imprints-input", "pet-mods-input", "pet-note-input")

    def _on_mod_add(self, _event=None):
        rank = self._int("ready-mod-rank-input", wf_insight.MOD_RANK_MAX)
        max_rank = self._int("ready-mod-max-input", wf_insight.MOD_RANK_MAX)
        result = (wf_insight.add_mod(self.ctx.state["readiness"]["mods"], self._val("ready-mod-name-input"), rank, max_rank)
                  if rank is not None and max_rank else (False, "Type the mod's rank and its max rank."))
        self._after("ready-message", result, "ready-mod-name-input", "ready-mod-rank-input", "ready-mod-max-input")

    def after_import(self, data, counts):
        """Called by import_last_data() once the resource counts are applied: marks crafts owned from
        the file's owned-item lists and stores this import's counts for the diff. Returns a sentence
        to append to the import summary ("" when there is nothing to add)."""
        tails, seen = wf_crafting.owned_tails(data)
        self.ui["seen"], self.ui["tails"] = seen, tails
        newly = wf_crafting.mark_imported(self.ctx.state["crafts"], tails)
        wf_insight.record_import(self.ctx.state["imports"], self.ctx.now_stamp(), counts, newly)
        if not self.ctx.state["crafts"]:
            return ""
        return (f" The file listed {seen} owned item(s); {len(newly)} of your crafting items were marked owned"
                + (f" ({', '.join(newly)})." if newly else "."))

    def setup(self):
        for key in ADV_KEYS:
            self._wire(f"adv-btn-{key}", "click", lambda _e, k=key: self.select_tab(k))
        self._wire("meta-select", "change", self._on_meta)
        self._wire("relic-want-add-button", "click", self._on_want_add)
        self._wire("relic-want-remove-button", "click", self._on_want_remove)
        self._wire("relic-owned-set-button", "click", self._on_owned_set)
        self._wire("relic-custom-add-button", "click", self._on_custom_add)
        self._wire("relic-custom-remove-button", "click", self._on_custom_remove)
        self._wire("craft-add-button", "click", self._on_craft_add)
        self._wire("craft-need-add-button", "click", self._on_need_add)
        self._wire("forma-add-button", "click", self._on_forma_add)
        self._wire("forma-have-input", "change", self._on_forma_counts)
        self._wire("forma-used-input", "change", self._on_forma_counts)
        self._wire("pet-add-button", "click", self._on_pet_add)
        self._wire("ready-mod-add-button", "click", self._on_mod_add)
        self.select_tab(self.ui["tab"])
