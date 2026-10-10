"""Round-7 pass: the sticky key-stats bar shows round and capacity too (C-20)."""
import re
from pathlib import Path

GAME_DIR = Path(__file__).resolve().parent.parent


def _hud_fields(page):
    html = (GAME_DIR / page).read_text(encoding="utf-8")
    block = html.split("MobileHud.init([", 1)[1].split("]);", 1)[0]
    return re.findall(r'selector: "([^"]+)", label: "([^"]+)"', block), html


def test_hud_lists_round_funds_demand_capacity_and_emissions():
    for page in ("index.html", "pc.html"):
        fields, _ = _hud_fields(page)
        assert [label for _, label in fields] == ["Round", "Funds", "Demand", "Capacity", "Emissions"], page


def test_every_hud_source_exists_on_both_pages(game_env):
    for page in ("index.html", "pc.html"):
        fields, html = _hud_fields(page)
        for selector, _ in fields:
            assert f'id="{selector[1:]}"' in html, (page, selector)
            assert selector[1:] in game_env.elements  # and game.py writes it every render


def test_hud_sources_carry_the_live_text(game_env):
    game_env.module.render()
    assert game_env.elements["round-display"].innerText.startswith("Round ")
    assert game_env.elements["capacity-display"].innerText.startswith("Capacity: ")
