"""Batch A #9: colour tags per build, with a filter."""

from .helpers import all_text, find_all, known_state


def test_presets_and_custom_labels(game_env):
    m = game_env.module
    assert m.tag_labels() == ["daily driver", "fun", "sell"]
    assert m.add_tag_label("keep")[0] is True
    assert m.add_tag_label("KEEP")[0] is False
    assert m.add_tag_label("Fun")[0] is False  # clashes with a preset
    assert m.add_tag_label("")[0] is False
    assert m.add_tag_label("x" * 40)[0] is True
    assert m.state["tag_labels"][1] == "x" * m.TAG_LABEL_MAX
    for i in range(m.TAG_CUSTOM_MAX):
        m.add_tag_label(f"l{i}")
    assert len(m.state["tag_labels"]) == m.TAG_CUSTOM_MAX
    assert m.add_tag_label("over")[0] is False


def test_each_label_has_a_distinct_colour_and_unknown_is_grey(game_env):
    m = game_env.module
    colours = [m.tag_color(label) for label in m.tag_labels()]
    assert len(set(colours)) == 3
    assert m.tag_color("nope") == "#8a94a6"


def test_assign_clear_and_remove_label(game_env):
    m = game_env.module
    m.add_tag_label("keep")
    assert m.assign_tag("raplak prism", "FUN") == (True, "Tagged Raplak Prism as fun.")
    assert m.assign_tag("Raplak Prism", "keep")[0] is True
    assert m.state["tags"] == {"Raplak Prism": "keep"}
    assert m.assign_tag("Nope", "fun")[0] is False
    assert m.assign_tag("Raplak Prism", "missing")[0] is False
    assert m.remove_tag_label("fun")[0] is False  # presets stay
    assert m.remove_tag_label("keep")[0] is True
    assert m.state["tags"] == {}  # assignments to the removed label go too
    m.assign_tag("Raplak Prism", "sell")
    assert m.assign_tag("Raplak Prism", "") == (True, "Cleared the tag on Raplak Prism.")
    assert m.state["tags"] == {}


def test_filter_shows_only_tagged_parts(game_env):
    m = game_env.module
    known_state(m)
    m.assign_tag("Raplak Prism", "fun")
    m.assign_tag("Rahn Prism", "sell")
    components, _ = m.calculate()
    assert [p["name"] for p in m.arrange_components(components, tag="fun")] == ["Raplak Prism"]
    assert len(m.arrange_components(components)) == 33  # default is unfiltered
    sel = game_env.elements["tag-filter-select"]
    sel.value = "sell"
    sel.dispatch("change", None)
    rows = [r for r in game_env.elements["components-body"].children if r.attributes.get("data-part")]
    assert [r.attributes["data-part"] for r in rows] == ["Rahn Prism"]
    sel.value = ""
    sel.dispatch("change", None)
    assert len([r for r in game_env.elements["components-body"].children if r.attributes.get("data-part")]) == 33


def test_row_picker_and_panel_buttons(game_env):
    m = game_env.module
    known_state(m)
    row = next(r for r in game_env.elements["components-body"].children if r.attributes.get("data-part") == "Raplak Prism")
    select = find_all(row, tag="select", class_name="tag-select")[0]
    select.value = "daily driver"
    select.dispatch("change", None)
    assert m.state["tags"] == {"Raplak Prism": "daily driver"}
    row = next(r for r in game_env.elements["components-body"].children if r.attributes.get("data-part") == "Raplak Prism")
    assert find_all(row, class_name="build-tag")[0].textContent == "daily driver"  # the name, not only a colour
    els = game_env.elements
    els["tag-label-input"].value = "gift"
    els["tag-add-label-button"].dispatch("click", None)
    els["tag-name-input"].value = "Shwaak Prism"
    els["tag-assign-select"].value = "gift"
    els["tag-assign-button"].dispatch("click", None)
    assert m.state["tags"]["Shwaak Prism"] == "gift"
    assert "gift (1)" in all_text(els["tag-legend"])


def test_save_round_trip_and_validation(game_env):
    m = game_env.module
    st = m.get_state()
    assert "tags" not in st and "tag_labels" not in st
    m.add_tag_label("keep")
    m.assign_tag("Raplak Prism", "keep")
    saved = m.get_state()
    m.state["tags"], m.state["tag_labels"] = {}, []
    m.load_state(saved)
    assert m.state["tag_labels"] == ["keep"] and m.state["tags"] == {"Raplak Prism": "keep"}
    m.load_state({"tag_labels": ["a", "A", "fun", 4, "", ["x"]], "tags": {"Raplak Prism": "A", "Nope": "a", "Rahn Prism": "zzz", "Lega Prism": 5}})
    assert m.state["tag_labels"] == ["a"]
    assert m.state["tags"] == {"Raplak Prism": "a"}
    m.load_state({"tags": []})
    assert m.state["tags"] == {}
