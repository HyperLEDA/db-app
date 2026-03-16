BEGIN ;

CREATE OR REPLACE VIEW layer0.recordview AS
SELECT
  r.pgc
, r.id AS record_id
, r.modification_time

, r.table_id
, t.table_name
, t.datatype
, t.status

, t.bib
, b.code AS bibcode
, b.year
, b.author
, b.title
FROM
  layer0.records AS r
  LEFT JOIN layer0.tables AS t ON (r.table_id = t.id)
  LEFT JOIN common.bib AS b ON (t.bib = b.id)
;


ALTER TABLE designation.data DROP COLUMN IF EXISTS modification_time cascade ;

CREATE OR REPLACE VIEW designation.dataview AS
SELECT
  d.design
, r.*
FROM
  designation.data AS d
  LEFT JOIN layer0.recordview AS r USING (record_id)
;


ALTER TABLE icrs.data DROP COLUMN IF EXISTS modification_time cascade ;

CREATE OR REPLACE VIEW icrs.dataview AS
SELECT
  d.ra
, d.dec
, d.e_ra
, d._dec
, r.*
FROM
  icrs.data AS d
  LEFT JOIN layer0.recordview AS r USING (record_id)
;


CREATE OR REPLACE VIEW nature.dataview AS
SELECT
  d.type_name
, r.*
FROM
  nature.data AS d
  LEFT JOIN layer0.recordview AS r USING (record_id)
;


CREATE OR REPLACE VIEW layer2.designations AS
SELECT
  r.pgc
, d.design
, r.bib
, r.code AS bibcode
, r.year
, r.author
, r.title
FROM
  designation.data AS d 
  LEFT JOIN layer0.recordview AS r USING (record_id)
WHERE
  r.pgc IS NOT NULL
;

COMMIT ;