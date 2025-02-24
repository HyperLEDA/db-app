/* pgmigrate-encoding: utf-8 */

CREATE SCHEMA IF NOT EXISTS rawdata;
COMMENT ON SCHEMA rawdata IS 'Container for the original tables from different sources' ;

CREATE TYPE rawdata.status AS ENUM(
  'initiated', 
  'downloading', 
  'failed', 
  'downloaded', 
  'auto x-id', 
  'auto x-id finished', 
  'manual x-id', 
  'processed'
);

COMMENT ON TYPE rawdata.status IS '{
  "initiated": "Structure is initiated",
  "downloading": "Data is downloading",
  "failed": "Data downloading failed",
  "auto x-id": "Automatic cross-identification",
  "auto x-id finished": "Manual cross-identification is finished",
  "manual x-id": "Manual cross-identification",
  "processed": "Table is processed"
}';

CREATE TABLE rawdata.tables (
  id	serial	PRIMARY KEY
, bib	integer	NOT NULL	REFERENCES common.bib(id)	ON DELETE restrict	ON UPDATE cascade
, table_name	text	NOT NULL	UNIQUE
, datatype	common.datatype	NOT NULL
, status	rawdata.status	NOT NULL	DEFAULT 'initiated'
, modification_dt timestamp DEFAULT NOW()
);
CREATE INDEX ON rawdata.tables (datatype) ;
CREATE INDEX ON rawdata.tables (bib) ;
CREATE INDEX ON rawdata.tables (table_name) ;

COMMENT ON TABLE rawdata.tables IS 'List of original data tables' ;
COMMENT ON COLUMN rawdata.tables.id IS 'Rawdata table ID' ;
COMMENT ON COLUMN rawdata.tables.bib IS 'Bibliography reference' ;
COMMENT ON COLUMN rawdata.tables.table_name IS 'Rawdata table name' ;
COMMENT ON COLUMN rawdata.tables.datatype IS 'Types of the data (regular,reprocessing,preliminary,compilation)' ;
COMMENT ON COLUMN rawdata.tables.status IS 'Data processing status' ;

CREATE TYPE rawdata.crossmatch_status AS ENUM ('unprocessed', 'new', 'existing', 'collided');

CREATE TABLE rawdata.objects (
  id text PRIMARY KEY
, table_id int NOT NULL REFERENCES rawdata.tables(id)
, data json
, modification_dt timestamp DEFAULT NOW()
);

CREATE OR REPLACE FUNCTION rawdata.update_modification_dt() RETURNS trigger
  LANGUAGE plpgsql
AS 
$$
  BEGIN
    NEW.modification_dt = NOW();
    RETURN NEW;
  END
$$;

CREATE TRIGGER update_modification_dt
  BEFORE UPDATE ON rawdata.objects
  FOR EACH ROW
EXECUTE PROCEDURE rawdata.update_modification_dt();

CREATE TABLE rawdata.crossmatch (
  object_id text PRIMARY KEY REFERENCES rawdata.objects(id)
, status rawdata.crossmatch_status NOT NULL DEFAULT 'unprocessed'
, metadata json
);

CREATE OR REPLACE FUNCTION rawdata.next_pgc() RETURNS integer AS $$
DECLARE
  next_id integer;
BEGIN
  SELECT MAX(id) + 1 INTO next_id FROM rawdata.pgc;
  RETURN COALESCE(next_id, 1);
END;
$$ LANGUAGE plpgsql;

CREATE TABLE rawdata.pgc (
  object_id text REFERENCES rawdata.objects (id)
, id integer NOT NULL DEFAULT rawdata.next_pgc()
, PRIMARY KEY (object_id)
);
