/* pgmigrate-encoding: utf-8 */
BEGIN;

CREATE TABLE layer2.morphology (
  pgc integer PRIMARY KEY REFERENCES common.pgc(id) ON DELETE RESTRICT ON UPDATE CASCADE,
  t real NOT NULL CHECK (t > -6.5 AND t < 11.5),
  em real CHECK (em >= 0),
  ep real CHECK (ep >= 0),
  CHECK ((em IS NULL AND ep IS NULL) OR (em IS NOT NULL AND ep IS NOT NULL))
);

SELECT meta.setparams('layer2', 'morphology', '{"description": "Averaged de Vaucouleurs numeric morphological type", "ucd": "meta.table"}'::json);
SELECT meta.setparams('layer2', 'morphology', 'pgc', '{"description": "PGC identifier", "ucd": "meta.id;meta.main"}'::json);
SELECT meta.setparams('layer2', 'morphology', 't', '{"description": "de Vaucouleurs numerical morphological type", "ucd": "src.morph.type;meta.main"}'::json);
SELECT meta.setparams('layer2', 'morphology', 'em', '{"description": "Lower uncertainty", "ucd": "stat.error"}'::json);
SELECT meta.setparams('layer2', 'morphology', 'ep', '{"description": "Upper uncertainty", "ucd": "stat.error"}'::json);

CREATE INDEX IF NOT EXISTS layer2_morphology_pgc_cover_idx ON layer2.morphology (pgc) INCLUDE (t, em, ep);

INSERT INTO layer2.last_update (dt, catalog) VALUES (to_timestamp(0), 'morphology');

COMMIT;
