BEGIN ;

DROP SCHEMA IF EXISTS geometry CASCADE ;

---------------------------------------------------
-------- Geometry catalog (level 1) ---------------
CREATE SCHEMA geometry ;
COMMENT ON SCHEMA geometry	IS 'Geometry catalog (size & position angle)' ;

-----------------------------------------------------
-- Equivalent diameter catalog (measurements in the circular apertures)
--   Dequv = sqrt( ab ) 
-- Ellise approximaiton (a,b,pa)
--
-- Measurement methods
--   Sigma
--   FHWM
--
-- Isophotal diameters (ellipse approximaiton)
-- Mehtods:
--   Visual
--   Iso
-----------------------------------------------------

-------- Geometry aperture shape  -------------
CREATE TABLE geometry.shape (
  id	text	PRIMARY KEY
, description	text	NOT NULL
) ;

COMMENT ON TABLE geometry.shape	IS 'Aperture shape' ;
COMMENT ON COLUMN geometry.shape.id	IS 'Aperture shape ID' ;
COMMENT ON COLUMN geometry.shape.description	IS 'Aperture shape description' ;

INSERT INTO geometry.shape (id,description) VALUES 
  ( 'slice'   , 'Slice along an axis' )
, ( 'circle'  , 'Circular aperture' )
, ( 'ellipse' , 'Elliptical approximaiton' )
;


-------- Geometry measurement method  -------------
CREATE TABLE geometry.method (
  id	text	PRIMARY KEY
, description	text	NOT NULL
) ;

COMMENT ON TABLE geometry.method	IS 'Geometry measurement method' ;
COMMENT ON COLUMN geometry.method.id	IS 'Method ID' ;
COMMENT ON COLUMN geometry.method.description	IS 'Method description' ;

INSERT INTO geometry.method (id,description) VALUES 
  ( 'Sigma' , 'Diameter=2*Sigma of the spatial dispersion of the object profile' )
, ( 'FWHM' , 'FWHM' )

, ( 'Kron' , 'Kron (1980, ApJS, 43, 305) diameter' )
, ( 'Petro', 'Petrosian diameter' )

, ( 'Total' , 'Diameter containing specific fraction of the total light. The fraction is 0.5 for the effective or half-light diameter' )
, ( 'Model' , 'Half-light diameter of the image fit' )
, ( 'Visual' , 'Visual estimates of the geometry' )

, ( 'Iso'  , 'Isophotal diameter' )
;


-------- Geometry Dataset ----------------------------------
CREATE TABLE geometry.dataset (
  id	serial	PRIMARY KEY
, shape	text	REFERENCES geometry.shape (id )	ON DELETE restrict ON UPDATE cascade
, method	text	NOT NULL	REFERENCES geometry.method (id )	ON DELETE restrict ON UPDATE cascade
, src	integer	REFERENCES rawdata.tables (id )	ON DELETE restrict ON UPDATE cascade
, datatype	text	REFERENCES common.datatype (id )	ON DELETE restrict ON UPDATE cascade
) ;

COMMENT ON TABLE geometry.dataset	IS 'Dataset' ;
COMMENT ON COLUMN geometry.dataset.id	IS 'Dataset ID' ;
COMMENT ON COLUMN geometry.dataset.method	IS 'Measurement method' ;
COMMENT ON COLUMN geometry.dataset.shape	IS 'Aperture shape' ;
COMMENT ON COLUMN geometry.dataset.src	IS 'Source table' ;
COMMENT ON COLUMN geometry.dataset.datatype	IS 'Type of the data (reguliar,reprocessing,preliminary,compilation)' ;


--- Geometry measurement table ----------
CREATE TABLE geometry.data (
  id	serial	PRIMARY KEY
, pgc	integer	NOT NULL	REFERENCES common.pgc (id )	ON DELETE restrict ON UPDATE cascade
, band	integer	REFERENCES common.calibpassband (id)	ON DELETE restrict ON UPDATE cascade
, quality	smallint	NOT NULL	REFERENCES common.quality (id)	ON DELETE restrict ON UPDATE cascade	DEFAULT 0   -- default 0 = reguliar measurement
, dataset	integer	NOT NULL	REFERENCES cz.dataset (id)	ON DELETE restrict ON UPDATE cascade
, modification_time	timestamp without time zone	NOT NULL	DEFAULT now()
) ;

COMMENT ON TABLE geometry.data	IS 'Geometry catalog' ;
COMMENT ON COLUMN geometry.data.id	IS 'Measurement ID' ;
COMMENT ON COLUMN geometry.data.pgc	IS 'PGC number of the object' ;
COMMENT ON COLUMN geometry.data.band	IS 'Passband ID' ;
COMMENT ON COLUMN geometry.data.quality	IS 'Measurement quality: 0 - reguliar, 1 - low S/N, 2 - suspected, 5 -wrong' ;
COMMENT ON COLUMN geometry.data.dataset	IS 'Dataset of the measurements' ;
COMMENT ON COLUMN geometry.data.modification_time	IS 'Timestamp when the record was added to the database' ;


--- Measurements in the Circular apertures ----------
CREATE TABLE geometry.circle (
, a	real	NOT NULL
, e_a	real
, PRIMARY KEY (id)
, UNIQUE (pgc,quality,band,a,dataset)
) INHERITS (geometry.data) ;
CREATE INDEX ON geometry.circle (dataset) ;

COMMENT ON TABLE geometry.circle	IS 'Equivalent diameter table (measurements in the circular apertures)' ;
COMMENT ON COLUMN geometry.circle.id	IS 'Measurement ID' ;
COMMENT ON COLUMN geometry.circle.pgc	IS 'PGC number of the object' ;
COMMENT ON COLUMN geometry.circle.band	IS 'Passband ID' ;
COMMENT ON COLUMN geometry.circle.quality	IS 'Measurement quality: 0 - reguliar, 1 - low S/N, 2 - suspected, 5 -wrong' ;
COMMENT ON COLUMN geometry.circle.dataset	IS 'Dataset of the measurements' ;
COMMENT ON COLUMN geometry.circle.modification_time	IS 'Timestamp when the record was added to the database' ;
COMMENT ON COLUMN geometry.circle.a	IS '{"description" : "Equivalent diameter", "unit" : "arcsec", "ucd" : "phys.angSize"}' ;
COMMENT ON COLUMN geometry.circle.e_a	IS '{"description" : "Error of the equavalent diameter", "unit" : "arcsec", "ucd" : "stat.error"}' ; ;


--- Measurements in the Ellipses or in the Slices ----------
CREATE TABLE geometry.ellipse (
, a	real	NOT NULL
, e_a	real
, b	real	NOT NULL
, e_p	real
, pa	real	NOT NULL
, e_pa	real
, PRIMARY KEY (id)
, UNIQUE (pgc,quality,band,a,b,pa,dataset)
) INHERITS (geometry.data) ;
CREATE INDEX ON geometry.ellipse (dataset) ;

COMMENT ON TABLE geometry.ellipse	IS 'Geometry table' ;
COMMENT ON COLUMN geometry.ellipse.id	IS 'Measurement ID' ;
COMMENT ON COLUMN geometry.ellipse.pgc	IS 'PGC number of the object' ;
COMMENT ON COLUMN geometry.ellipse.band	IS 'Passband ID' ;
COMMENT ON COLUMN geometry.ellipse.quality	IS 'Measurement quality: 0 - reguliar, 1 - low S/N, 2 - suspected, 5 -wrong' ;
COMMENT ON COLUMN geometry.ellipse.dataset	IS 'Dataset of the measurements' ;
COMMENT ON COLUMN geometry.ellipse.modification_time	IS 'Timestamp when the record was added to the database' ;
COMMENT ON COLUMN geometry.ellipse.a	IS '{"description" : "Major axis diameter", "unit" : "arcsec", "ucd" : "phys.angSize"}' ;
COMMENT ON COLUMN geometry.ellipse.e_a	IS '{"description" : "Error of the major axis diameter", "unit" : "arcsec", "ucd" : "stat.error"}' ; ;
COMMENT ON COLUMN geometry.ellipse.b	IS '{"description" : "Minor axis diameter", "unit" : "arcsec", "ucd" : "phys.angSize"}' ;
COMMENT ON COLUMN geometry.ellipse.e_b	IS '{"description" : "Error of the minor exis diameter", "unit" : "arcsec", "ucd" : "stat.error"}' ; ;
COMMENT ON COLUMN geometry.ellipse.pa     IS 'Position angle from North to East from 0 to 180 [degrees]' ;
COMMENT ON COLUMN geometry.ellipse.e_pa   IS 'Error of the position angle [degrees]' ;


--- Measurements in the Ellipses or in the Slices ----------
CREATE TABLE geometry.isophote (
  iso	real	NOT NULL
, PRIMARY KEY (id)
, UNIQUE (pgc,quality,band,a,b,pa,iso,dataset)
) INHERITS (geometry.ellipse) ;
CREATE INDEX ON geometry.isophote (dataset) ;

COMMENT ON TABLE geometry.isophote	IS 'Geometry table' ;
COMMENT ON COLUMN geometry.isophote.id	IS 'Measurement ID' ;
COMMENT ON COLUMN geometry.isophote.pgc	IS 'PGC number of the object' ;
COMMENT ON COLUMN geometry.isophote.band	IS 'Passband ID' ;
COMMENT ON COLUMN geometry.isophote.quality	IS 'Measurement quality: 0 - reguliar, 1 - low S/N, 2 - suspected, 5 -wrong' ;
COMMENT ON COLUMN geometry.isophote.dataset	IS 'Dataset of the measurements' ;
COMMENT ON COLUMN geometry.isophote.modification_time	IS 'Timestamp when the record was added to the database' ;
COMMENT ON COLUMN geometry.isophote.a	IS '{"description" : "Major axis diameter", "unit" : "arcsec", "ucd" : "phys.angSize"}' ;
COMMENT ON COLUMN geometry.isophote.e_a	IS '{"description" : "Error of the major axis diameter", "unit" : "arcsec", "ucd" : "stat.error"}' ; ;
COMMENT ON COLUMN geometry.isophote.b	IS '{"description" : "Minor axis diameter", "unit" : "arcsec", "ucd" : "phys.angSize"}' ;
COMMENT ON COLUMN geometry.isophote.e_b	IS '{"description" : "Error of the minor exis diameter", "unit" : "arcsec", "ucd" : "stat.error"}' ; ;
COMMENT ON COLUMN geometry.isophote.pa     IS 'Position angle from North to East from 0 to 180 [degrees]' ;
COMMENT ON COLUMN geometry.isophote.e_pa   IS 'Error of the position angle [degrees]' ;
COMMENT ON COLUMN geometry.isophote.iso     IS 'Isophote level [mag arcsec^-2]' ;


COMMIT ;