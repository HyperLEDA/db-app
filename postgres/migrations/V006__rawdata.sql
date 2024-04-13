/* pgmigrate-encoding: utf-8 */

BEGIN ;

DROP SCHEMA IF EXISTS rawdata CASCADE ;

-----------------------------------------------------------
-------- Raw data -----------------------------------------
CREATE SCHEMA rawdata;

COMMENT ON SCHEMA rawdata IS 'Container for the orginal tables from different sources' ;


-----------------------------------------------------------
-------- Data processing Status ---------------------------
CREATE TABLE rawdata.status (
  id	text	PRIMARY KEY
, description	text	NOT NULL	UNIQUE
) ;

COMMENT ON TABLE rawdata.status IS 'Data processing status' ;
COMMENT ON COLUMN rawdata.status.id IS 'Status ID' ;
COMMENT ON COLUMN rawdata.status.description IS 'Status description' ;

INSERT INTO rawdata.status VALUES
  ( 'initiated' , 'Structure is initiated' )
, ( 'downloading' , 'Data downloading' )
, ( 'failed' , 'Data downloading is failed' )
, ( 'downloaded' , 'Data are downloaded' )
, ( 'auto x-id' , 'Automatic cross-identification' )
, ( 'auto xid finished' , 'Manual cross-identification is finished' )
, ( 'manual xid' , 'Automatic cross-identification' )
, ( 'processed' , 'Table is processed' )
;


-----------------------------------------------------------
-------- List of source data tables -----------------------
CREATE TABLE rawdata.tables (
  id	serial	PRIMARY KEY
, bib	integer	NOT NULL	REFERENCES common.bib(id)	ON DELETE restrict ON UPDATE cascade
, table_name	text	NOT NULL	UNIQUE
, datatype	text	REFERENCES common.datatype (id)	ON DELETE restrict ON UPDATE cascade
, status	text	NOT NULL	REFERENCES rawdata.status (id)	ON DELETE restrict ON UPDATE cascade	DEFAULT 'initiated' ;
) ;

COMMENT ON TABLE rawdata.tables IS 'List of original data tables' ;
COMMENT ON COLUMN rawdata.tables.id IS 'Rawdata table ID' ;
COMMENT ON COLUMN rawdata.tables.bib IS 'Bibliography reference' ;
COMMENT ON COLUMN rawdata.tables.table_name IS 'Rawdata table name' ;
COMMENT ON COLUMN rawdata.tables.datatype IS 'Types of the data (reguliar,reprocessing,preliminary,compilation)' ;
COMMENT ON COLUMN rawdata.tables.status IS 'Data processing status' ;



COMMIT ;