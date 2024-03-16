QUERY_ONE_BIBLIOGRAPHY = """
SELECT id, bibcode, year, author, title FROM common.bib 
WHERE id = %s
"""
