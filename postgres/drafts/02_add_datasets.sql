BEGIN;

--------------------------------------
-- ICRS: datasets is pretty simple
-- Probably, it is necessary to add a field "spectral range" (optical, X-ray, radio, etc.)
--------------------------------------

CREATE TABLE icrs.datasets (
  id Integer PRIMARY KEY
, table_id Integer NOT NULL REFERENCES layer0.tables (id) ON DELETE restrict ON UPDATE cascade
, column_name Text NOT NULL
, datatype Common.DataType NOT NULL
) ;

ALTER TABLE icrs.data
ADD COLUMN dataset_id Integer NOT NULL REFERENCES icrs.datasets(id) ON DELETE restrict ON UPDATE cascade,
DROP COLUMN modification_time ;

CREATE VIEW icrs.dataview AS
SELECT
  r.pgc
, d.ra
, d.e_ra
, d.dec
, d.e_dec
, s.datatype

, d.record_id
, d.dataset_id
, s.table_id
, t.table_name
, s.column_name

, b.code
, b.year 
, b.author
, b.title

, r.modification_time
FROM
  icrs.data AS d 
  LEFT JOIN icrs.datasets  AS s ON (d.dataset_id = s.id )
  LEFT JOIN layer0.records AS r ON (d.record_id = r.id )
  LEFT JOIN layer0.tables  AS t ON (d.table_id = t.id )
  LEFT JOIN common.bib AS b ON (t.bib = b.id )
;

COMMIT;