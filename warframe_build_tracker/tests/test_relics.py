"""Batch B #2: the void relic planner (manual, with a sourced subset of the Wiki's relic data)."""

import wf_relics

from .helpers import all_text, click, find_all, known_state


def test_embedded_data_is_complete_and_shaped_like_the_wiki_pages():
    assert len(wf_relics.RELICS) == 34
    eras = {}
    for name, rows in wf_relics.RELICS.items():
        eras.setdefault(name.split()[0], []).append(name)
        assert [r["rarity"] for r in rows] == ["Common"] * 3 + ["Uncommon"] * 2 + ["Rare"]
    assert {k: len(v) for k, v in eras.items()} == {"Lith": 8, "Meso": 9, "Neo": 8, "Axi": 9}
    assert wf_relics.part_key("2 X Forma Blueprint") == "Forma Blueprint"
    assert "2026-09-27" in wf_relics.SOURCE_NOTE and "wiki.warframe.com/w/Void_Relic" in wf_relics.SOURCE_NOTE
    # spot checks against the relic pages read on 2026-09-27
    assert [r["part"] for r in wf_relics.RELICS["Lith A13"]][-1] == "Alternox Prime Blueprint"
    assert wf_relics.RELICS["Axi V14"][-1] == {"item": "Voruna Prime Blueprint", "part": "Voruna Prime Blueprint", "rarity": "Rare"}


def test_refinement_table_matches_the_wiki():
    assert wf_relics.chance("Common") == 25.33 and wf_relics.chance("Rare", "Radiant") == 10.0
    assert [(r["name"], r["traces"]) for r in wf_relics.REFINEMENT] == [
        ("Intact", 0), ("Exceptional", 25), ("Flawless", 50), ("Radiant", 100)]


def test_carriers_and_case_insensitive_want():
    rel = wf_relics.default_relics()
    assert wf_relics.add_want(rel, "fang prime blade") == (True, "Added Fang Prime Blade.")
    assert wf_relics.add_want(rel, "FANG PRIME BLADE")[0] is False
    found = {c["relic"]: c["rarity"] for c in wf_relics.carriers(rel, "Fang Prime Blade")}
    assert found == {"Lith A13": "Common", "Axi P10": "Common"}
    assert wf_relics.add_want(rel, "")[0] is False


def test_order_prefers_relics_carrying_more_wanted_parts_then_owned():
    rel = wf_relics.default_relics()
    for part in ("Fang Prime Blade", "Paris Prime Lower Limb", "Alternox Prime Blueprint"):
        wf_relics.add_want(rel, part)
    wf_relics.set_owned(rel, "axi d6", 4)
    plan = wf_relics.build_plan(rel)
    assert plan["steps"][0]["relic"] == "Lith A13" and len(plan["steps"][0]["carries"]) == 3
    assert plan["steps"][0]["level"] == "Intact"  # two commons outweigh the rare: 25.33+25.33+2 beats 16.67+16.67+10
    names = [s["relic"] for s in plan["steps"]]
    assert names.index("Axi D6") < names.index("Lith G14")  # owned before not owned, same size
    assert plan["owned_total"] == 4
    assert "You own 4: open these first" in wf_relics.step_text(next(s for s in plan["steps"] if s["relic"] == "Axi D6"), 2)


def test_a_wanted_rare_alone_pushes_the_best_level_to_radiant():
    rel = wf_relics.default_relics()
    wf_relics.add_want(rel, "Alternox Prime Blueprint")
    step = next(s for s in wf_relics.build_plan(rel)["steps"] if s["relic"] == "Lith A13")
    assert step["level"] == "Radiant" and step["traces"] == 100 and step["chance_sum"] == 10.0  # 10% vs 2% Intact
    assert "refine to Radiant (100 Void Traces)" in wf_relics.step_text(step, 1)


def test_commons_stay_intact_because_refining_lowers_their_chance():
    rel = wf_relics.default_relics()
    wf_relics.add_want(rel, "Braton Prime Barrel")
    step = wf_relics.build_plan(rel)["steps"][0]
    assert step["level"] == "Intact" and "keep it Intact" in wf_relics.step_text(step, 1)


def test_unknown_part_and_manual_relics():
    rel = wf_relics.default_relics()
    wf_relics.add_want(rel, "Zephyr Prime Wings")
    plan = wf_relics.build_plan(rel)
    assert plan["steps"] == [] and "not in the embedded relic data" in wf_relics.plan_lines(plan)[0]
    assert wf_relics.add_custom(rel, "Neo O1", "Zephyr Prime Wings, 2 x Forma Blueprint")[0] is True
    assert wf_relics.add_custom(rel, "neo o1", "x")[0] is False
    assert wf_relics.add_custom(rel, "Lith A13", "x")[0] is False  # clashes with an embedded relic
    assert wf_relics.add_custom(rel, "Empty", "")[0] is False
    plan = wf_relics.build_plan(rel)
    assert plan["steps"][0]["relic"] == "Neo O1" and plan["steps"][0]["yours"] is True
    assert "keep it Intact" not in wf_relics.step_text(plan["steps"][0], 1)  # no rarity typed: no chance claimed
    wf_relics.add_custom(rel, "Old", "Zephyr Prime Wings", unvaulted=False)
    plan = wf_relics.build_plan(rel)
    assert [s["relic"] for s in plan["steps"]] == ["Neo O1"]  # a vaulted relic is not farmable
    assert wf_relics.remove_custom(rel, "neo o1")[0] is True


def test_set_owned_validation():
    rel = wf_relics.default_relics()
    assert wf_relics.set_owned(rel, "Lith A13", 3)[0] is True and rel["owned"] == {"Lith A13": 3}
    assert wf_relics.set_owned(rel, "Nope", 3)[0] is False
    assert wf_relics.set_owned(rel, "Lith A13", -1)[0] is False and wf_relics.set_owned(rel, "Lith A13", 10 ** 6)[0] is False
    assert wf_relics.set_owned(rel, "Lith A13", 0)[0] is True and rel["owned"] == {}


def test_load_validates_everything():
    good = {"wants": ["Fang Prime Blade"], "owned": {"Lith A13": 2, "Nope": 1, "Meso D8": -1, "Meso C11": True},
            "custom": [{"n": "Neo O1", "v": True, "p": ["X"]}, {"n": "Lith A13", "v": True, "p": ["X"]},
                       {"n": "Bad", "v": "yes", "p": ["X"]}, {"n": "NoParts", "v": True, "p": []}, "junk"]}
    rel = wf_relics.load(good)
    assert rel["wants"] == ["Fang Prime Blade"] and rel["owned"] == {"Lith A13": 2}
    assert [c["n"] for c in rel["custom"]] == ["Neo O1"]
    assert wf_relics.load("junk") == wf_relics.default_relics() and wf_relics.load({"wants": {"a": 1}})["wants"] == []
    assert wf_relics.export(wf_relics.default_relics()) == {}
    assert wf_relics.load(wf_relics.export(rel)) == rel


def test_ui_add_owned_and_plan(game_env):
    m = game_env.module
    known_state(m)
    els = game_env.elements
    els["relic-want-input"].value = "paris prime lower limb"
    click(els["relic-want-add-button"])
    assert m.state["relics"]["wants"] == ["Paris Prime Lower Limb"] and els["relic-want-input"].value == ""
    els["relic-owned-name-input"].value = "Lith G14"
    els["relic-owned-count-input"].value = "2"
    click(els["relic-owned-set-button"])
    assert m.state["relics"]["owned"] == {"Lith G14": 2}
    text = all_text(els["relic-plan"])
    assert "Lith A13" in text and "You own 2" in text
    assert "Warframe Wiki" in els["relic-source"].textContent and "2026-09-27" in els["relic-source"].textContent
    els["relic-owned-count-input"].value = ""
    click(els["relic-owned-set-button"])
    assert "Type how many" in els["relic-message"].textContent
    click(find_all(els["relic-plan"], tag="button")[0])  # remove the wanted part
    assert m.state["relics"]["wants"] == []
    els["relic-custom-name-input"].value = "Neo O1"
    els["relic-custom-parts-input"].value = "Braton Prime Barrel"
    els["relic-custom-unvaulted-check"].checked = False
    click(els["relic-custom-add-button"])
    assert m.state["relics"]["custom"] == [{"n": "Neo O1", "v": False, "p": ["Braton Prime Barrel"]}]
    assert "vaulted" in all_text(els["relic-plan"])
