BEGIN ;
------------------------------------------------------------------
--------      Aperture photometry catalog (level 1)      ---------
------------------------------------------------------------------
-- Circle:
--	-> Mag
-- Ellipse
--	-> Mag
------------------------------------------------------------------

DROP SCHEMA IF EXISTS aperture CASCADE ;

CREATE SCHEMA aperture ;
COMMENT ON SCHEMA aperture	IS 'Aperture Photometry catalog' ;


----------------------------------------
------ Circular Aperture ---------------
CREATE TABLE aperture.circle (
  id	bigserial	PRIMARY KEY
, center	integer	NOT NULL	REFERENCES icrs.data (id)	ON DELETE restrict	ON UPDATE cascade
, a	real	NOT NULL	CHECK (a>0)
, UNIQUE (center,a)
) ;

COMMENT ON TABLE aperture.circle	IS 'Circular apertures' ;
COMMENT ON COLUMN aperture.circle.id	IS 'Circular aperture ID' ;
COMMENT ON COLUMN aperture.circle.center	IS 'Aperture center ID' ;
COMMENT ON COLUMN aperture.circle.a	IS 'Aperture diameter [arcsec]' ;

------ Magnitude --------------------------
CREATE TABLE aperture.circMag (
  pgc	integer	NOT NULL	REFERENCES common.pgc (id)	ON DELETE restrict	ON UPDATE cascade
, aper	bigint	NOT NULL	REFERENCES aperture.circle (id)	ON DELETE restrict	ON UPDATE cascade
, dataset	integer	NOT NULL	REFERENCES rawdata.tables (id)	ON DELETE restrict	ON UPDATE cascade
, band	integer	NOT NULL	REFERENCES common.calibpassband (id)	ON DELETE restrict	ON UPDATE cascade
, mag	real	NOT NULL	CHECK (mag>0 and mag<30)
, e_mag	real
, quality	common.quality	NOT NULL	DEFAULT 'ok'
, PRIMARY KEY (pgc,aper,dataset,band,quality)
) ;

COMMENT ON TABLE aperture.circMag	IS 'Photometry in circular apertures' ;
COMMENT ON COLUMN aperture.circMag.pgc	IS 'PGC number of the object' ;
COMMENT ON COLUMN aperture.circMag.band	IS 'Bandpass ID' ;
COMMENT ON COLUMN aperture.circMag.mag	IS 'Aperture magnitude [mag]' ;
COMMENT ON COLUMN aperture.circMag.e_mag	IS 'Error of the aperture magnitude [mag]' ;
COMMENT ON COLUMN aperture.circMag.quality	IS 'Measurement quality' ;
COMMENT ON COLUMN aperture.circMag.aper	IS 'Aperture ID' ;
COMMENT ON COLUMN aperture.circMag.dataset	IS 'Dataset' ;


----------------------------------------
------ Elliptical Aperture -------------
CREATE TABLE aperture.ellipse (
  b	real	NOT NULL	CHECK (b>0)
, pa	real	NOT NULL	CHECK (pa>=0 and pa<180)
, PRIMARY KEY (id)
, FOREIGN KEY (center)	REFERENCES icrs.data (id)	ON DELETE restrict	ON UPDATE cascade 
, UNIQUE (center,a,b,pa)
) INHERITS (aperture.circle) ;

COMMENT ON TABLE aperture.ellipse	IS 'Elliptical apertures' ;
COMMENT ON COLUMN aperture.ellipse.id	IS 'Elliptical aperture ID' ;
COMMENT ON COLUMN aperture.ellipse.center	IS 'Aperture center ID' ;
COMMENT ON COLUMN aperture.ellipse.a	IS 'Aperture major axis diameter [arcsec]' ;
COMMENT ON COLUMN aperture.ellipse.b	IS 'Aperture minor axis diameter [arcsec]' ;
COMMENT ON COLUMN aperture.ellipse.pa	IS 'Position angle of the major axis from North to East [degrees]' ;

------ Magnitude --------------------------
CREATE TABLE aperture.ellMag (
  PRIMARY KEY (pgc,aper,dataset,band,quality)
, FOREIGN KEY (pgc)	REFERENCES common.pgc(id)	ON DELETE restrict	ON UPDATE cascade
, FOREIGN KEY (aper)	REFERENCES aperture.ellipse(id)	ON DELETE restrict	ON UPDATE cascade
, FOREIGN KEY (dataset)	REFERENCES rawdata.tables(id)	ON DELETE restrict	ON UPDATE cascade
, FOREIGN KEY (band)	REFERENCES common.calibpassband(id)	ON DELETE restrict	ON UPDATE cascade
) INHERITS (aperture.circMag) ;

COMMENT ON TABLE aperture.ellMag	IS 'Photometry in elliptical apertures' ;
COMMENT ON COLUMN aperture.ellMag.pgc	IS 'PGC number of the object' ;
COMMENT ON COLUMN aperture.ellMag.band	IS 'Bandpass ID' ;
COMMENT ON COLUMN aperture.ellMag.mag	IS 'Aperture magnitude [mag]' ;
COMMENT ON COLUMN aperture.ellMag.e_mag	IS 'Error of the aperture magnitude [mag]' ;
COMMENT ON COLUMN aperture.ellMag.quality	IS 'Measurement quality' ;
COMMENT ON COLUMN aperture.ellMag.aper	IS 'Aperture ID' ;
COMMENT ON COLUMN aperture.ellMag.dataset	IS 'Dataset' ;


-------------------------------------
--------- List of values ------------
CREATE VIEW aperture.data AS
SELECT
  mag.*
, 'ellipse'::text        AS shape
, ell.center
, ell.a
, ell.b
, ell.pa
, ds.bib
, ds.table_name
, ds.datatype
FROM
  ONLY aperture.ellMag	AS mag
  LEFT JOIN ONLY aperture.ellipse	AS ell	ON (ell.id=mag.aper)
  LEFT JOIN rawdata.tables	AS ds	ON (mag.dataset=ds.id)
UNION
SELECT
  mag.*
, 'circle'::text	AS shape
, circ.center
, circ.a
, NULL::real	AS b
, NULL::real	AS pa
, ds.bib
, ds.table_name
, ds.datatype
FROM 
  ONLY aperture.circMag	AS mag	
  LEFT JOIN ONLY aperture.circle	AS circ	ON (circ.id=mag.aper)
  LEFT JOIN rawdata.tables	AS ds	ON (mag.dataset=ds.id)
;

COMMENT ON VIEW aperture.data	IS 'Aperture photometry' ;
COMMENT ON COLUMN aperture.data.pgc	IS 'PGC number of the object' ;
COMMENT ON COLUMN aperture.data.aper	IS 'Aperture ID' ;
COMMENT ON COLUMN aperture.data.dataset	IS 'Dataset ID' ;
COMMENT ON COLUMN aperture.data.band	IS 'Bandpass ID' ;
COMMENT ON COLUMN aperture.data.mag	IS 'Aperture magnitude [mag]' ;
COMMENT ON COLUMN aperture.data.e_mag	IS 'Error of the magnitude [mag]' ;
COMMENT ON COLUMN aperture.data.quality	IS 'Measurement quality' ;
COMMENT ON COLUMN aperture.data.shape	IS 'Aperture shape (circle|ellipse)' ;
COMMENT ON COLUMN aperture.data.center	IS 'Aperture center position ID' ;
COMMENT ON COLUMN aperture.data.a	IS 'Aperture major axis diameter [arcsec]' ;
COMMENT ON COLUMN aperture.data.b	IS 'Aperture minor axis diameter [arcsec]' ;
COMMENT ON COLUMN aperture.data.pa	IS 'Position angle of the major axis from North to East [degrees]' ;
COMMENT ON COLUMN aperture.data.bib	IS 'Bibliography ID' ;
COMMENT ON COLUMN aperture.data.table_name	IS 'Data source table' ;
COMMENT ON COLUMN aperture.data.datatype	IS 'Type of the data (reguliar,reprocessing,preliminary,compilation)' ;


COMMIT ;
