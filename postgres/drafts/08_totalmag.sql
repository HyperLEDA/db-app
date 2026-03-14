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
DROP SCHEMA IF EXISTS totalmag CASCADE;
CREATE SCHEMA IF NOT EXISTS totalmag;
COMMENT ON SCHEMA totalmag IS 'Catalog of the total magnitudes';


CREATE TYPE common.MagMethodType AS ENUM ( 'psf', 'visual', 'aperture', 'isophotal','asymptotic', 'model', 'petrosian', 'kron' ) ;
COMMENT ON TYPE common.MagMethodType IS '{ "psf":"Point Spread Function photometry for the point source", "visual":"Visual estimate", "aperture":"Aperture photometry", "isophotal":"Magnitude measurement inside a specified isophote", "asymptotic":"Asymptotic (extrapolated) magnitude when the aperture size -> Inf", "model":"Best fit model of the light distribution", "petrosian":"Petrosian adaptively scaled aperture", "kron":"Kron adaptively scaled aperture" }' ;


CREATE TABLE totalmag.data (
  record_id	Text	NOT NULL	REFERENCES layer0.records(id) ON UPDATE cascade ON DELETE restrict
, band	text	NOT NULL	REFERENCES photsys.data (id) ON DELETE restrict ON UPDATE cascade
, mag	real	NOT NULL	CHECK ( mag > -1 and mag < 30 )
, e_mag	real	CHECK ( e_mag > 0 and e_mag < 0.5 )
, method	common.MagMethodType	NOT NULL	CHECK (method IN ('psf','visual','asymptotic', 'model', 'petrosian', 'kron'))
, datatype	common.DataType	NOT NULL
, PRIMARY KEY (record_id, band, method)
);
CREATE INDEX IF NOT EXISTS ON totalmag (band) ;
CREATE INDEX IF NOT EXISTS ON totalmag (method) ;
CREATE INDEX IF NOT EXISTS ON totalmag (datatype) ;

COMMENT ON TABLE totalmag.data	IS 'Catalog of the total magnitudes';
COMMENT ON COLUMN totalmag.data.record_id	IS 'Record ID';
COMMENT ON COLUMN totalmag.data.band	IS 'Calibrated passband ID';
COMMENT ON COLUMN totalmag.data.mag	IS '{"description":"Total (PSF|model|asymptotic|etc.) magnitude", "unit":"mag", "ucd":"phot.mag"}';
COMMENT ON COLUMN totalmag.data.e_mag	IS '{"description":"Error of the total magnitude", "unit":"mag", "ucd":"stat.error;phot.mag"}';
COMMENT ON COLUMN totalmag.data.method	IS 'Photometry method type (PSF, Kron, etc.)' ;
COMMENT ON COLUMN totalmag.data.datatype	IS 'Types of the data (regular,reprocessing,preliminary,compilation)' ;


CREATE OR REPLACE VIEW totalmag.dataview AS
SELECT
  r.pgc
, d.band
, d.mag
, d.e_mag
, s.magsys
, d.method
, d.datatype

, s.band	AS band_id
, s.name	AS filter
, s.waveref
, s.fwhm
, s.relext
, s.photsys

, d.record_id
, d.table_id
, d.table_name

, d.bib
, b.code	AS bibcode
, b.year
, b.author
, b.title
FROM
  totalmag.data AS d
  LEFT JOIN layer0.records AS r ON (d.record_id = r.id)
  LEFT JOIN layer0.tables  AS t ON (d.table_id = t.id)
  LEFT JOIN common.bib AS b ON (t.bib = b.id)
  LEFT JOIN photsys.dataview AS s ON (d.band=s.id)
;

COMMENT ON VIEW totalmag.dataview	IS 'Catalog of the total magnitudes';
COMMENT ON COLUMN totalmag.dataview.pgc	IS 'PGC-number' ;
COMMENT ON COLUMN totalmag.dataview.band	IS 'Calibrated passband ID';
COMMENT ON COLUMN totalmag.dataview.mag	IS '{"description":"Total (PSF|model|asymptotic|etc.) magnitude", "unit":"mag", "ucd":"phot.mag"}';
COMMENT ON COLUMN totalmag.dataview.e_mag	IS '{"description":"Error of the total magnitude", "unit":"mag", "ucd":"stat.error;phot.mag"}';
COMMENT ON COLUMN totalmag.dataview.method	IS 'Photometry method type (PSF, Kron, etc.)' ;
COMMENT ON COLUMN totalmag.dataview.datatype	IS 'Types of the data (regular,reprocessing,preliminary,compilation)' ;

COMMENT ON COLUMN totalmag.dataview.band_id	IS 'Passband ID';
COMMENT ON COLUMN totalmag.dataview.filter	IS 'Common filter name';
COMMENT ON COLUMN totalmag.dataview.waveref IS 'The reference wavelength of the filter transmission' ;
COMMENT ON COLUMN totalmag.dataview.fwhm    IS 'The Full Width Half Maximum of the filter transmission' ;
COMMENT ON COLUMN totalmag.dataview.relext  IS 'Relative extinction. Ratio between extintion at λref, Af, and visual extintion, Av' ;
COMMENT ON COLUMN totalmag.dataview.photsys IS 'Photometric system' ;

COMMENT ON COLUMN totalmag.dataview.record_id	IS 'Record ID';
COMMENT ON COLUMN totalmag.dataview.bibcode	IS '{"description" : "ADS bibcode", "url" : "https://ui.adsabs.harvard.edu/abs/", "ucd" : "meta.ref.url"}' ;

COMMIT;