"""GB-28: the Forest Almanac, a checklist with silhouettes / '???' for unfound entries."""

from pathlib import Path

from .gb_helpers import decline_requests, make_mature, ring_around

HTML = (Path(__file__).resolve().parent.parent / "index.html").read_text(encoding="utf-8")


def _items(env):
    """{section heading text: [li elements]} in panel order."""
    panel = env.elements["almanac-panel"]
    sections = {}
    heading = None
    for child in panel.children:
        if child.className == "almanac-heading":
            heading = child.innerText
        elif child.className == "almanac-list":
            sections[heading] = child.children
    return sections


def _texts(li):
    return [c.innerText for c in li.children]


def test_panel_starts_hidden_and_toggles(game_env):
    panel = game_env.elements["almanac-panel"]
    toggle = game_env.elements["almanac-toggle-button"]
    assert panel.hidden is True and "Almanac" in toggle.innerText
    game_env.toggle_almanac()
    assert panel.hidden is False and "Hide Almanac" in toggle.innerText
    game_env.toggle_almanac()
    assert panel.hidden is True


def test_toggle_label_counts_found_entries(game_env):
    m = game_env.module
    found, total = m.almanac_found_total()
    assert f"({found}/{total})" in game_env.elements["almanac-toggle-button"].innerText
    assert total == 7 + 6 + 2 + 1


def test_unfound_entries_are_silhouettes_or_question_marks(game_env):
    game_env.toggle_almanac()
    sections = _items(game_env)
    wildlife = sections["Wildlife seen (0/6)"]
    assert all(_texts(li)[1] == "???" for li in wildlife)
    assert all("almanac-silhouette" in li.children[0].className for li in wildlife)
    rare = sections["Rare wildlife (0/2)"]
    assert all(_texts(li)[1] == "???" for li in rare)
    hidden = sections["Hidden structures (0/1)"][0]
    assert _texts(hidden) == ["", "???"]  # no silhouette hint at all
    assert hidden.getAttribute("aria-label") == "Hidden structures: not yet found"


def test_trees_planted_fill_in_as_you_play(game_env):
    m = game_env.module
    game_env.toggle_almanac()
    trees = _items(game_env)["Trees planted (1/7)"]
    assert _texts(trees[0])[1] == "Evergreen stand"
    game_env.select(0)
    game_env.clear()
    game_env.replant()
    game_env.tick(m.RECOVERY_TICKS)
    trees = _items(game_env)["Trees planted (3/7)"]
    assert [_texts(t)[1] for t in trees[:3]] == ["Evergreen stand", "Replanted seedling", "Recovered woodland"]


def test_wildlife_seen_lists_species_by_name(game_env):
    m = game_env.module
    game_env.tick(15)
    game_env.toggle_almanac()
    seen = [name for _i, name in m.species_seen()]
    assert seen
    section = next(v for k, v in _items(game_env).items() if k.startswith("Wildlife seen"))
    shown = [_texts(li)[1] for li in section if _texts(li)[1] != "???"]
    assert shown == seen


def test_rare_wildlife_and_heart_tree_appear_once_found(game_env):
    m = game_env.module
    game_env.tick(3)
    decline_requests(game_env, 5, 3)
    for plot in m.plots:
        plot.ticks_intact = 0
        plot.value = 1.0
    for index in ring_around(m, 14)[:7]:
        make_mature(m, index)
    game_env.tick()
    game_env.toggle_almanac()
    sections = _items(game_env)
    rare = sections["Rare wildlife (1/2)"]
    assert _texts(rare[1]) == ["\U0001F98A", "wary fox"] and _texts(rare[0])[1] == "???"
    hidden = sections["Hidden structures (1/1)"][0]
    assert _texts(hidden)[1] == "Heart Tree"
    assert hidden.getAttribute("aria-label") == "Heart Tree: found"


def test_seasons_survived(game_env):
    m = game_env.module
    m.forest_tick = 85
    game_env.toggle_almanac()
    panel = game_env.elements["almanac-panel"]
    headings = [c.innerText for c in panel.children if c.className == "almanac-heading"]
    assert "Seasons survived: 2" in headings
    chips = panel.children[panel.children.index(next(c for c in panel.children if c.innerText == "Seasons survived: 2")) + 1].children
    assert [_texts(c)[1] for c in chips] == ["Spring", "Summer", "???", "???"]


def test_panel_rebuilds_on_render_and_has_no_stale_children(game_env):
    game_env.toggle_almanac()
    first = len(game_env.elements["almanac-panel"].children)
    game_env.tick(2)
    assert len(game_env.elements["almanac-panel"].children) == first


def test_almanac_is_keyboard_reachable_and_registered_for_escape():
    assert '<button id="almanac-toggle-button"' in HTML
    assert '{ toggle: "almanac-toggle-button", panel: "almanac-panel" }' in HTML


def test_almanac_changes_no_save_state(game_env):
    m = game_env.module
    before = m.get_state()
    game_env.toggle_almanac()
    assert m.get_state() == before
