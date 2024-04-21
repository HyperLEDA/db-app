BEGIN ;
------------------------------------------------------------------
--------         Photometry catalog (level 1)            ---------
------------------------------------------------------------------
------------------  Methods  -------------------------------------
--  Visual:
--     -> magVisual
--     -> sizeVisual (in fact, it corresponds to the limiting isophote)
--  Profile: 
--     -> sizeSigma (1-sigma of the Gaussian light distribution)
--  Aperture: 
--     aperture -> magAper
--  Total (Asymptotic extrapolation when aperture size -> Inf) : 
--     -> magTotal -> size%total
--  Isophote:
--     -> magIso
--     -> sizeIso 
--  Petrosian: 
--     -> Rpetro -> aperture -> magPetro -> size%petro
--  Kron:
--     -> Rkron -> aperture -> magKron
--  Model:
--     model -> magModel
--           -> size%model
------------------  Apertures ------------------------------------
--  Circle: it defines equivalent diameter d=sqrt(a*b)
--  Ellipse: a,b,pa
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
, ( 'Aper' , 'Aperture photometry' )
, ( 'Iso'  , 'Isophotal photometry' )
, ( 'Total' , 'Asymptotic (extrapolated) magnitude' )
, ( 'Model' , 'Best fit model' )
, ( 'Kron' , 'Kron adaptively scaled aperture' )
, ( 'Petro' , 'Petrosian adaptively scaled aperture' )
;


CREATE TYPE photometry.adaptAperType	AS ENUM ('Kron','Petro') ;
COMMENT ON TYPE photometry.adaptAperType	IS 'Method of the adaptive aperture estimate' ;

CREATE TABLE photometry.adaptAperMethod (
  id	text	PRIMARY KEY
, method	photometry.adaptAperType	NOT NULL
, scale	real	NOT NULL	DEFAULT 2
, bib	integer	REFERENCES common.bib (id)	ON DELETE restrict ON UPDATE cascade
, description	text	NOT NULL
) ;

COMMENT ON TABLE photometry.adaptAperMethod	IS 'Adaptive apertures' ;
COMMENT ON COLUMN photometry.adaptAperMethod.id	IS 'Adaptive aperture ID' ;
COMMENT ON COLUMN photometry.adaptAperMethod.method	IS 'Adaptive aperture estimate (Kron|Petro)' ;
COMMENT ON COLUMN photometry.adaptAperMethod.scale	IS 'Scaling factor to estimate the aperture size' ;

INSERT INTO photometry.adaptAperMethod VALUES 
  ( 'SDSS.Petro' , 'Petro' , 2, NULL, 'SDSS Petrosian measurements: https://skyserver.sdss.org/dr7/en/help/docs/algorithm.asp?key=mag_petro' )
, ( 'SEx.AUTO' , 'Kron' , 2.5, NULL, 'SExtractor measurements: https://sextractor.readthedocs.io/en/latest/Photom.html#flux-auto-def' )
, ( 'SEx.PETRO' , 'Petro' , 2, NULL, 'SExtractor measurements: https://sextractor.readthedocs.io/en/latest/Photom.html#petrosian-aperture-flux-flux-petro' )
;



-------- Photometry Dataset -------------------------
CREATE TABLE photometry.dataset (
  id	serial	PRIMARY KEY
, method	text	NOT NULL	REFERENCES photometry.method (id )	ON DELETE restrict ON UPDATE cascade
, adaptAper	text	REFERENCES photometry.adaptAperMethod (id )	ON DELETE restrict ON UPDATE cascade
, src	integer	REFERENCES rawdata.tables (id )	ON DELETE restrict ON UPDATE cascade
, datatype	text	REFERENCES common.datatype (id )	ON DELETE restrict ON UPDATE cascade
) ;
CREATE INDEX ON photometry.dataset (method) ;

COMMENT ON TABLE photometry.dataset	IS 'Dataset' ;
COMMENT ON COLUMN photometry.dataset.id	IS 'Dataset ID' ;
COMMENT ON COLUMN photometry.dataset.method	IS 'Measurement method' ;
COMMENT ON COLUMN photometry.dataset.adaptAper	IS 'Adaptive aperture realisation' ;
COMMENT ON COLUMN photometry.dataset.src	IS 'Source table' ;
COMMENT ON COLUMN photometry.dataset.datatype	IS 'Type of the data (reguliar,reprocessing,preliminary,compilation)' ;


------ Photometry data ------------------------------
CREATE TABLE photometry.data (
  id	bigserial	PRIMARY KEY
, pgc	integer	NOT NULL	REFERENCES common.pgc (id )	ON DELETE restrict ON UPDATE cascade
, band	integer	REFERENCES common.calibpassband (id)	ON DELETE restrict ON UPDATE cascade
, dataset	integer	NOT NULL	REFERENCES photometry.dataset (id)	ON DELETE restrict ON UPDATE cascade
, modification_time	timestamp without time zone	NOT NULL	DEFAULT now()
, UNIQUE (pgc,dataset,band)
) ;

COMMENT ON TABLE photometry.data	IS 'Photometry catalog' ;
COMMENT ON COLUMN photometry.data.id	IS 'Measurement ID' ;
COMMENT ON COLUMN photometry.data.pgc	IS 'PGC number of the object' ;
COMMENT ON COLUMN photometry.data.band	IS 'Passband ID' ;
COMMENT ON COLUMN photometry.data.dataset	IS 'Dataset of the measurements' ;
COMMENT ON COLUMN photometry.data.modification_time	IS 'Timestamp when the record was added to the database' ;


-----------------------------------------------------
------ Total magnitude (PSF|asymptotic|model) -------
CREATE TABLE photometry.totalMag (
  id	bigint	PRIMARY KEY	REFERENCES photometry.data (id)
, mag	real	NOT NULL
, e_mag	real
, quality	common.quality	NOT NULL	DEFAULT 'ok'
) ;
CREATE INDEX ON photometry.totalMag (id,quality,mag) ;

COMMENT ON TABLE photometry.totalMag	IS 'Total magnitudes (PSF|model|asymptotic|etc.)' ;
COMMENT ON COLUMN photometry.totalMag.id	IS 'Photometry data ID' ;
COMMENT ON COLUMN photometry.totalMag.mag	IS 'Total (asymptotic) magnitude [mag]' ;
COMMENT ON COLUMN photometry.totalMag.e_mag	IS 'Error of the total magnitude [mag]' ;
COMMENT ON COLUMN photometry.totalMag.quality	IS 'Measurement quality' ;


------ Isophotal magnitude --------------------------
CREATE TABLE photometry.isoMag (
  iso	real	NOT NULL
, PRIMARY KEY (id) 
, FOREIGN KEY (id) REFERENCES photometry.data (id)
, UNIQUE (id,iso)
) INHERITS (photometry.totalMag) ;
CREATE INDEX ON photometry.isoMag (id,quality,iso,mag) ;

COMMENT ON TABLE photometry.isoMag	IS 'Isophotal magnitudes' ;
COMMENT ON COLUMN photometry.isoMag.id	IS 'Photometry data ID' ;
COMMENT ON COLUMN photometry.isoMag.mag	IS 'Isophotal magnitude (integrated flux above specific isophote) [mag]' ;
COMMENT ON COLUMN photometry.isoMag.e_mag	IS 'Error of the isophote magnitude [mag]' ;
COMMENT ON COLUMN photometry.isoMag.iso	IS 'Threshold isophote [mag]' ;
COMMENT ON COLUMN photometry.isoMag.quality	IS 'Measurement quality' ;


-----------------------------------------------------
------ Aperture photometry --------------------------

------ Circular Aperture ----------------------------
CREATE TABLE photometry.circAper (
  id	bigserial	PRIMARY KEY
, center	integer	NOT NULL	REFERENCES icrs.data (id)	ON DELETE restrict ON UPDATE cascade
, a	real	NOT NULL	CHECK (a>0)
, UNIQUE (center,a)
) ;

COMMENT ON TABLE photometry.circAper	IS 'Circular apertures' ;
COMMENT ON COLUMN photometry.circAper.id	IS 'Circular aperture ID' ;
COMMENT ON COLUMN photometry.circAper.center	IS 'Aperture center ID' ;
COMMENT ON COLUMN photometry.circAper.a	IS 'Aperture diameter [arcsec]' ;


------ Elliptical Aperture ----------------------------
CREATE TABLE photometry.ellAper (
  id	bigserial	PRIMARY KEY
, center	integer	NOT NULL	REFERENCES icrs.data (id)	ON DELETE restrict ON UPDATE cascade
, a	real	NOT NULL	CHECK (a>0)
, b	real	NOT NULL	CHECK (b>0)
, pa	real	NOT NULL	CHECK (pa>=0 and pa<180)
, UNIQUE (center,a,b,pa)
) ;

COMMENT ON TABLE photometry.ellAper	IS 'Elliptical apertures' ;
COMMENT ON COLUMN photometry.ellAper.id	IS 'Elliptical aperture ID' ;
COMMENT ON COLUMN photometry.ellAper.center	IS 'Aperture center ID' ;
COMMENT ON COLUMN photometry.ellAper.a	IS 'Aperture major diameter [arcsec]' ;
COMMENT ON COLUMN photometry.ellAper.b	IS 'Aperture minor diameter [arcsec]' ;
COMMENT ON COLUMN photometry.ellAper.pa	IS 'Aperture position angle [degrees]' ;


------ Aperture magnitude --------------------------
CREATE TABLE photometry.circMag (
  aper	bigint	NOT NULL	REFERENCES photometry.circAper (id)	ON DELETE restrict ON UPDATE cascade
, FOREIGN KEY (id) REFERENCES photometry.data (id)
, PRIMARY KEY (id,aper)
) INHERITS (photometry.totalMag) ;
CREATE INDEX ON photometry.circMag (id,quality,aper,mag) ;

COMMENT ON TABLE photometry.circMag	IS 'Photometry in circular apertures' ;
COMMENT ON COLUMN photometry.circMag.id	IS 'Photometry data ID' ;
COMMENT ON COLUMN photometry.circMag.mag	IS 'Aperture magnitude [mag]' ;
COMMENT ON COLUMN photometry.circMag.e_mag	IS 'Error of the aperture magnitude [mag]' ;
COMMENT ON COLUMN photometry.circMag.quality	IS 'Measurement quality' ;
COMMENT ON COLUMN photometry.circMag.aper	IS 'Aperture ID' ;


CREATE TABLE photometry.ellMag (
  FOREIGN KEY (id) REFERENCES photometry.data (id)
, FOREIGN KEY (aper) REFERENCES photometry.ellAper (id)	ON DELETE restrict ON UPDATE cascade
, PRIMARY KEY (id,aper)
) INHERITS (photometry.circMag) ;
CREATE INDEX ON photometry.ellMag (id,quality,aper,mag) ;

COMMENT ON TABLE photometry.ellMag	IS 'Photometry in elliptical apertures' ;
COMMENT ON COLUMN photometry.ellMag.id	IS 'Photometry data ID' ;
COMMENT ON COLUMN photometry.ellMag.mag	IS 'Aperture magnitude [mag]' ;
COMMENT ON COLUMN photometry.ellMag.e_mag	IS 'Error of the aperture magnitude [mag]' ;
COMMENT ON COLUMN photometry.ellMag.quality	IS 'Measurement quality' ;
COMMENT ON COLUMN photometry.ellMag.aper	IS 'Aperture ID' ;



-----------------------------------------------------
------ Equivalent diameter (circular aperture) ------
CREATE TABLE photometry.circle (
  id	bigint	PRIMARY KEY	REFERENCES photometry.data (id)
, a	real	NOT NULL	CHECK (a>0)
, e_a	real	CHECK (e_a>0)
, quality	common.quality	NOT NULL	DEFAULT 'ok'
) ;
CREATE INDEX ON photometry.circle (id,quality,a) ;

COMMENT ON TABLE photometry.circle	IS 'Equivalent diameters' ;
COMMENT ON COLUMN photometry.circle.id	IS 'Photometry data ID' ;
COMMENT ON COLUMN photometry.circle.a	IS 'Equivalent diameter [arcsec]' ;
COMMENT ON COLUMN photometry.circle.e_a	IS 'Error of the diameter [arcsec]' ;
COMMENT ON COLUMN photometry.circle.quality	IS 'Measurement quality' ;


------ Equivalent diameter at the specific level of the total flux ------
CREATE TABLE photometry.fluxPctCircle (
  level	real	NOT NULL	CHECK (level>0 and level<100)	DEFAULT 50
, FOREIGN KEY (id) REFERENCES photometry.data (id)
, UNIQUE (id,level)
) INHERITS (photometry.circle) ;
CREATE INDEX ON photometry.fluxPctCircle (id,quality,level,a) ;

COMMENT ON TABLE photometry.fluxPctCircle	IS 'Equivalent diameter at specific level of the total flux' ;
COMMENT ON COLUMN photometry.fluxPctCircle.id	IS 'Photometry data ID' ;
COMMENT ON COLUMN photometry.fluxPctCircle.a	IS 'Equivalent diameter corresponding to the specifil level of the total flux [arcsec]' ;
COMMENT ON COLUMN photometry.fluxPctCircle.e_a	IS 'Error of the diameter [arcsec]' ;
COMMENT ON COLUMN photometry.fluxPctCircle.quality	IS 'Measurement quality' ;
COMMENT ON COLUMN photometry.fluxPctCircle.level	IS 'Percent of the flux' ;


------ Equivalent diameter at the specific level of the adaptive aperture flux ------
CREATE TABLE photometry.fluxPctAdaptCircle (
  FOREIGN KEY (id) REFERENCES photometry.data (id)
, UNIQUE (id,level)
) INHERITS (photometry.fluxPctCircle) ;
CREATE INDEX ON photometry.fluxPctAdaptCircle (id,quality,level,a) ;

COMMENT ON TABLE photometry.fluxPctAdaptCircle	IS 'Equivalent diameter at specific level of the adaptive aperture flux' ;
COMMENT ON COLUMN photometry.fluxPctAdaptCircle.id	IS 'Photometry data ID' ;
COMMENT ON COLUMN photometry.fluxPctAdaptCircle.a	IS 'Equivalent diameter corresponding to the specifil level of the adaptive aperture flux [arcsec]' ;
COMMENT ON COLUMN photometry.fluxPctAdaptCircle.e_a	IS 'Error of the diameter [arcsec]' ;
COMMENT ON COLUMN photometry.fluxPctAdaptCircle.quality	IS 'Measurement quality' ;
COMMENT ON COLUMN photometry.fluxPctAdaptCircle.level	IS 'Percent of the flux' ;




-----------------------------------------------------
------ Major+minor diameters (elliptical aperture) ------
CREATE TABLE photometry.ellipse (
  id	bigint	PRIMARY KEY	REFERENCES photometry.data (id)
, a	real	NOT NULL	CHECK (a>0)
, e_a	real	CHECK (e_a>0)
, b	real	NOT NULL	CHECK (b>0)
, e_b	real	CHECK (e_b>0)
, pa	real	NOT NULL	CHECK (pa>=0 and pa<180)
, e_pa	real	CHECK (e_pa>0)
, quality	common.quality	NOT NULL	DEFAULT 'ok'
) ;
CREATE INDEX ON photometry.ellipse (id,quality,a,b,pa) ; -- NULLS NOT DISTINCT;

COMMENT ON TABLE photometry.ellipse	IS 'Object geometry' ;
COMMENT ON COLUMN photometry.ellipse.id	IS 'Photometry data ID' ;
COMMENT ON COLUMN photometry.ellipse.a	IS 'Major diameter [arcsec]' ;
COMMENT ON COLUMN photometry.ellipse.e_a	IS 'Error of the major diameter [arcsec]' ;
COMMENT ON COLUMN photometry.ellipse.b	IS 'Minor diameter [arcsec]' ;
COMMENT ON COLUMN photometry.ellipse.e_b	IS 'Error of the minor diameter [arcsec]' ;
COMMENT ON COLUMN photometry.ellipse.pa	IS 'Position angle from North to East from 0 to 180 [degrees]' ;
COMMENT ON COLUMN photometry.ellipse.e_pa	IS 'Error of the position angle [degrees]' ;
COMMENT ON COLUMN photometry.ellipse.quality	IS 'Measurement quality' ;


------ Isophotal size --------------------------
CREATE TABLE photometry.isoEllipse (
  iso	real	NOT NULL	CHECK (iso>0)
, FOREIGN KEY (id) REFERENCES photometry.data (id)
, UNIQUE (id,iso)
) INHERITS (photometry.ellipse) ;
CREATE INDEX ON photometry.isoEllipse (id,quality,iso,a,b,pa) ; -- NULLS NOT DISTINCT;

COMMENT ON TABLE photometry.isoEllipse	IS 'Object geometry at specific isophote' ;
COMMENT ON COLUMN photometry.isoEllipse.id	IS 'Photometry data ID' ;
COMMENT ON COLUMN photometry.isoEllipse.a	IS 'Isophotal major diameter [arcsec]' ;
COMMENT ON COLUMN photometry.isoEllipse.e_a	IS 'Error of the major diameter [arcsec]' ;
COMMENT ON COLUMN photometry.isoEllipse.b	IS 'Isophotal minor diameter [arcsec]' ;
COMMENT ON COLUMN photometry.isoEllipse.e_b	IS 'Error of the minor diameter [arcsec]' ;
COMMENT ON COLUMN photometry.isoEllipse.pa	IS 'Position angle from North to East from 0 to 180 [degrees]' ;
COMMENT ON COLUMN photometry.isoEllipse.e_pa	IS 'Error of the position angle [degrees]' ;
COMMENT ON COLUMN photometry.isoEllipse.quality	IS 'Measurement quality' ;
COMMENT ON COLUMN photometry.isoEllipse.iso	IS 'Isophote' ;


------ Major+minor diameters at specific of the total flux level ------
CREATE TABLE photometry.fluxPctEllipse (
  level	real	NOT NULL	CHECK (level>0 and level<100)	DEFAULT 50
, FOREIGN KEY (id) REFERENCES photometry.data (id)
, UNIQUE (id,level)
) INHERITS (photometry.ellipse) ;
CREATE INDEX ON photometry.fluxPctEllipse (id,quality,level,a,b,pa) ; -- NULLS NOT DISTINCT;

COMMENT ON TABLE photometry.fluxPctEllipse	IS 'Object geometry at specific level of the total flux' ;
COMMENT ON COLUMN photometry.fluxPctEllipse.id	IS 'Photometry data ID' ;
COMMENT ON COLUMN photometry.fluxPctEllipse.a	IS 'Major diameter corresponding to the specific level of the total flux [arcsec]' ;
COMMENT ON COLUMN photometry.fluxPctEllipse.e_a	IS 'Error of the major diameter [arcsec]' ;
COMMENT ON COLUMN photometry.fluxPctEllipse.b	IS 'Minor diameter corresponding to the specific level of the total flux [arcsec]' ;
COMMENT ON COLUMN photometry.fluxPctEllipse.e_b	IS 'Error of the minor diameter [arcsec]' ;
COMMENT ON COLUMN photometry.fluxPctEllipse.pa	IS 'Position angle from North to East from 0 to 180 [degrees]' ;
COMMENT ON COLUMN photometry.fluxPctEllipse.e_pa	IS 'Error of the position angle [degrees]' ;
COMMENT ON COLUMN photometry.fluxPctEllipse.quality	IS 'Measurement quality' ;
COMMENT ON COLUMN photometry.fluxPctEllipse.level	IS 'Percent of the flux' ;


------ Major+minor diameters at specific of the adaptive aperture flux ------
CREATE TABLE photometry.fluxPctAdaptEllipse (
  level	real	NOT NULL	CHECK (level>0 and level<100)	DEFAULT 50
, FOREIGN KEY (id) REFERENCES photometry.data (id)
, UNIQUE (id,level)
) INHERITS (photometry.ellipse) ;
CREATE INDEX ON photometry.fluxPctAdaptEllipse (id,quality,level,a,b,pa) ; -- NULLS NOT DISTINCT;

COMMENT ON TABLE photometry.fluxPctAdaptEllipse	IS 'Object geometry at specific level of the adaptive aperture flux' ;
COMMENT ON COLUMN photometry.fluxPctAdaptEllipse.id	IS 'Photometry data ID' ;
COMMENT ON COLUMN photometry.fluxPctAdaptEllipse.a	IS 'Major diameter corresponding to the specific level of the adaptive aperture flux [arcsec]' ;
COMMENT ON COLUMN photometry.fluxPctAdaptEllipse.e_a	IS 'Error of the major diameter [arcsec]' ;
COMMENT ON COLUMN photometry.fluxPctAdaptEllipse.b	IS 'Minor diameter corresponding to the specific level of the adaptive aperture flux [arcsec]' ;
COMMENT ON COLUMN photometry.fluxPctAdaptEllipse.e_b	IS 'Error of the minor diameter [arcsec]' ;
COMMENT ON COLUMN photometry.fluxPctAdaptEllipse.pa	IS 'Position angle from North to East from 0 to 180 [degrees]' ;
COMMENT ON COLUMN photometry.fluxPctAdaptEllipse.e_pa	IS 'Error of the position angle [degrees]' ;
COMMENT ON COLUMN photometry.fluxPctAdaptEllipse.quality	IS 'Measurement quality' ;
COMMENT ON COLUMN photometry.fluxPctAdaptEllipse.level	IS 'Percent of the flux' ;


COMMIT ;
