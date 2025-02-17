/* pgmigrate-encoding: utf-8 */

CREATE SCHEMA IF NOT EXISTS rawdata;
COMMENT ON SCHEMA rawdata IS 'Container for the original tables from different sources' ;

CREATE TABLE rawdata.tables (
  id	serial	PRIMARY KEY
, bib	integer	NOT NULL	REFERENCES common.bib(id)	ON DELETE restrict	ON UPDATE cascade
, table_name	text	NOT NULL	UNIQUE
, datatype	common.datatype	NOT NULL
);
CREATE INDEX ON rawdata.tables (datatype) ;
CREATE INDEX ON rawdata.tables (bib) ;
CREATE INDEX ON rawdata.tables (table_name) ;

COMMENT ON TABLE rawdata.tables IS 'List of original data tables' ;
COMMENT ON COLUMN rawdata.tables.id IS 'Rawdata table ID' ;
COMMENT ON COLUMN rawdata.tables.bib IS 'Bibliography reference' ;
COMMENT ON COLUMN rawdata.tables.table_name IS 'Rawdata table name' ;
COMMENT ON COLUMN rawdata.tables.datatype IS 'Types of the data (regular,reprocessing,preliminary,compilation)' ;

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
CREATE UNIQUE INDEX ON rawdata.objects (object_id);

COMMENT ON TABLE rawdata.objects IS 'Table to store processed objects and their metadata';
COMMENT ON COLUMN rawdata.objects.table_id IS 'Reference to the original table';
COMMENT ON COLUMN rawdata.objects.object_id IS 'Identifier for the object within the original table';
COMMENT ON COLUMN rawdata.objects.status IS 'Status of the processing';
COMMENT ON COLUMN rawdata.objects.data IS 'Homogeneous data about the object';
COMMENT ON COLUMN rawdata.objects.metadata IS 'Metadata related to the processing steps';

COMMIT ;
