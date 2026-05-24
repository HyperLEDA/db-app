def pg_to_tap_datatype(pg_type: str | None) -> str:
    if pg_type is None:
        return "char"
    normalized = pg_type.lower().strip()
    if normalized in {"smallint", "int2"}:
        return "short"
    if normalized in {"integer", "int", "int4"}:
        return "int"
    if normalized in {"bigint", "int8"}:
        return "bigint"
    if normalized in {"real", "float4"}:
        return "float"
    if normalized in {"double precision", "float8"}:
        return "double"
    if normalized.startswith(("numeric", "decimal")):
        return "double"
    if normalized in {"boolean", "bool"}:
        return "boolean"
    if normalized in {"text", "uuid"} or normalized.startswith("character"):
        return "char"
    if normalized.startswith(("timestamp", "date", "time")):
        return "char"
    return normalized
