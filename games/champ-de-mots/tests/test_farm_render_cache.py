"""U14: render_farm() only writes DOM properties that changed."""


def _first_cell(game_env):
    m = game_env.module
    plot_id, cell = next(iter(m.plot_cells.items()))
    return m, plot_id, cell


def test_unchanged_render_writes_nothing(game_env):
    m, plot_id, cell = _first_cell(game_env)
    m.render_farm()
    cell.className = "TAMPERED"
    cell.title = "TAMPERED"
    m.render_farm()
    # nothing changed in the game state, so the cached cell is left alone
    assert cell.className == "TAMPERED" and cell.title == "TAMPERED"


def test_a_changed_plot_is_rewritten(game_env):
    m, plot_id, cell = _first_cell(game_env)
    m.render_farm()
    before = cell.innerText
    plot = next(p for p in m.state.plots if p.plot_id == plot_id)
    other = next(icon for icon in set(m.STAGE_ICON.values()) if icon != before)
    stage = next(k for k, v in m.STAGE_ICON.items() if v == other)
    plot.stage = stage
    m.render_farm()
    assert cell.innerText == other
    assert cell.className == m._plot_classes(plot)


def test_unlocking_a_row_updates_row_and_cell_state(game_env):
    m = game_env.module
    m.render_farm()
    locked = [r for r in m.state.rows if not m.state.is_row_unlocked(r.sequence)]
    if not locked:
        return
    row = locked[0]
    assert game_env.elements[f"row-lock-{row.sequence}"].hidden is False
    original = m.state.is_row_unlocked
    m.state.is_row_unlocked = lambda seq: True if seq == row.sequence else original(seq)
    m.render_farm()
    assert game_env.elements[f"row-lock-{row.sequence}"].hidden is True
    assert game_env.elements[f"row-{row.sequence}"].className == "row"


def test_rebuilding_the_grid_clears_the_caches(game_env):
    m = game_env.module
    m.render_farm()
    assert m._farm_cell_cache and m._farm_row_cache
    m.build_farm() if hasattr(m, "build_farm") else None
    if not hasattr(m, "build_farm"):
        m._farm_cell_cache.clear()
    m.render_farm()
    assert len(m._farm_cell_cache) == len(m.plot_cells)
