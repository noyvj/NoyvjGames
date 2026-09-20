"""J22 -- a small one-shot particle/spark burst on a high-value sale.

Covers: the effect fires on a sale at/above SALE_SPARK_THRESHOLD, does NOT
fire on an ordinary/low-value sale, and cleans itself up (its transient
elements are removed from #sale-spark-container) once its one-shot
lifetime elapses. Same fake-timer "dispatch the action, assert the effect
is present/a timer is scheduled, fire the fake timer, assert it's cleaned
up" shape as tests/test_toast_stale_timer.py's toast test.

The burst deliberately lives in its own #sale-spark-container element, a
sibling of #profit-display-text inside #profit-display -- not a child of
#profit-display-text itself, since render() overwrites that span's
innerText every tick. A real-browser check during this feature's own
live verification caught that ordering bug (appending to the text span
directly meant the very next render() call wiped the sparks out before
they ever painted); these tests exercise the real #sale-spark-container
split so a regression back to the buggy shape would show up here too."""


def test_spark_burst_creates_transient_elements(game_env):
    game_env.module._spark_burst_high_value_sale()
    container = game_env.elements["sale-spark-container"]
    assert len(container.children) == game_env.module.SALE_SPARK_COUNT
    for spark in container.children:
        assert spark.className.startswith("sale-spark")


def test_spark_burst_does_not_disturb_the_profit_text(game_env):
    game_env.elements["profit-display-text"].innerText = "Total profit: 999 credits"
    game_env.module._spark_burst_high_value_sale()
    assert game_env.elements["profit-display-text"].innerText == "Total profit: 999 credits"


def test_spark_burst_elements_are_removed_after_their_lifetime(game_env):
    game_env.module._spark_burst_high_value_sale()
    container = game_env.elements["sale-spark-container"]
    assert len(container.children) == game_env.module.SALE_SPARK_COUNT

    game_env.timers.flush()  # fires the cleanup setTimeout

    assert container.children == []


def test_ordinary_sale_does_not_trigger_the_spark_burst(game_env):
    # Baseline Ore sale: CARGO_CAPACITY (10) x SELL_PRICE["ore"] (8) = 80
    # credits, well under SALE_SPARK_THRESHOLD (200) -- an ordinary early
    # sale, not a high-value one.
    game_env.load()
    game_env.depart("verdant")
    game_env.tick(game_env.module.TRAVEL_TICKS)

    container = game_env.elements["sale-spark-container"]
    assert container.children == []


def test_high_value_sale_triggers_the_spark_burst(game_env):
    game_env.load()
    # Bump this trip's cargo well past what an ordinary Ore run carries,
    # so the completed sale's profit clears SALE_SPARK_THRESHOLD (200):
    # 40 units x SELL_PRICE["ore"] (8) = 320 credits.
    game_env.ship().cargo_qty = 40
    game_env.depart("verdant")
    game_env.tick(game_env.module.TRAVEL_TICKS)

    container = game_env.elements["sale-spark-container"]
    assert len(container.children) == game_env.module.SALE_SPARK_COUNT


def test_high_value_sale_spark_burst_still_cleans_up(game_env):
    game_env.load()
    game_env.ship().cargo_qty = 40
    game_env.depart("verdant")
    game_env.tick(game_env.module.TRAVEL_TICKS)

    container = game_env.elements["sale-spark-container"]
    assert len(container.children) == game_env.module.SALE_SPARK_COUNT

    game_env.timers.flush()

    assert container.children == []


def test_sale_just_under_threshold_does_not_trigger(game_env):
    game_env.load()
    # 24 units x 8 credits = 192, just under SALE_SPARK_THRESHOLD (200).
    game_env.ship().cargo_qty = 24
    game_env.depart("verdant")
    game_env.tick(game_env.module.TRAVEL_TICKS)

    container = game_env.elements["sale-spark-container"]
    assert container.children == []


def test_sale_exactly_at_threshold_triggers(game_env):
    game_env.load()
    # 25 units x 8 credits = 200, exactly SALE_SPARK_THRESHOLD -- the
    # comparison in tick() is >=, so this boundary case should trigger.
    game_env.ship().cargo_qty = 25
    game_env.depart("verdant")
    game_env.tick(game_env.module.TRAVEL_TICKS)

    container = game_env.elements["sale-spark-container"]
    assert len(container.children) == game_env.module.SALE_SPARK_COUNT
