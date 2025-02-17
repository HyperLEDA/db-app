/* pgmigrate-encoding: utf-8 */
CREATE SCHEMA IF NOT EXISTS cz;

COMMENT ON SCHEMA cz IS 'Heliocentric Redshift catalog';

CREATE TABLE cz.data (
  id serial PRIMARY KEY,
  pgc integer NOT NULL REFERENCES common.pgc (id) ON DELETE restrict ON UPDATE cascade,
  object_id text NOT NULL REFERENCES rawdata.objects (object_id) ON DELETE restrict ON UPDATE cascade,
  cz real NOT NULL,
  e_cz real,
  modification_time timestamp without time zone NOT NULL DEFAULT now()
);

COMMENT ON TABLE cz.data IS 'Redshift measurement catalog';

COMMENT ON COLUMN cz.data.id IS 'ID of the measurement';

COMMENT ON COLUMN cz.data.pgc IS 'PGC number of the object';

COMMENT ON COLUMN cz.data.cz IS 'Heliocentric/Barycentric redshift (cz) in km/s in the optical convention: z = (λ-λ0)/λ0';

COMMENT ON COLUMN cz.data.e_cz IS 'cz measurement error in km/s';

COMMENT ON COLUMN cz.data.modification_time IS 'Timestamp when the record was added to the database';