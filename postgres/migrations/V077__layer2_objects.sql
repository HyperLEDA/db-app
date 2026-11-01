/* pgmigrate-encoding: utf-8 */
BEGIN;

CREATE TABLE layer2.objects (
  pgc integer PRIMARY KEY REFERENCES common.pgc(id) ON DELETE RESTRICT ON UPDATE CASCADE,
  name text NOT NULL,
  objtype text REFERENCES nature.object_type(type_name) ON DELETE RESTRICT ON UPDATE CASCADE,
  ra double precision CHECK (ra >= 0 AND ra < 360),
  dec double precision CHECK (dec >= -90 AND dec <= 90),
  e_ra double precision CHECK (e_ra >= 0),
  e_dec double precision CHECK (e_dec >= 0),
  l double precision CHECK (l >= 0 AND l < 360),
  b double precision CHECK (b >= -90 AND b <= 90),
  sgl double precision CHECK (sgl >= 0 AND sgl < 360),
  sgb double precision CHECK (sgb >= -90 AND sgb <= 90),
  ebv real CHECK (ebv >= 0)
);

SELECT meta.setparams('layer2', 'objects', '{"description": "Main catalogue of astronomical objects in LEDA", "ucd": "meta.table;meta.main"}'::json);
SELECT meta.setparams('layer2', 'objects', 'pgc', '{"description": "Principal Galaxy Catalog identifier", "ucd": "meta.id;meta.main"}'::json);
SELECT meta.setparams('layer2', 'objects', 'name', '{"description": "Principal designation of the object", "ucd": "meta.id"}'::json);
SELECT meta.setparams('layer2', 'objects', 'objtype', '{"description": "Object classification code", "ucd": "meta.code.class"}'::json);
SELECT meta.setparams('layer2', 'objects', 'ra', '{"description": "Right Ascension in the ICRS reference frame", "unit": "deg", "ucd": "pos.eq.ra;meta.main"}'::json);
SELECT meta.setparams('layer2', 'objects', 'dec', '{"description": "Declination in the ICRS reference frame", "unit": "deg", "ucd": "pos.eq.dec;meta.main"}'::json);
SELECT meta.setparams('layer2', 'objects', 'e_ra', '{"description": "One-sigma uncertainty in Right Ascension along RA axis (sigma_RA*cos(Dec))", "unit": "deg", "ucd": "stat.error;pos.eq.ra"}'::json);
SELECT meta.setparams('layer2', 'objects', 'e_dec', '{"description": "One-sigma uncertainty in Declination", "unit": "deg", "ucd": "stat.error;pos.eq.dec"}'::json);
SELECT meta.setparams('layer2', 'objects', 'l', '{"description": "Galactic longitude in the IAU Galactic coordinate system", "unit": "deg", "ucd": "pos.galactic.lon"}'::json);
SELECT meta.setparams('layer2', 'objects', 'b', '{"description": "Galactic latitude in the IAU Galactic coordinate system", "unit": "deg", "ucd": "pos.galactic.lat"}'::json);
SELECT meta.setparams('layer2', 'objects', 'sgl', '{"description": "Supergalactic longitude in the de Vaucouleurs supergalactic coordinate system improved by Lahav et al. (2000MNRAS.312..166L)", "unit": "deg", "ucd": "pos.supergalactic.lon"}'::json);
SELECT meta.setparams('layer2', 'objects', 'sgb', '{"description": "Supergalactic latitude in the de Vaucouleurs supergalactic coordinate system improved by Lahav et al. (2000MNRAS.312..166L)", "unit": "deg", "ucd": "pos.supergalactic.lat"}'::json);
SELECT meta.setparams('layer2', 'objects', 'ebv', '{"description": "Galactic foreground color excess E(B-V) from the Schlegel, Finkbeiner & Davis (1998ApJ...500..525S) map", "unit": "mag", "ucd": "phot.color.excess"}'::json);

CREATE INDEX IF NOT EXISTS layer2_objects_pgc_cover_idx
  ON layer2.objects (pgc) INCLUDE (name, objtype, ra, e_ra, dec, e_dec, l, b, sgl, sgb, ebv);

CREATE INDEX IF NOT EXISTS layer2_objects_geography_idx
  ON layer2.objects USING GIST ((ST_MakePoint(ra, dec)::geography))
  WHERE ra IS NOT NULL AND dec IS NOT NULL;

INSERT INTO layer2.last_update (dt, catalog) VALUES (to_timestamp(0), 'objects');

COMMIT;
