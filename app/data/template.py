import jinja2


def render_query(query_string: str, **kwargs) -> str:
    tpl = jinja2.Environment(loader=jinja2.BaseLoader()).from_string(query_string)

    return tpl.render(**kwargs)


GET_SOURCE_BY_CODE = """
SELECT id, bibcode, year, author, title FROM common.bib
WHERE bibcode = %s
LIMIT 1
"""

GET_SOURCE_BY_ID = """
SELECT id, bibcode, year, author, title FROM common.bib
WHERE id = %s
LIMIT 1
"""

GET_TASK_INFO = """
SELECT id, task_name, payload, user_id, status, start_time, end_time, message FROM common.tasks WHERE id = %s
"""

CREATE_TABLE = """
CREATE TABLE {{ schema }}.{{ name }} (
    {% for field_name, field_type in fields %}
    {{field_name}} {{field_type}}{% if not loop.last %},{% endif %}
    {% endfor %}
)
"""

CREATE_TMP_TABLE = """
CREATE TEMPORARY TABLE {{ name }} (
    {% for field_name, field_type in fields %}
    {{field_name}} {{field_type}}{% if not loop.last %},{% endif %}
    {% endfor %}
)
"""

ADD_COLUMN_COMMENT = """
SELECT meta.setparams('{{ schema }}', '{{ table_name }}', '{{ column_name }}', '{{ params }}'::json)
"""

ADD_TABLE_COMMENT = """
SELECT meta.setparams('{{ schema }}', '{{ table_name }}', '{{ params }}'::json)
"""

INSERT_TABLE_REGISTRY_ITEM = """
INSERT INTO rawdata.tables (bib, table_name, datatype)
VALUES (%s, %s, %s)
RETURNING id
"""

INSERT_RAW_DATA = """
INSERT INTO 
    {{ schema }}.{{ table }} 
    ({% for field_name in fields %}{{ field_name }}{% if not loop.last %},{% endif %}{% endfor %})
    VALUES{% for object in objects %}
    ({% for field_name in fields %}
        {{ object[field_name] }}{% if not loop.last %},{% endif %}{% endfor %}){% if not loop.last %},{% endif %}
    {% endfor %}
"""

INSERT_TMP_RAW_DATA = """
INSERT INTO 
    {{ table }} 
    ({% for field_name in fields %}{{ field_name }}{% if not loop.last %},{% endif %}{% endfor %})
    VALUES{% for object in objects %}
    ({% for field_name in fields %}
        {{ object[field_name] }}{% if not loop.last %},{% endif %}{% endfor %}){% if not loop.last %},{% endif %}
    {% endfor %}
"""

GET_TMP_DATA_INSIDE = """
SELECT idx FROM {{ table_name }}
WHERE
    dec >= {{ dec0 - delta }} AND dec <= {{ dec0 + delta }} AND
    sphdist(ra, dec, {{ ra0 }}, {{ dec0 }}) <= {{ delta }}
"""

GET_TMP_DATA_BY_NAME = """
SELECT idx
FROM {{ table_name }}
WHERE
    name && array[{% for n in all_names %}'{{ n }}'{% if not loop.last %},{% endif %}{% endfor %}]
"""

GET_RAWDATA_TABLE = """
SELECT table_name FROM rawdata.tables
WHERE id = %s
"""

BUILD_INDEX = """
CREATE INDEX {{ index_name }} 
ON {{ table_name }}({% for col_name in columns %}{{ col_name }}{% if not loop.last %},{% endif %}{% endfor %})
"""

DROP_TABLE = """DROP TABLE {{ table_name }}"""

GET_COLUMN_NAMES = """
SELECT column_name
FROM information_schema.columns
WHERE
    table_schema = %s
    AND table_name = %s
"""

FETCH_RAWDATA = """
SELECT 
    {% if rows is not none %}
        {% for row in rows %} {{ row }}{% if not loop.last %},{% endif %} {% endfor %}
    {% else %}
        *
    {% endif %}
FROM {{ schema }}.{{ table }}
"""

FETCH_COLUMN_METADATA = """
SELECT param
FROM meta.column_info 
WHERE
    schema_name = %s and
    table_name = %s and
    column_name = %s
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
FROM rawdata.tables
WHERE table_name=%s
"""
