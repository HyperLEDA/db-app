/* pgmigrate-encoding: utf-8 */
BEGIN;

CREATE TABLE layer2.data (
  pgc       integer PRIMARY KEY REFERENCES common.pgc(id) ON DELETE CASCADE ON UPDATE CASCADE
, design    text
, ra        double precision
, e_ra      real
, dec       double precision
, e_dec     real
, type_name text REFERENCES nature.object_type(type_name)
, bt        real
, e_bt      real
, d25       real CHECK (d25 > 0)
, ba        real CHECK (ba > 0 AND ba <= 1)
);

CREATE INDEX data_geography_idx
  ON layer2.data USING GIST ((ST_MakePoint(ra, dec)::geography));

INSERT INTO layer2.last_update (dt, catalog) VALUES (to_timestamp(0), 'data');

SELECT meta.setparams('layer2', 'data', '{"description": "Summary of information about PGC objects"}');
SELECT meta.setparams('layer2', 'data', 'pgc', '{"description": "PGC identifier", "ucd": "meta.id;meta.main"}');
SELECT meta.setparams('layer2', 'data', 'design', '{"description": "Main designation", "ucd": "meta.id"}');
SELECT meta.setparams('layer2', 'data', 'ra', '{"description": "Right ascension (ICRS)", "unit": "deg", "ucd": "pos.eq.ra;meta.main"}');
SELECT meta.setparams('layer2', 'data', 'e_ra', '{"description": "Right ascension error", "unit": "deg", "ucd": "stat.error;pos.eq.ra"}');
SELECT meta.setparams('layer2', 'data', 'dec', '{"description": "Declination (ICRS)", "unit": "deg", "ucd": "pos.eq.dec;meta.main"}');
SELECT meta.setparams('layer2', 'data', 'e_dec', '{"description": "Declination error", "unit": "deg", "ucd": "stat.error;pos.eq.dec"}');
SELECT meta.setparams('layer2', 'data', 'type_name', '{"description": "Object type code", "ucd": "src.class"}');
SELECT meta.setparams('layer2', 'data', 'bt', '{"description": "Total B magnitude", "unit": "mag", "ucd": "phot.mag;em.opt.B"}');
SELECT meta.setparams('layer2', 'data', 'e_bt', '{"description": "Error of the total B magnitude", "unit": "mag", "ucd": "stat.error;phot.mag;em.opt.B"}');
SELECT meta.setparams('layer2', 'data', 'd25', '{"description": "Diameter at the 25 mag/arcsec² B-band isophote", "unit": "arcsec", "ucd": "phys.angSize;src"}');
SELECT meta.setparams('layer2', 'data', 'ba', '{"description": "Minor-to-major axis ratio at the 25 mag/arcsec² B-band isophote", "ucd": "phys.size.axisRatio"}');

COMMIT;
