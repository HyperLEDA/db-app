BEGIN ;

DROP SCHEMA IF EXISTS geometry CASCADE ;

---------------------------------------------------
-------- Geometry catalog (level 1) ---------------

CREATE SCHEMA geometry ;

COMMENT ON SCHEMA geometry	IS 'Geometry catalog (size & position angle)' ;


---------------------------------------------------
-------- Geometry measurement method  -------------
CREATE TABLE geometry.method (
  id	text	PRIMARY KEY
, description	text	NOT NULL
) ;

COMMENT ON TABLE geometry.method	IS 'Geometry measurement method' ;
COMMENT ON COLUMN geometry.method.id	IS 'Method ID' ;
COMMENT ON COLUMN geometry.method.description	IS 'Method description' ;

INSERT INTO geometry.method (id,description) VALUES 
  ( 'Flux' , 'Diameter containing specific fraction of the total light. The fraction is 0.5 for the effective or half-light diameter' )
, ( 'Sigma' , 'Diameter=2*Sigma of the spatial dispersion of the object profile' )
, ( 'FWHM' , 'FWHM' )
, ( 'Kron' , 'Kron (1980, ApJS, 43, 305) diameter' )
, ( 'Petro', 'Petrosian diameter' )
, ( 'Iso'  , 'Isophotal diameter' )
, ( 'Model', 'Half-light diameter of the image fit' )
;


CREATE TABLE geometry.shape (
  id	text	PRIMARY KEY
, description	text	NOT NULL
) ;

COMMENT ON TABLE geometry.shape	IS 'Aperture shape' ;
COMMENT ON COLUMN geometry.shape.id	IS 'Shape ID' ;
COMMENT ON COLUMN geometry.shape.description	IS 'Shape description' ;

INSERT INTO geometry.shape (id,description) VALUES 
  ( 'slice'   , 'Slice along an axis' )
, ( 'circle'  , 'Circular aperture' )
, ( 'ellipse' , 'Elliptical approximaiton' )
;


---------------------------------------------------
-------- Dataset ----------------------------------
CREATE TABLE geometry.dataset (
  id	serial	PRIMARY KEY
, bib	integer	NOT NULL	REFERENCES common.bib ( id )	ON DELETE restrict ON UPDATE cascade
, datatype	text	REFERENCES common.datatype (id )	ON DELETE restrict ON UPDATE cascade
, srctab	text
, method	text	NOT NULL	REFERENCES geometry.method (id )	ON DELETE restrict ON UPDATE cascade
, level	real	CHECK ( (method='Flux' and level>0 and level<1) or (method='Iso' and level>20) )
, shape	text	REFERENCES geometry.shape (id )	ON DELETE restrict ON UPDATE cascade
) ;

COMMENT ON TABLE geometry.dataset	IS 'Dataset' ;
COMMENT ON COLUMN geometry.dataset.id	IS 'Dataset ID' ;
COMMENT ON COLUMN geometry.dataset.datatype	IS 'Type of the data (reguliar,reprocessing,preliminary,compilation)' ;
COMMENT ON COLUMN geometry.dataset.method	IS 'Measurement method' ;
COMMENT ON COLUMN geometry.dataset.level	IS 'Level of the measurement. For "Flux", it is a fraction of the total flux (level=0.5 for effective or half-light diameter). For "Iso", it is an Isophote level' ;
COMMENT ON COLUMN geometry.dataset.shape	IS 'Aperture shape' ;
COMMENT ON COLUMN geometry.dataset.bib	IS 'Bibliography reference' ;
COMMENT ON COLUMN geometry.dataset.srctab	IS 'Source table' ;  -- Maybe it is better to create the registry for all downloaded tables and reffer ther src id?


------------------------------------------
--- Geometry measurement table ----------

CREATE TABLE geometry.data (
  id	serial	PRIMARY KEY
, pgc	integer	NOT NULL	REFERENCES common.pgc (id )	ON DELETE restrict ON UPDATE cascade
, a	real	NOT NULL
, e_a	real
, b	real	NOT NULL
, e_b	real
, pa	real	CHECK (pa>=0 and pa<180)
, e_pa	real
, band	integer	REFERENCES common.passband (id)	ON DELETE restrict ON UPDATE cascade
, quality	smallint	NOT NULL	REFERENCES common.quality (id)	ON DELETE restrict ON UPDATE cascade
, dataset	integer	NOT NULL	REFERENCES cz.dataset (id)	ON DELETE restrict ON UPDATE cascade
, modification_time	timestamp without time zone	NOT NULL	DEFAULT now()
) ;
CREATE UNIQUE INDEX ON geometry.data (pgc,quality,band,a,b,pa,dataset) ;
CREATE INDEX ON geometry.data (dataset) ;

COMMENT ON TABLE geometry.data	IS 'Geometry catalog' ;
COMMENT ON COLUMN geometry.data.id	IS 'Measurement ID' ;
COMMENT ON COLUMN geometry.data.pgc	IS 'PGC number of the object' ;
COMMENT ON COLUMN geometry.data.a	IS 'Major axis diameter [arcsec]' ;
COMMENT ON COLUMN geometry.data.e_a	IS 'Error of the major axis diameter [arcsec]' ;
COMMENT ON COLUMN geometry.data.b	IS 'Major axis diameter [arcsec]' ;
COMMENT ON COLUMN geometry.data.e_b	IS 'Error of the major axis diameter [arcsec]' ;
COMMENT ON COLUMN geometry.data.pa	IS 'Position angle from North to East from 0 to 180 [degrees]' ;
COMMENT ON COLUMN geometry.data.e_pa	IS 'Error of the position angle [degrees]' ;
COMMENT ON COLUMN geometry.data.quality	IS 'Measurement quality: 0 - reguliar, 1 - low S/N, 2 - suspected, 5 -wrong' ;
COMMENT ON COLUMN geometry.data.dataset	IS 'Dataset of the measurements' ;
COMMENT ON COLUMN geometry.data.modification_time	IS 'Timestamp when the record was added to the database' ;


---------------------------------------------
-- List of excluded measurements ------------
CREATE TABLE geometry.excluded (
  id	integer	PRIMARY KEY	REFERENCES geometry.data (id) ON DELETE restrict ON UPDATE cascade
, bib	integer	NOT NULL	REFERENCES common.bib ( id ) ON DELETE restrict ON UPDATE cascade
, note	text	NOT NULL
, modification_time	timestamp without time zone	NOT NULL	DEFAULT NOW()
) ;

COMMENT ON TABLE geometry.excluded	IS 'List of measurements excluded from consideration' ;
COMMENT ON COLUMN geometry.excluded.id	IS 'measurement ID' ;
COMMENT ON COLUMN geometry.excluded.bib	IS 'Bibliography reference where given measurement was marked as wrong' ;
COMMENT ON COLUMN geometry.excluded.note	IS 'Note on exclusion' ;
COMMENT ON COLUMN geometry.excluded.modification_time	IS 'Timestamp when the record was added to the database' ;



------------------------------------------
--- List of geometry measurements --------
CREATE VIEW geometry.list AS
SELECT
  d.id
, d.pgc
, d.a
, d.e_a
, d.b
, d.e_b
, d.pa
, d.e_pa
, d.band
, d.quality
, d.dataset
, obsol.bib IS NULL and excl.id IS NULL	AS isok
, greatest( d.modification_time, obsol.modification_time, excl.modification_time )	AS modification_time
FROM
  geometry.data AS d
  LEFT JOIN geometry.dataset ON (geometry.dataset.id=d.dataset)
  LEFT JOIN common.obsoleted AS obsol ON (obsol.bib=geometry.dataset.bib)
  LEFT JOIN geometry.excluded AS excl ON (excl.id=d.id)
;

COMMENT ON VIEW geometry.list	IS 'Geometry catalog' ;
COMMENT ON COLUMN geometry.list.id	IS 'Measurement ID' ;
COMMENT ON COLUMN geometry.list.pgc	IS 'PGC number of the object' ;
COMMENT ON COLUMN geometry.list.a	IS 'Major axis diameter [arcsec]' ;
COMMENT ON COLUMN geometry.list.e_a	IS 'Error of the major axis diameter [arcsec]' ;
COMMENT ON COLUMN geometry.list.b	IS 'Major axis diameter [arcsec]' ;
COMMENT ON COLUMN geometry.list.e_b	IS 'Error of the major axis diameter [arcsec]' ;
COMMENT ON COLUMN geometry.list.pa	IS 'Position angle from North to East from 0 to 180 [degrees]' ;
COMMENT ON COLUMN geometry.list.e_pa	IS 'Error of the position angle [degrees]' ;
COMMENT ON COLUMN geometry.list.quality	IS 'Measurement quality: 0 - reguliar, 1 - low S/N, 2 - suspected, 5 -wrong' ;
COMMENT ON COLUMN geometry.list.dataset	IS 'Dataset of the measurements' ;
COMMENT ON COLUMN geometry.list.isok	IS 'True if the measurement is actual and False if it is obsoleted or excluded' ;
COMMENT ON COLUMN geometry.list.modification_time	IS 'Timestamp when the record was added to the database' ;


COMMIT ;