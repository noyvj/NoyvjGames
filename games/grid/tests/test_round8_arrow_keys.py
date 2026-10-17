"""Round-8 pass: arrow keys on the plant rows (C-5)."""
from pathlib import Path

from .test_confirm_dialog import _install_fake_confirm_dialog
from .pagefiles import page_text

GAME_DIR = Path(__file__).resolve().parent.parent


class _Target:
    def __init__(self, id_="", tag="BUTTON"):
        self.id = id_
        self.tagName = tag


class _Key:
    def __init__(self, key, target=None, repeat=False, ctrl=False, alt=False, meta=False):
        self.key = key
        self.target = target or _Target("coal-build-button")
        self.repeat = repeat
        self.ctrlKey = ctrl
        self.altKey = alt
        self.metaKey = meta
        self.prevented = False

    def preventDefault(self):
        self.prevented = True


def _press(env, plant, key, **kw):
    event = _Key(key, **kw)
    env.elements[f"{plant}-row"].dispatch("keydown", event)
    return event


def test_every_plant_row_listens_for_keys(game_env):
    for plant in game_env.module.PLANT_TYPES:
        assert game_env.elements[f"{plant}-row"]._listeners.get("keydown")


def test_right_arrow_builds_one_exactly_like_the_button(game_env):
    funds = game_env.state.funds
    cost = game_env.state.plant_cost("coal")
    event = _press(game_env, "coal", "ArrowRight")
    assert event.prevented is True
    assert game_env.state.plant_counts["coal"] == 1 and game_env.state.funds == funds - cost
    _press(game_env, "coal", "ArrowRight")
    assert game_env.state.plant_counts["coal"] == 2


def test_left_arrow_retires_one_with_the_same_refund(game_env):
    game_env.build("coal")
    game_env.build("coal")
    funds = game_env.state.funds
    _press(game_env, "coal", "ArrowLeft")
    assert game_env.state.plant_counts["coal"] == 1 and game_env.state.funds > funds


def test_retiring_the_last_unit_by_key_still_asks_first(game_env):
    game_env.build("coal")
    window = _install_fake_confirm_dialog()
    _press(game_env, "coal", "ArrowLeft")
    assert game_env.state.plant_counts["coal"] == 1
    assert window.ConfirmDialog.calls[-1]["id"] == "grid-retire-last-coal"
    window.ConfirmDialog.confirm()
    assert game_env.state.plant_counts["coal"] == 0


def test_refusals_are_spoken_not_silent(game_env):
    game_env.state.funds = 0
    _press(game_env, "coal", "ArrowRight")
    assert game_env.state.plant_counts["coal"] == 0
    assert "Cannot build Coal" in game_env.elements["sr-announcer"].innerText
    _press(game_env, "gas", "ArrowLeft")
    assert "none are standing" in game_env.elements["sr-announcer"].innerText


def test_a_held_key_does_not_repeat_the_action(game_env):
    _press(game_env, "coal", "ArrowRight", repeat=True)
    assert game_env.state.plant_counts["coal"] == 0
    _press(game_env, "coal", "ArrowRight")
    _press(game_env, "coal", "ArrowRight", repeat=True)
    assert game_env.state.plant_counts["coal"] == 1


def test_modifier_keys_and_selects_are_left_alone(game_env):
    for kw in ({"ctrl": True}, {"alt": True}, {"meta": True}):
        event = _press(game_env, "coal", "ArrowRight", **kw)
        assert event.prevented is False
    event = _press(game_env, "coal", "ArrowRight", target=_Target("coal-maintenance-schedule-select", "SELECT"))
    assert event.prevented is False
    assert game_env.state.plant_counts["coal"] == 0


def test_other_keys_are_ignored(game_env):
    for key in ("Enter", " ", "a", "Tab", "Home"):
        event = _press(game_env, "coal", key)
        assert event.prevented is False
    assert game_env.state.plant_counts["coal"] == 0


def test_up_and_down_move_focus_keeping_the_kind_of_control(game_env):
    focused = []
    for plant in game_env.module.PLANT_TYPES:
        for kind in ("build", "retire", "maintain"):
            el = game_env.elements[f"{plant}-{kind}-button"]
            el.focus = (lambda name: lambda: focused.append(name))(f"{plant}-{kind}")
    _press(game_env, "gas", "ArrowDown", target=_Target("gas-retire-button"))
    assert focused == ["nuclear-retire"]
    _press(game_env, "gas", "ArrowUp", target=_Target("gas-maintain-button"))
    assert focused[-1] == "coal-maintain"
    _press(game_env, "coal", "ArrowUp")           # top row: stays where it is
    assert focused[-1] == "coal-build"
    _press(game_env, "battery", "ArrowDown")      # bottom row: stays
    assert focused[-1] == "battery-build"
    assert game_env.state.plant_counts["gas"] == 0  # moving never builds


def test_command_table(game_env):
    cmd = game_env.module.plant_key_command
    assert cmd("ArrowRight", "solar") == ("build", "solar")
    assert cmd("ArrowLeft", "solar") == ("retire", "solar")
    assert cmd("ArrowDown", "solar") == ("move", "wind")
    assert cmd("ArrowUp", "coal") == ("move", "coal")
    assert cmd("ArrowDown", "battery") == ("move", "battery")
    assert cmd("ArrowRight", "solar", tag="select") is None
    assert cmd("ArrowRight", "solar", ctrl=True) is None
    assert cmd("x", "solar") is None


def test_the_keys_are_explained_on_screen_and_in_the_shortcut_help():
    for page in ("index.html", "pc.html"):
        html = page_text(page)
        assert "Right arrow (focus on a plant) — build one" in html
    assert 'id="plant-keys-hint"' in page_text("index.html")
    assert "Retire / build (focus a plant)" in (GAME_DIR / "pc-config.json").read_text()
