/* pgmigrate-encoding: utf-8 */

CREATE TABLE common.pgc (
  id serial PRIMARY KEY
);

COMMENT ON TABLE common.pgc     IS 'The list of existing PGC-numbers' ;
COMMENT ON COLUMN common.pgc.id IS 'Unique PGC-number' ;

ALTER TABLE rawdata.objects 
ADD COLUMN pgc integer REFERENCES common.pgc (id) ON DELETE restrict ON UPDATE cascade,
ADD COLUMN modification_time timestamp without time zone ;

COMMENT ON TABLE rawdata.objects IS 'The registry of all objects in original data tables' ;
COMMENT ON COLUMN rawdata.objects.id  IS 'The record id' ;
COMMENT ON COLUMN rawdata.objects.table_id IS 'The table in which the record is located' ;
COMMENT ON COLUMN rawdata.objects.pgc IS 'Crossidentification of the record with the PGC-number' ;
COMMENT ON COLUMN rawdata.objects.modification_time IS 'Time of PGC-number assignment to the record' ;

INSERT INTO common.pgc (id)
SELECT id 
FROM rawdata.pgc 
ORDER BY rawdata.pgc.id;

ALTER SEQUENCE common.pgc_id_seq RESTART WITH 6775395 ;

UPDATE rawdata.objects
SET
  pgc=rawdata.pgc.id
FROM rawdata.pgc
WHERE 
  rawdata.pgc.object_id=rawdata.objects.id
;
