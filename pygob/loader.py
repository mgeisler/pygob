import struct
import collections

from .types import (BOOL, INT, UINT, FLOAT, BYTE_SLICE, STRING, COMPLEX,
                    WIRE_TYPE, ARRAY_TYPE, COMMON_TYPE, SLICE_TYPE,
                    STRUCT_TYPE, FIELD_TYPE, MAP_TYPE)


class Loader:
    def __init__(self):
        # Compound types that depend on the basic types above.
        common_type = GoStruct('CommonType', self, [
            ('Name', STRING),
            ('Id', INT),
        ])
        array_type = GoStruct('ArrayType', self, [
            ('CommonType', COMMON_TYPE),
            ('Elem', INT),
            ('Len', INT),
        ])
        slice_type = GoStruct('SliceType', self, [
            ('CommonType', COMMON_TYPE),
            ('Elem', INT),
        ])
        struct_type = GoStruct('StructType', self, [
            ('CommonType', COMMON_TYPE),
            ('Field', INT),
        ])
        field_type = GoStruct('FieldType', self, [
            ('Name', STRING),
            ('Id', INT),
        ])
        # TODO: 22 is slice of fieldType.
        map_type = GoStruct('MapType', self, [
            ('CommonType', COMMON_TYPE),
            ('Key', INT),
            ('Elem', INT),
        ])
        wire_type = GoWireType('WireType', self, [
            ('ArrayT', ARRAY_TYPE),
            ('SliceT', SLICE_TYPE),
            ('StructT', STRUCT_TYPE),
            ('MapT', MAP_TYPE),
        ])

        # We can now register basic and compound types.
        self.types = {
            INT: GoInt,
            UINT: GoUint,
            BOOL: GoBool,
            FLOAT: GoFloat,
            BYTE_SLICE: GoByteSlice,
            STRING: GoString,
            COMPLEX: GoComplex,
            WIRE_TYPE: wire_type,
            ARRAY_TYPE: array_type,
            COMMON_TYPE: common_type,
            SLICE_TYPE: slice_type,
            STRUCT_TYPE: struct_type,
            FIELD_TYPE: field_type,
            # 22 is slice of fieldType.
            MAP_TYPE: map_type,
        }

    def load(self, buf):
        while True:
            length, buf = GoUint.decode(buf)
            typeid, buf = GoInt.decode(buf)
            if typeid > 0:
                break  # Found a value.

            # Decode wire type and register type for later.
            custom_type, buf = self.decode_value(WIRE_TYPE, buf)
            self.types[-typeid] = custom_type

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
    @property
    def zero(self):
        values = [self._loader.types[t].zero for (n, t) in self._fields]
        return self._class._make(values)

    def __init__(self, name, loader, fields):
        """A Go struct with a certain set of fields.

        The zero value of a GoStruct is based on the zero values of
        each field:

        >>> person = GoStruct('Person', Loader(), [
        ...     ('Name', STRING),
        ...     ('Age', INT),
        ... ])
        >>> person.zero
        Person(Name=b'', Age=0)
        """
        self._name = name
        self._loader = loader
        self._fields = fields
        self._class = collections.namedtuple(name, [n for (n, t) in fields])

    def decode(self, buf):
        """Decode data from buf and return a namedtuple."""
        values = {}
        field_id = -1
        while True:
            delta, buf = GoUint.decode(buf)
            if delta == 0:
                break
            field_id += delta
            name, typeid = self._fields[field_id]
            value, buf = self._loader.types[typeid].decode(buf)
            values[name] = value
        return self.zero._replace(**values), buf


class GoWireType(GoStruct):
    def decode(self, buf):
        """Decode data from buf and return a GoType."""
        wire_type, buf = super().decode(buf)

        if wire_type.ArrayT != self._loader.types[ARRAY_TYPE].zero:
            typeid = wire_type.ArrayT.Elem
            length = wire_type.ArrayT.Len
            return GoArray(self._loader, typeid, length), buf

        if wire_type.SliceT != self._loader.types[SLICE_TYPE].zero:
            typeid = wire_type.SliceT.Elem
            return GoSlice(self._loader, typeid), buf

        if wire_type.MapT != self._loader.types[MAP_TYPE].zero:
            key_typeid = wire_type.MapT.Key
            elem_typeid = wire_type.MapT.Elem
            return GoMap(self._loader, key_typeid, elem_typeid), buf

        raise NotImplementedError("cannot handle %s" % wire_type)


class GoArray(GoType):
    @property
    def zero(self):
        return (self._loader.types[self._typeid].zero, ) * self._length

    def __init__(self, loader, typeid, length):
        """A Go array of a certain type and length.

        >>> int3 = GoArray(Loader(), INT, 3)
        >>> int3.zero
        (0, 0, 0)
        """
        self._loader = loader
        self._typeid = typeid
        self._length = length

    def decode(self, buf):
        """Decode data from buf and return a tuple.

        Go arrays have a fixed size and cannot be resized. This makes
        them more like Python tuples than Python lists.
        """
        count, buf = GoUint.decode(buf)
        assert count == self._length, \
            "expected %d elements, found %d" % (self._length, count)

        result = []
        for i in range(count):
            value, buf = self._loader.decode_value(self._typeid, buf)
            result.append(value)
        return tuple(result), buf


class GoSlice(GoType):
    @property
    def zero(cls):
        return []

    def __init__(self, loader, typeid):
        """A Go slice of a certain type.

        >>> int_slice = GoSlice(Loader(), INT)
        >>> int_slice.zero
        []
        """
        self._loader = loader
        self._typeid = typeid

    def decode(self, buf):
        """Decode data from buf and return a list.

        Go slices can extended later (with a possible reallocation of
        the underlying array) and are thus similar to Python lists.
        """
        count, buf = GoUint.decode(buf)

        result = []
        for i in range(count):
            value, buf = self._loader.decode_value(self._typeid, buf)
            result.append(value)
        return result, buf


class GoMap(GoType):
    @property
    def zero(cls):
        return {}

    def __init__(self, loader, key_typeid, elem_typeid):
        """A Go map with a certain key and element type.

        >>> int_string_map = GoMap(Loader(), INT, STRING)
        >>> int_string_map.zero
        {}
        """
        self._loader = loader
        self._key_typeid = key_typeid
        self._elem_typeid = elem_typeid

    def decode(self, buf):
        """Decode data from buf and return a dict."""
        count, buf = GoUint.decode(buf)

        result = {}
        for i in range(count):
            key, buf = self._loader.decode_value(self._key_typeid, buf)
            value, buf = self._loader.decode_value(self._elem_typeid, buf)
            result[key] = value
        return result, buf
