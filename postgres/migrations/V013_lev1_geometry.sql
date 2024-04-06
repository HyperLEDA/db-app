BEGIN ;

DROP SCHEMA IF EXISTS geometry CASCADE ;

---------------------------------------------------
-------- Geometry catalog (level 1) ---------------

CREATE SCHEMA geometry ;

COMMENT ON SCHEMA geometry IS 'Geometry catalog (size & position angle)' ;


---------------------------------------------------
-------- Geometry measurement method  -------------
CREATE TABLE geometry.method (
  id	text	PRIMARY KEY
, description	text	NOT NULL
) ;

COMMENT ON TABLE geometry.method IS 'Geometry measurement method' ;
COMMENT ON COLUMN geometry.method.id IS 'Method ID' ;
COMMENT ON COLUMN geometry.method.description IS 'Method description' ;

INSERT INTO geometry.method (id,description) VALUES 
  ( 'Flux' , 'Diameter containing specific fraction of the total light. The fraction is 0.5 for the effective or half-light diameter' )
, ( 'Sigma' , 'Diameter=2*Sigma of the spatial dispersion of the object profile' )
, ( 'FWHM' , 'FWHM' )
, ( 'Kron' , 'Kron (1980, ApJS, 43, 305) diameter' )
, ( 'Petro' , 'Petrosian diameter' )
, ( 'Iso' , 'Isophotal diameter' )
, ( 'Model', 'Half-light diameter of the image fit' )
;


-- CREATE TABLE geometry.shape (
--   id	text	PRIMARY KEY
-- , description	text	NOT NULL
-- ) ;
-- 
-- COMMENT ON TABLE geometry.shape IS 'Aperture shape' ;
-- COMMENT ON COLUMN geometry.shape.id IS 'Shape ID' ;
-- COMMENT ON COLUMN geometry.shape.description IS 'Shape description' ;
-- 
-- INSERT INTO geometry.shape (id,description) VALUES 
--   ( 'circle' , 'Circular aperture' )
-- , ( 'ellipse' , 'Elliptical approximaiton' )
-- ;


---------------------------------------------------
-------- Dataset ----------------------------------
CREATE TABLE geometry.dataset (
  id	serial	PRIMARY KEY
, datatype	text	REFERENCES common.datatype (id )	ON DELETE restrict ON UPDATE cascade
, method	text	NOT NULL	REFERENCES geometry.method (id )	ON DELETE restrict ON UPDATE cascade
, level	real	CHECK ( (method='Flux' and level>0 and level<1) or (method='Iso' and level>20) )
, model	text
, bib	integer	NOT NULL	REFERENCES common.bib ( id )	ON DELETE restrict ON UPDATE cascade
, srctab	text
) ;

COMMENT ON TABLE geometry.dataset IS 'Dataset' ;
COMMENT ON COLUMN geometry.dataset.id IS 'Dataset ID' ;
COMMENT ON COLUMN geometry.dataset.datatype IS 'Type of the data (reguliar,reprocessing,preliminary,compilation)' ;
COMMENT ON COLUMN geometry.dataset.method IS 'Measurement method' ;
COMMENT ON COLUMN geometry.dataset.level IS ;
COMMENT ON COLUMN geometry.dataset.shape IS ;
COMMENT ON COLUMN geometry.dataset.bib IS 'Bibliography reference' ;
COMMENT ON COLUMN geometry.dataset.srctab IS 'Source table' ;  -- Maybe it is better to create the registry for all downloaded tables and reffer ther src id?


------------------------------------------
--- Geometry measurement table ----------

CREATE TABLE geometry.data (
  id	serial	PRIMARY KEY
, pgc	integer	NOT NULL	REFERENCES common.pgc (id )	ON DELETE restrict ON UPDATE cascade
, a	real	NOT NULL
, e_a	real
, b	real
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

COMMENT ON TABLE geometry.data IS 'Redshift measurement catalog' ;
COMMENT ON COLUMN geometry.data.id IS 'ID of the measurement' ;
COMMENT ON COLUMN geometry.data.pgc IS 'PGC number of the object' ;
COMMENT ON COLUMN geometry.data.cz IS 'Heliocentric/Barycentric redshift (cz) in km/s in the optical convention: z = (λ-λ0)/λ0' ;
COMMENT ON COLUMN geometry.data.e_cz IS 'cz measurement error in km/s' ;
COMMENT ON COLUMN geometry.data.quality IS 'Measurement quality: 0 - reguliar, 1 - low S/N, 2 - suspected, 5 -wrong' ;
COMMENT ON COLUMN geometry.data.dataset IS 'Dataset of the measurements' ;
COMMENT ON COLUMN geometry.data.modification_time IS 'Timestamp when the record was added to the database' ;


COMMIT ;