BEGIN;

----------------------------------------------------
-------------- Radio Observations schema -----------
----------------------------------------------------
CREATE SCHEMA IF NOT EXISTS radio ;
COMMENT ON SCHEMA radio IS 'Catalog of the radio observations';

CREATE TYPE radio.FluxMethodType AS ENUM ( 'sum', 'fit' ) ;
COMMENT ON TYPE radio.FluxMethodType IS '{"sum":"Integrated radio line flux by summing all velocity channels", "fit":"Integrated radio line flux by model line fitting"}' ;

CREATE TYPE radio.VelConventionType AS ENUM ( 'optical', 'radio', 'relativistic' ) ;
COMMENT ON TYPE radio.VelConventionType IS '{"optical":"Voptical=c(λ-λ0)/λ0=cz", "radio":"Vradio=c(ν0-ν)/ν0; cz=Vradio/(1-Vradio/c)", "relativistic":"Relativistic Doppler effect: V=c(ν0^2-ν^2)/(ν0^2+ν^2)=c(λ^2-λ0^2)/(λ^2+λ0^2)=c[(1+z)^2-1]/[(1+z)^2+1]"}' ;

CREATE TYPE radio.WidthMethodType AS ENUM ( 'max', 'peak', 'w2p', 'mean', 'int', 'edge', 'model' ) ;
COMMENT ON TYPE radio.WidthMethodType IS '{"max":"Maximal-value-based width", "peak":"Every peak-based width", "w2p":"Mean of peaks double-horn specific width", "mean":"Mean-flux–based width", "int":"Integrated-flux–based width", "edge":"Edge-based width", "model":"Model-based width"}' ;




------------ Radio lines -------------------
CREATE TABLE radio.lines (
  id	Text	PRIMARY KEY
, species	Text	NOT NULL
, transition	Text	NOT NULL
, frequency	Real	NOT NULL
, UNIQUE (species,transition)
);

COMMENT ON TABLE radio.lines	IS 'List of radio lines' ;
COMMENT ON COLUMN radio.lines.id	IS 'Line ID' ;
COMMENT ON COLUMN radio.lines.species	IS 'Designation of atoms and molecules' ;
COMMENT ON COLUMN radio.lines.transition	IS 'Transition' ;
COMMENT ON COLUMN radio.lines.frequency	IS '{"description":"Line frequency", "unit":"Hz", "ucd":"em.freq"}' ;

INSERT INTO radio.lines (id,species,transition,frequency) VALUES 
  ('HI', 'HI', '21 cm', 1420.4058e6)
, ('CO(1-0)', 'CO', '(1-0)', 115.271)
, ('CO(2-1)', 'CO', '(2-1)', 230.538)
, ('OH 1612 MHz', 'OH', '1612 MHz', 1612.231e6)
, ('OH 1665 MHz', 'OH', '1665 MHz', 1665.402e6)
, ('OH 1667 MHz', 'OH', '1667 MHz', 1667.359e6)
, ('OH 1720 MHz', 'OH', '1612 MHz', 1720.530e6)
;


------------- Telescopes --------------------
CREATE TABLE radio.telescopes (
  id	Text	PRIMARY KEY
, description	Text	NOT NULL
) ;

COMMENT ON TABLE radio.telescopes	IS 'List of radio lines' ;
COMMENT ON COLUMN radio.telescopes.id	IS 'Telescope ID' ;
COMMENT ON COLUMN radio.telescopes.description	IS 'Telescope description' ;

INSERT INTO radio.telescopes (id,description) VALUES
  ('Nancay', 'Large radio telescope of the Nançay Radio Observatory')
, ('WSRT',   'Westerbork Synthesis Radio Telescope')
, ('GB140ft', 'NRAO Green Bank (43m, 140ft)')
, ('GB300ft', 'NRAO Green Bank (91m, 300ft)')
, ('GBT',     'Robert C. Byrd Green Bank Telescope (100m)')
, ('Effelsberg', 'Effelsberg Radio Telescope (100m)')
, ('Arecibo', 'Arecibo Telescope (305m, 1000ft)')
, ('Parkes',  'Murriyang, Parkes 64m Radio Telescope')
, ('ATCA',    'Australia Telescope Compact Array')
, ('GMRT',    'Giant Metrewave Radio Telescope')
, ('FAST',    'Five-hundred-meter Aperture Spherical Telescope')
, ('VLA',     'Karl G. Jansky Very Large Array')
, ('VLA A',   'A-configuration of the Karl G. Jansky Very Large Array')
, ('VLA B',   'B-configuration of the Karl G. Jansky Very Large Array')
, ('VLA C',   'C-configuration of the Karl G. Jansky Very Large Array')
, ('VLA D',   'A-configuration of the Karl G. Jansky Very Large Array')
;


------------- Data sets ---------------------
CREATE TABLE radio.datasets (
  id	Integer	PRIMARY KEY
, table_id	Integer	NOT NULL	REFERENCES layer0.tables (id) ON DELETE restrict ON UPDATE cascade
, telescope_id	Text	NOT NULL	REFERENCES radio.telescopes (id) ON DELETE restrict ON UPDATE cascade
, line_id	Text	NOT NULL	DEFAULT 'HI'
, resolution	real	NOT NULL
, velocity_convention	radio.VelConventionType	NOT NULL	DEFAULT 'optical'
, flux_correction	boolean	NOT NULL	DEFAULT false
, resolution_correction	boolean	NOT NULL	DEFAULT false
, redshift_correction	boolean	NOT NULL	DEFAULT false
) ;

COMMENT ON TABLE radio.datasets	IS 'Dataset description' ;
COMMENT ON COLUMN radio.datasets.id	IS 'Dataset ID' ;
COMMENT ON COLUMN radio.datasets.table_id	IS 'Original data table ID' ;
COMMENT ON COLUMN radio.datasets.telescope_id	IS 'Telescope ID' ;
COMMENT ON COLUMN radio.datasets.line_id	IS 'Spectral line ID' ;
COMMENT ON COLUMN radio.datasets.resolution	IS '{"description":"Effective spectral resolution", "unit":"km/s", "ucd":"spect.resolution"}' ;
COMMENT ON COLUMN radio.datasets.flux_correction	IS 'Indication if the flux was corrected for the beam filling factor' ;
COMMENT ON COLUMN radio.datasets.resolution_correction	IS 'Indication if the line width was corrected for the spectral resolution' ;
COMMENT ON COLUMN radio.datasets.redshift_correction	IS 'Indication if the line width was corrected for the cosmological broadening' ;


------------- Line flux ---------------------
CREATE TABLE radio.line_flux (
  record_id	Text	NOT NULL	REFERENCES layer0.records(id) ON UPDATE cascade ON DELETE restrict
, flux	real	NOT NULL
, e_flux	real
, method	radio.line_fluxMethodType	NOT NULL	DEFAULT 'sum'
, PRIMARY KEY (record_id, method)
);
CREATE INDEX ON radio.line_flux (record_id) ;
CREATE INDEX ON radio.line_flux (method) ;

COMMENT ON TABLE radio.line_flux	IS 'Catalog of the radio line fluxes' ;
COMMENT ON COLUMN radio.line_flux.record_id	IS 'Record ID' ;
COMMENT ON COLUMN radio.line_flux.flux	IS '{"description":"Integrated radio line flux", "unit":"Jy.km/s", "ucd":"phot.flux.density;spect.line"}' ;
COMMENT ON COLUMN radio.line_flux.e_flux	IS '{"description":"Error of the integrated radio line flux", "unit":"Jy.km/s", "ucd":"stat.error"}' ;
COMMENT ON COLUMN radio.line_flux.method	IS 'Measurement type (sum, fit)' ;


------------- Line flux ---------------------
-- CREATE TABLE radio.continuum_flux (
--   record_id	Text	NOT NULL	REFERENCES layer0.records(id) ON UPDATE cascade ON DELETE restrict
-- , flux	real	NOT NULL
-- , e_flux	real
-- , frequency	real	NOT NULL
-- , bandwidth	real	NOT NULL
-- , PRIMARY KEY (record_id, frequency)
-- );
-- CREATE INDEX ON radio.data (record_id) ;
-- CREATE INDEX ON radio.data (method) ;
-- 
-- COMMENT ON TABLE radio.continuum_flux	IS 'Catalog of the radio continuum fluxes' ;
-- COMMENT ON COLUMN radio.continuum_flux.record_id	IS 'Record ID' ;
-- COMMENT ON COLUMN radio.continuum_flux.flux	IS '{"description":"Flux density", "unit":"Jy", "ucd":"phot.flux.density;spect.line"}' ;
-- COMMENT ON COLUMN radio.continuum_flux.e_flux	IS '{"description":"Error of the flux density", "unit":"Jy", "ucd":"stat.error"}' ;
-- COMMENT ON COLUMN radio.continuum_flux.frequency	IS '{"description":"Frequency", "unit":"Hz", "ucd":"em.freq"}' ;
-- COMMENT ON COLUMN radio.continuum_flux.frequency	IS '{"description":"Bandwidth", "unit":"Hz", "ucd":"em.freq"}' ;


------------- Line Width ---------------------
CREATE TABLE radio.line_width (
  record_id	Text	NOT NULL	REFERENCES layer0.records(id) ON UPDATE cascade ON DELETE restrict
, width	real	NOT NULL
, e_width	real
, method	radio.WidthMethodType	NOT NULL	DEFAULT 'peak'
, level	real	NOT NULL	DEFAULT 50
, PRIMARY KEY (record_id, method, level)
);
CREATE INDEX ON radio.data (record_id) ;
CREATE INDEX ON radio.data (method) ;

COMMENT ON TABLE radio.line_width	IS 'Catalog of the HI line width' ;
COMMENT ON COLUMN radio.line_width.record_id	IS 'Record ID' ;
COMMENT ON COLUMN radio.line_width.flux	IS '{"description":"HI line width", "unit":"km/s", "ucd":"spect.line.width"}' ;
COMMENT ON COLUMN radio.line_width.e_flux	IS '{"description":"Error of the HI line width", "unit":"km/s", "ucd":"stat.error"}' ;
COMMENT ON COLUMN radio.line_width.method	IS 'Measurement type' ;
COMMENT ON COLUMN radio.line_width.level	IS 'Measurement level in percent' ;


COMMIT;