"""H11: opt-in donation of surplus supply to the shared regional recycling pool."""

import sys
import types


class _FakePool:
    def __init__(self):
        self.adds = []

    def add(self, game, pool, amount):
        self.adds.append((game, pool, amount))


def _install():
    pool = _FakePool()
    sys.modules["js"].window = types.SimpleNamespace(NoyvjPool=pool)
    return pool


def _make_surplus(m):
    """Supply beyond the production target so there is something to donate."""
    m.chain.exportable_surplus = lambda: 12.0


def test_off_by_default_and_surplus_is_sold(game_env):
    m = game_env.module
    assert m.chain.donate_surplus is False
    _make_surplus(m)
    m.chain.advance_cycle()
    assert m.chain.lifetime_pool_donated == 0 and m.chain.last_donation == 0
    assert m.chain.lifetime_export_revenue == 12.0 * m.EXPORT_PRICE_PER_UNIT


def test_donating_forgoes_the_sale_and_counts_the_units(game_env):
    m = game_env.module
    _make_surplus(m)
    m.chain.donate_surplus = True
    m.chain.advance_cycle()
    assert m.chain.lifetime_export_revenue == 0.0
    assert m.chain.last_donation == 12.0 and m.chain.lifetime_pool_donated == 12.0
    m.chain.advance_cycle()
    assert m.chain.lifetime_pool_donated == 24.0


def test_no_surplus_means_no_donation_even_when_on(game_env):
    m = game_env.module
    m.chain.exportable_surplus = lambda: 0.0
    m.chain.donate_surplus = True
    m.chain.advance_cycle()
    assert m.chain.last_donation == 0 and m.chain.lifetime_pool_donated == 0


def test_button_toggles_and_shows_the_trade_off(game_env):
    m = game_env.module
    m.render()
    assert "off" in game_env.elements["pool-donate-button"].innerText
    assert "sold outward" in game_env.elements["pool-donate-status"].innerText
    game_env.elements["pool-donate-button"].dispatch("click", None)
    assert m.chain.donate_surplus is True
    assert game_env.elements["pool-donate-button"].innerText == "Surplus donation: on"
    assert "regional pool" in game_env.elements["pool-donate-status"].innerText


def test_a_cycle_reports_its_donation_to_the_shared_pool_client(game_env):
    m = game_env.module
    pool = _install()
    _make_surplus(m)
    m.chain.donate_surplus = True
    m.on_advance_cycle()
    assert pool.adds == [("loop", "recovered_units", 12.0)]
    m.chain.donate_surplus = False
    m.on_advance_cycle()
    assert len(pool.adds) == 1


def test_no_pool_script_is_harmless(game_env):
    m = game_env.module
    _make_surplus(m)
    m.chain.donate_surplus = True
    m.on_advance_cycle()
    assert m.chain.lifetime_pool_donated == 12.0


def test_save_only_when_used_and_validated_on_load(game_env):
    m = game_env.module
    state = m.get_state()
    assert "donate_surplus" not in state and "lifetime_pool_donated" not in state
    m.chain.donate_surplus = True
    m.chain.lifetime_pool_donated = 30.0
    saved = m.get_state()
    assert saved["donate_surplus"] is True and saved["lifetime_pool_donated"] == 30.0
    m.chain.donate_surplus = False
    m.chain.lifetime_pool_donated = 0.0
    m.load_state(saved)
    assert m.chain.donate_surplus is True and m.chain.lifetime_pool_donated == 30.0
    for bad in (True, -5, "x", float("nan"), 1e30, None):
        m.load_state({**saved, "lifetime_pool_donated": bad})
        assert m.chain.lifetime_pool_donated == 0.0
    m.load_state({**saved, "donate_surplus": "yes"})
    assert m.chain.donate_surplus is False


def test_page_includes_the_pool_script_and_display():
    import pathlib
    html = (pathlib.Path(__file__).resolve().parent.parent / "index.html").read_text()
    assert 'shared/community-pool.js" data-game-id="loop" data-pool="recovered_units"' in html
    assert 'id="pool-display"' in html
