import numpy as np

TYPE_TEXT = "text"
TYPE_INTEGER = "integer"
TYPE_DOUBLE_PRECISION = "double precision"
TYPE_TIMESTAMP = "timestamp without time zone"

type_map = {
    "str": TYPE_TEXT,
    "string": TYPE_TEXT,
    "character varying": TYPE_TEXT,
    "text": TYPE_TEXT,
    "character": TYPE_TEXT,
    "char": TYPE_TEXT,
    "short": TYPE_INTEGER,
    "int": TYPE_INTEGER,
    "long": TYPE_INTEGER,
    "integer": TYPE_INTEGER,
    "smallint": TYPE_INTEGER,
    "float": TYPE_DOUBLE_PRECISION,
    "double": TYPE_DOUBLE_PRECISION,
    "double precision": TYPE_DOUBLE_PRECISION,
    "real": TYPE_DOUBLE_PRECISION,
    "timestamp without time zone": TYPE_TIMESTAMP,
}


def get_type(t: str) -> str:
    if t in type_map:
        return type_map[t]

    raise ValueError(f"unable to cast: unknown type {t}")


def get_type_from_dtype(t: np.dtype) -> str:
    if t.kind in {"U", "S", "O"}:
        return TYPE_TEXT

    if t in [np.float16, np.float32, np.float64]:
        return TYPE_DOUBLE_PRECISION

    if t in [np.int16, np.int32, np.int64]:
        return TYPE_INTEGER

    raise ValueError(f"unknown type: {t}")
