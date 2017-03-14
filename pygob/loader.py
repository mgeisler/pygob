import struct
import collections

from .types import TypeID


class Loader:
    def __init__(self):
        # Basic types that can be decoded in terms of each other.
        self._types = {
            TypeID.INT: GoInt,
            TypeID.UINT: GoUint,
            TypeID.BOOL: GoBool,
            TypeID.FLOAT: GoFloat,
            TypeID.BYTE_SLICE: GoByteSlice,
            TypeID.STRING: GoString,
            TypeID.COMPLEX: GoComplex,
        }

        # Compound types that depend on the basic types above. We must
        # define these after the above definition since the
        # constructors will lookup the zero values using the above
        # dict.
        self._types[TypeID.COMMON_TYPE] = GoStruct('CommonType', self, [
            ('Name', TypeID.STRING),
            ('Id', TypeID.INT),
        ])
        self._types[TypeID.ARRAY_TYPE] = GoStruct('ArrayType', self, [
            ('CommonType', TypeID.COMMON_TYPE),
            ('Elem', TypeID.INT),
            ('Len', TypeID.INT),
        ])
        self._types[TypeID.SLICE_TYPE] = GoStruct('SliceType', self, [
            ('CommonType', TypeID.COMMON_TYPE),
            ('Elem', TypeID.INT),
        ])
        self._types[TypeID.STRUCT_TYPE] = GoStruct('StructType', self, [
            ('CommonType', TypeID.COMMON_TYPE),
            ('Field', TypeID.INT),
        ])
        self._types[TypeID.FIELD_TYPE] = GoStruct('FieldType', self, [
            ('Name', TypeID.STRING),
            ('Id', TypeID.INT),
        ])
        # TODO: 22 is slice of fieldType.
        self._types[TypeID.MAP_TYPE] = GoStruct('MapType', self, [
            ('CommonType', TypeID.COMMON_TYPE),
            ('Key', TypeID.INT),
            ('Elem', TypeID.INT),
        ])
        self._types[TypeID.WIRE_TYPE] = GoWireType('WireType', self, [
            ('ArrayT', TypeID.ARRAY_TYPE),
            ('SliceT', TypeID.SLICE_TYPE),
            ('StructT', TypeID.STRUCT_TYPE),
            ('MapT', TypeID.MAP_TYPE),
        ])

    def load(self, buf):
        while True:
            length, buf = GoUint.decode(buf)
            typeid, buf = GoInt.decode(buf)
            if typeid > 0:
                break  # Found a value.

            # Decode wire type and register type for later.
            custom_type, buf = self.decode_value(TypeID.WIRE_TYPE, buf)
            self._types[-typeid] = custom_type

        try:
            typeid = TypeID(typeid)
        except ValueError:
            pass  # We only have enum values for the basic types.

        # TODO: why must we skip a zero byte here?
        value, buf = self.decode_value(typeid, buf[1:])
        assert buf == b'', "trailing garbage: %s" % list(buf)
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


class GoWireType(GoStruct):
    def decode(self, buf):
        """Decode data from buf and return a GoType."""
        wire_type, buf = super().decode(buf)
        if wire_type.ArrayT is not None:
            return GoArray(self._loader, wire_type.ArrayT), buf
        else:
            raise NotImplementedError("cannot handle %s" % wire_type)


class GoArray(GoType):
    def __init__(self, loader, array_type):
        self._loader = loader
        self._array_type = array_type

    def decode(self, buf):
        """Decode data from buf and return a tuple.

        Go arrays have a fixed size and cannot be resized. This makes
        them more like Python tuples than Python lists.
        """
        count, buf = GoUint.decode(buf)
        typeid = self._array_type.Elem
        try:
            typeid = TypeID(typeid)
        except ValueError:
            pass

        result = []
        for i in range(count):
            value, buf = self._loader.decode_value(typeid, buf)
            result.append(value)
        return tuple(result), buf
