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


CREATE TABLE photometry.data (
  record_id	Text	NOT NULL	REFERENCES layer0.records(id) ON UPDATE cascade ON DELETE restrict
, band	text	NOT NULL	REFERENCES photometry.calib_bands (id) ON DELETE restrict ON UPDATE cascade
, mag	real	NOT NULL	CHECK ( mag > -1 and mag < 30 )
, e_mag	real	CHECK ( e_mag > 0 and e_mag < 0.5 )
, method	photometry.MagMethodType	NOT NULL	CHECK ( method IN ('psf', 'visual', 'asymptotic', 'model', 'petrosian', 'kron') )
, PRIMARY KEY (record_id, method, band)
);
CREATE INDEX ON photometry.data (record_id) ;
CREATE INDEX ON photometry.data (band) ;
CREATE INDEX ON photometry.data (method) ;

COMMENT ON TABLE photometry.data	IS 'Catalog of the total magnitudes';
COMMENT ON COLUMN photometry.data.record_id	IS 'Record ID';
COMMENT ON COLUMN photometry.data.band	IS '{"description":"Calibrated passband ID", "ucd":"instr.filter"}';
COMMENT ON COLUMN photometry.data.mag	IS '{"description":"Total (PSF|model|asymptotic|etc.) magnitude", "unit":"mag", "ucd":"phot.mag"}';
COMMENT ON COLUMN photometry.data.e_mag	IS '{"description":"Error of the total magnitude", "unit":"mag", "ucd":"stat.error;phot.mag"}';
COMMENT ON COLUMN photometry.data.method	IS 'Photometry method type (PSF, Kron, etc.)' ;

COMMIT;
