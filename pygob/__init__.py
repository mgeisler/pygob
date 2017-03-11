import enum
import struct


class TypeID(enum.Enum):
    BOOL = 1
    INT = 2
    UINT = 3
    FLOAT = 4
    BYTE_SLICE = 5
    STRING = 6
    COMPLEX = 7
    INTERFACE = 8
    # gap for reserved ids.
    WIRE_TYPE = 16
    ARRAY_TYPE = 17
    COMMON_TYPE = 18
    SLICE_TYPE = 19
    STRUCT_TYPE = 20
    FIELD_TYPE = 21
    # 22 is slice of fieldType.
    MAP_TYPE = 23


def decode_bool(buf):
    n, buf = decode_uint(buf)
    return n == 1, buf


def decode_uint(buf):
    (length, ) = struct.unpack('b', buf[:1])
    if length >= 0:  # small uint in a single byte
        return length, buf[1:]

    # larger uint split over multiple bytes
    length = -length
    n = 0
    for b in buf[1:length]:
        n = (n + b) << 8
    n += buf[length]
    return n, buf[length + 1:]


def decode_int(buf):
    uint, buf = decode_uint(buf)
    if uint & 1:
        return ~(uint >> 1), buf
    else:
        return (uint >> 1), buf


def decode_float(buf):
    n, buf = decode_uint(buf)
    rev = bytes(reversed(struct.pack('L', n)))
    (f, ) = struct.unpack('d', rev)
    return f, buf


def decode_byte_slice(buf):
    count, buf = decode_uint(buf)
    return bytearray(buf[:count]), buf[count:]


def decode_string(buf):
    count, buf = decode_uint(buf)
    # TODO: Go strings do not guarantee any particular encoding. Add
    # support for trying to decode the bytes using, say, UTF-8, so we
    # can return a real Python string.
    return buf[:count], buf[count:]


def decode_value(typeid, buf):
    if typeid == TypeID.INT:
        return decode_int(buf)
    if typeid == TypeID.UINT:
        return decode_uint(buf)
    if typeid == TypeID.BOOL:
        return decode_bool(buf)
    if typeid == TypeID.FLOAT:
        return decode_float(buf)
    if typeid == TypeID.BYTE_SLICE:
        return decode_byte_slice(buf)
    if typeid == TypeID.STRING:
        return decode_string(buf)
    raise NotImplementedError("cannot decode %s" % typeid)


def load(buf):
    """Load and decode a bytes object."""
    length, buf = decode_uint(buf)
    assert len(buf) == length

    typeid, buf = decode_int(buf)
    if typeid < 0:
        raise NotImplementedError("cannot decode non-standard type ID %d" %
                                  -typeid)
    typeid = TypeID(typeid)
    # TODO: why must we skip a zero byte here?
    value, buf = decode_value(typeid, buf[1:])
    return value
