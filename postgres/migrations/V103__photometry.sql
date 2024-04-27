BEGIN ;
------------------------------------------------------------------
--------         Photometry catalog (level 1)            ---------
------------------------------------------------------------------
------------------  Methods  -------------------------------------
--  Visual:
--     -> magVisual
--     -> sizeVisual
--        (in fact, it corresponds to the limiting isophote)
--  Profile: 
--     -> sizeSigma 
--        (1-sigma of the Gaussian light distribution)
--  Total 
--  (Asymptotic extrapolation when aperture size -> Inf) : 
--     -> magTotal -> size%total
--  Model:
--     model -> magModel
--           -> size%model
--  Petrosian: 
--     -> Rpetro -> aperture -> magPetro -> size%petro
--  Kron:
--     -> Rkron -> aperture -> magKron
------------------------------------------------------------------


DROP SCHEMA IF EXISTS photometry CASCADE ;

CREATE SCHEMA photometry ;
COMMENT ON SCHEMA photometry	IS 'Photometry catalog' ;


-------- Photometry measurement method --------------
CREATE TABLE photometry.method (
  id	text	PRIMARY KEY
, description	text	NOT NULL
) ;

COMMENT ON TABLE photometry.method	IS 'Photometry measurement method' ;
COMMENT ON COLUMN photometry.method.id	IS 'Method ID' ;
COMMENT ON COLUMN photometry.method.description	IS 'Method description' ;

INSERT INTO photometry.method (id,description) VALUES 
  ( 'PSF' , 'Point Spread Function photometry' )
, ( 'Vis' , 'Visual estimates' )
, ( 'Sigma' , '1-sigma of the light distribution' )
, ( 'Total' , 'Asymptotic (extrapolated) magnitude' )
, ( 'Model' , 'Best fit model' )
, ( 'Kron' , 'Kron adaptively scaled aperture' )
, ( 'Petro' , 'Petrosian adaptively scaled aperture' )
;


-------- Photometry Dataset -------------------------
CREATE TABLE photometry.dataset (
  id	serial	PRIMARY KEY
, method	text	NOT NULL	REFERENCES photometry.method (id )	ON DELETE restrict ON UPDATE cascade
, src	integer	REFERENCES rawdata.tables (id )	ON DELETE restrict ON UPDATE cascade
) ;
CREATE INDEX ON photometry.dataset (method) ;

COMMENT ON TABLE photometry.dataset	IS 'Dataset' ;
COMMENT ON COLUMN photometry.dataset.id	IS 'Dataset ID' ;
COMMENT ON COLUMN photometry.dataset.method	IS 'Measurement method' ;
COMMENT ON COLUMN photometry.dataset.src	IS 'Source table' ;


------ Total Magnitude ------------------------------
CREATE TABLE photometry.data (
  id	bigserial	PRIMARY KEY
, pgc	integer	NOT NULL	REFERENCES common.pgc (id )	ON DELETE restrict	ON UPDATE cascade
, dataset	integer	NOT NULL	REFERENCES photometry.dataset (id)	ON DELETE restrict	ON UPDATE cascade
, band	integer	NOT NULL	REFERENCES common.calibpassband (id)	ON DELETE restrict	ON UPDATE cascade
, mag	real	NOT NULL	CHECK (mag>-1 and mag<30)
, e_mag	real	CHECK (e_mag>0 and e_mag<0.5)
, quality	common.quality	NOT NULL	DEFAULT 'ok'
, modification_time	timestamp without time zone	NOT NULL	DEFAULT now()
, UNIQUE (pgc,dataset,band)
) ;

COMMENT ON TABLE photometry.data	IS 'Total magnitudes catalog' ;
COMMENT ON COLUMN photometry.data.id	IS 'Totla magnitude ID' ;
COMMENT ON COLUMN photometry.data.pgc	IS 'PGC number of the object' ;
COMMENT ON COLUMN photometry.data.dataset	IS 'Dataset of the measurements' ;
COMMENT ON COLUMN photometry.data.band	IS 'Passband ID' ;
COMMENT ON COLUMN photometry.data.mag	IS 'Total (PSF|model|asymptotic|etc.) magnitude [mag]' ;
COMMENT ON COLUMN photometry.data.e_mag	IS 'Error of the total magnitude [mag]' ;
COMMENT ON COLUMN photometry.data.quality	IS 'Measurement quality' ;
COMMENT ON COLUMN photometry.data.modification_time	IS 'Timestamp when the record was added to the database' ;


COMMIT ;
