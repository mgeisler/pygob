import pytest

import pygob


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
