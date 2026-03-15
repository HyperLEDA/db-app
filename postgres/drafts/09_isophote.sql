BEGIN;

CREATE SCHEMA IF NOT EXISTS isophote ;
COMMENT ON SCHEMA isophote IS 'Catalog of the isophotal photometry';

CREATE TABLE isophote.data (
  record_id	Text	NOT NULL	REFERENCES layer0.records(id) ON UPDATE cascade ON DELETE restrict
, band	text	NOT NULL	REFERENCES photometry.calib_bands (id) ON DELETE restrict ON UPDATE cascade
, isophote	real	NOT NULL	CHECK ( mag > -1 and mag < 30 )
, mag	real	NOT NULL	CHECK ( mag > -1 and mag < 30 )
, e_mag	real	CHECK ( e_mag > 0 and e_mag < 0.5 )
, a	real	NOT NULL	CHECK (a>0)
, e_a	real	CHECK (e_a>0)
, b	real	NOT NULL	CHECK (b<=a)
, e_b	real	CHECK (e_b>0)
, pa	real	NOT NULL	CHECK (pa>=0 and pa<180)
, e_pa	real	CHECK (e_pa>0)
, PRIMARY KEY (record_id, band, isophote)
);
CREATE INDEX ON isophote.data (record_id) ;
CREATE INDEX ON isophote.data (band) ;
CREATE INDEX ON isophote.data (isophote) ;

COMMENT ON TABLE isophote.data	IS 'Catalog of the isophotal photometry';
COMMENT ON COLUMN isophote.data.record_id	IS 'Record ID';
COMMENT ON COLUMN isophote.data.band	IS '{"description":"Calibrated passband ID", "ucd":"instr.filter"}';
COMMENT ON COLUMN isophote.data.isophote	IS '{"description":"Isophote level",, "unit":"mag/arcmin2", "ucd":"phot.mag.sb"}' ;
COMMENT ON COLUMN isophote.data.mag	IS '{"description":"Isophotal magnitude", "unit":"mag", "ucd":"phot.mag"}';
COMMENT ON COLUMN isophote.data.e_mag	IS '{"description":"Error of the isophotal magnitude", "unit":"mag", "ucd":"stat.error;phot.mag"}';
COMMENT ON COLUMN isophote.data.a	IS '{"description":"Semi-major axis length at the given isophote", "unit":"arcsec", "ucd":"phys.angSize.smajAxis"}';
COMMENT ON COLUMN isophote.data.e_a	IS '{"description":"Error of the semi-major axis length at the given isophote", "unit":"arcsec", "ucd":"stat.error;phys.angSize.smajAxis"}';
COMMENT ON COLUMN isophote.data.b	IS '{"description":"Semi-minor axis length at the given isophote", "unit":"arcsec", "ucd":"phys.angSize.sminAxis"}';
COMMENT ON COLUMN isophote.data.e_b	IS '{"description":"Error of the semi-minor axis length at the given isophote", "unit":"arcsec", "ucd":"stat.error;phys.angSize.sminAxis"}';
COMMENT ON COLUMN isophote.data.pa	IS '{"description":"Position angle (measured east of north)", "unit":"deg", "ucd":"pos.posAng"}';
COMMENT ON COLUMN isophote.data.e_pa	IS '{"description":"Error of the position angle", "unit":"deg", "ucd":"stat.error;pos.posAng"}';

COMMIT;
