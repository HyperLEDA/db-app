import numpy as np

TYPE_TEXT = "text"
TYPE_INTEGER = "integer"
TYPE_DOUBLE_PRECISION = "double precision"

type_map = {
    "str": TYPE_TEXT,
    "string": TYPE_TEXT,
    "int": TYPE_INTEGER,
    "integer": TYPE_INTEGER,
    "float": TYPE_DOUBLE_PRECISION,
    "double": TYPE_DOUBLE_PRECISION,
}


def get_type(t: str) -> str:
    if t in type_map:
        return type_map[t]

    raise ValueError(f"unable to cast: unknown type {t}")


def get_type_from_dtype(t: np.dtype) -> str:
    if t.kind in {"U", "S"}:
        return TYPE_TEXT

    if t in [np.float16, np.float32, np.float64]:
        return TYPE_DOUBLE_PRECISION

    if t in [np.int16, np.int32, np.int64]:
        return TYPE_INTEGER

    raise ValueError(f"unknown type: {t}")
