BEGIN;

------------------------------------------------------------------
--------         Geometry catalog (level 1)            -----------
------------------------------------------------------------------
DROP SCHEMA IF EXISTS geometry CASCADE;
CREATE SCHEMA IF NOT EXISTS geometry;
COMMENT ON SCHEMA geometry IS 'Catalog of the object geometry';


CREATE TABLE geometry.data (
  record_id	Text	NOT NULL	REFERENCES layer0.records(id) ON UPDATE cascade ON DELETE restrict
, band	text	NOT NULL	REFERENCES photometry.calib_bands (id) ON DELETE restrict ON UPDATE cascade
, method	photometry.MagMethodType	NOT NULL	CHECK ( method IN ('moments', 'asymptotic', 'model', 'petrosian', 'kron') )
, level	real	NOT NULL	CHECK (level>0 and level<100)	DEFAULT 39.3 
, a	real	NOT NULL	CHECK (a>0)
, e_a	real	CHECK (e_a>0)
, b	real	NOT NULL	CHECK (b<=a)
, e_b	real	CHECK (e_b>0)
, pa	real	CHECK (pa>=0 and pa<180)
, e_pa	real	CHECK (e_pa>0)
, isophote	real	CHECK (isophote>-1 and isophote<30)
, e_isophote	real	CHECK (e_isophote>0 and e_isophote<0.5)
, PRIMARY KEY (record_id, band, method, level)
);
CREATE INDEX ON geometry.data (record_id) ;
CREATE INDEX ON geometry.data (band) ;
CREATE INDEX ON geometry.data (level) ;

COMMENT ON TABLE geometry.data	IS 'Catalog of the isophotal photometry';
COMMENT ON COLUMN geometry.data.record_id	IS 'Record ID';
COMMENT ON COLUMN geometry.data.band	IS '{"description":"Calibrated passband ID", "ucd":"instr.filter"}';
COMMENT ON COLUMN geometry.data.method	IS 'Measurement method of the total magnitude' ;
COMMENT ON COLUMN geometry.data.level	IS 'Percent of the enclosed flux' ;
COMMENT ON COLUMN geometry.data.a	IS '{"description":"Semi-major axis length at the given isophote", "unit":"arcsec", "ucd":"phys.angSize.smajAxis"}' ;
COMMENT ON COLUMN geometry.data.e_a	IS '{"description":"Error of the semi-major axis length at the given isophote", "unit":"arcsec", "ucd":"stat.error;phys.angSize.smajAxis"}' ;
COMMENT ON COLUMN geometry.data.b	IS '{"description":"Semi-minor axis length at the given isophote", "unit":"arcsec", "ucd":"phys.angSize.sminAxis"}' ;
COMMENT ON COLUMN geometry.data.e_b	IS '{"description":"Error of the semi-minor axis length at the given isophote", "unit":"arcsec", "ucd":"stat.error;phys.angSize.sminAxis"}' ;
COMMENT ON COLUMN geometry.data.pa	IS '{"description":"Position angle (measured east of north)", "unit":"deg", "ucd":"pos.posAng"}' ;
COMMENT ON COLUMN geometry.data.e_pa	IS '{"description":"Error of the position angle", "unit":"deg", "ucd":"stat.error;pos.posAng"}' ;
COMMENT ON COLUMN geometry.data.isophote	IS '{"description":"Surface brightness at given level",, "unit":"mag/arcmin2", "ucd":"phot.mag.sb"}' ;
COMMENT ON COLUMN geometry.data.e_isophote	IS '{"description":"Error fo the surface brightness at given level",, "unit":"mag/arcmin2", "ucd":"stat.error;phot.mag.sb"}' ;

COMMIT;
