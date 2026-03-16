BEGIN;

--------------------------------------------------
-- The schema is based on two object type schemas:
-- SIMBAD Object types: https://simbad.cds.unistra.fr/Pages/guide/otypes.htx
-- HyperLeda nature of objects: http://atlas.obs-hp.fr/hyperleda/a115/
--------------------------------------------------


CREATE TABLE nature.datasets (
  id Integer PRIMARY KEY; 
, table_id Integer NOT NULL REFERENCES layer0.tables (id) ON DELETE restrict ON UPDATE cascade
, column_name Text NOT NULL
, datatype Common.DataType NOT NULL
) ;


CREATE VIEW nature.dataview AS
SELECT
  r.pgc
, d.objtype
, c.objclass
, c.description

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
  nature.data AS d 
  LEFT JOIN nature.objectType AS c ON (d.objtype = c.objtype) 
  LEFT JOIN nature.datasets  AS s ON (d.dataset_id = s.id )
  LEFT JOIN layer0.records AS r ON (d.record_id = r.id )
  LEFT JOIN layer0.tables  AS t ON (d.table_id = t.id )
  LEFT JOIN common.bib AS b ON (t.bib = b.id )
;

COMMIT;
