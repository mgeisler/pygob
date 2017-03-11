import math

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


@pytest.mark.parametrize(('data', 'expected'), [
    ([3, 8, 0, 0], 0),
    ([5, 8, 0, 254, 240, 63], 1),
    ([4, 8, 0, 255, 192], -2),
    ([11, 8, 0, 248, 122, 0, 139, 252, 250, 33, 9, 64], 3.141592),
    ([5, 8, 0, 254, 240, 255], -math.inf),
    ([5, 8, 0, 254, 240, 127], +math.inf),
])
def test_float(data, expected):
    assert pygob.load(bytes(data)) == expected


def test_float_nan():
    data = [11, 8, 0, 248, 1, 0, 0, 0, 0, 0, 248, 127]
    result = pygob.load(bytes(data))
    assert math.isnan(result)


@pytest.mark.parametrize(('data', 'expected'), [
    ([3, 10, 0, 0], b''),
    ([4, 10, 0, 1, 97], b'a'),
    ([5, 10, 0, 2, 97, 98], b'ab'),
    ([6, 10, 0, 3, 97, 98, 99], b'abc'),
])
def test_byte_slice(data, expected):
    result = pygob.load(bytes(data))
    assert type(result) == bytearray
    assert result == expected


@pytest.mark.parametrize(('data', 'expected'), [
    ([3, 12, 0, 0], b''),
    ([4, 12, 0, 1, 97], b'a'),
    ([5, 12, 0, 2, 97, 98], b'ab'),
    ([6, 12, 0, 3, 97, 98, 99], b'abc'),
])
def test_string(data, expected):
    result = pygob.load(bytes(data))
    assert type(result) == bytes
    assert result == expected
