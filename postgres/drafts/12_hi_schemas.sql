BEGIN;

----------------------------------------------------
-------------- Line Flux schema --------------------
----------------------------------------------------
CREATE SCHEMA IF NOT EXISTS lineflux ;
COMMENT ON SCHEMA lineflux IS 'Catalog of the spectral line fluxes';

CREATE TYPE lineflux.HIMethodType AS ENUM ( 'sum', 'fit' ) ;
COMMENT ON TYPE lineflux.HIMethodType IS '{"sum":"Integrated HI line flux by summing all velocity channels", "fit":"Integrated HI line flux by model line fitting"}' ;


CREATE TABLE lineflux.hi (
  record_id	Text	NOT NULL	REFERENCES layer0.records(id) ON UPDATE cascade ON DELETE restrict
, flux	real	NOT NULL
, e_flux	real
, method	lineflux.HIMethodType	NOT NULL	DEFAULT 'sum'
, PRIMARY KEY (record_id, method)
);
CREATE INDEX ON lineflux.data (record_id) ;
CREATE INDEX ON lineflux.data (method) ;

COMMENT ON TABLE lineflux.hi	IS 'Catalog of the HI line fluxes' ;
COMMENT ON COLUMN lineflux.hi.record_id	IS 'Record ID' ;
COMMENT ON COLUMN lineflux.hi.flux	IS '{"description":"Integrated HI line flux", "unit":"Jy.km/s", "ucd":"phot.flux.density;spect.line"}' ;
COMMENT ON COLUMN lineflux.hi.e_flux	IS '{"description":"Error of the integrated HI line flux", "unit":"Jy.km/s", "ucd":"stat.error"}' ;
COMMENT ON COLUMN lineflux.hi.method	IS 'Measurement type (sum, fit)' ;


CREATE OR REPLACE VIEW lineflux.hiview AS
SELECT
  d.flux
, d.e_flux
, d.method
, r.*
FROM
  lineflux.hi AS d
  LEFT JOIN layer0.recordview AS r USING (record_id)
;

COMMENT ON TABLE lineflux.hiview	IS 'Catalog of the HI line fluxes' ;
COMMENT ON COLUMN lineflux.hiview.record_id	IS 'Record ID' ;
COMMENT ON COLUMN lineflux.hiview.flux	IS '{"description":"Integrated HI line flux", "unit":"Jy.km/s", "ucd":"phot.flux.density;spect.line"}' ;
COMMENT ON COLUMN lineflux.hiview.e_flux	IS '{"description":"Error of the integrated HI line flux", "unit":"Jy.km/s", "ucd":"stat.error"}' ;
COMMENT ON COLUMN lineflux.hiview.method	IS 'Measurement type (sum, fit)' ;



----------------------------------------------------
-------------- Line Width schema -------------------
----------------------------------------------------
CREATE SCHEMA IF NOT EXISTS linewidth ;
COMMENT ON SCHEMA linewidth IS 'Catalog of the HI line width' ;


CREATE TYPE linewidth.WidthMethodType AS ENUM ( 'max', 'peak', 'w2p', 'mean', 'int', 'edge', 'model' ) ;
COMMENT ON TYPE linewidth.WidthMethodType IS '{"max":"Maximal-value-based width", "peak":"Every peak-based width", "w2p":"Mean of peaks double-horn specific width", "mean":"Mean-flux–based width", "int":"Integrated-flux–based width", "edge":"Edge-based width", "model":"Model-based width"}' ;

CREATE TABLE linewidth.data (
  record_id	Text	NOT NULL	REFERENCES layer0.records(id) ON UPDATE cascade ON DELETE restrict
, width	real	NOT NULL
, e_width	real
, method	linewidth.WidthMethodType	NOT NULL	DEFAULT 'peak'
, level	real	NOT NULL	DEFAULT 50
, PRIMARY KEY (record_id, method, level)
);
CREATE INDEX ON lineflux.data (record_id) ;
CREATE INDEX ON lineflux.data (method) ;

COMMENT ON TABLE linewidth.data	IS 'Catalog of the HI line width' ;
COMMENT ON COLUMN linewidth.data.record_id	IS 'Record ID' ;
COMMENT ON COLUMN linewidth.data.flux	IS '{"description":"HI line width", "unit":"km/s", "ucd":"spect.line.width"}' ;
COMMENT ON COLUMN linewidth.data.e_flux	IS '{"description":"Error of the HI line width", "unit":"km/s", "ucd":"stat.error"}' ;
COMMENT ON COLUMN linewidth.data.method	IS 'Measurement type' ;
COMMENT ON COLUMN linewidth.data.level	IS 'Measurement level in percent' ;


CREATE TABLE linewidth.dataset (
  table_id	Integer	PRIMARY KEY	REFERENCES layer0.tables(id) ON UPDATE cascade ON DELETE restrict
, telescope	Text	NOT NULL
, resolution	real	NOT NULL
, correction	boolean	NOT NULL	DEFAULT false
);

COMMENT ON TABLE linewidth.dataset	IS 'Description of the data on the HI line width' ;
COMMENT ON COLUMN linewidth.dataset.table_id	IS 'Table ID' ;
COMMENT ON COLUMN linewidth.dataset.telescope	IS 'Rdio telescope' ; -- It seems we need a special table on telescopes
COMMENT ON COLUMN linewidth.dataset.resolution	IS '{"description":"Effective spectral resolution for the HI line width correction", "unit":"km/s", "ucd":"spect.resolution"}' ;
COMMENT ON COLUMN linewidth.dataset.correction	IS 'The flag describing if the spectral resolution correction is already applied' ;



CREATE OR REPLACE VIEW linewidth.dataview AS
SELECT
  d.width
, d.e_width
, d.method
, d.level
, s.telescope
, s.resolution
, s.correction
, r.*
FROM
  linewidth.data AS d
  LEFT JOIN layer0.recordview AS r USING (record_id)
  LEFT JOIN linewidth.dataset AS s USING (table_id)
;

COMMIT;