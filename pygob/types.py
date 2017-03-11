import enum


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
