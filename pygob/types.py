"""The predefined gob types.

These are the well-known gob types that both senders and receivers
already agree on to bootstrap the protocol.
"""

import struct
import collections

# We do not use an Enum for this since this set isn't the full set of
# all type IDs -- the protocol allows a sender to define custom IDs in
# terms of the IDs below.
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
FIELD_TYPE_SLICE = 22
MAP_TYPE = 23


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
    """An Go Boolean.

    Go Booleans are mapped to Python Booleans. This class is meant to
    be used statically:

    >>> GoBool.decode(bytes([0]))
    (False, b'')
    >>> GoBool.decode(bytes([1]))
    (True, b'')
    """
    zero = False

    @staticmethod
    def decode(buf):
        n, buf = GoUint.decode(buf)
        return n == 1, buf


class GoUint(GoType):
    """An unsigned Go integer.

    Go unsigned integers are mapped to Python integers. This class is
    meant to be used statically:

    >>> GoUint.decode(bytes([56]))
    (56, b'')
    >>> GoUint.decode(bytes([254, 1, 0]))
    (256, b'')
    """
    zero = 0

    @staticmethod
    def decode(buf):
        if buf[0] < 128:  # small uint in a single byte
            return buf[0], buf[1:]

        # larger uint split over multiple bytes
        length = 256 - buf[0]
        n = 0
        for b in buf[1:length]:
            n = (n + b) << 8
        n += buf[length]
        return n, buf[length + 1:]


class GoInt(GoType):
    """A signed Go integer.

    Go signed integers are mapped to Python integers. This class is
    meant to be used statically:

    >>> GoInt.decode(bytes([5]))
    (-3, b'')
    >>> GoInt.decode(bytes([6]))
    (3, b'')
    """
    zero = 0

    @staticmethod
    def decode(buf):
        uint, buf = GoUint.decode(buf)
        if uint & 1:
            uint = ~uint
        return uint >> 1, buf


class GoFloat(GoType):
    """A Go 64-bit float.

    Go floats are mapped to Python floats. This class is meant to be
    used statically:

    >>> GoFloat.decode(bytes([0]))
    (0.0, b'')
    >>> GoFloat.decode(bytes([254, 244, 63]))
    (1.25, b'')
    """
    zero = 0.0

    @staticmethod
    def decode(buf):
        n, buf = GoUint.decode(buf)
        rev = bytes(reversed(struct.pack('L', n)))
        (f, ) = struct.unpack('d', rev)
        return f, buf


class GoByteSlice(GoType):
    """A Go byte slice.

    Go byte slices are mapped to Python bytearrays.

    This class is meant to be used statically:

    >>> GoByteSlice.decode(bytes([5, 104, 101, 108, 108, 111]))
    (bytearray(b'hello'), b'')
    """

    @classproperty
    def zero(cls):
        return bytearray()

    @staticmethod
    def decode(buf):
        count, buf = GoUint.decode(buf)
        return bytearray(buf[:count]), buf[count:]


class GoString(GoType):
    """A Go string.

    Go strings are mapped to Python bytes since Go strings do not
    guarantee any particular encoding.

    This This class is meant to be used statically:

    >>> GoString.decode(bytes([5, 104, 101, 108, 108, 111]))
    (b'hello', b'')
    """
    zero = b''

    @staticmethod
    def decode(buf):
        count, buf = GoUint.decode(buf)
        # TODO: Go strings do not guarantee any particular encoding.
        # Add support for trying to decode the bytes using, say,
        # UTF-8, so we can return a real Python string.
        return buf[:count], buf[count:]


class GoComplex(GoType):
    """A Go complex number.

    Go complex numbers are mapped to Python complex numbers. This
    class is meant to be used statically:

    >>> GoComplex.decode(bytes([0, 254, 244, 63]))
    (1.25j, b'')
    """
    zero = 0 + 0j

    @staticmethod
    def decode(buf):
        re, buf = GoFloat.decode(buf)
        im, buf = GoFloat.decode(buf)
        return complex(re, im), buf


class GoStruct(GoType):
    """A Go struct.

    Go structs are mapped to Python named tuples.
    """

    @property
    def zero(self):
        values = [self._loader.types[t].zero for (n, t) in self._fields]
        return self._class._make(values)

    def __init__(self, name, loader, fields):
        """A Go struct with a certain set of fields.

        The zero value of a GoStruct is based on the zero values of
        each field:

        >>> from pygob import Loader
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

    def __repr__(self):
        """GoStruct representation.

        >>> GoStruct('Person', None, [('Name', STRING), ('Age', INT)])
        <GoStruct Person Name=6, Age=2>
        """
        fields = ['%s=%s' % f for f in self._fields]
        return '<GoStruct %s %s>' % (self._name, ', '.join(fields))


class GoWireType(GoStruct):
    """A Go wire type.

    This type is used in the gob stream to describe custom types.
    Decoding a WIRE_TYPE value yields another GoType subclass which
    can be used later to decode actual values of the custom type.
    """

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

        if wire_type.StructT != self._loader.types[STRUCT_TYPE].zero:
            # Named tuples must be constructed using strings, not
            # bytes, so we need to decode the names here. Go source
            # files are defined to be UTF-8 encoded.
            name = wire_type.StructT.CommonType.Name.decode('utf-8')
            fields = [(f.Name.decode('utf-8'), f.Id)
                      for f in wire_type.StructT.Field]
            return GoStruct(name, self._loader, fields), buf

        if wire_type.MapT != self._loader.types[MAP_TYPE].zero:
            key_typeid = wire_type.MapT.Key
            elem_typeid = wire_type.MapT.Elem
            return GoMap(self._loader, key_typeid, elem_typeid), buf

        raise NotImplementedError("cannot handle %s" % wire_type)


class GoArray(GoType):
    """A Go array.

    Go arrays are mapped to Python tuples.
    """

    @property
    def zero(self):
        return (self._loader.types[self._typeid].zero, ) * self._length

    def __init__(self, loader, typeid, length):
        """A Go array of a certain type and length.

        >>> from pygob import Loader
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
    """A Go slice.

    Go slices are mapped to Python lists.
    """

    @property
    def zero(cls):
        return []

    def __init__(self, loader, typeid):
        """A Go slice of a certain type.

        >>> from pygob import Loader
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
    """A Go map.

    Go maps are mapped to Python dictionaries.
    """

    @property
    def zero(cls):
        return {}

    def __init__(self, loader, key_typeid, elem_typeid):
        """A Go map with a certain key and element type.

        >>> from pygob import Loader
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
