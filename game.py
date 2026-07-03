import math
from js import document, setInterval, setTimeout
from pyodide.ffi import create_proxy

# --- state ---
resource_count = 0.0
generator_count = 0

GENERATOR_BASE_COST = 10
GENERATOR_COST_GROWTH = 1.15
GENERATOR_RATE = 1  # iron per second, per generator
TICK_INTERVAL_MS = 100


def generator_cost():
    return math.ceil(GENERATOR_BASE_COST * (GENERATOR_COST_GROWTH ** generator_count))


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


def press_feedback(button):
    button.classList.add("pressed")

    def _clear(*args):
        button.classList.remove("pressed")
    setTimeout(create_proxy(_clear), 120)


def on_click(event):
    global resource_count
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


def tick(*args):
    global resource_count
    if generator_count > 0:
        resource_count += generator_count * GENERATOR_RATE * (TICK_INTERVAL_MS / 1000)
        update_display()


def setup():
    click_button = document.getElementById("click-button")
    click_button.innerText = "Mine Iron"
    click_button.disabled = False
    click_button.addEventListener("click", create_proxy(on_click))

    buy_button = document.getElementById("buy-generator-button")
    buy_button.disabled = False
    buy_button.addEventListener("click", create_proxy(on_buy_generator))

    update_display()
    update_generator_display()
    setInterval(create_proxy(tick), TICK_INTERVAL_MS)


setup()
