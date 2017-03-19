import pytest

import pygob


def load_all(data):
    seq = pygob.load_all(bytes(data))
    return list(seq)


@pytest.mark.parametrize(('data', 'expected'), [
    ([3, 4, 0, 2, 3, 4, 0, 4, 3, 4, 0, 6], [1, 2, 3]),
    ([3, 2, 0, 1, 3, 4, 0, 34, 4, 12, 0, 1, 33], [True, 17, b'!'])
])
def test_basic_types(data, expected):
    assert load_all(data) == expected


def test_custom_types():
    data = [
        2, 255, 129, 2, 1, 2, 255, 130, 0, 1, 2, 0, 0, 5, 255, 130, 0, 1, 1, 6,
        255, 130, 0, 2, 1, 0
    ]
    assert load_all(data) == [[True], [True, False]]


def test_iterator():
    data = [3, 4, 0, 2, 3, 4, 0, 4, 3, 4, 0, 6]
    seq = pygob.load_all(bytes(data))
    assert next(seq) == 1
    assert next(seq) == 2
    assert next(seq) == 3
    with pytest.raises(StopIteration):
        next(seq)
