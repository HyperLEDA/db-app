import jinja2

# TODO: make a unified way for querying with templates


def render_query(query_string: str, **kwargs) -> str:
    tpl = jinja2.Environment(loader=jinja2.BaseLoader()).from_string(query_string)

    return tpl.render(**kwargs)


ONE_BIBLIOGRAPHY = """
SELECT id, bibcode, year, author, title FROM common.bib
WHERE id = %s
"""


BIBLIOGRAPHY_TEMPLATE = """
SELECT
    id, bibcode, year, author, title
FROM common.bib
WHERE
    1 = 1
    AND
    title LIKE CONCAT('%%', %s::text, '%%')
ORDER BY modification_time DESC
OFFSET %s
LIMIT %s
"""

GET_TASK_INFO = """
SELECT id, task_name, payload, user_id, status, start_time, end_time, message FROM common.tasks WHERE id = %s
"""


NEW_OBJECTS = """
INSERT INTO common.pgc
VALUES {% for _ in range(n) %}(DEFAULT){% if not loop.last %},{% endif %}{% endfor %}
RETURNING id;
"""

NEW_DESIGNATIONS = """
INSERT INTO designation.data (pgc, design, bib)
VALUES
    {% for obj in objects %}
    (%s, %s, %s){% if not loop.last %},{% endif %}
    {% endfor %}
"""

NEW_COORDINATES = """
INSERT INTO icrs.data (pgc, ra, dec, bib)
VALUES
    {% for obj in objects %}
    (%s, %s, %s, %s){% if not loop.last %},{% endif %}
    {% endfor %}
"""

GET_DESIGNATIONS = """
SELECT design, bib, modification_time
FROM designation.data
WHERE pgc = %s
OFFSET %s
LIMIT %s
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
    VALUES ({% for _ in fields %}%s{% if not loop.last %},{% endif %} {% endfor %})
"""

GET_TMP_DATA_INSIDE = """
SELECT idx FROM {{ table_name }}
WHERE
    dec >= {{ dec0 - delta }} AND dec <= {{ dec0 + delta }} AND
    sphdist(ra, dec, {{ ra0 }}, {{ dec0 }}) <= {{ delta }}
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
