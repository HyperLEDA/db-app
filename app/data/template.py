import jinja2


def render_query(query_string: str, **kwargs) -> str:
    tpl = jinja2.Environment(loader=jinja2.BaseLoader()).from_string(query_string)

    return tpl.render(**kwargs)


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

CREATE_TABLE = """
CREATE TABLE {{ schema }}."{{ name }}" (
    {% for field_name, field_type, constraint in fields %}
    "{{field_name}}" {{field_type}} {{constraint}}{% if not loop.last %},{% endif %}
    {% endfor %}
)
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
