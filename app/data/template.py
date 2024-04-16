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


NEW_OBJECTS = jinja2.Environment(loader=jinja2.BaseLoader()).from_string(
    """
INSERT INTO common.pgc
VALUES {% for _ in range(n) %}(DEFAULT){% if not loop.last %},{% endif %}{% endfor %}
RETURNING id;
"""
)

NEW_DESIGNATIONS = jinja2.Environment(loader=jinja2.BaseLoader()).from_string(
    """
INSERT INTO designation.data (pgc, design, bib)
VALUES
    {% for obj in objects %}
    (%s, %s, %s){% if not loop.last %},{% endif %}
    {% endfor %}
"""
)

NEW_COORDINATES = jinja2.Environment(loader=jinja2.BaseLoader()).from_string(
    """
INSERT INTO icrs.data (pgc, ra, dec, bib)
VALUES
    {% for obj in objects %}
    (%s, %s, %s, %s){% if not loop.last %},{% endif %}
    {% endfor %}
"""
)

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

# TODO: use meta.setparam
ADD_COLUMN_COMMENT = """
COMMENT ON COLUMN {{ schema }}.{{ table_name }}.{{ column_name }} IS '{{ params }}'
"""

ADD_TABLE_COMMENT = """
COMMENT ON TABLE {{ schema }}.{{ table_name }} IS '{{ params }}'
"""

INSERT_RAW_DATA = jinja2.Environment(loader=jinja2.BaseLoader()).from_string(
    """
INSERT INTO 
    {{ schema }}.{{ table }} ({% for field_name in fields %}{{ field_name }}{% if not loop.last %},{% endif %}{% endfor %}) 
    VALUES{% for object in objects %}
    ({% for field_name in fields %}{{ object[field_name] }}{% if not loop.last %},{% endif %}{% endfor %}){% if not loop.last %},{% endif %}
    {% endfor %}
"""
)
