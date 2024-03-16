import jinja2

# TODO: make a unified way for querying with templates

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
