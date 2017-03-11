import struct

from .types import TypeID


class Loader:
    def __init__(self):
        self._decoders = {
            TypeID.INT: self.decode_int,
            TypeID.UINT: self.decode_uint,
            TypeID.BOOL: self.decode_bool,
            TypeID.FLOAT: self.decode_float,
            TypeID.BYTE_SLICE: self.decode_byte_slice,
            TypeID.STRING: self.decode_string,
            TypeID.COMPLEX: self.decode_complex,
        }

    def load(self, buf):
        length, buf = self.decode_uint(buf)
        assert len(buf) == length

        typeid, buf = self.decode_int(buf)
        if typeid < 0:
            raise NotImplementedError("cannot decode non-standard type ID %d" %
                                      -typeid)
        typeid = TypeID(typeid)
        # TODO: why must we skip a zero byte here?
        value, buf = self.decode_value(typeid, buf[1:])
        return value

    def decode_bool(self, buf):
        n, buf = self.decode_uint(buf)
        return n == 1, buf

    def decode_uint(self, buf):
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

    def decode_int(self, buf):
        uint, buf = self.decode_uint(buf)
        if uint & 1:
            uint = ~uint
        return uint >> 1, buf

    def decode_float(self, buf):
        n, buf = self.decode_uint(buf)
        rev = bytes(reversed(struct.pack('L', n)))
        (f, ) = struct.unpack('d', rev)
        return f, buf

    def decode_byte_slice(self, buf):
        count, buf = self.decode_uint(buf)
        return bytearray(buf[:count]), buf[count:]

    def decode_string(self, buf):
        count, buf = self.decode_uint(buf)
        # TODO: Go strings do not guarantee any particular encoding.
        # Add support for trying to decode the bytes using, say,
        # UTF-8, so we can return a real Python string.
        return buf[:count], buf[count:]

    def decode_complex(self, buf):
        re, buf = self.decode_float(buf)
        im, buf = self.decode_float(buf)
        return complex(re, im), buf

    def decode_value(self, typeid, buf):
        decoder = self._decoders.get(typeid)
        if decoder is None:
            raise NotImplementedError("cannot decode %s" % typeid)
        return decoder(buf)
