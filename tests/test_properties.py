import math

from hypothesis import given, event
from hypothesis import strategies as st

from pygob.types import GoBool, GoUint, GoInt, GoFloat, GoByteSlice, GoString


def test_bool_false():
    assert GoBool.decode(GoBool.encode(False)) == (False, b'')


def test_bool_true():
    assert GoBool.decode(GoBool.encode(True)) == (True, b'')


@given(st.integers(min_value=0))
def test_uint(n):
    event('%d-bit integer' % n.bit_length())
    assert GoUint.decode(GoUint.encode(n)) == (n, b'')


@given(st.integers(-2**63, 2**63 - 1))
def test_int(n):
    assert GoInt.decode(GoInt.encode(n)) == (n, b'')


@given(st.floats())
def test_float(f):
    result, buf = GoFloat.decode(GoFloat.encode(f))
    assert buf == b''
    if math.isnan(f):
        assert math.isnan(result)
    else:
        assert result == f


@given(st.binary())
def test_byte_slice(buf):
    assert GoByteSlice.decode(GoByteSlice.encode(buf)) == (buf, b'')


@given(st.text())
def test_str(text):
    assert GoString.decode(GoString.encode(text)) == (text.encode('utf-8'),
                                                      b'')
