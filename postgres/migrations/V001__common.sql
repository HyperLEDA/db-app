/* pgmigrate-encoding: utf-8 */

BEGIN;

DROP SCHEMA IF EXISTS common CASCADE ;
DROP TYPE IF EXISTS task_status CASCADE ;

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
-- Помимо ссылок на литературу содержит ID работ, которые выполняются в рамках Леда, а также на частные сообщения
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
COMMENT ON COLUMN common.bib.bibcode IS 'The bibcode references the ADS database: https://ui.adsabs.harvard.edu/' ;
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

-----------------------------------------------------------
--------- Tasks -------------------------------------------

CREATE TYPE task_status AS ENUM('new', 'in_progress', 'failed', 'done');

CREATE TABLE common.tasks (
  id	serial	PRIMARY KEY
, task_name	text	NOT NULL
, status	task_status	NOT NULL DEFAULT 'new'
, start_time	timestamp without time zone
, end_time	timestamp without time zone
, payload	jsonb
, user_id	integer REFERENCES common.users(id)
, message	jsonb
);

COMMENT ON TABLE common.tasks IS 'Asynchronous tasks for data processing';
COMMENT ON COLUMN common.tasks.id IS 'Task ID';
COMMENT ON COLUMN common.tasks.task_name IS 'Name of the task from task registry';
COMMENT ON COLUMN common.tasks.status IS 'Current status of the task';
COMMENT ON COLUMN common.tasks.start_time IS 'Task start time';
COMMENT ON COLUMN common.tasks.end_time IS 'Task end time';
COMMENT ON COLUMN common.tasks.payload IS 'Data that was used to start the task';
COMMENT ON COLUMN common.tasks.user_id IS 'User who started the task';

CREATE OR REPLACE FUNCTION common.set_task_times() RETURNS trigger
    LANGUAGE plpgsql
AS
$$
    BEGIN
    IF NEW.status = 'done' OR NEW.status = 'failed' THEN
      UPDATE common.tasks
      SET end_time = NOW()
      WHERE id = NEW.id;
    END IF;
    IF NEW.status = 'in_progress' THEN
      UPDATE common.tasks
      SET start_time = NOW()
      WHERE id = NEW.id;
    END IF;
    RETURN NEW;
    END
$$;

CREATE TRIGGER tr_set_task_end_time
    AFTER UPDATE OF status
    ON common.tasks
    FOR EACH ROW
EXECUTE PROCEDURE common.set_task_times();

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


------------------------------------------------
------ Notes -----------------------------------
CREATE TABLE common.notes (
  pgc	integer	NULL	REFERENCES common.pgc ( id ) ON DELETE restrict ON UPDATE cascade
, bib	integer	NOT NULL	REFERENCES common.bib ( id ) ON DELETE restrict ON UPDATE cascade
, note	text	NOT NULL
, modification_time	timestamp without time zone	NOT NULL	DEFAULT now()
, PRIMARY KEY (pgc,bib)
) ;

COMMENT ON TABLE common.notes IS 'List of important notes on object' ;
COMMENT ON COLUMN common.notes.pgc	IS '{"description" : "PGC number of the object" , "ucd" : "meta.id"}' ;
COMMENT ON COLUMN common.notes.bib	IS '{"description" : "Bibliography reference" , "ucd" : "meta.bib"}' ;
COMMENT ON COLUMN common.notes.note	IS '{"description" : "Important comments on the object" , "ucd" : "meta.note"}' ;
COMMENT ON COLUMN common.notes.modification_time	IS '{"description" : "Timestamp when the record was added to the database" , "ucd" : "time.creation"}' ;


COMMIT;