CREATE SCHEMA dataviews;

CREATE ROLE db_researcher;

GRANT USAGE, CREATE ON SCHEMA dataviews TO db_researcher;
