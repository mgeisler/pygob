import struct
import collections

from .types import TypeID


class Loader:
    def __init__(self):
        # Compound types that depend on the basic types above.
        common_type = GoStruct('CommonType', self, [
            ('Name', GoString),
            ('Id', GoInt),
        ])
        array_type = GoStruct('ArrayType', self, [
            ('CommonType', common_type),
            ('Elem', GoInt),
            ('Len', GoInt),
        ])
        slice_type = GoStruct('SliceType', self, [
            ('CommonType', common_type),
            ('Elem', GoInt),
        ])
        struct_type = GoStruct('StructType', self, [
            ('CommonType', common_type),
            ('Field', GoInt),
        ])
        field_type = GoStruct('FieldType', self, [
            ('Name', GoString),
            ('Id', GoInt),
        ])
        # TODO: 22 is slice of fieldType.
        map_type = GoStruct('MapType', self, [
            ('CommonType', common_type),
            ('Key', GoInt),
            ('Elem', GoInt),
        ])
        wire_type = GoWireType('WireType', self, [
            ('ArrayT', array_type),
            ('SliceT', slice_type),
            ('StructT', struct_type),
            ('MapT', map_type),
        ])

        # We can now register basic and compound types.
        self.types = {
            TypeID.INT: GoInt,
            TypeID.UINT: GoUint,
            TypeID.BOOL: GoBool,
            TypeID.FLOAT: GoFloat,
            TypeID.BYTE_SLICE: GoByteSlice,
            TypeID.STRING: GoString,
            TypeID.COMPLEX: GoComplex,
            TypeID.WIRE_TYPE: wire_type,
            TypeID.ARRAY_TYPE: array_type,
            TypeID.COMMON_TYPE: common_type,
            TypeID.SLICE_TYPE: slice_type,
            TypeID.STRUCT_TYPE: struct_type,
            TypeID.FIELD_TYPE: field_type,
            # 22 is slice of fieldType.
            TypeID.MAP_TYPE: map_type,
        }

    def load(self, buf):
        while True:
            length, buf = GoUint.decode(buf)
            typeid, buf = GoInt.decode(buf)
            if typeid > 0:
                break  # Found a value.

            # Decode wire type and register type for later.
            custom_type, buf = self.decode_value(TypeID.WIRE_TYPE, buf)
            self.types[-typeid] = custom_type

        try:
            typeid = TypeID(typeid)
        except ValueError:
            pass  # We only have enum values for the basic types.

        # TODO: why must we skip a zero byte here?
        value, buf = self.decode_value(typeid, buf[1:])
        assert buf == b'', "trailing garbage: %s" % list(buf)
        return value

    def decode_value(self, typeid, buf):
        go_type = self.types.get(typeid)
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
        self.zero = self._class._make([t.zero for (n, t) in fields])

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
            value, buf = field.decode(buf)
            values[name] = value
        return self.zero._replace(**values), buf


class GoWireType(GoStruct):
    def decode(self, buf):
        """Decode data from buf and return a GoType."""
        wire_type, buf = super().decode(buf)
        if wire_type.ArrayT != self._loader.types[TypeID.ARRAY_TYPE].zero:
            return GoArray(self._loader, wire_type.ArrayT), buf
        if wire_type.SliceT != self._loader.types[TypeID.SLICE_TYPE].zero:
            return GoSlice(self._loader, wire_type.SliceT), buf
        if wire_type.MapT != self._loader.types[TypeID.MAP_TYPE].zero:
            return GoMap(self._loader, wire_type.MapT), buf
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
        assert count == self._array_type.Len, \
            "expected %d elements, found %d" % (self._array_type.Len, count)
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


class GoSlice(GoType):
    def __init__(self, loader, slice_type):
        self._loader = loader
        self._slice_type = slice_type

    def decode(self, buf):
        """Decode data from buf and return a list.

        Go slices can extended later (with a possible reallocation of
        the underlying array) and are thus similar to Python lists.
        """
        count, buf = GoUint.decode(buf)
        typeid = self._slice_type.Elem
        try:
            typeid = TypeID(typeid)
        except ValueError:
            pass

        result = []
        for i in range(count):
            value, buf = self._loader.decode_value(typeid, buf)
            result.append(value)
        return result, buf


class GoMap(GoType):
    @property
    def zero(cls):
        return {}

    def __init__(self, loader, map_type):
        self._loader = loader
        self._map_type = map_type

    def decode(self, buf):
        """Decode data from buf and return a dict."""
        count, buf = GoUint.decode(buf)
        key_typeid = self._map_type.Key
        try:
            key_typeid = TypeID(key_typeid)
        except ValueError:
            pass

        elem_typeid = self._map_type.Elem
        try:
            elem_typeid = TypeID(elem_typeid)
        except ValueError:
            pass

        result = {}
        for i in range(count):
            key, buf = self._loader.decode_value(key_typeid, buf)
            value, buf = self._loader.decode_value(elem_typeid, buf)
            result[key] = value
        return result, buf
