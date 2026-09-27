"""Batch B #5: the Forma planner and its Overframe links."""

from urllib.parse import quote

import wf_forma

from .helpers import all_text, click, find_all, known_state

TARGETS = ["Kronsh Strike", "177", "Excalibur Prime"]


def test_polarity_parsing_aliases_and_bounds():
    assert wf_forma.parse_polarities("Madurai, -, universal") == ["madurai", "none", "any"]
    assert wf_forma.parse_polarities("madurai,vazarin") == ["madurai", "vazarin"]
    assert wf_forma.parse_polarities("madurai, bogus") is None
    assert wf_forma.parse_polarities("") is None and wf_forma.parse_polarities(None) is None
    assert wf_forma.parse_polarities(",".join(["madurai"] * 13)) is None


def test_steps_count_only_slots_that_differ():
    forma = wf_forma.default_forma()
    assert wf_forma.add_plan(forma, "kronsh strike", "madurai, -, vazarin", "madurai, naramon, unairu", TARGETS)[0] is True
    plan = forma["plans"][0]
    assert plan["n"] == "Kronsh Strike"
    assert wf_forma.steps(plan) == [{"slot": 2, "from": "none", "to": "naramon"}, {"slot": 3, "from": "vazarin", "to": "unairu"}]
    text = wf_forma.step_text(plan)
    assert "Forma 1 of 2: slot 2, none to naramon" in text and "Forma 2 of 2: slot 3" in text and "Unranked" in text
    assert wf_forma.step_text({"cur": ["madurai"], "want": ["madurai"]}).startswith("Already matches")


def test_add_plan_validation_and_replace():
    forma = wf_forma.default_forma()
    assert wf_forma.add_plan(forma, "Not real", "madurai", "vazarin", TARGETS)[0] is False
    assert wf_forma.add_plan(forma, "177", "madurai", "vazarin, naramon", TARGETS)[0] is False  # slot counts differ
    assert wf_forma.add_plan(forma, "177", "madurai", "bogus", TARGETS)[0] is False
    assert wf_forma.add_plan(forma, "177", "madurai", "vazarin", TARGETS)[0] is True
    assert wf_forma.add_plan(forma, "177", "madurai", "madurai", TARGETS)[0] is True  # replaces, not duplicates
    assert len(forma["plans"]) == 1 and wf_forma.steps(forma["plans"][0]) == []


def test_running_total_across_active_plans_against_forma_held():
    forma = wf_forma.default_forma()
    wf_forma.add_plan(forma, "Kronsh Strike", "madurai, -", "vazarin, naramon", TARGETS)  # 2
    wf_forma.add_plan(forma, "177", "-", "madurai", TARGETS)  # 1
    wf_forma.add_plan(forma, "Excalibur Prime", "-,-,-", "madurai,madurai,madurai", TARGETS)  # 3
    assert wf_forma.totals(forma)["needed"] == 6 and wf_forma.totals(forma)["short"] == 6
    wf_forma.set_active(forma, "Excalibur Prime", False)
    assert wf_forma.totals(forma) == {"needed": 3, "have": 0, "short": 3, "used": 0, "active": 2}
    forma["have"] = 5
    assert wf_forma.totals(forma)["short"] == 0 and "that covers it" in wf_forma.totals_text(forma)
    forma["have"] = 1
    assert "still short 2" in wf_forma.totals_text(forma)
    assert wf_forma.totals_text(wf_forma.default_forma()) == "No plans yet."


def test_overframe_links_are_plain_external_and_come_from_the_verified_set():
    verified = {
        "/builds/warframes/", "/builds/primary-weapons/", "/builds/secondary-weapons/", "/builds/melee-weapons/",
        "/builds/sentinels/", "/items/warframe/", "/items/melee/", "/items/primary/", "/items/secondary/", "/items/pet/",
        "/items/all/", "/items/weapon/",
    }
    for category in (None, "warframe", "zaw", "kitgun", "amp", "companion", "weapon"):
        links = wf_forma.overframe_links("Kronsh Strike", category)
        assert 2 <= len(links) <= 3 and links[-1][1] == f"https://overframe.gg/search/?q={quote('Kronsh Strike')}"
        for _label, url in links[:-1]:
            assert url.startswith("https://overframe.gg/") and url[len("https://overframe.gg"):] in verified
    assert wf_forma.overframe_links("A B&c", "zaw")[-1][1].endswith("?q=A%20B%26c")  # the name is URL-encoded


def test_load_validation_and_round_trip():
    good = {"n": "177", "cur": ["madurai"], "want": ["vazarin"], "on": True}
    forma = wf_forma.load({"have": 3, "used": 2, "plans": [
        good, dict(good, n="Nope"), dict(good, cur=["madurai", "x"]), dict(good, cur=["bogus"]), dict(good, on="yes"),
        dict(good, cur=[], want=[]), dict(good, n="Kronsh Strike", want=["vazarin", "vazarin"]), "junk"]}, set(TARGETS))
    assert forma == {"have": 3, "used": 2, "plans": [good]}
    assert wf_forma.load({"have": -1, "used": True}, set(TARGETS)) == wf_forma.default_forma()
    assert wf_forma.load("junk", set(TARGETS)) == wf_forma.default_forma()
    assert wf_forma.export(wf_forma.default_forma()) == {} and wf_forma.load(wf_forma.export(forma), set(TARGETS)) == forma


def test_ui_plan_total_links_and_remove(game_env):
    m = game_env.module
    known_state(m)
    els = game_env.elements
    els["forma-build-input"].value = "Kronsh Strike"
    els["forma-current-input"].value = "madurai, -"
    els["forma-wanted-input"].value = "vazarin, naramon"
    click(els["forma-add-button"])
    assert els["forma-build-input"].value == "" and m.state["forma"]["plans"][0]["n"] == "Kronsh Strike"
    els["forma-have-input"].value = "1"
    els["forma-have-input"].dispatch("change", None)
    assert m.state["forma"]["have"] == 1 and "2 Forma needed across 1 active plan(s)" in els["forma-total"].textContent
    assert "still short 1" in els["forma-total"].textContent
    text = all_text(els["forma-list"])
    assert "Kronsh Strike: 2 Forma" in text and "Overframe" in text
    links = [a for a in find_all(els["forma-list"], tag="a") if a.attributes.get("href", "").startswith("https://overframe.gg/")]
    assert len(links) == 3 and all(a.attributes["rel"] == "noopener" and a.attributes["target"] == "_blank" for a in links)
    assert "melee" in links[0].attributes["href"]  # a zaw strike links the melee lists
    assert "Forma Blueprint" in els["forma-note"].textContent and "Unranked" in els["forma-note"].textContent
    box = find_all(els["forma-list"], tag="input")[0]
    box.checked = False
    box.dispatch("change", None)
    assert m.state["forma"]["plans"][0]["on"] is False and "0 Forma needed" in els["forma-total"].textContent
    click(find_all(els["forma-list"], tag="button", text="Remove")[0])
    assert m.state["forma"]["plans"] == []


def test_removing_a_combo_prunes_its_plan_and_a_craft_item_can_be_planned(game_env):
    m = game_env.module
    known_state(m)
    m.add_combo("Mine", ["Raplak Prism"])
    assert wf_forma.add_plan(m.state["forma"], "Mine", "-", "madurai", m._planner.ctx.build_names())[0] is True
    m.remove_combo("Mine")
    assert m.state["forma"]["plans"] == []
    els = game_env.elements
    els["craft-kind-select"].value = "warframe"
    els["craft-name-input"].value = "Excalibur Prime"
    click(els["craft-add-button"])
    els["forma-build-input"].value = "Excalibur Prime"
    els["forma-current-input"].value = "-"
    els["forma-wanted-input"].value = "madurai"
    click(els["forma-add-button"])
    assert m.state["forma"]["plans"][0]["n"] == "Excalibur Prime"
    hrefs = [a.attributes["href"] for a in find_all(els["forma-list"], tag="a")]
    assert "https://overframe.gg/builds/warframes/" in hrefs  # a crafting-tracker warframe uses the warframe lists
    click(find_all(els["craft-list"], tag="button", text="Remove item")[0])  # removing the craft prunes its plan
    assert m.state["forma"]["plans"] == []
