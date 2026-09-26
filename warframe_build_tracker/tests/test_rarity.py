"""Resource value heuristic: rare / uncommon / common from the location text."""

from .test_tracker import _reset_to_known_state
from .test_refinery import _all_text


def test_many_places_is_common(game_env):
    m = game_env.module
    assert m.resource_rarity(m.RESOURCE_LOCATIONS["Ferrite"]) == "common"
    assert m.resource_rarity(m.RESOURCE_LOCATIONS["Rubedo"]) == "common"


def test_gated_or_single_sources_are_rare(game_env):
    m = game_env.module
    assert m.resource_rarity("Orb Vallis (Venus) -- Heist reward") == "rare"
    assert m.resource_rarity("Plains of Eidolon (Earth) -- bounty reward") == "rare"
    assert m.resource_rarity("Plains of Eidolon (Earth) -- fish part (Norg)") == "rare"
    assert m.resource_rarity("Cambion Drift (Deimos)") == "rare"  # one place


def test_two_to_four_places_is_uncommon(game_env):
    m = game_env.module
    assert m.resource_rarity("Venus, Ceres, and the Kuva Fortress") == "uncommon"


def test_refined_and_blank_are_their_own_kind(game_env):
    m = game_env.module
    assert m.resource_rarity("Refined from Pyrol (see Pyrol's own Wiki page)") == "refined"
    assert m.resource_rarity("") == "refined"


def test_every_tracked_resource_gets_a_kind(game_env):
    m = game_env.module
    kinds = {m.resource_rarity(where) for where in m.RESOURCE_LOCATIONS.values()}
    assert kinds <= {"common", "uncommon", "rare", "refined"}
    assert "rare" in kinds and "common" in kinds


def test_rows_and_badge(game_env):
    m = game_env.module
    _reset_to_known_state(m, parts={"Shwaak Prism": {"owned": 0, "target": 1}})
    _, rows = m.calculate()
    by_name = {r["name"]: r for r in rows}
    assert by_name["Norg Brain"]["rarity"] == "rare"
    assert by_name["Iradite"]["rarity"] in ("rare", "uncommon", "common")
    m.render()
    tbody = game_env.elements["resources-body"]
    norg = next(c for c in tbody.children if c.attributes.get("data-resource") == "Norg Brain")
    assert "rare-flag" in _all_text(norg)
