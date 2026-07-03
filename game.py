import math
from js import document, setInterval, setTimeout
from pyodide.ffi import create_proxy

# --- state ---
resource_count = 0.0
generator_count = 0
recycler_count = 0
ecology_health = 100.0
research_progress = 0.0
near_bodies_unlocked = False
current_planet = "Earth"
governor_priority = "balance"  # "growth" | "balance" | "ecology"
governor_budget_pct = 50.0
governor_tick_count = 0

GENERATOR_BASE_COST = 10
GENERATOR_COST_GROWTH = 1.15
GENERATOR_RATE = 1  # iron per second, per generator
TICK_INTERVAL_MS = 100

ECOLOGY_MAX = 100.0
ECOLOGY_DECAY_PER_GENERATOR_PER_SEC = 1.0  # auto-miners pollute as they work
LOW_ECOLOGY_THRESHOLD = 10.0
LOW_ECOLOGY_PENALTY_MULTIPLIER = 0.75

RECYCLER_BASE_COST = 15
RECYCLER_COST_GROWTH = 1.15
RECYCLER_RESTORE_PER_SEC = 2.0  # ecology health restored, per recycler

# Research isn't strictly linear — reaching a distance tier can unlock
# several bodies in parallel rather than one planet at a time.
RESEARCH_FUND_COST = 50  # flat Iron per investment, not a scaling purchase
RESEARCH_TARGET_NEAR_BODIES = 1000
NEAR_BODIES_UNLOCKS = ["Moon", "Mars"]

GOVERNOR_BUDGET_STEP = 10.0
GOVERNOR_BUDGET_MIN = 0.0
GOVERNOR_BUDGET_MAX = 100.0


def generator_cost():
    return math.ceil(GENERATOR_BASE_COST * (GENERATOR_COST_GROWTH ** generator_count))


def recycler_cost():
    return math.ceil(RECYCLER_BASE_COST * (RECYCLER_COST_GROWTH ** recycler_count))


def production_multiplier():
    if ecology_health <= 0:
        return 0.0
    if ecology_health < LOW_ECOLOGY_THRESHOLD:
        return LOW_ECOLOGY_PENALTY_MULTIPLIER
    return 1.0


def clamp(value, low, high):
    return max(low, min(high, value))


def update_display():
    # Repeated fractional += from tick() accumulates float error (e.g. ten
    # 0.1 additions land on 0.9999999999999999, not 1.0), which would make
    # the floored display lag a whole unit behind the real total. A tiny
    # epsilon nudge keeps the display honest without affecting real progress.
    document.getElementById("resource-count").innerText = str(math.floor(resource_count + 1e-9))


def update_generator_display():
    document.getElementById("generator-count").innerText = str(generator_count)
    document.getElementById("generator-rate").innerText = str(generator_count * GENERATOR_RATE)
    document.getElementById("buy-generator-button").innerText = (
        f"Buy Auto-Miner ({generator_cost()} Iron)"
    )


def update_ecology_display():
    document.getElementById("ecology-percent").innerText = f"{round(ecology_health)}%"
    document.getElementById("ecology-bar").style.width = f"{ecology_health}%"
    document.getElementById("recycler-count").innerText = str(recycler_count)
    document.getElementById("recycler-rate").innerText = str(round(recycler_count * RECYCLER_RESTORE_PER_SEC, 2))
    document.getElementById("buy-recycler-button").innerText = (
        f"Build Recycler ({recycler_cost()} Iron)"
    )

    status = document.getElementById("ecology-status")
    if ecology_health <= 0:
        status.innerText = "Production halted — ecological collapse"
    elif ecology_health < LOW_ECOLOGY_THRESHOLD:
        status.innerText = "Output reduced 25% — ecological health critical"
    else:
        status.innerText = ""


def update_research_display():
    progress_pct = (research_progress / RESEARCH_TARGET_NEAR_BODIES) * 100
    document.getElementById("research-bar").style.width = f"{progress_pct}%"

    button = document.getElementById("fund-research-button")
    status = document.getElementById("research-status")

    if near_bodies_unlocked:
        document.getElementById("research-progress").innerText = "Unlocked"
        status.innerText = "Near Bodies unlocked: " + ", ".join(NEAR_BODIES_UNLOCKS)
        button.innerText = "Near Bodies Unlocked"
        button.disabled = True
    else:
        document.getElementById("research-progress").innerText = (
            f"{math.floor(research_progress)} / {RESEARCH_TARGET_NEAR_BODIES}"
        )
        status.innerText = ""
        button.innerText = f"Fund Research ({RESEARCH_FUND_COST} Iron)"
        button.disabled = False


def update_travel_display():
    moon_button = document.getElementById("travel-moon-button")
    mars_button = document.getElementById("travel-mars-button")
    status = document.getElementById("travel-status")

    if near_bodies_unlocked:
        status.innerText = "Choose a destination:"
        for button in (moon_button, mars_button):
            button.hidden = False
            button.disabled = False
    else:
        status.innerText = "Reach the Near Bodies tier to unlock travel."
        for button in (moon_button, mars_button):
            button.hidden = True
            button.disabled = True


def update_governor_display():
    priority_buttons = {
        "growth": document.getElementById("priority-growth-button"),
        "balance": document.getElementById("priority-balance-button"),
        "ecology": document.getElementById("priority-ecology-button"),
    }
    for priority, button in priority_buttons.items():
        if priority == governor_priority:
            button.classList.add("selected")
        else:
            button.classList.remove("selected")

    document.getElementById("governor-budget-value").innerText = str(round(governor_budget_pct))


def update_away_summary():
    document.getElementById("away-planet-name").innerText = current_planet.upper()
    document.getElementById("away-iron").innerText = str(math.floor(resource_count + 1e-9))
    document.getElementById("away-generators").innerText = str(generator_count)
    document.getElementById("away-recyclers").innerText = str(recycler_count)
    document.getElementById("away-ecology").innerText = str(round(ecology_health))


def show_earth_view():
    document.getElementById("earth-view").hidden = False
    document.getElementById("away-view").hidden = True


def show_away_view():
    document.getElementById("earth-view").hidden = True
    document.getElementById("away-view").hidden = False
    update_away_summary()


def press_feedback(button):
    button.classList.add("pressed")

    def _clear(*args):
        button.classList.remove("pressed")
    setTimeout(create_proxy(_clear), 120)


def on_click(event):
    global resource_count
    # Manual mining always works, even during an ecological collapse that
    # halts automated production — otherwise a player who lets health hit
    # 0% with no Iron banked could get permanently stuck with no way to earn
    # the Iron needed to build a recovery Recycler. Per the project's "no
    # dead-end/unwinnable states" balance rule, there must always be a lever.
    resource_count += 1
    update_display()
    press_feedback(document.getElementById("click-button"))


def on_buy_generator(event):
    global resource_count, generator_count
    button = document.getElementById("buy-generator-button")
    cost = generator_cost()
    if resource_count >= cost:
        resource_count -= cost
        generator_count += 1
        update_display()
        update_generator_display()
    press_feedback(button)


def on_buy_recycler(event):
    global resource_count, recycler_count
    button = document.getElementById("buy-recycler-button")
    cost = recycler_cost()
    if resource_count >= cost:
        resource_count -= cost
        recycler_count += 1
        update_display()
        update_ecology_display()
    press_feedback(button)


def on_fund_research(event):
    global resource_count, research_progress, near_bodies_unlocked
    button = document.getElementById("fund-research-button")
    if not near_bodies_unlocked and resource_count >= RESEARCH_FUND_COST:
        resource_count -= RESEARCH_FUND_COST
        research_progress = min(research_progress + RESEARCH_FUND_COST, RESEARCH_TARGET_NEAR_BODIES)
        if research_progress >= RESEARCH_TARGET_NEAR_BODIES:
            near_bodies_unlocked = True
            update_travel_display()
        update_display()
        update_research_display()
    press_feedback(button)


def on_priority_growth(event):
    global governor_priority
    governor_priority = "growth"
    update_governor_display()
    press_feedback(document.getElementById("priority-growth-button"))


def on_priority_balance(event):
    global governor_priority
    governor_priority = "balance"
    update_governor_display()
    press_feedback(document.getElementById("priority-balance-button"))


def on_priority_ecology(event):
    global governor_priority
    governor_priority = "ecology"
    update_governor_display()
    press_feedback(document.getElementById("priority-ecology-button"))


def on_budget_increase(event):
    global governor_budget_pct
    governor_budget_pct = clamp(governor_budget_pct + GOVERNOR_BUDGET_STEP, GOVERNOR_BUDGET_MIN, GOVERNOR_BUDGET_MAX)
    update_governor_display()
    press_feedback(document.getElementById("budget-increase-button"))


def on_budget_decrease(event):
    global governor_budget_pct
    governor_budget_pct = clamp(governor_budget_pct - GOVERNOR_BUDGET_STEP, GOVERNOR_BUDGET_MIN, GOVERNOR_BUDGET_MAX)
    update_governor_display()
    press_feedback(document.getElementById("budget-decrease-button"))


def on_travel_moon(event):
    global current_planet
    if near_bodies_unlocked:
        current_planet = "Moon"
        show_away_view()
    press_feedback(document.getElementById("travel-moon-button"))


def on_travel_mars(event):
    global current_planet
    if near_bodies_unlocked:
        current_planet = "Mars"
        show_away_view()
    press_feedback(document.getElementById("travel-mars-button"))


def on_return_to_earth(event):
    global current_planet
    current_planet = "Earth"
    show_earth_view()
    press_feedback(document.getElementById("return-to-earth-button"))


def governor_step():
    # Only makes autonomous purchases while the player is away from Earth —
    # on Earth the player is back in direct manual control.
    global resource_count, generator_count, recycler_count, governor_tick_count
    if current_planet == "Earth":
        return

    governor_tick_count += 1
    if governor_priority == "growth":
        buy_generator_turn = True
    elif governor_priority == "ecology":
        buy_generator_turn = False
    else:  # "balance" — alternate turns between the two buildings
        buy_generator_turn = governor_tick_count % 2 == 0

    budget = resource_count * (governor_budget_pct / 100)

    if buy_generator_turn:
        cost = generator_cost()
        if cost <= budget:
            resource_count -= cost
            generator_count += 1
            update_generator_display()
    else:
        cost = recycler_cost()
        if cost <= budget:
            resource_count -= cost
            recycler_count += 1
            update_ecology_display()


def tick(*args):
    global resource_count, ecology_health

    if generator_count > 0:
        multiplier = production_multiplier()
        if multiplier > 0:
            resource_count += generator_count * GENERATOR_RATE * (TICK_INTERVAL_MS / 1000) * multiplier

    decay = generator_count * ECOLOGY_DECAY_PER_GENERATOR_PER_SEC * (TICK_INTERVAL_MS / 1000)
    restore = recycler_count * RECYCLER_RESTORE_PER_SEC * (TICK_INTERVAL_MS / 1000)
    ecology_health = clamp(ecology_health - decay + restore, 0.0, ECOLOGY_MAX)

    governor_step()

    update_display()
    update_ecology_display()
    if current_planet != "Earth":
        update_away_summary()


def setup():
    click_button = document.getElementById("click-button")
    click_button.innerText = "Mine Iron"
    click_button.disabled = False
    click_button.addEventListener("click", create_proxy(on_click))

    buy_button = document.getElementById("buy-generator-button")
    buy_button.disabled = False
    buy_button.addEventListener("click", create_proxy(on_buy_generator))

    recycler_button = document.getElementById("buy-recycler-button")
    recycler_button.disabled = False
    recycler_button.addEventListener("click", create_proxy(on_buy_recycler))

    research_button = document.getElementById("fund-research-button")
    research_button.disabled = False
    research_button.addEventListener("click", create_proxy(on_fund_research))

    document.getElementById("priority-growth-button").addEventListener(
        "click", create_proxy(on_priority_growth)
    )
    document.getElementById("priority-balance-button").addEventListener(
        "click", create_proxy(on_priority_balance)
    )
    document.getElementById("priority-ecology-button").addEventListener(
        "click", create_proxy(on_priority_ecology)
    )
    document.getElementById("budget-increase-button").addEventListener(
        "click", create_proxy(on_budget_increase)
    )
    document.getElementById("budget-decrease-button").addEventListener(
        "click", create_proxy(on_budget_decrease)
    )

    moon_button = document.getElementById("travel-moon-button")
    moon_button.addEventListener("click", create_proxy(on_travel_moon))

    mars_button = document.getElementById("travel-mars-button")
    mars_button.addEventListener("click", create_proxy(on_travel_mars))

    document.getElementById("return-to-earth-button").addEventListener(
        "click", create_proxy(on_return_to_earth)
    )

    show_earth_view()
    update_display()
    update_generator_display()
    update_ecology_display()
    update_research_display()
    update_governor_display()
    update_travel_display()
    setInterval(create_proxy(tick), TICK_INTERVAL_MS)


setup()
