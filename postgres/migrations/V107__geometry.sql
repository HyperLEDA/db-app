/* pgmigrate-encoding: utf-8 */

BEGIN ;
------------------------------------------------------------------
--------         Geometry catalog (level 1)            -----------
------------------------------------------------------------------


DROP SCHEMA IF EXISTS geometry CASCADE ;

CREATE SCHEMA geometry ;
COMMENT ON SCHEMA geometry	IS 'Geometry catalog' ;


-------- Geometry uses measurement methods and datasets of the Photometry schema --------------

------ Elliptical shape --------
CREATE TABLE geometry.ellipse (
  pgc	integer	NOT NULL	REFERENCES common.pgc (id )	ON DELETE restrict ON UPDATE cascade
, dataset	integer	NOT NULL	REFERENCES photometry.dataset (id)	ON DELETE restrict ON UPDATE cascade
, band	integer	REFERENCES common.calibpassband (id)	ON DELETE restrict ON UPDATE cascade
, a	real	NOT NULL	CHECK (a>0)
, e_a	real	CHECK (e_a>0)
, b	real	NOT NULL	CHECK (b>=a)
, e_b	real	CHECK (e_b>0)
, pa	real	NOT NULL	CHECK (pa>=0 and pa<180)
, e_pa	real	CHECK (e_pa>0)
, quality	common.quality	NOT NULL	DEFAULT 'ok'
, modification_time	timestamp without time zone	NOT NULL	DEFAULT now()
, PRIMARY KEY (pgc,dataset,band)
) ;

COMMENT ON TABLE geometry.ellipse	IS 'Elliptial shape' ;
COMMENT ON COLUMN geometry.ellipse.pgc	IS 'PGC number of the object' ;
COMMENT ON COLUMN geometry.ellipse.dataset	IS 'Dataset of the measurements' ;
COMMENT ON COLUMN geometry.ellipse.band	IS 'Passband ID' ;
COMMENT ON COLUMN geometry.ellipse.a	IS 'Major diameter [arcsec]' ;
COMMENT ON COLUMN geometry.ellipse.e_a	IS 'Error of the major diameter [arcsec]' ;
COMMENT ON COLUMN geometry.ellipse.b	IS 'Minor diameter [arcsec]' ;
COMMENT ON COLUMN geometry.ellipse.e_b	IS 'Error of the minor diameter [arcsec]' ;
COMMENT ON COLUMN geometry.ellipse.pa	IS 'Position angle from North to East from 0 to 180 [degrees]' ;
COMMENT ON COLUMN geometry.ellipse.e_pa	IS 'Error of the position angle [degrees]' ;
COMMENT ON COLUMN geometry.ellipse.quality	IS 'Measurement quality' ;
COMMENT ON COLUMN geometry.ellipse.modification_time	IS 'Timestamp when the record was added to the database' ;


------ Ellipse corresponding to the specific total flux level --------
CREATE TABLE geometry.fluxLevelEllipse (
  phot	bigint	NOT NULL	REFERENCES photometry.data (id)	ON DELETE restrict	ON UPDATE cascade
, level	real	NOT NULL	CHECK (level>0 and level<100)
, a	real	NOT NULL	CHECK (a>0)
, e_a	real	CHECK (e_a>0)
, b	real	NOT NULL	CHECK (b>=a)
, e_b	real	CHECK (e_b>0)
, pa	real	NOT NULL	CHECK (pa>=0 and pa<180)
, e_pa	real	CHECK (e_pa>0)
, iso	real	CHECK (iso>10 and iso<30)
, e_iso	real	CHECK (e_iso>0 and e_iso<0.5)
, UNIQUE (phot,level)
) ;

COMMENT ON TABLE geometry.fluxLevelEllipse	IS 'Elliptial geometry at specific flux level' ;
COMMENT ON COLUMN geometry.fluxLevelEllipse.phot	IS 'Totoal magnitude ID' ;
COMMENT ON COLUMN geometry.fluxLevelEllipse.level	IS 'Level of the total flux at which the ellipse corresponds [percent]' ;
COMMENT ON COLUMN geometry.fluxLevelEllipse.a	IS 'Major diameter [arcsec]' ;
COMMENT ON COLUMN geometry.fluxLevelEllipse.e_a	IS 'Error of the major diameter [arcsec]' ;
COMMENT ON COLUMN geometry.fluxLevelEllipse.b	IS 'Minor diameter [arcsec]' ;
COMMENT ON COLUMN geometry.fluxLevelEllipse.e_b	IS 'Error of the minor diameter [arcsec]' ;
COMMENT ON COLUMN geometry.fluxLevelEllipse.pa	IS 'Position angle from North to East from 0 to 180 [degrees]' ;
COMMENT ON COLUMN geometry.fluxLevelEllipse.e_pa	IS 'Error of the position angle [degrees]' ;
COMMENT ON COLUMN geometry.fluxLevelEllipse.iso	IS 'Isophote corresponing to the given level of the total flux [mag*srcsec^2]' ;
COMMENT ON COLUMN geometry.fluxLevelEllipse.e_iso	IS 'Error of the isophote [mag*srcsec^2]' ;


------ Data Collection --------
CREATE VIEW geometry.data AS
SELECT
  mag.pgc
, mag.dataset
, ds.method
, mag.band
, ell.level
, ell.a
, ell.e_a
, ell.b
, ell.e_b
, ell.pa
, ell.e_pa
, ell.iso
, ell.e_iso
, mag.quality
, mag.modification_time
, ds.src
, src.bib
, src.datatype
, src.table_name
FROM
  geometry.fluxLevelEllipse	AS ell
  LEFT JOIN photometry.data	AS mag	ON (ell.phot=mag.id)
  LEFT JOIN photometry.dataset	AS ds	ON (mag.dataset=ds.id)
  LEFT JOIN rawdata.tables	AS src	ON (ds.src=src.id)

UNION

SELECT
  ell.pgc
, ell.dataset
, ds.method
, ell.band
, NULL::real	AS level
, ell.a
, ell.e_a
, ell.b
, ell.e_b
, ell.pa
, ell.e_pa
, NULL::real	AS iso
, NULL::real	AS e_iso
, ell.quality
, ell.modification_time
, ds.src
, src.bib
, src.datatype
, src.table_name
FROM
  geometry.ellipse	AS ell
  LEFT JOIN photometry.dataset	AS ds	ON (ell.dataset=ds.id)
  LEFT JOIN rawdata.tables	AS src	ON (ds.src=src.id)
;

COMMENT ON VIEW geometry.data	IS 'Geometry catalog' ;
COMMENT ON COLUMN geometry.data.pgc	IS 'PGC number of the object' ;
COMMENT ON COLUMN geometry.data.dataset	IS 'Dataset ID' ;
COMMENT ON COLUMN geometry.data.method	IS 'Photometry measurement method' ;
COMMENT ON COLUMN geometry.data.band	IS 'Passband ID' ;
COMMENT ON COLUMN geometry.data.level	IS 'Level of the total flux [percent]' ;
COMMENT ON COLUMN geometry.data.a	IS 'Major diameter [arcsec]' ;
COMMENT ON COLUMN geometry.data.e_a	IS 'Error of the major diameter [arcsec]' ;
COMMENT ON COLUMN geometry.data.b	IS 'Minor diameter [arcsec]' ;
COMMENT ON COLUMN geometry.data.e_b	IS 'Error of the minor diameter [arcsec]' ;
COMMENT ON COLUMN geometry.data.pa	IS 'Position angle from North to East from 0 to 180 [degrees]' ;
COMMENT ON COLUMN geometry.data.e_pa	IS 'Error of the position angle [degrees]' ;
COMMENT ON COLUMN geometry.data.iso	IS 'Isophote corresponing to the given level of the total flux [mag*srcsec^2]' ;
COMMENT ON COLUMN geometry.data.e_iso	IS 'Error of the isophote [mag*srcsec^2]' ;
COMMENT ON COLUMN geometry.data.quality	IS 'Measurement quality' ;
COMMENT ON COLUMN geometry.data.modification_time	IS 'Timestamp when the record was added to the database' ;
COMMENT ON COLUMN geometry.data.src	IS 'Source table ID' ;
COMMENT ON COLUMN geometry.data.bib	IS 'Bibliography reference ID' ;
COMMENT ON COLUMN geometry.data.datatype	IS 'Types of the data (regular,reprocessing,preliminary,compilation)' ;
COMMENT ON COLUMN geometry.data.table_name	IS 'Source table name' ;


COMMIT ;
