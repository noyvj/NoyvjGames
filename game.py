import math
from js import document, setInterval, setTimeout
from pyodide.ffi import create_proxy

# --- state ---
resource_count = 0.0
generator_count = 0
recycler_count = 0
ecology_health = 100.0

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


def tick(*args):
    global resource_count, ecology_health

    if generator_count > 0:
        multiplier = production_multiplier()
        if multiplier > 0:
            resource_count += generator_count * GENERATOR_RATE * (TICK_INTERVAL_MS / 1000) * multiplier

    decay = generator_count * ECOLOGY_DECAY_PER_GENERATOR_PER_SEC * (TICK_INTERVAL_MS / 1000)
    restore = recycler_count * RECYCLER_RESTORE_PER_SEC * (TICK_INTERVAL_MS / 1000)
    ecology_health = clamp(ecology_health - decay + restore, 0.0, ECOLOGY_MAX)

    update_display()
    update_ecology_display()


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

    update_display()
    update_generator_display()
    update_ecology_display()
    setInterval(create_proxy(tick), TICK_INTERVAL_MS)


setup()
