from herd_model import FarmState


def test_allocation_poultry_default():
    f = FarmState()
    assert f.allocation_poultry == 0.0


def test_allocation_poultry_updates_on_slider_input(game_env):
    slider = game_env.elements["allocation-slider"]
    slider.value = "50"

    class FakeEvent:
        target = type('obj', (), {'value': "50"})()
    slider.dispatch("input", FakeEvent())
    assert game_env.farm.allocation_poultry == 0.5


def test_allocation_bar_hidden_when_poultry_locked(game_env):
    alloc_el = game_env.elements["allocation-control"]
    assert alloc_el.hidden is True


def test_allocation_bar_visible_when_poultry_unlocked(game_env):
    game_env.farm.certified = True
    game_env.module.render()
    alloc_el = game_env.elements["allocation-control"]
    assert alloc_el.hidden is False


def test_allocation_survives_save_load(game_env):
    game_env.farm.allocation_poultry = 0.75
    state = game_env.module.get_state()
    assert state.get("allocation_poultry") == 0.75

    game_env.farm.allocation_poultry = 0.0
    game_env.module.load_state({"allocation_poultry": 0.75})
    assert game_env.farm.allocation_poultry == 0.75
