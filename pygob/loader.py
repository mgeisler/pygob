import struct
import collections

from .types import TypeID


class Loader:
    def __init__(self):
        self._types = {
            TypeID.INT: GoInt,
            TypeID.UINT: GoUint,
            TypeID.BOOL: GoBool,
            TypeID.FLOAT: GoFloat,
            TypeID.BYTE_SLICE: GoByteSlice,
            TypeID.STRING: GoString,
            TypeID.COMPLEX: GoComplex,
        }

    def load(self, buf):
        length, buf = GoUint.decode(buf)
        assert len(buf) == length

        typeid, buf = GoInt.decode(buf)
        if typeid < 0:
            raise NotImplementedError("cannot decode non-standard type ID %d" %
                                      -typeid)
        typeid = TypeID(typeid)
        # TODO: why must we skip a zero byte here?
        value, buf = self.decode_value(typeid, buf[1:])
        return value

    def decode_value(self, typeid, buf):
        go_type = self._types.get(typeid)
        if go_type is None:
            raise NotImplementedError("cannot decode %s" % typeid)
        return go_type.decode(buf)


class classproperty(object):
    def __init__(self, fget):
        self.fget = fget

    def __get__(self, owner_self, owner_cls):
        return self.fget(owner_cls)


class GoType:
    """Represents a Go type.

    Go types know how to decode a gob stream to their corresponding
    Python type.
    """
    pass


class GoBool(GoType):
    zero = False

    @staticmethod
    def decode(buf):
        n, buf = GoUint.decode(buf)
        return n == 1, buf


class GoUint(GoType):
    zero = 0

    @staticmethod
    def decode(buf):
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


class GoInt(GoType):
    zero = 0

    @staticmethod
    def decode(buf):
        uint, buf = GoUint.decode(buf)
        if uint & 1:
            uint = ~uint
        return uint >> 1, buf


class GoFloat(GoType):
    zero = 0.0

    @staticmethod
    def decode(buf):
        n, buf = GoUint.decode(buf)
        rev = bytes(reversed(struct.pack('L', n)))
        (f, ) = struct.unpack('d', rev)
        return f, buf


class GoByteSlice(GoType):
    @classproperty
    def zero(cls):
        return bytearray()

    @staticmethod
    def decode(buf):
        count, buf = GoUint.decode(buf)
        return bytearray(buf[:count]), buf[count:]


class GoString(GoType):
    zero = b''

    @staticmethod
    def decode(buf):
        count, buf = GoUint.decode(buf)
        # TODO: Go strings do not guarantee any particular encoding.
        # Add support for trying to decode the bytes using, say,
        # UTF-8, so we can return a real Python string.
        return buf[:count], buf[count:]


class GoComplex(GoType):
    zero = 0 + 0j

    @staticmethod
    def decode(buf):
        re, buf = GoFloat.decode(buf)
        im, buf = GoFloat.decode(buf)
        return complex(re, im), buf


class GoStruct(GoType):
    def __init__(self, name, loader, fields):
        self._name = name
        self._loader = loader
        self._fields = fields

        self._class = collections.namedtuple(name, [n for (n, t) in fields])
        self.zero = self._class._make(
            [loader._types[t].zero for (n, t) in fields])

    def decode(self, buf):
        """Decode data from buf and return a namedtuple."""
        values = {}
        field_id = -1
        while True:
            delta, buf = GoUint.decode(buf)
            if delta == 0:
                break
            field_id += delta
            name, field = self._fields[field_id]
            value, buf = self._loader.decode_value(field, buf)
            values[name] = value
        return self.zero._replace(**values), buf
