BEGIN;

DROP SCHEMA IF EXISTS common CASCADE ;

-----------------------------------------------------------
------ Common ---------------------------------------------
CREATE SCHEMA common ;

COMMENT ON SCHEMA common IS 'Common Leda tables' ;


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


------------------------------------------
-- List of obsoleted bibliography --------
CREATE TABLE common.obsoleted (
  bib	integer	PRIMARY KEY	REFERENCES common.bib ( id ) ON DELETE restrict ON UPDATE cascade
, renewed	integer	NOT NULL	REFERENCES common.bib ( id ) ON DELETE restrict ON UPDATE cascade
, modification_time	timestamp without time zone	NOT NULL	DEFAULT NOW()
) ;

COMMENT ON TABLE common.obsoleted	IS 'List of obsoleted bibliography' ;
COMMENT ON COLUMN common.obsoleted.bib	IS 'Obsoleted bibliography' ;
COMMENT ON COLUMN common.obsoleted.renewed	IS 'Bibliography that made the previous one obsolete' ;
COMMENT ON COLUMN common.obsoleted.modification_time	IS 'Timestamp when the record was added to the database' ;




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



-----------------------------------------------
--------- Observation Data Types --------------
CREATE TABLE common.datatype (
  id	text	PRIMARY KEY
, description	text	NOT NULL
) ;

COMMENT ON TABLE common.datatype IS 'The types of the published data' ;
COMMENT ON COLUMN common.datatype.id IS 'ID of the data type' ;
COMMENT ON COLUMN common.datatype.description IS 'Description of the data type' ;

INSERT INTO common.datatype VALUES 
  ( 'reguliar'     , 'Reguliar measurements' )
, ( 'reprocessing' , 'Reprocessing of observations' )
, ( 'preliminary'  , 'Preliminary results' )
, ( 'compilation'  , 'Compilation of data from literature' )
;


-----------------------------------------------
--------- Data Quality ------------------------
CREATE TABLE common.quality (
  id	smallint	PRIMARY KEY
, description	text	NOT NULL
) ;

COMMENT ON TABLE common.quality IS 'Data quality' ;
COMMENT ON COLUMN common.quality.id IS 'ID of the data quality' ;
COMMENT ON COLUMN common.quality.description IS 'Description of the data quality' ;

INSERT INTO common.datatype VALUES 
  ( 0 , 'Reguliar measurements' )
, ( 1 , 'Low signal to noise' )
, ( 2 , 'Suspected measurement' )
, ( 3 , 'Lower limit' )
, ( 4 , 'Upper limit' )
, ( 5 , 'Wrong measurement' )
;


COMMIT;