"""render(): redraws the whole page from the live chain. Calls every panel's own render function."""

import html

from js import document

import loop_runstate as runstate
from loop_achievements import update_achievements_display
from loop_assist import render_assist
from loop_career import founder_rank, founder_text, render_ring_themes, secret_unlocked
from loop_changelog import update_changelog_display
from loop_effects import damage_strain_tier
from loop_ghost_codes import render_ghost
from loop_info_panel import render_info_page
from loop_ledger import render_ledger_and_past
from loop_messages import (
    _request_community_comparison, chain_flow_message, circular_trend_message, cycles_to_close_loop_message,
    real_world_comparison_message, render_scorecard, sector_comparison_message, vignette_message,
)
from loop_narrator import render_narrator
from loop_planner import render_planner
from loop_readouts import (
    audit_lines, combo_text, cost_equation_text, featured_goods_category, insurance_text, mode_status_text,
    near_miss_message, network_map_text, purchase_label, render_pool_donation, rival_bar_widths,
    rival_lines, score_pie_percentages, score_pie_style, streak_progress_text, top_investment_measure,
)
from loop_rules import (
    BUY_MULTIPLES, CIRCULARITY_BONUS_WEIGHT, CIRCULARITY_INVESTMENTS, CULTURE_DEMAND_REDUCTION,
    CULTURE_MAX_LEVEL, GOODS_CATEGORIES, IMPORT_SUPPLY_PER_UNIT, INSURANCE_COST, MAX_COST_MULTIPLIER,
    OVERSEAS_IMPORT_SUPPLY_PER_UNIT, OVERSEAS_TRADE_COST, PRODUCTION_TARGET, REDESIGN_MAX_LEVEL,
    REDESIGN_SUPPLY_BONUS, REGIONAL_IMPORT_SUPPLY_PER_UNIT, REGIONAL_TRADE_COST, RIVAL_NAME,
    SECRET_GOODS_CATEGORY, TRADE_LINK_COST,
)
from loop_runstate import current_goods_label
from loop_savegame import load_note_lines
from loop_sparklines import render_node_sparklines
from loop_summaries import (
    accessible_chain_lines, render_career, render_passport, rewind_text, rewind_token_text,
    rival_status_text, secret_text, shock_banner_text, shock_status_text,
)
from loop_visual_maps import render_visual_views


def render():
    render_info_page()
    update_achievements_display()
    update_changelog_display()

    for count in BUY_MULTIPLES:
        chip = document.getElementById(f"buy-x{count}-button")
        chip.setAttribute("aria-pressed", "true" if runstate.buy_multiple == count else "false")
        if runstate.buy_multiple == count:
            chip.classList.add("selected")
        else:
            chip.classList.remove("selected")

    picker = document.getElementById("goods-category-picker")
    picker.hidden = runstate.chain.total_produced > 0
    for key in GOODS_CATEGORIES:
        button = document.getElementById(f"goods-category-{key}-button")
        if key == runstate.chain.goods_category:
            button.classList.add("selected")
        else:
            button.classList.remove("selected")

    # GH-14: the secret category, hidden until every ordinary category has had a closed cycle.
    secret_button = document.getElementById("goods-category-shipyard-button")
    secret_button.hidden = not secret_unlocked()
    if runstate.chain.goods_category == SECRET_GOODS_CATEGORY:
        secret_button.classList.add("selected")
    else:
        secret_button.classList.remove("selected")
    secret_hint = document.getElementById("secret-category-hint")
    secret_hint.innerText = secret_text()
    secret_hint.hidden = secret_unlocked()

    # H13/H23: the two opt-in modes live in the picker (so they vanish with
    # it after the first cycle); their status line stays visible.
    for which, active in (("challenge", runstate.chain.challenge_mode), ("zero-waste", runstate.chain.zero_waste)):
        mode_button = document.getElementById(f"{which}-mode-button")
        if active:
            mode_button.classList.add("selected")
        else:
            mode_button.classList.remove("selected")
        mode_button.innerText = (
            ("\u2713 " if active else "")
            + ("Circular design challenge" if which == "challenge" else "Zero-waste challenge")
        )
    culture_button = document.getElementById("culture-invest-button")
    if runstate.chain.culture_level >= CULTURE_MAX_LEVEL:
        culture_button.innerText = "Culture campaign (max)"
        culture_button.disabled = True
    else:
        culture_button.innerText = f"Culture campaign ({runstate.chain.culture_cost()})"
        culture_button.disabled = runstate.chain.funds < runstate.chain.culture_cost()
    document.getElementById("culture-count").innerText = str(runstate.chain.culture_level)
    document.getElementById("culture-stats").innerText = (
        f"Each level trims {CULTURE_DEMAND_REDUCTION * 100:.0f}% off the material a cycle needs · "
        f"now {runstate.chain.material_need():.0f} of {PRODUCTION_TARGET:.0f} units"
    )
    render_passport()
    mode_text = mode_status_text()
    mode_el = document.getElementById("mode-status")
    mode_el.innerText = mode_text
    mode_el.hidden = mode_text == ""

    # H4: relabel panel only once the picker itself is gone.
    document.getElementById("relabel-goods-panel").hidden = not picker.hidden
    for key in GOODS_CATEGORIES:
        rb = document.getElementById(f"relabel-{key}-button")
        if key == runstate.chain.goods_category:
            rb.classList.add("selected")
        else:
            rb.classList.remove("selected")
    featured = featured_goods_category()
    document.getElementById("featured-goods-display").innerText = (
        f"Challenge of the week: try a chain of {GOODS_CATEGORIES[featured]['label']} "
        f"{GOODS_CATEGORIES[featured]['icon']}."
    )

    fraction = runstate.chain.circular_fraction_this_cycle()
    flow_el = document.getElementById("chain-flow")
    flow_el.className = "chain-flow chain-flow--closed" if fraction >= 1.0 else "chain-flow"
    extract_stage = document.getElementById("stage-extract")
    extract_stage.className = "chain-stage chain-stage--inactive" if fraction >= 1.0 else "chain-stage"
    document.getElementById("chain-flow-message").innerText = chain_flow_message(fraction, runstate.chain.cycle_number)

    return_flow_row = document.getElementById("return-flow-row")
    return_flow_row.style.opacity = f"{fraction:.2f}"

    import_fraction = min(1.0, runstate.chain.imported_supply() / PRODUCTION_TARGET)
    import_flow_row = document.getElementById("import-flow-row")
    import_flow_row.style.opacity = f"{import_fraction:.2f}"

    vignette_variant = (runstate.chain.cycle_number - 1) if runstate.chain.cycle_number > 0 else 0
    document.getElementById("vignette-display").innerText = vignette_message(
        fraction, variant_seed=vignette_variant + runstate.vignette_session_offset
    )

    document.getElementById("cycle-display").innerText = f"Cycle {runstate.chain.cycle_number}"
    document.getElementById("funds-display").innerText = f"Funds: {runstate.chain.funds:.0f}"
    document.getElementById("extraction-display").innerText = (
        "Loop closed — no new extraction needed" if runstate.chain.is_loop_closed()
        else f"New extraction this cycle: {runstate.chain.new_extraction_needed():.0f} units of raw material for {current_goods_label()}"
    )
    document.getElementById("production-display").innerText = (
        f"Production target: {PRODUCTION_TARGET:.0f} units of {current_goods_label()} per cycle"
    )
    document.getElementById("total-extracted-display").innerText = (
        f"Total raw material extracted (lifetime): {runstate.chain.total_extracted:.0f} units"
    )
    document.getElementById("damage-display").innerText = (
        f"Environmental damage: {runstate.chain.damage_fraction() * 100:.0f}% "
        f"(extraction cost x{runstate.chain.extraction_cost_multiplier():.2f})"
    )
    # H8: a small trend arrow on the per-unit extraction cost; H22: the
    # hard-ceiling multiplier spelled out in the tooltip.
    trend_word = runstate.chain.extraction_cost_trend()
    trend_note = " \u2197 pricier than last cycle" if trend_word == "rising" else ""
    document.getElementById("damage-display").innerText += trend_note
    document.getElementById("damage-display").title = (
        f"Extraction cost has a hard ceiling of x{MAX_COST_MULTIPLIER:.2f} -- it can never rise above that, "
        f"however much damage accumulates. Currently x{runstate.chain.extraction_cost_multiplier():.2f}."
    )
    # V-E-4 (H10): the same ceiling note as visible text, not only a hover tooltip.
    document.getElementById("damage-ceiling-note").innerText = (
        f"Extraction cost has a hard ceiling of x{MAX_COST_MULTIPLIER:.2f}: it can never rise above that, "
        f"however much damage accumulates. Currently x{runstate.chain.extraction_cost_multiplier():.2f}."
    )
    document.getElementById("damage-bar").style.width = f"{runstate.chain.damage_fraction() * 100:.0f}%"
    # H-15: the extraction price as a worked equation (visible text, also the tooltip).
    equation = cost_equation_text()
    equation_el = document.getElementById("cost-equation-display")
    equation_el.innerText = equation
    equation_el.title = equation
    # GH-25: a "so close" note with the cheapest single fix.
    near_text = near_miss_message()
    near_el = document.getElementById("near-miss-display")
    near_el.innerText = near_text
    near_el.hidden = near_text == ""
    # GH-12 / GH-24: the Perfect Cycle combo and the streak insurance.
    document.getElementById("combo-display").innerText = combo_text()
    insurance_button = document.getElementById("insurance-button")
    if runstate.chain.insurance_armed:
        insurance_button.innerText = "Streak insurance: armed"
    elif runstate.chain.insurance_used:
        insurance_button.innerText = "Streak insurance: used"
    else:
        insurance_button.innerText = f"Streak insurance ({INSURANCE_COST})"
    insurance_button.disabled = not runstate.chain.can_buy_insurance()
    document.getElementById("insurance-status").innerText = insurance_text()
    # GH-5 / FY-38: the Rival Corporation race.
    rival_button = document.getElementById("rival-button")
    rival_button.innerText = f"{RIVAL_NAME}: on" if runstate.chain.rival_on else f"{RIVAL_NAME}: off"
    rival_button.setAttribute("aria-pressed", "true" if runstate.chain.rival_on else "false")
    document.getElementById("rival-status").innerText = rival_status_text()
    document.getElementById("rival-lines").innerHTML = "".join(f"<li>{html.escape(line)}</li>" for line in rival_lines())
    document.getElementById("rival-race").hidden = not runstate.chain.rival_on
    you_pct, rival_pct = rival_bar_widths()
    document.getElementById("rival-bar-you").style.width = f"{you_pct}%"
    document.getElementById("rival-bar-rival").style.width = f"{rival_pct}%"
    # GH-3 / FY-37: the market-shock switch and notice.
    shock_button = document.getElementById("market-shocks-button")
    shock_button.innerText = "Market shocks: on" if runstate.chain.market_shocks else "Market shocks: off"
    shock_button.setAttribute("aria-pressed", "true" if runstate.chain.market_shocks else "false")
    document.getElementById("shock-status").innerText = shock_status_text()
    banner_text = shock_banner_text()
    banner = document.getElementById("shock-banner")
    banner.innerText = banner_text
    banner.hidden = banner_text == ""
    # GH-18 / FY-39: the one rewind token.
    document.getElementById("rewind-token-display").innerText = rewind_token_text()
    rewind_button = document.getElementById("rewind-button")
    rewind_button.innerText = "Rewind used" if runstate.chain.rewind_used else "Rewind last cycle"
    rewind_button.disabled = not runstate.chain.can_rewind()
    document.getElementById("rewind-status").innerText = rewind_text()
    # H-4: the same numbers as a plain list (screen readers, and anyone who prefers text).
    document.getElementById("a11y-chain-list").innerHTML = "".join(
        f"<li>{html.escape(line)}</li>" for line in accessible_chain_lines()
    )
    # H-22: a live tab title.
    document.title = f"Loop - C{runstate.chain.cycle_number} - {runstate.chain.circular_fraction_this_cycle() * 100:.0f}% circular"
    render_career()
    render_ledger_and_past()
    render_ring_themes()
    note_lines = load_note_lines()
    document.getElementById("load-note").hidden = not note_lines
    document.getElementById("load-note-list").innerHTML = "".join(f"<li>{html.escape(line)}</li>" for line in note_lines)
    document.getElementById("game").setAttribute("data-damage-tier", str(damage_strain_tier()))
    document.getElementById("rank-badge").innerText = f"\U0001F396\uFE0F {founder_rank()[1]}"
    document.getElementById("rank-detail").innerText = founder_text()

    document.getElementById("circular-fraction-display").innerText = (
        f"Circular this cycle: {runstate.chain.circular_fraction_this_cycle() * 100:.0f}%"
    )
    document.getElementById("lifetime-circular-display").innerText = (
        f"Lifetime circular share: {runstate.chain.lifetime_circular_fraction() * 100:.0f}%"
    )
    document.getElementById("circular-bar").style.width = (
        f"{runstate.chain.circular_fraction_this_cycle() * 100:.0f}%"
    )
    document.getElementById("score-display").innerText = f"Score: {runstate.chain.score():.0f}"
    # H17: a live score breakdown, always visible, instead of the score
    # figure only being explained on click through the info-toggle below.
    bonus_component = runstate.chain.lifetime_circular_fraction() * CIRCULARITY_BONUS_WEIGHT
    combo_part = f" + combo bonus ({runstate.chain.perfect_bonus:.0f})" if runstate.chain.perfect_bonus > 0 else ""
    document.getElementById("score-breakdown-display").innerText = (
        f"Score = funds ({runstate.chain.funds:.0f}) + circular bonus ({bonus_component:.0f}){combo_part} = {runstate.chain.score():.0f}"
    )
    document.getElementById("trend-display").innerText = circular_trend_message(runstate.chain.circular_trend())
    document.getElementById("loop-projection-display").innerText = cycles_to_close_loop_message()
    document.getElementById("real-world-comparison-display").innerText = (
        real_world_comparison_message(runstate.chain.lifetime_circular_fraction())
    )
    document.getElementById("sector-comparison-display").innerText = (
        sector_comparison_message(runstate.chain.lifetime_circular_fraction())
    )
    render_scorecard()
    # H5: live cross-player comparison, distinct from the two static
    # real-world/sector comparisons just above -- see
    # _request_community_comparison()'s own docstring.
    _request_community_comparison()
    document.getElementById("streak-display").innerText = (
        f"Closed-loop streak: {runstate.chain.closed_loop_streak} cycle(s) (best: {runstate.chain.best_closed_loop_streak})"
    )

    # H2 / H24: streak progress, and cycles since last new extraction.
    document.getElementById("streak-progress").innerText = streak_progress_text()
    since = document.getElementById("streak-since-display")
    since.hidden = runstate.chain.circular_fraction_this_cycle() < 0.75
    since.innerText = f"Cycles since last new extraction: {runstate.chain.closed_loop_streak}"
    # H12: score-source pie, H15: audit.
    funds_pct, bonus_pct = score_pie_percentages()
    document.getElementById("score-pie").style.background = score_pie_style()
    document.getElementById("score-pie-legend").innerText = (
        f"Score sources: funds {funds_pct}% (gold), circular bonus {bonus_pct}% (green)"
    )
    document.getElementById("audit-body").innerHTML = "".join(f"<p>{line}</p>" for line in audit_lines())

    top_measure = top_investment_measure()
    for measure, spec in CIRCULARITY_INVESTMENTS.items():
        document.getElementById(f"{measure}-name").innerText = f"{spec['icon']} {spec['label']}"
        document.getElementById(f"{measure}-count").innerText = str(
            runstate.chain.circularity_investment[measure]
        )
        button = document.getElementById(f"{measure}-invest-button")
        button.innerText = purchase_label(measure, spec["label"])
        button.disabled = runstate.chain.funds < spec["cost"]

        # H4 + H15: cost-per-unit-of-supply, and each measure's running
        # supply contribution per cycle, next to its owned count.
        cost_per_unit = spec["cost"] / spec["supply_per_unit"]
        contribution = runstate.chain.measure_supply(measure)
        focus_note = " · focus +25%" if runstate.chain.waste_focus == measure else ""
        if measure == "recycle" and runstate.chain.head_start > 0:
            focus_note += f" · yard scrap line +{runstate.chain.head_start:.0f}"
        if runstate.chain.redesign_level[measure]:
            focus_note += f" · redesign +{round(REDESIGN_SUPPLY_BONUS * runstate.chain.redesign_level[measure] * 100)}%"
        redesign_button = document.getElementById(f"redesign-{measure}-button")
        if runstate.chain.redesign_level[measure] >= REDESIGN_MAX_LEVEL:
            redesign_button.innerText = "Redesigned (max)"
            redesign_button.disabled = True
        elif not runstate.chain.redesign_unlocked():
            redesign_button.innerText = "Redesign (unlocks once the loop closes)"
            redesign_button.disabled = True
        else:
            redesign_button.innerText = f"Redesign ({runstate.chain.redesign_cost(measure)})"
            redesign_button.disabled = runstate.chain.funds < runstate.chain.redesign_cost(measure)
        document.getElementById(f"{measure}-stats").innerText = (
            f"{cost_per_unit:.1f} funds/unit · supplying {contribution:.0f}/cycle{focus_note}"
        )
        focus_button = document.getElementById(f"focus-{measure}-button")
        if runstate.chain.waste_focus == measure:
            focus_button.classList.add("focus-button--on")
        else:
            focus_button.classList.remove("focus-button--on")
        focus_button.innerText = "\u2605 Focused" if runstate.chain.waste_focus == measure else "Focus"

        # H5: highlight the decorative loop-ring nodes proportional to
        # real investment instead of leaving them purely static.
        node = document.getElementById(f"loop-ring-node-{measure}")
        base_class = f"loop-ring-node loop-ring-node--{measure}"
        count = runstate.chain.circularity_investment[measure]
        if count >= 5:
            node.className = f"{base_class} loop-ring-node--charged"
        elif count >= 1:
            node.className = f"{base_class} loop-ring-node--active"
        else:
            node.className = base_class
        # H18: extra glow on the node receiving the most investment.
        if measure == top_measure:
            node.className += " loop-ring-node--top"

    document.getElementById("trade-link-count").innerText = str(runstate.chain.trade_link_investment)
    trade_link_button = document.getElementById("trade-link-invest-button")
    trade_link_button.innerText = purchase_label("trade", "Trade Link")
    trade_link_button.disabled = runstate.chain.funds < TRADE_LINK_COST
    # Onboarding-tooltip coverage (planning/TODO.md, origin A14): the two
    # trade-partner buttons look interchangeable at a glance and the
    # section's own "i" toggle only explains Trade Link generally, never
    # mentioning Regional Partner exists or how the two differ. A returning
    # player who forgot the H8 second-partner mechanic had nothing in the
    # permanent UI to explain the choice. `title` states each one's real
    # cost-per-unit so the two buttons self-explain on hover/long-press.
    trade_link_button.title = (
        f"{TRADE_LINK_COST} funds for {IMPORT_SUPPLY_PER_UNIT:.0f} imported units/cycle "
        f"({TRADE_LINK_COST / IMPORT_SUPPLY_PER_UNIT:.2f} funds/unit)."
    )

    document.getElementById("regional-trade-count").innerText = str(runstate.chain.regional_trade_investment)
    regional_trade_button = document.getElementById("regional-trade-invest-button")
    regional_trade_button.innerText = purchase_label("regional", "Regional Partner")
    regional_trade_button.disabled = runstate.chain.funds < REGIONAL_TRADE_COST
    regional_trade_button.title = (
        f"{REGIONAL_TRADE_COST} funds for {REGIONAL_IMPORT_SUPPLY_PER_UNIT:.0f} imported units/cycle "
        f"({REGIONAL_TRADE_COST / REGIONAL_IMPORT_SUPPLY_PER_UNIT:.2f} funds/unit) — a separate trade "
        f"partner from Trade Link, so both can be invested in at once."
    )

    document.getElementById("overseas-trade-count").innerText = str(runstate.chain.overseas_trade_investment)
    overseas_button = document.getElementById("overseas-trade-invest-button")
    overseas_button.innerText = purchase_label("overseas", "Overseas Consortium")
    overseas_button.disabled = runstate.chain.funds < OVERSEAS_TRADE_COST
    overseas_button.title = (
        f"{OVERSEAS_TRADE_COST} funds for {OVERSEAS_IMPORT_SUPPLY_PER_UNIT:.0f} imported units/cycle "
        f"({OVERSEAS_TRADE_COST / OVERSEAS_IMPORT_SUPPLY_PER_UNIT:.2f} funds/unit) -- the best price per unit "
        f"of the three partners, but a big single purchase."
    )
    # H28: one-time hint the first time the Regional Partner is affordable.
    document.getElementById("regional-hint").hidden = not (
        runstate.chain.funds >= REGIONAL_TRADE_COST and not runstate.regional_hint_seen
    )
    document.getElementById("network-map-display").innerText = network_map_text()
    render_visual_views()
    render_pool_donation()

    document.getElementById("trade-network-display").innerText = (
        f"Importing {runstate.chain.imported_supply():.0f} units/cycle from the trade network; "
        f"exporting {runstate.chain.exportable_surplus():.0f} units/cycle of surplus this cycle."
    )
    render_narrator()  # GH-19
    render_node_sparklines()  # H-26
    render_planner()  # H-3
    render_assist()  # H-8
    render_ghost()  # GH-28 / H-7
