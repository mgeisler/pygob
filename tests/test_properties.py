from hypothesis import given
from hypothesis import strategies as st

from pygob.types import GoUint, GoInt


@given(st.integers(0, 2**64 - 1))
def test_uint(n):
    assert GoUint.decode(GoUint.encode(n)) == (n, b'')


@given(st.integers(-2**63, 2**63 - 1))
def test_int(n):
    assert GoInt.decode(GoInt.encode(n)) == (n, b'')
