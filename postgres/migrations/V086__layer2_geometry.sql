/* pgmigrate-encoding: utf-8 */
BEGIN;

CREATE TABLE layer2.geometry (
  pgc integer PRIMARY KEY REFERENCES common.pgc(id) ON DELETE RESTRICT ON UPDATE CASCADE,
  a25 real,
  b25 real,
  pa25 real,
  a_re real,
  b_re real,
  pa_re real,
  CHECK (a25 IS NULL OR a25 > 0),
  CHECK (a_re IS NULL OR a_re > 0),
  CHECK (b25 IS NULL OR b25 <= a25),
  CHECK (b_re IS NULL OR b_re <= a_re),
  CHECK (pa25 IS NULL OR (pa25 >= 0 AND pa25 < 180)),
  CHECK (pa_re IS NULL OR (pa_re >= 0 AND pa_re < 180)),
  CHECK (
    (a25 IS NULL AND b25 IS NULL AND pa25 IS NULL)
    OR (a25 IS NOT NULL AND b25 IS NOT NULL AND pa25 IS NOT NULL)
  ),
  CHECK (
    (a_re IS NULL AND b_re IS NULL AND pa_re IS NULL)
    OR (a_re IS NOT NULL AND b_re IS NOT NULL AND pa_re IS NOT NULL)
  ),
  CHECK (a25 IS NOT NULL OR a_re IS NOT NULL)
);

SELECT meta.setparams('layer2', 'geometry', '{"description": "Compiled optical ellipse: B-band d25 and mean half-light radius", "ucd": "meta.table"}'::json);
SELECT meta.setparams('layer2', 'geometry', 'pgc', '{"description": "PGC identifier", "ucd": "meta.id;meta.main"}'::json);
SELECT meta.setparams('layer2', 'geometry', 'a25', '{"description": "Semi-major axis at the B-band 25 mag/arcmin2 isophote", "unit": "arcsec", "ucd": "phys.angSize.smajAxis"}'::json);
SELECT meta.setparams('layer2', 'geometry', 'b25', '{"description": "Semi-minor axis at the B-band 25 mag/arcmin2 isophote", "unit": "arcsec", "ucd": "phys.angSize.sminAxis"}'::json);
SELECT meta.setparams('layer2', 'geometry', 'pa25', '{"description": "Position angle at the B-band 25 mag/arcmin2 isophote, east of north", "unit": "deg", "ucd": "pos.posAng"}'::json);
SELECT meta.setparams('layer2', 'geometry', 'a_re', '{"description": "Mean optical semi-major axis at 50% enclosed flux", "unit": "arcsec", "ucd": "phys.angSize.smajAxis"}'::json);
SELECT meta.setparams('layer2', 'geometry', 'b_re', '{"description": "Mean optical semi-minor axis at 50% enclosed flux", "unit": "arcsec", "ucd": "phys.angSize.sminAxis"}'::json);
SELECT meta.setparams('layer2', 'geometry', 'pa_re', '{"description": "Mean optical position angle at 50% enclosed flux, east of north", "unit": "deg", "ucd": "pos.posAng"}'::json);

CREATE INDEX IF NOT EXISTS layer2_geometry_pgc_cover_idx ON layer2.geometry (pgc) INCLUDE (a25, b25, pa25, a_re, b_re, pa_re);

INSERT INTO layer2.last_update (dt, catalog) VALUES (to_timestamp(0), 'geometry');

COMMIT;
