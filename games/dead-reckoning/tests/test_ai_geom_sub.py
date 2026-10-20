from geom import sub


def test_subtracts_two_vectors_normally():
    assert sub((5, 3), (2, 1)) == (3, 2)


def test_subtracts_with_negative_coordinates():
    assert sub((0, 0), (-4, -6)) == (4, 6)


def test_subtracting_a_point_from_itself_yields_zero():
    assert sub((1.5, 2.5), (1.5, 2.5)) == (0.0, 0.0)
