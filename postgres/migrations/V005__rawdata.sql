/* pgmigrate-encoding: utf-8 */

BEGIN ;

DROP SCHEMA IF EXISTS rawdata CASCADE ;

-----------------------------------------------------------
-------- Raw data -----------------------------------------
CREATE SCHEMA rawdata;

COMMENT ON SCHEMA rawdata IS 'Container for the original tables from different sources' ;


-----------------------------------------------------------
-------- Data processing Status ---------------------------
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

-----------------------------------------------------------
-------- List of source data tables -----------------------
CREATE TABLE rawdata.tables (
  id	serial	PRIMARY KEY
, bib	integer	NOT NULL	REFERENCES common.bib(id)	ON DELETE restrict	ON UPDATE cascade
, table_name	text	NOT NULL	UNIQUE
, datatype	common.datatype	NOT NULL
, status	rawdata.status	NOT NULL	DEFAULT 'initiated'
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

-----------------------------------------------------------
-------- Processed objects table --------------------------

CREATE TYPE rawdata.processing_status AS ENUM ('unprocessed', 'new', 'existing', 'collided');

CREATE TABLE rawdata.objects (
  table_id int NOT NULL REFERENCES rawdata.tables(id)
, object_id text NOT NULL
, pgc int NULL
, status rawdata.processing_status NOT NULL DEFAULT 'unprocessed'
, data jsonb
, metadata jsonb
, PRIMARY KEY (table_id, object_id)
);

CREATE INDEX ON rawdata.objects (status);

COMMENT ON TABLE rawdata.objects IS 'Table to store processed objects and their metadata';
COMMENT ON COLUMN rawdata.objects.table_id IS 'Reference to the original table';
COMMENT ON COLUMN rawdata.objects.object_id IS 'Identifier for the object within the original table';
COMMENT ON COLUMN rawdata.objects.status IS 'Status of the processing';
COMMENT ON COLUMN rawdata.objects.data IS 'Homogeneous data about the object';
COMMENT ON COLUMN rawdata.objects.metadata IS 'Metadata related to the processing steps';

COMMIT ;
