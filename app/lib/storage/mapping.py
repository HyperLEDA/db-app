import numpy as np


def get_type_from_dtype(t: np.dtype) -> str:
    if t.kind in {"U", "S"}:
        return "text"

    if t in [np.float16, np.float32, np.float64]:
        return "double precision"

    if t in [np.int16, np.int32, np.int64]:
        return "integer"

    raise ValueError(f"unknown type: {t}")
