import io

from .types import (GoBool, GoInt, GoUint, GoFloat, GoStruct, GoByteSlice,
                    GoString, GoComplex)


class Dumper:
    def __init__(self):
        self.types = {
            bool: GoBool,
            int: GoInt,
            float: GoFloat,
            bytes: GoByteSlice,
            str: GoString,
            complex: GoComplex,
        }

    def dump(self, value):
        return self._dump(value)

    def _dump(self, value):
        # Top-level singletons are sent with an extra zero byte which
        # serves as a kind of field delta.
        python_type = type(value)
        go_type = self.types.get(python_type)
        if go_type is None:
            raise NotImplementedError("cannot encode %s of type %s" %
                                      (value, python_type))

        segment = io.BytesIO()
        segment.write(GoInt.encode(go_type.typeid))
        if not isinstance(go_type, GoStruct):
            segment.write(b'\x00')
        segment.write(go_type.encode(value))
        return GoUint.encode(segment.tell()) + segment.getvalue()
