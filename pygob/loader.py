import struct

from .types import TypeID


class Loader:
    def __init__(self):
        self._decoders = {
            TypeID.INT: GoInt.decode,
            TypeID.UINT: GoUint.decode,
            TypeID.BOOL: GoBool.decode,
            TypeID.FLOAT: GoFloat.decode,
            TypeID.BYTE_SLICE: GoByteSlice.decode,
            TypeID.STRING: GoString.decode,
            TypeID.COMPLEX: GoComplex.decode,
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
        decoder = self._decoders.get(typeid)
        if decoder is None:
            raise NotImplementedError("cannot decode %s" % typeid)
        return decoder(buf)


class GoType:
    """Represents a Go type.

    Go types know how to decode a gob stream to their corresponding
    Python type.
    """
    pass


class GoBool(GoType):
    @staticmethod
    def decode(buf):
        n, buf = GoUint.decode(buf)
        return n == 1, buf


class GoUint(GoType):
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
    @staticmethod
    def decode(buf):
        uint, buf = GoUint.decode(buf)
        if uint & 1:
            uint = ~uint
        return uint >> 1, buf


class GoFloat(GoType):
    @staticmethod
    def decode(buf):
        n, buf = GoUint.decode(buf)
        rev = bytes(reversed(struct.pack('L', n)))
        (f, ) = struct.unpack('d', rev)
        return f, buf


class GoByteSlice(GoType):
    @staticmethod
    def decode(buf):
        count, buf = GoUint.decode(buf)
        return bytearray(buf[:count]), buf[count:]


class GoString(GoType):
    @staticmethod
    def decode(buf):
        count, buf = GoUint.decode(buf)
        # TODO: Go strings do not guarantee any particular encoding.
        # Add support for trying to decode the bytes using, say,
        # UTF-8, so we can return a real Python string.
        return buf[:count], buf[count:]


class GoComplex(GoType):
    @staticmethod
    def decode(buf):
        re, buf = GoFloat.decode(buf)
        im, buf = GoFloat.decode(buf)
        return complex(re, im), buf
