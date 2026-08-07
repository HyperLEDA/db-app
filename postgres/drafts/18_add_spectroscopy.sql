BEGIN;

------------ Spectral lines -------------------
CREATE TYPE common.LineType AS ENUM ( 'atomic', 'molecular', 'recombination', 'forbidden', 'fine-structure', 'hyperfine' );
COMMENT ON TYPE common.LineType IS '{
"description": "Classification of spectral lines by their physical origin or transition type",
"values": {
  "atomic": "Electronic transitions in neutral atoms or ions",
  "molecular": "Rotational or vibrational transitions in molecules",
  "recombination": "Recombination transitions of hydrogen- and helium-like atoms",
  "forbidden": "Forbidden atomic or ionic transitions",
  "fine-structure": "Fine-structure transitions caused by electron spin-orbit interaction",
  "hyperfine": "Hyperfine transitions caused by nuclear spin interaction"
  }
}' ;


CREATE TABLE common.lines (
  id	Text	PRIMARY KEY
, species	Text	NOT NULL
, transition	Text	NOT NULL
, line_type	common.LineType	NOT NULL
, UNIQUE (species,transition)
);

COMMENT ON TABLE common.lines	IS 'Dictionary of spectral line identifiers' ;
COMMENT ON COLUMN common.lines.id	IS 'Line ID' ;
COMMENT ON COLUMN common.lines.species	IS 'Atomic, ionic or molecular species' ;
COMMENT ON COLUMN common.lines.transition	IS 'Transition' ;
COMMENT ON COLUMN common.lines.line_type	IS 'Physical origin or transition type' ;


INSERT INTO common.lines (id,species,transition,line_type) VALUES 
  ('HI', 'H', '21 cm', 'hyperfine' )

, ('CO(1-0)', 'CO', 'J=1→0', 'molecular' )
, ('CO(2-1)', 'CO', 'J=2→1', 'molecular' )

, ('OH1612', 'OH', '1612 MHz', 'hyperfine' )
, ('OH1665', 'OH', '1665 MHz', 'hyperfine' )
, ('OH1667', 'OH', '1667 MHz', 'hyperfine' )
, ('OH1720', 'OH', '1720 MHz', 'hyperfine' )

, ('Lyalpha', 'H', 'n=2→1', 'recombination')

, ('Halpha', 'H', 'n=3→2', 'recombination' )
, ('Hbeta',  'H', 'n=4→2', 'recombination' )
, ('Hgamma', 'H', 'n=5→2', 'recombination' )
, ('Hdelta', 'H', 'n=6→2', 'recombination' )

, ('[OII]3727', 'OII', '²D→⁴S', 'forbidden')
, ('[OIII]4959', 'OIII', '¹D₂→³P₁', 'forbidden' )
, ('[OIII]5007', 'OIII', '¹D₂→³P₂', 'forbidden' )

, ('[NII]6548', 'NII', '¹D₂→³P₁', 'forbidden' )
, ('[NII]6583', 'NII', '¹D₂→³P₂', 'forbidden' )

, ('[SII]6716', 'SII', '²D₃/₂→⁴S₃/₂', 'forbidden')
, ('[SII]6731', 'SII', '²D₅/₂→⁴S₃/₂', 'forbidden')
;


----------------------------------------------------
-------------- Spectroscopy schema -----------------
----------------------------------------------------
CREATE SCHEMA IF NOT EXISTS spectroscopy ;
COMMENT ON SCHEMA spectroscopy IS 'Catalog of the spectroscopy observations';

CREATE TYPE spectroscopy.FluxMethodType AS ENUM ( 'sum', 'gauss', 'busy' ) ;
COMMENT ON TYPE spectroscopy.FluxMethodType	IS '{
"description": "Method of the integrated line flux measurement",
"values": {
  "sum": "Integrated flux density of the line determined by summing all spectral channels", 
  "gauss": "Line flux approximated by gaussian profile",
  "busy": "Profile of the line approximated by busy function"
  }
}' ;


------------- Line flux ---------------------
CREATE TABLE spectroscopy.integrated_flux_density (
  record_id	Text	NOT NULL	REFERENCES layer0.records(id) ON UPDATE cascade ON DELETE restrict
, line_id	Text	NOT NULL	REFERENCES common.lines(id) ON UPDATE cascade ON DELETE restrict
, flux	real	NOT NULL
, e_flux	real
, method	spectroscopy.FluxMethodType	NOT NULL	DEFAULT 'sum'
, quality	common.QualityType	NOT NULL	DEFAULT 'regular'
, PRIMARY KEY (record_id, line_id, method)
);
CREATE INDEX ON spectroscopy.integrated_flux_density (record_id) ;
CREATE INDEX ON spectroscopy.integrated_flux_density (line_id) ;
CREATE INDEX ON spectroscopy.integrated_flux_density (method) ;
CREATE INDEX ON spectroscopy.integrated_flux_density (quality) ;

COMMENT ON TABLE  spectroscopy.integrated_flux_density	IS 'Catalog of the integrated flux densities of the spectral lines' ;
COMMENT ON COLUMN spectroscopy.integrated_flux_density.record_id	IS 'Record ID' ;
COMMENT ON COLUMN spectroscopy.integrated_flux_density.line_id	IS 'Spectral line ID' ;
COMMENT ON COLUMN spectroscopy.integrated_flux_density.flux	IS '{"description":"Integrated flux density", "unit":"Jy.km/s", "ucd":"spect.line;phot.flux.density;arith.sum"}' ;
COMMENT ON COLUMN spectroscopy.integrated_flux_density.e_flux	IS '{"description":"Error of the integrated flux density", "unit":"Jy.km/s", "ucd":"stat.error"}' ;
COMMENT ON COLUMN spectroscopy.integrated_flux_density.method	IS 'Measurement type (sum, gauss, busy)' ;



CREATE TABLE spectroscopy.energy_flux (
  record_id	Text	NOT NULL	REFERENCES layer0.records(id) ON UPDATE cascade ON DELETE restrict
, line_id	Text	NOT NULL	REFERENCES common.lines(id) ON UPDATE cascade ON DELETE restrict
, flux	real	NOT NULL
, e_flux	real
, quality	common.QualityType	NOT NULL	DEFAULT 'regular'
, PRIMARY KEY (record_id, line_id)
);
CREATE INDEX ON spectroscopy.energy_flux (record_id) ;
CREATE INDEX ON spectroscopy.energy_flux (line_id) ;
CREATE INDEX ON spectroscopy.energy_flux (quality) ;

COMMENT ON TABLE  spectroscopy.energy_flux	IS 'Catalog of spectral line energy fluxes' ;
COMMENT ON COLUMN spectroscopy.energy_flux.record_id	IS 'Record ID' ;
COMMENT ON COLUMN spectroscopy.energy_flux.line_id	IS 'Spectral line ID' ;
COMMENT ON COLUMN spectroscopy.energy_flux.flux	IS '{"description":"Total energy flux in the line", "unit":"erg/cm2/s", "ucd":"spect.line;phot.flux"}' ;
COMMENT ON COLUMN spectroscopy.energy_flux.e_flux	IS '{"description":"Error of the total energy flux in the line", "unit":"erg/cm2/s", "ucd":"stat.error"}' ;

COMMIT;
