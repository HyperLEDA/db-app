/* pgmigrate-encoding: utf-8 */
CREATE SCHEMA IF NOT EXISTS nature;

COMMENT ON SCHEMA nature IS 'Nature of the object';

CREATE TYPE nature.status AS ENUM(
  'g',
  'gg',
  's',
  'gs',
  'ie',
  'o',
  'nd'
);

COMMENT ON TYPE nature.status IS '{
  "g": "Galaxy",
  "gg": "Group of galaxies",
  "s": "Star",
  "gs": "Group of stars",
  "ie": "Interstellar environment",
  "o": "Other",
  "nd": "Not defined"
}';

CREATE TABLE nature.data (
  id serial PRIMARY KEY,
  pgc integer NOT NULL REFERENCES common.pgc (id) ON DELETE restrict ON UPDATE cascade,
  status nature.status NOT NULL DEFAULT 'nd',
  bib integer NOT NULL REFERENCES common.bib (id) ON DELETE restrict ON UPDATE cascade
);

CREATE INDEX ON nature.data (pgc);

CREATE INDEX ON nature.data (status);

COMMENT ON TABLE nature.data IS 'Nature of the object';

COMMENT ON COLUMN nature.data.id IS 'ID of the position';

COMMENT ON COLUMN nature.data.pgc IS 'PGC number of the object';

COMMENT On COLUMN nature.data.status IS 'Object status';

COMMENT ON COLUMN nature.data.bib IS 'Bibliography reference';