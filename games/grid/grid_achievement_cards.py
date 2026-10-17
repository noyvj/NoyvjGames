"""Achievement cards in the skyline look (C-31): the building icons, the panel and the stats request.
Part of the split of the old single-file game.py: see "File map" in games/grid/CLAUDE.md.
"""

from js import document

import grid_runstate as runstate
from grid_achievements import (
    ACHIEVEMENTS, _achievement_powerup_ids, achievement_ids_earned, achievements_summary, next_milestone,
)
from grid_skyline import SKYLINE_BUILDINGS


def achievement_building_index(achievement_id):
    """The skyline building an achievement wears: its position in the manifest, wrapped over the 16 shapes."""
    for position, entry in enumerate(ACHIEVEMENTS):
        if entry["id"] == achievement_id:
            return position % len(SKYLINE_BUILDINGS)
    return 0


def achievement_icon_svg(achievement_id, earned):
    _x, _width, height = SKYLINE_BUILDINGS[achievement_building_index(achievement_id)]
    body_h = 10 + round(height * 0.36)  # 20 to 29 tall inside a 32-high icon
    top = 32 - body_h
    state = "earned" if earned else "locked"
    parts = [f'<rect x="4" y="{top}" width="16" height="{body_h}" class="sky-building sky-building--{"lit" if earned else "dark"}" />']
    if earned:
        index = 0
        for row in range(max(1, (body_h - 4) // 8)):
            for col in range(3):
                parts.append(
                    f'<rect x="{6 + col * 5}" y="{top + 3 + row * 8}" width="3" height="4" '
                    f'class="sky-window ach-window" style="animation-delay:{index * 0.12:.2f}s" />'
                )
                index += 1
    label = "Earned" if earned else "Not earned yet"
    return (
        f'<svg viewBox="0 0 24 32" class="achievement-icon achievement-icon--{state}" role="img" '
        f'aria-label="{label}">{"".join(parts)}</svg>'
    )


def on_toggle_achievements(event=None):
    runstate.achievements_open = not runstate.achievements_open
    update_achievements_display()


def update_achievements_display():
    toggle = document.getElementById("achievements-toggle-button")
    panel = document.getElementById("achievements-panel")
    earned_count = len(achievement_ids_earned())
    toggle.innerText = (
        f"Hide Achievements ({earned_count}/{len(ACHIEVEMENTS)})"
        if runstate.achievements_open
        else f"🏆 Achievements ({earned_count}/{len(ACHIEVEMENTS)})"
    )
    panel.hidden = not runstate.achievements_open
    if not runstate.achievements_open:
        return

    panel.innerHTML = ""
    upcoming = next_milestone()
    if upcoming is not None:
        current, target = upcoming["progress"]
        note = document.createElement("p")
        note.className = "achievement-next"
        note.innerText = f"Next milestone: {upcoming['label']} ({current} of {target})"
        panel.appendChild(note)
    flash_ids = set(_achievement_powerup_ids)
    _achievement_powerup_ids.clear()
    for entry in achievements_summary():
        card = document.createElement("div")
        card.className = "achievement-card achievement-card--earned" if entry["earned"] else "achievement-card"
        card.dataset.achievementId = entry["id"]
        flash = entry["earned"] and entry["id"] in flash_ids
        if flash:
            card.className += " achievement-card--powerup" + ("" if runstate.prefs["unlock_flash"] else " achievement-card--still")

        icon = document.createElement("span")
        icon.className = "achievement-card-icon"
        icon.innerHTML = achievement_icon_svg(entry["id"], entry["earned"])
        card.appendChild(icon)

        label = document.createElement("p")
        label.className = "achievement-card-label"
        label.innerText = entry["label"]
        card.appendChild(label)

        if flash:
            fresh = document.createElement("p")
            fresh.className = "achievement-card-fresh"
            fresh.innerText = "Just powered up"
            card.appendChild(fresh)

        description = document.createElement("p")
        description.className = "achievement-card-description"
        description.innerText = entry["description"]
        card.appendChild(description)

        if not entry["earned"] and entry["progress"] is not None:
            current, target = entry["progress"]
            progress = document.createElement("p")
            progress.className = "achievement-card-progress"
            progress.innerText = f"{current} of {target}"
            card.appendChild(progress)

        panel.appendChild(card)

    # A link out to the hub-wide achievements dashboard (root index.html's
    # #account-achievements-dashboard, ACHIEVEMENTS-SYSTEM-DESIGN.md §5),
    # same convention as SOL's reference retrofit. Relative path, no
    # leading "/" (site-level milestone 7's GitHub Pages subpath fix).
    # Rebuilt each open alongside the cards since the panel is cleared
    # first. Note: the hub-side script.js registration that makes Grid's
    # save data actually show up on that dashboard is a root-file change,
    # out of scope for this games/grid/-only dispatch — see CLAUDE.md.
    hub_link = document.createElement("a")
    hub_link.innerText = "View the hub-wide achievements dashboard →"
    hub_link.href = "../../index.html#account-achievements-dashboard"
    hub_link.className = "achievements-hub-link"
    panel.appendChild(hub_link)

    _request_achievement_stats()


def _request_achievement_stats():
    """Z27b: asks the page's optional JS hook (window.applyAchievementStats,
    shared/achievement-stats.js) to fill in each achievement card's own
    "Earned by N% of players" line from the cross-player stats endpoint
    (planning/TODO.md Z1). Absent hook (pytest, or a page without the
    shared script) leaves the cards exactly as rendered above -- same
    fails-soft shape as this file's own C15 window.gridCompare."""
    try:
        from js import window  # noqa: PLC0415 -- Pyodide-only, deliberately lazy
    except ImportError:
        return
    hook = getattr(window, "applyAchievementStats", None)
    if hook is not None:
        hook()
