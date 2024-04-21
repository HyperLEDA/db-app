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
, bib	integer	NOT NULL	REFERENCES common.bib(id)	ON DELETE restrict ON UPDATE cascade
, table_name	text	NOT NULL	UNIQUE
, datatype	common.datatype	NOT NULL
, status	rawdata.status NOT NULL DEFAULT 'initiated'
);

COMMENT ON TABLE rawdata.tables IS 'List of original data tables' ;
COMMENT ON COLUMN rawdata.tables.id IS 'Rawdata table ID' ;
COMMENT ON COLUMN rawdata.tables.bib IS 'Bibliography reference' ;
COMMENT ON COLUMN rawdata.tables.table_name IS 'Rawdata table name' ;
COMMENT ON COLUMN rawdata.tables.datatype IS 'Types of the data (regular,reprocessing,preliminary,compilation)' ;
COMMENT ON COLUMN rawdata.tables.status IS 'Data processing status' ;



COMMIT ;