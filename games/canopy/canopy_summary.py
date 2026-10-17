"""The session summary pieces: breakdown text, counterfactual, history sparkline, share text, replay and the forest card."""

from js import document

import canopy_runstate as runstate
from canopy_effects import current_legacy_multiplier, vault_growth_multiplier
from canopy_helpers import (
    SPARKLINE_HEIGHT, SPARKLINE_INCOME_COLOR, SPARKLINE_STANDING_COLOR, SPARKLINE_WIDTH, _announce, _el,
    _sparkline_points, _svg_text, session_tag_text,
)
from canopy_rules import (
    BARE, BASE_ACCRUAL, PRESERVED, RECOVERED, REPLANTING, SEASONS, SEASON_CYCLE_TICKS, growth_per_tick,
    season_multiplier_for,
)
from canopy_valuation import (
    BADGE_ICON, active_plot_count, playstyle_badge, standing_forest_value, state_breakdown,
    total_biodiversity,
)
from canopy_weather import weather_multiplier_at
from canopy_worldvars import _value_history


def state_breakdown_text():
    counts = state_breakdown()
    return (
        f"{counts[PRESERVED]} preserved · {counts[BARE]} bare · "
        f"{counts[REPLANTING]} replanting · {counts[RECOVERED]} recovered"
    )


# ===========================================================================
# Session Summary (B1/B6/B18/B20, planning/TODO.md "Per-game: Canopy") --
# a player-triggered panel recapping the session, same "optional, never
# forced" pattern as the info page. Reuses stats that already exist
# elsewhere in this module; the two pieces genuinely new here are B20's
# counterfactual (below) and B6's sparkline (render_session_summary()).
# ===========================================================================


def _ideal_accrual_for_ticks(n):
    """The standing value a single never-cleared, never-degraded plot
    would have accrued after `n` ticks of full PRESERVED accrual -- i.e.
    Plot.accrue_tick()'s own formula (BASE_ACCRUAL * productivity_
    multiplier() * (1 + ticks_intact * GROWTH_PER_TICK)) summed over
    ticks_intact = 1..n with productivity_multiplier() fixed at 1.0 (no
    clearing, so no soil degradation).

    B17/B15 made the per-tick multiplier season-dependent (and scaled by a
    session-constant legacy bonus), so the old closed-form arithmetic-sum
    no longer matches accrue_tick()'s real formula -- season changes every
    SEASON_CYCLE_TICKS, breaking the single-ratio assumption a closed form
    needs. Looping is the only way to stay exact; tick() runs at ~1/sec so
    even an hours-long session is a few thousand cheap iterations, run only
    on demand when the summary panel is opened (never per-tick).

    `start_tick` is forest_tick's value when *this session* began -- tick()
    increments forest_tick before calling accrue_tick(), so the season in
    effect during the plot's j-th accrual this session was whatever
    current_season() would have returned at absolute forest_tick
    (start_tick + j)."""
    if n <= 0:
        return 0.0
    start_tick = runstate.forest_tick - runstate._session_ticks
    total = 0.0
    for j in range(1, n + 1):
        season = SEASONS[((start_tick + j) // SEASON_CYCLE_TICKS) % len(SEASONS)]
        total += (
            BASE_ACCRUAL * (1 + j * growth_per_tick()) * season_multiplier_for(season)
            * weather_multiplier_at(start_tick + j)  # GB-23: the same rain/drought the real forest saw
        )
    return total * current_legacy_multiplier() * vault_growth_multiplier()


def counterfactual_standing_value():
    """B20's hope-angle counterfactual: what the *entire* grid would be
    worth right now if every plot had been left standing, untouched, since
    the session began -- the "if you'd done this from day one" comparison
    CLAUDE.md's hope-angle section calls for. Deliberately every plot at
    the *current* grid size, not a fixed 36 -- a "large" (B13) session
    compares against its own larger ideal."""
    return active_plot_count() * _ideal_accrual_for_ticks(runstate._session_ticks)


def counterfactual_message():
    """The closing line itself. Framed as a comparison, not a scolding —
    matching this game's no-dead-end-states, no-wrong-answer philosophy;
    clearing plots for quick income is a legitimate playstyle, not a
    mistake to be corrected."""
    if runstate._session_ticks == 0:
        return "Not enough time has passed yet to compare against a fully-preserved forest."
    ideal = counterfactual_standing_value()
    if ideal <= 0:
        return ""
    actual = standing_forest_value()
    if actual >= ideal - 0.5:
        return (
            f"Your standing forest ({actual:.1f}) is right around what every plot would be "
            f"worth if none had ever been cleared ({ideal:.1f}) — patience paid off in full."
        )
    pct = max(0, round((actual / ideal) * 100))
    return (
        f"If every plot had been left standing since the start, this forest would be worth "
        f"about {ideal:.1f} by now — your actual standing value ({actual:.1f}) is {pct}% of that, "
        f"a {100 - pct}% difference."
    )


def session_history_svg():
    """Returns "" (rather than an empty/degenerate <svg>) once there's no
    history yet -- render_session_summary() shows a plain "not enough
    data yet" message instead in that case."""
    if not _value_history:
        return ""
    incomes = [point[0] for point in _value_history]
    standing_values = [point[1] for point in _value_history]
    max_value = max(max(incomes, default=0.0), max(standing_values, default=0.0))
    income_points = _sparkline_points(incomes, max_value)
    standing_points = _sparkline_points(standing_values, max_value)
    return (
        f'<svg viewBox="0 0 {SPARKLINE_WIDTH} {SPARKLINE_HEIGHT}" '
        f'class="session-sparkline" role="img" '
        f'aria-label="Income and standing value over the session">'
        f'<polyline points="{standing_points}" fill="none" '
        f'stroke="{SPARKLINE_STANDING_COLOR}" stroke-width="2" />'
        f'<polyline points="{income_points}" fill="none" '
        f'stroke="{SPARKLINE_INCOME_COLOR}" stroke-width="2" />'
        f"</svg>"
    )


# B18: a short, plain-text shareable summary -- deliberately NOT a
# decodable save code (that's the separate shared/save-widget.js system);
# this is just bragging-rights text a player can paste somewhere, same
# spirit as SOL's A8 "shareable my solar system end-state summary card".
def share_snippet():
    standing_value = standing_forest_value()
    counts = state_breakdown()
    standing_plots = counts[PRESERVED] + counts[RECOVERED]
    return (
        f"\U0001F332 Canopy — {runstate.forest_name or 'my forest'} so far: {standing_value:.1f} standing value, "
        f"{runstate.total_income:.1f} harvested, {total_biodiversity():.1f} biodiversity. "
        f"{standing_plots}/{active_plot_count()} plots still standing."
        + (f" ({session_tag_text()})" if session_tag_text() else "")
    )


# B-4 (2026-10-09): a shareable forest image: the final grid, the playstyle badge and three headline numbers on one
# 1200 x 630 card, drawn in code as an SVG (no generated images). Each plot shows a letter as well as a colour, so the
# card still reads in greyscale or for colour-blind viewers.
CARD_STATE_STYLE = {
    PRESERVED: ("#2f7d4a", "P"),
    BARE: ("#8a6a3f", "B"),
    REPLANTING: ("#9bc873", "R"),
    RECOVERED: ("#3d9aa6", "C"),
}


# B-3 (2026-10-09): replay scrubber. A snapshot of every plot's state is kept every few ticks; when the list is full it
# is thinned to every other frame and the spacing doubles, so a session of any length fits in REPLAY_MAX_FRAMES.
# Ephemeral like the other session histories: never saved, restarted on a new session.
REPLAY_START_EVERY = 5
REPLAY_MAX_FRAMES = 120
_replay_frames = []  # (tick, "PBRC..." one letter per plot)
_replay_state = {"every": REPLAY_START_EVERY}


def _plot_letters():
    return "".join(CARD_STATE_STYLE.get(p.state, ("", "?"))[1] for p in runstate.plots)


def _record_replay_frame():
    if _replay_frames and runstate.forest_tick % _replay_state["every"] != 0:
        return
    if _replay_frames and _replay_frames[-1][0] == runstate.forest_tick:
        return
    _replay_frames.append((runstate.forest_tick, _plot_letters()))
    if len(_replay_frames) > REPLAY_MAX_FRAMES:
        _replay_frames[:] = _replay_frames[::2] if len(_replay_frames) % 2 == 0 else _replay_frames[::2] + [_replay_frames[-1]]
        _replay_state["every"] *= 2


def replay_frames():
    """Recorded frames plus the live forest as the final frame."""
    frames = list(_replay_frames)
    if not frames or frames[-1][0] != runstate.forest_tick:
        frames.append((runstate.forest_tick, _plot_letters()))
    return frames


def replay_grid_svg(letters):
    """One frame as a small SVG: each plot is its state colour and also its letter, so it reads without colour."""
    if len(letters) != runstate.GRID_ROWS * runstate.GRID_COLS:
        return ""
    cell = 28
    colour_for_letter = {letter: colour for colour, letter in CARD_STATE_STYLE.values()}
    parts = [f'<svg viewBox="0 0 {runstate.GRID_COLS * cell} {runstate.GRID_ROWS * cell}" class="replay-svg" role="img" '
             f'aria-label="Forest at one moment of the session: {letters.count("P")} preserved, {letters.count("B")} bare, '
             f'{letters.count("R")} replanting, {letters.count("C")} recovered">']
    for i, letter in enumerate(letters):
        row, col = divmod(i, runstate.GRID_COLS)
        colour = colour_for_letter.get(letter, "#555555")
        x, y = col * cell, row * cell
        parts.append(f'<rect x="{x + 1}" y="{y + 1}" width="{cell - 2}" height="{cell - 2}" rx="4" fill="{colour}"/>')
        parts.append(f'<text x="{x + cell / 2}" y="{y + cell / 2 + 4}" font-size="12" text-anchor="middle" fill="#ffffff" font-family="sans-serif" font-weight="700">{letter}</text>')
    parts.append("</svg>")
    return "".join(parts)


def render_replay():
    slider, grid, label = _el("replay-slider"), _el("replay-grid"), _el("replay-label")
    if grid is None:
        return
    frames = replay_frames()
    if slider is not None:
        slider.min = "0"
        slider.max = str(len(frames) - 1)
        try:
            chosen = int(getattr(slider, "value", "") or len(frames) - 1)
        except (TypeError, ValueError):
            chosen = len(frames) - 1
        chosen = max(0, min(len(frames) - 1, chosen))
        slider.value = str(chosen)
    else:
        chosen = len(frames) - 1
    tick, letters = frames[chosen]
    grid.innerHTML = replay_grid_svg(letters)
    if label is not None:
        label.innerText = (f"Moment {chosen + 1} of {len(frames)}: tick {tick}, "
                           f"{letters.count('P') + letters.count('C')} plots standing, {letters.count('B')} bare. "
                           "P preserved, B bare, R replanting, C recovered.")


def on_replay_scrub(event=None):
    render_replay()


def forest_card_svg():
    """The card as an SVG string. Pure: reads the live session and returns text."""
    width, height = 1200, 630
    cell = min(int(560 / runstate.GRID_ROWS), int(560 / runstate.GRID_COLS), 90)
    grid_w, grid_h = cell * runstate.GRID_COLS, cell * runstate.GRID_ROWS
    left, top = 40 + (560 - grid_w) // 2, 35 + (560 - grid_h) // 2
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-label="Canopy forest card">',
        f'<rect width="{width}" height="{height}" fill="#14221a"/>',
        f'<rect x="{left - 6}" y="{top - 6}" width="{grid_w + 12}" height="{grid_h + 12}" rx="10" fill="#0d1511"/>',
    ]
    for plot in runstate.plots:
        row, col = divmod(plot.index, runstate.GRID_COLS)
        colour, letter = CARD_STATE_STYLE.get(plot.state, ("#555555", "?"))
        x, y = left + col * cell, top + row * cell
        parts.append(f'<rect x="{x + 2}" y="{y + 2}" width="{cell - 4}" height="{cell - 4}" rx="6" fill="{colour}"/>')
        parts.append(
            f'<text x="{x + cell / 2}" y="{y + cell / 2 + cell * 0.14}" font-size="{int(cell * 0.4)}" font-family="sans-serif" '
            f'font-weight="700" text-anchor="middle" fill="#ffffff">{letter}</text>'
        )
    fields = copy_result_fields()
    badge = playstyle_badge()
    title = runstate.forest_name or "My forest"
    right = 660
    parts += [
        f'<text x="{right}" y="110" font-size="30" font-family="sans-serif" fill="#9bc873">Canopy</text>',
        f'<text x="{right}" y="170" font-size="52" font-family="sans-serif" font-weight="700" fill="#ffffff">{_svg_text(title[:28])}</text>',
        f'<text x="{right}" y="225" font-size="32" font-family="sans-serif" fill="#e9d8a6">{BADGE_ICON[badge]} {_svg_text(badge)}</text>',
        f'<text x="{right}" y="330" font-size="64" font-family="sans-serif" font-weight="700" fill="#ffffff">{fields["score"]:.1f}</text>',
        f'<text x="{right}" y="368" font-size="26" font-family="sans-serif" fill="#cfd8d2">{_svg_text(fields["unit"])}</text>',
    ]
    for n, stat in enumerate(fields["stats"]):
        parts.append(
            f'<text x="{right}" y="{440 + n * 48}" font-size="32" font-family="sans-serif" fill="#ffffff">{_svg_text(stat)}</text>'
        )
    parts += [
        f'<text x="{right}" y="590" font-size="22" font-family="sans-serif" fill="#8fa397">P preserved, B bare, R replanting, C recovered</text>',
        "</svg>",
    ]
    return "".join(parts)


def _download_text_file(filename, text, mime):
    """Hands text to the browser as a file download (a no-op outside the browser)."""
    try:
        from js import Blob, URL  # noqa: PLC0415 -- Pyodide-only, deliberately lazy
    except ImportError:
        return False
    blob = Blob.new([text], {"type": mime})
    url = URL.createObjectURL(blob)
    link = document.createElement("a")
    link.href = url
    link.download = filename
    link.click()
    URL.revokeObjectURL(url)
    return True


def on_download_forest_card(event=None):
    ok = _download_text_file("canopy-forest-card.svg", forest_card_svg(), "image/svg+xml")
    _announce("Forest card downloaded" if ok else "Forest card could not be downloaded here")


def copy_result_fields():
    """Z-20: the fields shared/copy-result.js turns into one pasteable line,
    e.g. "Canopy, 41.2 standing value, 12.5 harvested, ...". Read by the
    page's own inline script through pyodide.globals when the shared Copy
    result button is pressed, so it always matches the session right now."""
    counts = state_breakdown()
    standing_plots = counts[PRESERVED] + counts[RECOVERED]
    return {
        "game": "Canopy",
        "score": round(standing_forest_value(), 1),
        "unit": "standing forest value",
        "stats": [
            f"{runstate.total_income:.1f} harvested",
            f"{total_biodiversity():.1f} biodiversity",
            f"{standing_plots}/{active_plot_count()} plots standing",
        ],
    }
