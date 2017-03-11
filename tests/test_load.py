import pytest

import pygob


@pytest.mark.parametrize(('data', 'expected'), [
    ([3, 6, 0, 1], 1),
    ([3, 6, 0, 2], 2),
    ([3, 6, 0, 3], 3),
    ([4, 6, 0, 255, 255], 255),
    ([5, 6, 0, 254, 1, 0], 256),
    ([5, 6, 0, 254, 1, 1], 257),
])
def test_uint(data, expected):
    assert pygob.load(bytes(data)) == expected


@pytest.mark.parametrize(('data', 'expected'), [
    ([3, 4, 0, 5], -3),
    ([3, 4, 0, 3], -2),
    ([3, 4, 0, 1], -1),
    ([3, 4, 0, 0], 0),
    ([3, 4, 0, 2], 1),
    ([3, 4, 0, 4], 2),
    ([3, 4, 0, 6], 3),
    ([5, 4, 0, 254, 1, 255], -256),
    ([5, 4, 0, 254, 1, 253], -255),
    ([5, 4, 0, 254, 1, 254], 255),
    ([5, 4, 0, 254, 2, 0], 256),
])
def test_int(data, expected):
    assert pygob.load(bytes(data)) == expected


@pytest.mark.parametrize(('data', 'expected'), [
    ([3, 2, 0, 1], True),
    ([3, 2, 0, 0], False),
])
def test_bool(data, expected):
    assert pygob.load(bytes(data)) == expected
