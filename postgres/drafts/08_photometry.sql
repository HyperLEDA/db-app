BEGIN;

------------------------------------------------------------------
--------         Photometry catalog (level 1)            ---------
------------------------------------------------------------------
------------------  Methods  -------------------------------------
--  Visual:
--     -> magVisual
--     -> sizeVisual
--        (in fact, it corresponds to the limiting isophote)
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

CREATE TYPE photometry.MagMethodType AS ENUM ( 'psf', 'visual', 'aperture', 'isophotal', 'asymptotic', 'model', 'petrosian', 'kron' ) ;
COMMENT ON TYPE photometry.MagMethodType IS '{ "psf":"Point Spread Function photometry for the point source", "visual":"Visual estimate", "aperture":"Aperture photometry", "isophotal":"Magnitude measurement inside a specified isophote", "asymptotic":"Asymptotic (extrapolated) magnitude when the aperture size -> Inf", "model":"Best fit model of the light distribution", "petrosian":"Petrosian adaptively scaled aperture", "kron":"Kron adaptively scaled aperture" }' ;


CREATE TABLE photometry.total (
  record_id	Text	NOT NULL	REFERENCES layer0.records(id) ON UPDATE cascade ON DELETE restrict
, band	text	NOT NULL	REFERENCES photometry.calib_bands (id) ON DELETE restrict ON UPDATE cascade
, mag	real	NOT NULL	CHECK ( mag > -1 and mag < 30 )
, e_mag	real	CHECK ( e_mag > 0 and e_mag < 0.5 )
, method	photometry.MagMethodType	NOT NULL	CHECK ( method IN ('psf', 'visual', 'asymptotic', 'model', 'petrosian', 'kron') )
, PRIMARY KEY (record_id, method, band)
);
CREATE INDEX ON photometry.total (record_id) ;
CREATE INDEX ON photometry.total (band) ;
CREATE INDEX ON photometry.total (method) ;

COMMENT ON TABLE photometry.total	IS 'Catalog of the total magnitudes';
COMMENT ON COLUMN photometry.total.record_id	IS 'Record ID';
COMMENT ON COLUMN photometry.total.band	IS 'Calibrated passband ID';
COMMENT ON COLUMN photometry.total.mag	IS '{"description":"Total (PSF|model|asymptotic|etc.) magnitude", "unit":"mag", "ucd":"phot.mag"}';
COMMENT ON COLUMN photometry.total.e_mag	IS '{"description":"Error of the total magnitude", "unit":"mag", "ucd":"stat.error;phot.mag"}';
COMMENT ON COLUMN photometry.total.method	IS 'Photometry method type (PSF, Kron, etc.)' ;


CREATE TABLE photometry.isophotal (
  record_id	Text	NOT NULL	REFERENCES layer0.records(id) ON UPDATE cascade ON DELETE restrict
, band	text	NOT NULL	REFERENCES photometry.calib_bands (id) ON DELETE restrict ON UPDATE cascade
, mag	real	NOT NULL	CHECK ( mag > -1 and mag < 30 )
, e_mag	real	CHECK ( e_mag > 0 and e_mag < 0.5 )
, isophote	real	NOT NULL	CHECK ( mag > -1 and mag < 30 )
, PRIMARY KEY (record_id, band, isophote)
);
CREATE INDEX ON photometry.isophotal (record_id) ;
CREATE INDEX ON photometry.isophotal (band) ;
CREATE INDEX ON photometry.isophotal (isophote) ;

COMMENT ON TABLE photometry.isophotal	IS 'Catalog of the isophotal magnitudes';
COMMENT ON COLUMN photometry.isophotal.record_id	IS 'Record ID';
COMMENT ON COLUMN photometry.isophotal.band	IS 'Calibrated passband ID';
COMMENT ON COLUMN photometry.isophotal.mag	IS '{"description":"Isophotal magnitude", "unit":"mag", "ucd":"phot.mag"}';
COMMENT ON COLUMN photometry.isophotal.e_mag	IS '{"description":"Error of the isophotal magnitude", "unit":"mag", "ucd":"stat.error;phot.mag"}';
COMMENT ON COLUMN photometry.isophotal.isophote	IS 'Isophote level' ;

COMMIT;
