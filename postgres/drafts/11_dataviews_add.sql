BEGIN ;

CREATE OR REPLACE VIEW dataviews.recordview AS
SELECT
  r.pgc
, r.id AS record_id
, r.modification_time

, r.table_id
, t.table_name
, t.datatype
, t.status

, t.bib
, b.code
, b.year
, b.author
, b.title
FROM
  layer0.records AS r
  LEFT JOIN layer0.tables AS t ON (r.table_id = t.id)
  LEFT JOIN common.bib AS b ON (t.bib = b.id)
;


-- ALTER TABLE designation.data DROP COLUMN IF EXISTS modification_time cascade ;

CREATE OR REPLACE VIEW dataviews.designation AS
SELECT
  d.design
, r.*
FROM
  designation.data AS d
  LEFT JOIN dataviews.recordview AS r USING (record_id)
;


-- ALTER TABLE icrs.data DROP COLUMN IF EXISTS modification_time cascade ;

CREATE OR REPLACE VIEW dataviews.icrs AS
SELECT
  d.ra
, d.dec
, d.e_ra
, d.e_dec
, r.*
FROM
  icrs.data AS d
  LEFT JOIN dataviews.recordview AS r USING (record_id)
;


CREATE OR REPLACE VIEW dataviews.nature AS
SELECT
  d.type_name
, r.*
FROM
  nature.data AS d
  LEFT JOIN dataviews.recordview AS r USING (record_id)
;


CREATE OR REPLACE VIEW dataviews.cz AS
SELECT
  d.cz
, d.e_cz
, r.*
FROM
  cz.data AS d
  LEFT JOIN dataviews.recordview AS r USING (record_id)
;


CREATE OR REPLACE VIEW dataviews.total_mag AS
SELECT
  d.band
, d.mag
, d.e_mag
, d.method
, r.*
FROM
  photometry.data AS d
  LEFT JOIN dataviews.recordview AS r USING (record_id)
;


-- ROLLBACK ;
COMMIT ;
