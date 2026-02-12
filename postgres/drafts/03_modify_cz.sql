BEGIN;

-- CREATE TYPE cz.DimentionType AS ENUM (0, 1, 2) ;
-- COMMENT ON TYPE cz.DimentionType IS '0 corresponds to a beam/fiber, 1 corresponds to a long-slit, 2 corresponds to panoramic spectroscopy ' ;

CREATE TYPE cz.MethodType AS ENUM ('average','emission','absorption','xcorr','fit','photoz') ;

COMMENT ON TYPE cz.MethodType IS '{ 
"average": "Average of measurements of membersi",
"emission": "Emission lines",
"absorption": "Absorption lines",
"xcorr": "Cross correlation",
"fit": "Stellar populations fit",
"photoz": "Photometric redshift"
}' ;


CREATE TABLE cz.datasets (
  id Integer PRIMARY KEY; 
, table_id Integer NOT NULL REFERENCES layer0.tables (id) ON DELETE restrict ON UPDATE cascade
, column_name Text NOT NULL
, datatype Common.DataType NOT NULL
, method cz.MethodType
) ;

ALTER TABLE cz.data
ADD COLUMN quality Common.Quality NOT NULL,
ADD COLUMN dataset_id Integer NOT NULL REFERENCES cz.datasets(id) ON DELETE restrict ON UPDATE cascade,
DROP COLUMN modification_time ;

CREATE VIEW cz.dataview AS
SELECT
  r.pgc
, d.cz
, d.e_cz
, d.quality
, s.datatype

, s.method

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
  cz.data AS d 
  LEFT JOIN cz.datasets  AS s ON (d.dataset_id = s.id )
  LEFT JOIN layer0.records AS r ON (d.record_id = r.id )
  LEFT JOIN layer0.tables  AS t ON (d.table_id = t.id )
  LEFT JOIN common.bib AS b ON (t.bib = b.id )
;

COMMIT;
