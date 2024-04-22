BEGIN ;

DROP SCHEMA IF EXISTS leda CASCADE ;

------------------------------------------------------------
--------- Leda structure (level 2) -------------------------
CREATE SCHEMA leda ;

CREATE TABLE leda.data (
  pgc	integer	PRIMARY KEY	REFERENCES common.pgc (id)	ON DELETE restrict	ON UPDATE cascade
, objname	text	NOT NULL	UNIQUE	REFERENCES designation.data (design)	ON DELETE restrict	ON UPDATE cascade
, objclass	text
, ra	double precision	NOT NULL
, dec	double precision	NOT NULL
, e_ra	real	NOT NULL
, e_dec	real	NOT NULL
, FOREIGN KEY (pgc,objname) REFERENCES designation.data (pgc,design)	ON DELETE restrict	ON UPDATE cascade
) ;
CREATE INDEX ON leda.data (objclass) ;
CREATE INDEX ON leda.data (ra,dec) ;

COMMENT ON TABLE leda.data	IS 'Leda' ;
COMMENT ON COLUMN leda.data.pgc	IS 'Principal Galaxy Catalog (PGC) number' ;
COMMENT ON COLUMN leda.data.objname	IS 'Principal object designation' ;
COMMENT ON COLUMN leda.data.objclass	IS 'Object class (star, galaxy, etc)' ;
COMMENT ON COLUMN leda.data.ra	IS 'Right Ascension (ICRS) [degrees]' ;
COMMENT ON COLUMN leda.data.dec	IS 'Declination (ICRS) [degrees]' ;
COMMENT ON COLUMN leda.data.e_ra	IS 'Right Ascension error (RAerr*cos(Dec) [arcsec]' ;
COMMENT ON COLUMN leda.data.e_dec	IS 'Declination error [arcsec]' ;


COMMIT ;