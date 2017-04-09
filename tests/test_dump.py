import pytest

import pygob


@pytest.mark.parametrize(('value', 'encoded'), [
    (False, [3, 2, 0, 0]),
    (True, [3, 2, 0, 1]),
])
def test_bool(value, encoded):
    assert pygob.dump(value) == bytes(encoded)


@pytest.mark.parametrize(('value', 'encoded'), [
    (-2, [3, 4, 0, 3]),
    (-1, [3, 4, 0, 1]),
    (0, [3, 4, 0, 0]),
    (1, [3, 4, 0, 2]),
    (2, [3, 4, 0, 4]),
    (-256, [5, 4, 0, 254, 1, 255]),
    (-255, [5, 4, 0, 254, 1, 253]),
    (255, [5, 4, 0, 254, 1, 254]),
    (256, [5, 4, 0, 254, 2, 0]),
])
def test_int(value, encoded):
    assert pygob.dump(value) == bytes(encoded)


@pytest.mark.parametrize(('value', 'encoded'), [
    (0.0, [3, 8, 0, 0]),
    (1.0, [5, 8, 0, 254, 240, 63]),
    (-2.0, [4, 8, 0, 255, 192]),
    (3.141592, [11, 8, 0, 248, 122, 0, 139, 252, 250, 33, 9, 64]),
    (float('-inf'), [5, 8, 0, 254, 240, 255]),
    (float('+inf'), [5, 8, 0, 254, 240, 127]),
    (float('nan'), [5, 8, 0, 254, 248, 127]),
])
def test_float(value, encoded):
    assert pygob.dump(value) == bytes(encoded)
