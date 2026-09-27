"""Batch B #10: the endgame readiness score (a personal benchmark)."""

import wf_insight

from .helpers import all_text, click, find_all, known_state


def _components(owned, target):
    return [{"owned": owned, "target": target}]


def test_score_is_the_weighted_sum_with_a_visible_breakdown():
    mods = [{"n": "Serration", "r": 5, "m": 10}, {"n": "Vitality", "r": 10, "m": 10}]
    result = wf_insight.readiness(_components(1, 2), 10, mods)
    assert result["parts"]["points"] == 20.0 and result["forma"]["points"] == 10.0 and result["mods"]["points"] == 30.0
    assert result["score"] == 60 and result["title"] == "Steel Path regular"
    lines = "\n".join(wf_insight.readiness_lines(result))
    assert "1 of 2 owned = 20.0 of 40" in lines and "10 used" in lines and "15 of 20 ranks across 2 typed mod(s) = 30.0 of 40" in lines
    assert "not a game figure" in lines


def test_extremes_and_caps():
    empty = wf_insight.readiness([], 0, [])
    assert empty["score"] == 0 and empty["title"] == "Fresh out of cryosleep"
    assert "none typed yet" in "\n".join(wf_insight.readiness_lines(empty))
    full = wf_insight.readiness(_components(3, 3), 500, [{"n": "A", "r": 5, "m": 5}])
    assert full["score"] == 100 and full["forma"]["points"] == 20.0 and full["title"] == "Beyond the Duviri sky"
    assert wf_insight.readiness(_components(5, 3), 0, [])["parts"]["owned"] == 3  # owned is capped at the target


def test_add_mod_validation_update_and_remove():
    mods = []
    assert wf_insight.add_mod(mods, "Serration", 3, 10)[0] is True
    assert wf_insight.add_mod(mods, "serration", 10, 10) == (True, "Updated Serration.") and mods[0]["r"] == 10 and len(mods) == 1
    assert wf_insight.add_mod(mods, "", 1, 5)[0] is False
    assert wf_insight.add_mod(mods, "X", 6, 5)[0] is False and wf_insight.add_mod(mods, "X", -1, 5)[0] is False
    assert wf_insight.add_mod(mods, "X", 1, 0)[0] is False and wf_insight.add_mod(mods, "X", 1, 999)[0] is False
    for i in range(wf_insight.MOD_MAX):
        wf_insight.add_mod(mods, f"M{i}", 1, 5)
    assert len(mods) == wf_insight.MOD_MAX and wf_insight.add_mod(mods, "Extra", 1, 5)[0] is False
    assert wf_insight.remove_mod(mods, "m0") is True and wf_insight.remove_mod(mods, "nope") is False


def test_load_validation_and_round_trip():
    good = {"n": "Serration", "r": 3, "m": 10}
    rd = wf_insight.load_readiness({"mods": [good, dict(good, n="B", r=11), dict(good, n="C", m=0), dict(good, n="D", r=True),
                                             dict(good, n="serration"), "junk", dict(good, n="")]})
    assert rd == {"mods": [good]}
    assert wf_insight.load_readiness("junk") == wf_insight.default_readiness()
    assert wf_insight.load_readiness(wf_insight.export_readiness(rd)) == rd


def test_ui_score_forma_used_and_mods(game_env):
    m = game_env.module
    known_state(m)
    els = game_env.elements
    assert "40 / 100 (Steady grinder)" in els["ready-score"].textContent  # every part owned, no Forma or mods yet
    els["forma-used-input"].value = "10"
    els["forma-used-input"].dispatch("change", None)
    assert m.state["forma"]["used"] == 10 and "50 / 100" in els["ready-score"].textContent
    els["ready-mod-name-input"].value = "Serration"
    els["ready-mod-rank-input"].value = "10"
    els["ready-mod-max-input"].value = "10"
    click(els["ready-mod-add-button"])
    assert m.state["readiness"]["mods"] == [{"n": "Serration", "r": 10, "m": 10}]
    assert "90 / 100 (Endgame-ready)" in els["ready-score"].textContent
    total = sum(p["target"] for p in m.state["parts"].values())
    assert f"Parts: {total} of {total} owned = 40.0 of 40 points." in all_text(els["ready-breakdown"])
    assert "Mods: 10 of 10 ranks across 1 typed mod(s) = 40.0 of 40 points." in all_text(els["ready-breakdown"])
    assert "Serration: rank 10/10" in all_text(els["ready-mod-list"])
    els["ready-mod-name-input"].value = "Bad"
    els["ready-mod-rank-input"].value = ""
    click(els["ready-mod-add-button"])
    assert "Type the mod's rank" in els["ready-message"].textContent
    click(find_all(els["ready-mod-list"], tag="button", text="Remove")[0])
    assert m.state["readiness"]["mods"] == []


def test_readiness_changes_no_needs(game_env):
    m = game_env.module
    known_state(m, parts={"Rahn Prism": {"owned": 0}})
    before = m.calculate()
    wf_insight.add_mod(m.state["readiness"]["mods"], "X", 1, 2)
    m.render()
    assert m.calculate() == before
