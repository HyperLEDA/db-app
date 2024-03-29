BEGIN;

DROP SCHEMA IF EXISTS common CASCADE ;
DROP SCHEMA IF EXISTS rawdata CASCADE ;

-----------------------------------------------------------
------ Common ---------------------------------------------
CREATE SCHEMA common ;

COMMENT ON SCHEMA common IS 'The schema contains the common Leda tables' ;


-----------------------------------------------------------
--------- The object list ---------------------------------
-- Все остальные параметры (координаты, имена, природа и т.д. определяются на основе данных уровня 1)
CREATE TABLE common.pgc (
  id	serial PRIMARY KEY	-- autoincrementing 4B-index from 1 to 2147483647
);

COMMENT ON TABLE common.pgc IS 'The list of Principal Galaxy Catalog (PGC) numbers used as the primary identifier for objects in the database.' ;
COMMENT ON COLUMN common.pgc.id IS 'Main ID of the object list of Principal Galaxy Catalog (PGC) numbers used as the primary identifier for objects in the database.' ;



-----------------------------------------------------------
--------- Bibliography ------------------------------------
-- Помимо ссылок на литературу содержит ID работ, которые выболняются в рамках Леда, а также на частные сообщения
CREATE TABLE common.bib (
  id	serial	PRIMARY KEY
-- bibcode references the ADS databse: https://ui.adsabs.harvard.edu/
, bibcode	char(19)	UNIQUE	CHECK ( bibcode~'^(1[89]|20)[0-9]{2}[A-Za-z.]{5}[A-Za-z0-9.]{4}[ELPQ-Z0-9.][0-9.]{4}[A-Z]$' )
, year	smallint	NOT NULL	CHECK (year>=1800 and extract(year from now())>=year)
, author	text[]	CHECK (array_length(author,1)>=1 and author[1] IS NOT NULL and author[1]!~'^ *$' and author[1]!~'^ +' and author[1]!~' +$' )
, title	text	NOT NULL	CHECK (title!~'^ *$' and title!~'^ +' and title!~' +$' )
, modification_time	timestamp without time zone	NOT NULL	DEFAULT NOW()
);
CREATE INDEX ON common.bib (year) ;
CREATE INDEX ON common.bib USING GIN(author) ;
CREATE INDEX ON common.bib (title) ;

COMMENT ON TABLE common.bib IS 'Bibliography catalog' ;
COMMENT ON COLUMN common.bib.id IS 'Bibliography ID' ;
COMMENT ON COLUMN common.bib.bibcode IS 'The bibcode references the ADS databse: https://ui.adsabs.harvard.edu/' ;
COMMENT ON COLUMN common.bib.year IS 'Year of publication' ;
COMMENT ON COLUMN common.bib.author IS 'Author list' ;
COMMENT ON COLUMN common.bib.title IS 'Publication title' ;
COMMENT ON COLUMN common.bib.modification_time IS 'Timestamp when the record was added to the database' ;


-----------------------------------------------------------
--------- User --------------------------------------------
CREATE TABLE common.users (
  id	serial	PRIMARY KEY
, name	text	NOT NULL	UNIQUE
, email	text	NOT NULL	UNIQUE
);

COMMENT ON TABLE common.users IS 'User list' ;
COMMENT ON COLUMN common.users.id IS 'User ID' ;
COMMENT ON COLUMN common.users.name IS 'Full name' ;
COMMENT ON COLUMN common.users.email IS 'User email' ;


-----------------------------------------------------------
-------- Raw data -----------------------------------------
CREATE SCHEMA rawdata;

COMMENT ON SCHEMA rawdata IS 'The schema is a container for the orginal tables from different sources' ;



COMMIT;