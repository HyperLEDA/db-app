/* pgmigrate-encoding: utf-8 */
CREATE SCHEMA IF NOT EXISTS icrs;

COMMENT ON SCHEMA icrs IS 'Catalog of positions in the International Celestial Reference System';

CREATE TABLE icrs.data (
  id serial PRIMARY KEY,
  pgc integer NOT NULL REFERENCES common.pgc (id) ON DELETE restrict ON UPDATE cascade,
  object_id text NOT NULL REFERENCES rawdata.old_objects (object_id) ON DELETE restrict ON UPDATE cascade,
  ra double precision NOT NULL,
  dec double precision NOT NULL,
  e_ra real NOT NULL,
  e_dec real NOT NULL,
  modification_time timestamp without time zone NOT NULL DEFAULT NOW(),
  CHECK (
    ra >= 0
    and ra < 360
    and dec >= -90
    and dec <= 90
  )
);

CREATE INDEX ON icrs.data (ra, dec);
CREATE INDEX ON icrs.data (pgc);

COMMENT ON TABLE icrs.data IS 'Collection of the object positions in the International Celestial Reference System (ICRS)';
COMMENT ON COLUMN icrs.data.pgc IS 'PGC number of the object';
COMMENT ON COLUMN icrs.data.object_id IS 'ID of the object in original table';
COMMENT ON COLUMN icrs.data.ra IS 'Right Ascension (ICRS) in degrees';
COMMENT ON COLUMN icrs.data.dec IS 'Declination (ICRS) in degrees';
COMMENT ON COLUMN icrs.data.e_ra IS 'Right Ascension error (RAerr*cos(Des) in arcsec';
COMMENT ON COLUMN icrs.data.e_dec IS 'Declination error in arcsec';
COMMENT ON COLUMN icrs.data.modification_time IS 'Timestamp when the record was added to the database';