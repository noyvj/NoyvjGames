"""K5 (planning/TODO.md): the council-minutes policy log (minutes.py)."""

import minutes
import sim


def test_record_adds_a_worded_entry_stamped_with_era_and_season():
    ui = {}
    assert minutes.record(ui, "research", "Fire-Keeping", "tribal", 3)
    entry = minutes.entries(ui)[0]
    assert entry["season"] == 3 and entry["era"] == "tribal" and entry["kind"] == "research"
    assert "Fire-Keeping" in entry["text"] and entry["text"].startswith("Motion carried")


def test_log_is_capped_keeping_the_newest():
    ui = {}
    for i in range(minutes.MAX_ENTRIES + 15):
        minutes.record(ui, "build", f"Shelter {i}", "tribal", 1)
    entries = minutes.entries(ui)
    assert len(entries) == minutes.MAX_ENTRIES
    assert "Shelter 14" not in entries[0]["text"] and "Shelter 15" in entries[0]["text"]
    assert f"Shelter {minutes.MAX_ENTRIES + 14}" in entries[-1]["text"]


def test_malformed_requests_are_refused():
    ui = {}
    assert not minutes.record(ui, "nonsense", "x", "tribal", 1)
    assert not minutes.record(ui, "build", "  ", "tribal", 1)
    assert not minutes.record(ui, "build", "x", "not_an_era", 1)
    assert not minutes.record(ui, "build", "x", "tribal", 0)
    assert not minutes.record(ui, "build", "x", "tribal", True)
    assert ui == {}


def test_clean_drops_junk_from_a_hand_edited_save():
    raw = [
        {"kind": "build", "era": "tribal", "season": 2, "text": "ok"},
        {"kind": "bad", "era": "tribal", "season": 2, "text": "x"},
        {"kind": "build", "era": "nowhere", "season": 2, "text": "x"},
        {"kind": "build", "era": "tribal", "season": "2", "text": "x"},
        {"kind": "build", "era": "tribal", "season": 2, "text": ""},
        "not a dict",
        None,
    ]
    assert minutes.clean(raw) == [{"kind": "build", "era": "tribal", "season": 2, "text": "ok"}]
    assert minutes.clean("junk") == [] and minutes.clean(None) == []


def test_text_is_length_capped():
    ui = {"policy_log": [{"kind": "build", "era": "tribal", "season": 1, "text": "x" * 999}]}
    assert len(minutes.entries(ui)[0]["text"]) == minutes.TEXT_MAX


# --- game.py wiring ----------------------------------------------------


def test_researching_and_building_are_minuted_and_shown(game_env):
    m = game_env.module
    m.state.resources["materials"] = 999.0
    m.state.resources["knowledge"] = 999.0
    game_env.elements["minutes-toggle-button"].dispatch("click", None)
    before = len(minutes.entries(m.campaign.ui))
    m._make_build_handler("shelter")()
    node_id = next(n.node_id for n in m.tree.nodes.values() if m.tree.is_available(n.node_id))
    m._make_research_handler(node_id)()
    entries = minutes.entries(m.campaign.ui)
    assert len(entries) == before + 2
    assert "Shelter" in entries[-2]["text"] or "shelter" in entries[-2]["text"].lower()
    assert m.tree.nodes[node_id].name in entries[-1]["text"]
    rows = " ".join(c.innerText for c in game_env.elements["minutes-list"].children)
    assert m.tree.nodes[node_id].name in rows


def test_a_refused_build_is_not_minuted(game_env):
    m = game_env.module
    m.state.resources["materials"] = 0.0
    before = len(minutes.entries(m.campaign.ui))
    m._make_build_handler("shelter")()
    assert len(minutes.entries(m.campaign.ui)) == before


def test_minutes_panel_toggles_and_round_trips_through_a_save(game_env):
    m = game_env.module
    panel = game_env.elements["minutes-panel"]
    game_env.elements["minutes-toggle-button"].dispatch("click", None)
    assert panel.hidden is False
    game_env.elements["minutes-toggle-button"].dispatch("click", None)
    assert panel.hidden is True
    m.state.resources["materials"] = 999.0
    m._make_build_handler("shelter")()
    saved = m.get_state()
    assert m.load_state(saved) is True
    assert any("Motion carried" in e["text"] for e in minutes.entries(m.campaign.ui))


def test_era_labels_used_by_minutes_exist():
    assert all(era in sim.ERA_LABEL for era in sim.ERA_ORDER)
