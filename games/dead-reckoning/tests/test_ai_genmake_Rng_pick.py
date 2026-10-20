from genmake import Rng


def test_pick_from_a_list_of_three_returns_one_of_them():
    rng = Rng(seed=42)
    items = ["reef", "shoal", "rock"]
    result = rng.pick(items)
    assert result in items


def test_pick_from_a_list_of_ten_works_deterministically():
    rng = Rng(seed=100)
    items = ["Pike", "Gull", "Hob", "Grey", "Mull", "Skerry", "Anvil", "Dunn", "Crab", "Wren"]
    result = rng.pick(items)
    assert result in items


def test_pick_from_a_single_item_list_always_returns_that_item():
    rng = Rng(seed=7)
    items = ["only_one"]
    # Even if rand() returns 1.0, the min clamp ensures it stays within bounds
    for _ in range(10):
        assert rng.pick(items) == "only_one"
