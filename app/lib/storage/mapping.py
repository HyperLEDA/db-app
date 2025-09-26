TYPE_TEXT = "text"
TYPE_INTEGER = "integer"
TYPE_BIGINT = "bigint"
TYPE_DOUBLE_PRECISION = "double precision"
TYPE_TIMESTAMP = "timestamp without time zone"

type_map = {
    # SQL types
    "str": TYPE_TEXT,
    "string": TYPE_TEXT,
    "character varying": TYPE_TEXT,
    "text": TYPE_TEXT,
    "character": TYPE_TEXT,
    "char": TYPE_TEXT,
    "short": TYPE_INTEGER,
    "int": TYPE_INTEGER,
    "long": TYPE_BIGINT,
    "integer": TYPE_INTEGER,
    "smallint": TYPE_INTEGER,
    "float": TYPE_DOUBLE_PRECISION,
    "double": TYPE_DOUBLE_PRECISION,
    "double precision": TYPE_DOUBLE_PRECISION,
    "real": TYPE_DOUBLE_PRECISION,
    "timestamp without time zone": TYPE_TIMESTAMP,
    # XML Schema types
    "unsignedLong": TYPE_BIGINT,
    "unsignedInt": TYPE_INTEGER,
    "unsignedShort": TYPE_INTEGER,
    "unsignedByte": TYPE_INTEGER,
    "positiveInteger": TYPE_INTEGER,
    # JSON Schema types
    "number": TYPE_DOUBLE_PRECISION,
}
