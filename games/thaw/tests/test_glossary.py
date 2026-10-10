"""G-28: glossary pop-ups on key terms and the full list."""

import re
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent


def test_strip_has_the_four_key_terms_with_popups(game_env):
    html = game_env.elements["glossary-strip-terms"].innerHTML
    for term in ("Melt threshold", "Feedback dampening", "Acceleration factor", "Monitoring &amp; Response"):
        assert term in html
    assert html.count('role="tooltip"') == 4
    assert html.count("aria-describedby") == 4


def test_every_button_points_at_its_popup(game_env):
    html = game_env.elements["glossary-strip-terms"].innerHTML
    for described in re.findall(r'aria-describedby="([^"]+)"', html):
        assert f'id="{described}"' in html


def test_full_list_has_every_term_and_definition(game_env):
    m = game_env.module
    html = game_env.elements["glossary-list"].innerHTML
    assert len(m.GLOSSARY) >= 8
    for key, term, _text in m.GLOSSARY:
        assert m._escape(term) in html
        assert m._escape(m.glossary_definition(key)) in html


def test_definitions_follow_the_temperature_unit(game_env):
    m = game_env.module
    assert "+10°" in m.glossary_definition("melt")
    m.set_temp_unit("f")
    assert "+18°F" in m.glossary_definition("melt")
    m.render()
    assert "+18°F" in game_env.elements["glossary-strip-terms"].innerHTML


def test_definitions_match_the_game_numbers(game_env):
    m = game_env.module
    assert f"({m.DAMPENING_PER_MONITOR_UNIT * 100:.0f}%)" in m.glossary_definition("monitoring")
    assert f"({m.DAMPENING_PER_PRESERVE_UNIT * 100:.0f}%)" in m.glossary_definition("preservation")
    assert f"{m.CRITICAL_ACCELERATION_FACTOR:.0f}x" in m.glossary_definition("critical")
    assert f"{m.RESTORATION_STREAK_ROUNDS}" in m.glossary_definition("restoration").replace("three", "3")


def test_definitions_never_claim_a_real_world_figure(game_env):
    for _key, _term, text in game_env.module.GLOSSARY:
        assert "Gt" not in text and "gigatonne" not in text.lower()


def test_how_to_play_walkthroughs_carry_the_same_wording(game_env):
    """The first four definitions are repeated word for word in both walkthroughs (Classic in
    index.html, Desktop in pc.js), so How to Play matches the pop-ups."""
    m = game_env.module
    texts = {
        "index.html": (HERE / "index.html").read_text(encoding="utf-8"),
        "pc.js": (HERE / "pc.js").read_text(encoding="utf-8"),
    }
    for name, text in texts.items():
        assert 'title: "Key terms"' in text, name
        for key, term, _t in m.GLOSSARY:
            if key in m.STRIP_TERMS:
                assert f"{term}: {m.glossary_definition(key)[0].lower()}{m.glossary_definition(key)[1:]}" in text or (
                    f"{term}: {m.glossary_definition(key)}" in text
                ), (name, term)
