BEGIN ;

DROP SCHEMA IF EXISTS photometry CASCADE ;

-----------------------------------------------------
-------- Photometry catalog (level 1) ---------------
CREATE SCHEMA photometry ;
COMMENT ON SCHEMA photometry	IS 'Photometry catalog (visual magnitudes)' ;

-----------------------------------------------------
-- Total flux methods:
--   Visual
--   Total (asymptotic, extrapolated)
--   Model
--
-- Isophotal flux
--   Iso
-----------------------------------------------------

-------- Photometry measurement method --------------
CREATE TABLE photometry.method (
  id	text	PRIMARY KEY
, description	text	NOT NULL
) ;

COMMENT ON TABLE photometry.method	IS 'Photometry measurement method' ;
COMMENT ON COLUMN photometry.method.id	IS 'Method ID' ;
COMMENT ON COLUMN photometry.method.description	IS 'Method description' ;

INSERT INTO photometry.method (id,description) VALUES 
  ( 'Visual' , 'Visual estimate of the total magnitude' )
, ( 'Total' , 'Asymptotic (extrapolated) magnitude' )
, ( 'Model' , 'Model best fit magnitude' )
, ( 'Kron' , 'Kron magnitude' )
, ( 'Petro' , 'Petrosian magnitude' )
, ( 'Iso'  , 'Isophotal magnitude' )
, ( 'Aper' , 'Aperture photometry' )
;

-------- Photometry Dataset -------------------------
CREATE TABLE photometry.dataset (
  id	serial	PRIMARY KEY
, method	text	NOT NULL	REFERENCES photometry.method (id )	ON DELETE restrict ON UPDATE cascade
, src	integer	REFERENCES rawdata.tables (id )	ON DELETE restrict ON UPDATE cascade
, datatype	text	REFERENCES common.datatype (id )	ON DELETE restrict ON UPDATE cascade
) ;

COMMENT ON TABLE photometry.dataset	IS 'Dataset' ;
COMMENT ON COLUMN photometry.dataset.id	IS 'Dataset ID' ;
COMMENT ON COLUMN photometry.dataset.method	IS 'Measurement method' ;
COMMENT ON COLUMN photometry.dataset.src	IS 'Source table' ;
COMMENT ON COLUMN photometry.dataset.datatype	IS 'Type of the data (reguliar,reprocessing,preliminary,compilation)' ;


--- Photometry measurement table -----------------------------------
--  it must contains only total, asymptotic, extrapolated values  --
CREATE TABLE photometry.data (
  id	serial	PRIMARY KEY
, pgc	integer	NOT NULL	REFERENCES common.pgc (id )	ON DELETE restrict ON UPDATE cascade
, mag	real	NOT NULL
, e_mag	real
, band	integer	REFERENCES common.calibpassband (id)	ON DELETE restrict ON UPDATE cascade
, quality	common.quality	NOT NULL
, dataset	integer	NOT NULL	REFERENCES photometry.dataset (id)	ON DELETE restrict ON UPDATE cascade
, modification_time	timestamp without time zone	NOT NULL	DEFAULT now()
) ;
CREATE UNIQUE INDEX ON photometry.data (pgc,quality,band,mag,dataset) ;
CREATE INDEX ON photometry.data (dataset) ;

COMMENT ON TABLE photometry.data	IS 'photometry catalog' ;
COMMENT ON COLUMN photometry.data.id	IS 'Measurement ID' ;
COMMENT ON COLUMN photometry.data.pgc	IS 'PGC number of the object' ;
COMMENT ON COLUMN photometry.data.mag	IS '{"description" : "Apparent magnitude", "unit" : "mag", "ucd" : "phot.mag"}' ;
COMMENT ON COLUMN photometry.data.e_mag	IS '{"description" : "Error of the apparent magnitude", "unit" : "mag", "ucd" : "stat.error"}' ;
COMMENT ON COLUMN photometry.data.quality	IS 'Measurement quality' ;
COMMENT ON COLUMN photometry.data.dataset	IS 'Dataset of the measurements' ;
COMMENT ON COLUMN photometry.data.modification_time	IS 'Timestamp when the record was added to the database' ;


--------------------------------------------------------------------
----------  Aperture photometry  -----------------------------------
CREATE TABLE photometry.circAperture (
  id	serial	PRIMARY KEY
, a	real	NOT NULL
, icrs	integer	REFERENCES icrs.data (id)	ON DELETE restrict ON UPDATE cascade
) ;

COMMENT ON TABLE photometry.circAperture	IS 'Circular aperture table' ;
COMMENT ON COLUMN photometry.circAperture.id	IS 'Circular aperture ID' ;
COMMENT ON COLUMN photometry.circAperture.a	IS 'Circular aperture diameter [arcsec]' ;
COMMENT ON COLUMN photometry.circAperture.icrs	IS 'Reference the aperture center' ;



COMMIT ;