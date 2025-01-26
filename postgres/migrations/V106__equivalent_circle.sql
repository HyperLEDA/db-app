/* pgmigrate-encoding: utf-8 */

BEGIN ;
------------------------------------------------------------------
--------      Equivalent Circle catalog (level 1)      -----------
------------------------------------------------------------------


DROP SCHEMA IF EXISTS equivCircle CASCADE ;

CREATE SCHEMA equivCircle ;
COMMENT ON SCHEMA equivCircle	IS 'Equivalent Circle catalog' ;


------ Circle shape --------
CREATE TABLE equivCircle.circle (
  pgc	integer	NOT NULL	REFERENCES common.pgc (id )	ON DELETE restrict ON UPDATE cascade
, dataset	integer	NOT NULL	REFERENCES photometry.dataset (id)	ON DELETE restrict ON UPDATE cascade
, band	integer	REFERENCES common.calibpassband (id)	ON DELETE restrict ON UPDATE cascade
, a	real	NOT NULL	CHECK (a>0)
, e_a	real	CHECK (e_a>0)
, quality	common.quality	NOT NULL	DEFAULT 'ok'
, modification_time	timestamp without time zone	NOT NULL	DEFAULT now()
, PRIMARY KEY (pgc,dataset,band)
) ;

COMMENT ON TABLE equivCircle.circle	IS 'Equivalent Circle' ;
COMMENT ON COLUMN equivCircle.circle.pgc	IS 'PGC number of the object' ;
COMMENT ON COLUMN equivCircle.circle.dataset	IS 'Dataset of the measurements' ;
COMMENT ON COLUMN equivCircle.circle.band	IS 'Passband ID' ;
COMMENT ON COLUMN equivCircle.circle.a	IS 'Circle diameter [arcsec]' ;
COMMENT ON COLUMN equivCircle.circle.e_a	IS 'Error of the diameter [arcsec]' ;
COMMENT ON COLUMN equivCircle.circle.quality	IS 'Measurement quality' ;
COMMENT ON COLUMN equivCircle.circle.modification_time	IS 'Timestamp when the record was added to the database' ;


------ Equivalent circle corresponding to the specific total flux level --------
CREATE TABLE equivCircle.fluxLevelCircle (
  phot	bigint	NOT NULL	REFERENCES photometry.data (id)	ON DELETE restrict	ON UPDATE cascade
, level	real	NOT NULL	CHECK (level>0 and level<100)
, a	real	NOT NULL	CHECK (a>0)
, e_a	real	CHECK (e_a>0)
, UNIQUE (phot,level)
) ;

COMMENT ON TABLE equivCircle.fluxLevelCircle	IS 'Equivalent Circle at specific flux level' ;
COMMENT ON COLUMN equivCircle.fluxLevelCircle.phot	IS 'Totoal magnitude ID' ;
COMMENT ON COLUMN equivCircle.fluxLevelCircle.level	IS 'Level of the total flux [percent]' ;
COMMENT ON COLUMN equivCircle.fluxLevelCircle.a	IS 'Circle diameter [arcsec]' ;
COMMENT ON COLUMN equivCircle.fluxLevelCircle.e_a	IS 'Error of the diameter [arcsec]' ;


------ Data Collection --------
CREATE VIEW equivCircle.data AS
SELECT
  mag.pgc
, mag.dataset
, ds.method
, mag.band
, circ.level
, circ.a
, circ.e_a
, mag.quality
, mag.modification_time
, ds.src
, src.bib
, src.datatype
, src.table_name
FROM
  equivCircle.fluxLevelCircle	AS circ
  LEFT JOIN photometry.data	AS mag	ON (circ.phot=mag.id)
  LEFT JOIN photometry.dataset	AS ds	ON (mag.dataset=ds.id)
  LEFT JOIN rawdata.tables	AS src	ON (ds.src=src.id)

UNION

SELECT
  circ.pgc
, circ.dataset
, ds.method
, circ.band
, NULL::real	AS level
, circ.a
, circ.e_a
, circ.quality
, circ.modification_time
, ds.src
, src.bib
, src.datatype
, src.table_name
FROM
  equivCircle.circle	AS circ
  LEFT JOIN photometry.dataset	AS ds	ON (circ.dataset=ds.id)
  LEFT JOIN rawdata.tables	AS src	ON (ds.src=src.id)
;

COMMENT ON VIEW equivCircle.data	IS 'Equivalent Circle catalog' ;
COMMENT ON COLUMN equivCircle.data.pgc	IS 'PGC number of the object' ;
COMMENT ON COLUMN equivCircle.data.dataset	IS 'Dataset ID' ;
COMMENT ON COLUMN equivCircle.data.method	IS 'Photometry measurement method' ;
COMMENT ON COLUMN equivCircle.data.band	IS 'Passband ID' ;
COMMENT ON COLUMN equivCircle.data.level	IS 'Level of the total flux [percent]' ;
COMMENT ON COLUMN equivCircle.data.a	IS 'Circle diameter [arcsec]' ;
COMMENT ON COLUMN equivCircle.data.e_a	IS 'Error of the diameter [arcsec]' ;
COMMENT ON COLUMN equivCircle.data.quality	IS 'Measurement quality' ;
COMMENT ON COLUMN equivCircle.data.modification_time	IS 'Timestamp when the record was added to the database' ;
COMMENT ON COLUMN equivCircle.data.src	IS 'Source table ID' ;
COMMENT ON COLUMN equivCircle.data.bib	IS 'Bibliography reference ID' ;
COMMENT ON COLUMN equivCircle.data.datatype	IS 'Types of the data (regular,reprocessing,preliminary,compilation)' ;
COMMENT ON COLUMN equivCircle.data.table_name	IS 'Source table name' ;


COMMIT ;
