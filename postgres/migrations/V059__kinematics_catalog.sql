/* pgmigrate-encoding: utf-8 */

CREATE SCHEMA IF NOT EXISTS kinematics;
SELECT meta.setparams('kinematics', '{"description": "Catalog of galaxy kinematics"}');

CREATE TYPE kinematics.width_method_type AS ENUM (
  'max',
  'peak',
  'w2p',
  'mean',
  'int',
  'edge',
  'model'
);
COMMENT ON TYPE kinematics.width_method_type IS '{
  "description": "Method of the line width measurement",
  "values": {
    "max": "Width measured at a fixed fraction of the global maximum line profile intensity",
    "peak": "Width measured at a fixed fraction of the intensity of each horn independently",
    "w2p": "Width measured at a fixed fraction of the mean intensity of the two profile peaks",
    "mean": "Width measured at a fixed fraction of the mean flux density over the line profile",
    "int": "Width determined from the cumulative (integrated) flux distribution of the line profile",
    "edge": "Width determined from the inferred profile edges",
    "model": "Width derived from a fitted model of the spectral line profile"
  }
}';

CREATE TABLE kinematics.line_width (
  record_id text NOT NULL REFERENCES layer0.records(id) ON UPDATE CASCADE ON DELETE RESTRICT,
  line_id text NOT NULL REFERENCES common.lines(id) ON UPDATE CASCADE ON DELETE RESTRICT,
  width real NOT NULL CHECK (width > 0),
  e_width real CHECK (e_width IS NULL OR e_width >= 0),
  method kinematics.width_method_type NOT NULL DEFAULT 'peak',
  level real NOT NULL DEFAULT 50,
  resolution real NOT NULL CHECK (resolution > 0),
  quality common.quality_type NOT NULL DEFAULT 'regular',
  PRIMARY KEY (record_id, line_id, method, level)
);
CREATE INDEX ON kinematics.line_width (record_id);
CREATE INDEX ON kinematics.line_width (line_id);
CREATE INDEX ON kinematics.line_width (method);

SELECT meta.setparams('kinematics', 'line_width', '{"description": "Catalog of spectral line width measurements"}');
SELECT meta.setparams('kinematics', 'line_width', 'record_id', '{"description": "Record ID"}');
SELECT meta.setparams('kinematics', 'line_width', 'line_id', '{"description": "Spectral line ID"}');
SELECT meta.setparams('kinematics', 'line_width', 'width', '{"description": "Spectral line width", "unit": "km/s", "ucd": "spect.line.width"}');
SELECT meta.setparams('kinematics', 'line_width', 'e_width', '{"description": "Error of the spectral line width", "unit": "km/s", "ucd": "stat.error"}');
SELECT meta.setparams('kinematics', 'line_width', 'method', '{"description": "Width measurement method"}');
SELECT meta.setparams('kinematics', 'line_width', 'level', '{"description": "Reference level expressed as a percentage of the adopted intensity measure"}');
SELECT meta.setparams('kinematics', 'line_width', 'resolution', '{"description": "Effective velocity resolution after smoothing", "unit": "km/s", "ucd": "spect.resolution;phys.veloc"}');
SELECT meta.setparams('kinematics', 'line_width', 'quality', '{"description": "Quality flag of the measurement"}');

GRANT USAGE ON SCHEMA kinematics TO db_reader;
GRANT SELECT ON ALL TABLES IN SCHEMA kinematics TO db_reader;
ALTER DEFAULT PRIVILEGES IN SCHEMA kinematics GRANT SELECT ON TABLES TO db_reader;

GRANT USAGE ON SCHEMA kinematics TO db_writer;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA kinematics TO db_writer;
ALTER DEFAULT PRIVILEGES IN SCHEMA kinematics GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO db_writer;

GRANT USAGE ON SCHEMA kinematics TO db_private_reader;
GRANT SELECT ON ALL TABLES IN SCHEMA kinematics TO db_private_reader;
ALTER DEFAULT PRIVILEGES IN SCHEMA kinematics GRANT SELECT ON TABLES TO db_private_reader;
