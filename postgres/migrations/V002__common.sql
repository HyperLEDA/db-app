/* pgmigrate-encoding: utf-8 */

CREATE SCHEMA IF NOT EXISTS common;
COMMENT ON SCHEMA common IS 'Common Leda tables';

CREATE TABLE common.pgc (
  id	serial PRIMARY KEY
);

COMMENT ON TABLE common.pgc IS 'The list of Principal Galaxy Catalog (PGC) numbers used as the primary identifier for objects in the database.' ;
COMMENT ON COLUMN common.pgc.id IS 'Main ID of the object.' ;


CREATE TABLE common.bib (
  id	serial	PRIMARY KEY
, code	text	UNIQUE
, year	smallint	NOT NULL	CHECK (year>=1600 and extract(year from now())>=year)
, author	text[]	CHECK (array_length(author,1)>=1 and author[1] IS NOT NULL and author[1]!~'^ *$' and author[1]!~'^ +' and author[1]!~' +$' )
, title	text	NOT NULL	CHECK (title!~'^ *$' and title!~'^ +' and title!~' +$' )
, modification_time	timestamp without time zone	NOT NULL	DEFAULT NOW()
);
CREATE INDEX ON common.bib (year) ;
CREATE INDEX ON common.bib USING GIN(author) ;
CREATE INDEX ON common.bib (title) ;

COMMENT ON TABLE common.bib IS 'Bibliography catalog' ;
COMMENT ON COLUMN common.bib.id IS 'Bibliography ID' ;
COMMENT ON COLUMN common.bib.code IS 'This field contains symbolic code for the bibliography entry. If it is the ADS bibcode, it references the ADS database: https://ui.adsabs.harvard.edu/';
COMMENT ON COLUMN common.bib.year IS 'Year of publication' ;
COMMENT ON COLUMN common.bib.author IS 'Author list' ;
COMMENT ON COLUMN common.bib.title IS 'Publication title' ;
COMMENT ON COLUMN common.bib.modification_time IS 'Timestamp when the record was added to the database' ;
CREATE TYPE common.user_role AS ENUM('admin');

CREATE TABLE common.users (
  id	serial	PRIMARY KEY
, login text  NOT NULL  UNIQUE
, name	text	NOT NULL
, email	text	NOT NULL	UNIQUE
, role common.user_role NOT NULL
, password_hash  bytea  NOT NULL
);

COMMENT ON TABLE common.users IS 'User list' ;
COMMENT ON COLUMN common.users.id IS 'User ID' ;
COMMENT ON COLUMN common.users.name IS 'Full name' ;
COMMENT ON COLUMN common.users.email IS 'User email' ;
COMMENT ON COLUMN common.users.password_hash IS 'Hash of the user password glued with salt' ;

CREATE TABLE common.tokens (
  token text PRIMARY KEY
, user_id integer NOT NULL REFERENCES common.users(id)
, expiry_time timestamp without time zone NOT NULL
, active bool DEFAULT 'true'
);

COMMENT ON TABLE common.tokens IS 'List of access tokens' ;
COMMENT ON COLUMN common.tokens.token IS 'Value of the token, usually - randomly generated string' ;
COMMENT ON COLUMN common.tokens.user_id IS 'Owner of the token' ;
COMMENT ON COLUMN common.tokens.expiry_time IS 'Time after which token becomes invalid' ;
COMMENT ON COLUMN common.tokens.active IS 'Is this token obsolete or not' ;

CREATE OR REPLACE FUNCTION common.disable_other_tokens() RETURNS trigger
  LANGUAGE plpgsql
AS
$$
  BEGIN
  UPDATE common.tokens
  SET active = false
  WHERE user_id = NEW.user_id
  AND token != NEW.token;
  RETURN NEW;
  END
$$;

CREATE TRIGGER tr_disable_other_tokens
  AFTER INSERT ON common.tokens
  FOR EACH ROW
EXECUTE PROCEDURE common.disable_other_tokens();

CREATE TYPE common.datatype AS ENUM('regular', 'reprocessing', 'preliminary', 'compilation');

-- TODO: add meta function to read/write these comments
COMMENT ON TYPE common.datatype IS '{
  "regular": "Regular measurements",
  "reprocessing": "Reprocessing of observations",
  "preliminary": "Preliminary results",
  "compilation": "Compilation of data from literature"
}';

CREATE TYPE common.task_status AS ENUM('new', 'in_progress', 'failed', 'done');

CREATE TABLE common.tasks (
  id	serial	PRIMARY KEY
, task_name	text	NOT NULL
, status	common.task_status	NOT NULL DEFAULT 'new'
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
COMMENT ON COLUMN common.tasks.message IS 'Some payload about the task or error message if it failed';

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

CREATE TYPE common.quality AS ENUM ('ok', 'lowsnr', 'sus', '>', '<', 'wrong' ) ;
COMMENT ON TYPE common.quality IS 'Data quality: ok = regular measurement; lowsnr = low signal-to-noise; sus = suspected measurement; > = lower limit; < = upper limit; wrong = wrong measurement' ;
