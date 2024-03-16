import jinja2

QUERY_ONE_BIBLIOGRAPHY = """
SELECT id, bibcode, year, author, title FROM common.bib 
WHERE id = %s
"""


QUERY_BIBLIOGRAPHY_TEMPLATE = jinja2.Environment(loader=jinja2.BaseLoader()).from_string(
    """
SELECT id, bibcode, year, author, title FROM common.bib 
WHERE
    1 = 1
ORDER BY modification_time DESC
OFFSET {{offset}}
LIMIT {{limit}}
"""
)
