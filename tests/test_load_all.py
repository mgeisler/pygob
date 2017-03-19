import collections

import pytest

import pygob


def load_all(data):
    seq = pygob.load_all(bytes(data))
    return list(seq)


@pytest.mark.parametrize(('data', 'expected'), [
    ([3, 4, 0, 2, 3, 4, 0, 4, 3, 4, 0, 6], [1, 2, 3]),
    ([3, 2, 0, 1, 3, 4, 0, 34, 4, 12, 0, 1, 33], [True, 17, b'!']),
])
def test_basic_types(data, expected):
    assert load_all(data) == expected


def test_custom_type():
    data = [
        31, 255, 131, 3, 1, 1, 5, 80, 111, 105, 110, 116, 1, 255, 132, 0, 1, 2,
        1, 1, 88, 1, 4, 0, 1, 1, 89, 1, 4, 0, 0, 0, 3, 255, 132, 0, 7, 255,
        132, 1, 6, 1, 8, 0
    ]
    Point = collections.namedtuple('Point', ['X', 'Y'])
    assert load_all(data) == [Point(0, 0), Point(3, 4)]


def test_iterator():
    data = [3, 4, 0, 2, 3, 4, 0, 4, 3, 4, 0, 6]
    seq = pygob.load_all(bytes(data))
    assert next(seq) == 1
    assert next(seq) == 2
    assert next(seq) == 3
    with pytest.raises(StopIteration):
        next(seq)
