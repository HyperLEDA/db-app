/* pgmigrate-encoding: utf-8 */

ALTER TYPE common.quality RENAME VALUE 'ok' TO 'regular';
ALTER TYPE common.quality RENAME VALUE 'lowsnr' TO 'low_snr';
ALTER TYPE common.quality RENAME VALUE 'sus' TO 'suspected';
ALTER TYPE common.quality RENAME VALUE '>' TO 'lower_limit';
ALTER TYPE common.quality RENAME VALUE '<' TO 'upper_limit';
ALTER TYPE common.quality RENAME TO quality_type;

COMMENT ON TYPE common.quality_type IS '{
  "description": "Quality flag of the measurement",
  "values": {
    "regular": "regular measurement",
    "low_snr": "low signal-to-noise",
    "suspected": "suspected measurement",
    "lower_limit": "lower limit",
    "upper_limit": "upper limit",
    "wrong": "wrong measurement"
  }
}';

CREATE TYPE common.line_type AS ENUM (
  'atomic',
  'molecular',
  'recombination',
  'forbidden',
  'fine-structure',
  'hyperfine'
);
COMMENT ON TYPE common.line_type IS '{
  "description": "Classification of spectral lines by their physical origin or transition type",
  "values": {
    "atomic": "Electronic transitions in neutral atoms or ions",
    "molecular": "Rotational or vibrational transitions in molecules",
    "recombination": "Recombination transitions of hydrogen- and helium-like atoms",
    "forbidden": "Forbidden atomic or ionic transitions",
    "fine-structure": "Fine-structure transitions caused by electron spin-orbit interaction",
    "hyperfine": "Hyperfine transitions caused by nuclear spin interaction"
  }
}';

CREATE TABLE common.lines (
  id text PRIMARY KEY,
  species text NOT NULL,
  transition text NOT NULL,
  line_type common.line_type NOT NULL,
  UNIQUE (species, transition)
);

SELECT meta.setparams('common', 'lines', '{"description": "Dictionary of spectral line identifiers"}');
SELECT meta.setparams('common', 'lines', 'id', '{"description": "Line ID"}');
SELECT meta.setparams('common', 'lines', 'species', '{"description": "Atomic, ionic or molecular species"}');
SELECT meta.setparams('common', 'lines', 'transition', '{"description": "Transition"}');
SELECT meta.setparams('common', 'lines', 'line_type', '{"description": "Physical origin or transition type"}');

INSERT INTO common.lines (id, species, transition, line_type) VALUES
  ('HI', 'H', '21 cm', 'hyperfine')
, ('CO(1-0)', 'CO', 'J=1→0', 'molecular')
, ('CO(2-1)', 'CO', 'J=2→1', 'molecular')
, ('OH1612', 'OH', '1612 MHz', 'hyperfine')
, ('OH1665', 'OH', '1665 MHz', 'hyperfine')
, ('OH1667', 'OH', '1667 MHz', 'hyperfine')
, ('OH1720', 'OH', '1720 MHz', 'hyperfine')
, ('Lyalpha', 'H', 'n=2→1', 'recombination')
, ('Halpha', 'H', 'n=3→2', 'recombination')
, ('Hbeta', 'H', 'n=4→2', 'recombination')
, ('Hgamma', 'H', 'n=5→2', 'recombination')
, ('Hdelta', 'H', 'n=6→2', 'recombination')
, ('[OII]3727', 'OII', '²D→⁴S', 'forbidden')
, ('[OIII]4959', 'OIII', '¹D₂→³P₁', 'forbidden')
, ('[OIII]5007', 'OIII', '¹D₂→³P₂', 'forbidden')
, ('[NII]6548', 'NII', '¹D₂→³P₁', 'forbidden')
, ('[NII]6583', 'NII', '¹D₂→³P₂', 'forbidden')
, ('[SII]6716', 'SII', '²D₃/₂→⁴S₃/₂', 'forbidden')
, ('[SII]6731', 'SII', '²D₅/₂→⁴S₃/₂', 'forbidden')
;

CREATE SCHEMA IF NOT EXISTS spectroscopy;
SELECT meta.setparams('spectroscopy', '{"description": "Catalog of the spectroscopy observations"}');

CREATE TYPE spectroscopy.flux_method_type AS ENUM ('sum', 'gauss', 'busy');
COMMENT ON TYPE spectroscopy.flux_method_type IS '{
  "description": "Method of the integrated line flux measurement",
  "values": {
    "sum": "Integrated flux density of the line determined by summing all spectral channels",
    "gauss": "Line flux approximated by gaussian profile",
    "busy": "Profile of the line approximated by busy function"
  }
}';

CREATE TABLE spectroscopy.integrated_flux_density (
  record_id text NOT NULL REFERENCES layer0.records(id) ON UPDATE CASCADE ON DELETE RESTRICT,
  line_id text NOT NULL REFERENCES common.lines(id) ON UPDATE CASCADE ON DELETE RESTRICT,
  flux real NOT NULL,
  e_flux real CHECK (e_flux IS NULL OR e_flux >= 0),
  method spectroscopy.flux_method_type NOT NULL DEFAULT 'sum',
  quality common.quality_type NOT NULL DEFAULT 'regular',
  PRIMARY KEY (record_id, line_id, method)
);
CREATE INDEX ON spectroscopy.integrated_flux_density (record_id);
CREATE INDEX ON spectroscopy.integrated_flux_density (line_id);
CREATE INDEX ON spectroscopy.integrated_flux_density (method);

SELECT meta.setparams('spectroscopy', 'integrated_flux_density', '{"description": "Catalog of the integrated flux densities of the spectral lines"}');
SELECT meta.setparams('spectroscopy', 'integrated_flux_density', 'record_id', '{"description": "Record ID"}');
SELECT meta.setparams('spectroscopy', 'integrated_flux_density', 'line_id', '{"description": "Spectral line ID"}');
SELECT meta.setparams('spectroscopy', 'integrated_flux_density', 'flux', '{"description": "Integrated flux density", "unit": "Jy.km/s", "ucd": "spect.line;phot.flux.density;arith.sum"}');
SELECT meta.setparams('spectroscopy', 'integrated_flux_density', 'e_flux', '{"description": "Error of the integrated flux density", "unit": "Jy.km/s", "ucd": "stat.error"}');
SELECT meta.setparams('spectroscopy', 'integrated_flux_density', 'method', '{"description": "Measurement type (sum, gauss, busy)"}');
SELECT meta.setparams('spectroscopy', 'integrated_flux_density', 'quality', '{"description": "Quality flag of the measurement"}');

CREATE TABLE spectroscopy.energy_flux (
  record_id text NOT NULL REFERENCES layer0.records(id) ON UPDATE CASCADE ON DELETE RESTRICT,
  line_id text NOT NULL REFERENCES common.lines(id) ON UPDATE CASCADE ON DELETE RESTRICT,
  flux real NOT NULL CHECK (flux > 0),
  e_flux real CHECK (e_flux IS NULL OR e_flux >= 0),
  quality common.quality_type NOT NULL DEFAULT 'regular',
  PRIMARY KEY (record_id, line_id)
);
CREATE INDEX ON spectroscopy.energy_flux (record_id);
CREATE INDEX ON spectroscopy.energy_flux (line_id);

SELECT meta.setparams('spectroscopy', 'energy_flux', '{"description": "Catalog of spectral line energy fluxes"}');
SELECT meta.setparams('spectroscopy', 'energy_flux', 'record_id', '{"description": "Record ID"}');
SELECT meta.setparams('spectroscopy', 'energy_flux', 'line_id', '{"description": "Spectral line ID"}');
SELECT meta.setparams('spectroscopy', 'energy_flux', 'flux', '{"description": "Total energy flux in the line", "unit": "erg/cm2/s", "ucd": "spect.line;phot.flux"}');
SELECT meta.setparams('spectroscopy', 'energy_flux', 'e_flux', '{"description": "Error of the total energy flux in the line", "unit": "erg/cm2/s", "ucd": "stat.error"}');
SELECT meta.setparams('spectroscopy', 'energy_flux', 'quality', '{"description": "Quality flag of the measurement"}');

GRANT USAGE ON SCHEMA spectroscopy TO db_reader;
GRANT SELECT ON ALL TABLES IN SCHEMA spectroscopy TO db_reader;
ALTER DEFAULT PRIVILEGES IN SCHEMA spectroscopy GRANT SELECT ON TABLES TO db_reader;

GRANT USAGE ON SCHEMA spectroscopy TO db_writer;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA spectroscopy TO db_writer;
ALTER DEFAULT PRIVILEGES IN SCHEMA spectroscopy GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO db_writer;

GRANT USAGE ON SCHEMA spectroscopy TO db_private_reader;
GRANT SELECT ON ALL TABLES IN SCHEMA spectroscopy TO db_private_reader;
ALTER DEFAULT PRIVILEGES IN SCHEMA spectroscopy GRANT SELECT ON TABLES TO db_private_reader;
