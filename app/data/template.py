from psycopg import sql


def build_create_table_query(schema: str, name: str, fields: list[tuple[str, str, str]]) -> sql.Composed:
    field_parts = []
    for field_name, field_type, constraint in fields:
        parts = [sql.Identifier(field_name), sql.SQL(" "), sql.SQL(field_type)]
        if constraint:
            parts.extend([sql.SQL(" "), sql.SQL(constraint)])
        field_parts.append(sql.Composed(parts))

    return sql.SQL("CREATE TABLE {}.{} ({})").format(
        sql.Identifier(schema),
        sql.Identifier(name),
        sql.SQL(", ").join(field_parts),
    )


GET_SOURCE_BY_CODE = """
SELECT id, code, year, author, title FROM common.bib
WHERE code = %s
LIMIT 1
"""

GET_SOURCE_BY_ID = """
SELECT id, code, year, author, title FROM common.bib
WHERE id = %s
LIMIT 1
"""

INSERT_TABLE_REGISTRY_ITEM = """
INSERT INTO layer0.tables (bib, table_name, datatype)
VALUES (%s, %s, %s)
RETURNING id
"""

GET_RAWDATA_TABLE = """
SELECT table_name, modification_dt FROM layer0.tables
WHERE id = %s
"""

FETCH_TABLE_METADATA = """
SELECT param
FROM meta.table_info 
WHERE
    schema_name = %s and
    table_name = %s
"""

FETCH_RAWDATA_REGISTRY = """
SELECT * 
FROM layer0.tables
WHERE table_name=%s
"""
