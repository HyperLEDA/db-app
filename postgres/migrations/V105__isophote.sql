BEGIN ;
------------------------------------------------------------------
--------      Isophote photometry catalog (level 1)      ---------
------------------------------------------------------------------
-- Isophote:
--	-> Mag
--	-> Ellipse
------------------------------------------------------------------

DROP SCHEMA IF EXISTS isophote CASCADE ;

CREATE SCHEMA isophote ;
COMMENT ON SCHEMA isophote	IS 'Isophote Photometry catalog' ;


----------------------------------------
CREATE TABLE isophote.data (
  pgc	integer	NOT NULL	REFERENCES common.pgc (id)	ON DELETE restrict	ON UPDATE cascade
, dataset	integer	NOT NULL	REFERENCES rawdata.tables (id)	ON DELETE restrict	ON UPDATE cascade
, band	integer	NOT NULL	REFERENCES common.calibpassband (id)	ON DELETE restrict	ON UPDATE cascade
, iso	real	NOT NULL	CHECK (iso>0 and iso<30)
, mag	real	NOT NULL	CHECK (mag>0 and mag<30)
, e_mag	real
, a	real	NOT NULL
, e_a	real
, b	real	NOT NULL
, e_b	real
, pa	real	NOT NULL
, e_pa	real
, quality	common.quality	NOT NULL	DEFAULT 'ok'
, modification_time	timestamp without time zone	NOT NULL	DEFAULT now()
, PRIMARY KEY (pgc,dataset,band,iso,quality)
) ;

COMMENT ON TABLE isophote.data	IS 'Isophotal Photometry' ;
COMMENT ON COLUMN isophote.data.pgc	IS 'PGC number of the object' ;
COMMENT ON COLUMN isophote.data.dataset	IS 'Dataset' ;
COMMENT ON COLUMN isophote.data.band	IS 'Bandpass ID' ;
COMMENT ON COLUMN isophote.data.iso	IS 'Threshold isophote level [mag]' ;
COMMENT ON COLUMN isophote.data.mag	IS 'Isophotal magnitude [mag]' ;
COMMENT ON COLUMN isophote.data.e_mag	IS 'Error of the isophotal magnitude [mag]' ;
COMMENT ON COLUMN isophote.data.a	IS 'Isophotal major diameter [arcsec]' ;
COMMENT ON COLUMN isophote.data.e_a	IS 'Error of the major diameter [arcsec]' ;
COMMENT ON COLUMN isophote.data.b	IS 'Isophotal minor diameter [arcsec]' ;
COMMENT ON COLUMN isophote.data.e_b	IS 'Error of the minor diameter [arcsec]' ;
COMMENT ON COLUMN isophote.data.pa	IS 'Position angle from North to East from 0 to 180 [degrees]' ;
COMMENT ON COLUMN isophote.data.e_pa	IS 'Error of the position angle [degrees]' ;
COMMENT ON COLUMN isophote.data.quality	IS 'Measurement quality' ;
COMMENT ON COLUMN isophote.data.modification_time	IS 'Timestamp when the record was added to the database' ;

COMMIT ;
