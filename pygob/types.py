"""Predefined gob type IDs.

These are the well-known type IDs that both senders and receivers
already agree on to bootstrap the protocol.
"""

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
