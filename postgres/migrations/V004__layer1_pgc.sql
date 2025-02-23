/* pgmigrate-encoding: utf-8 */

CREATE SCHEMA IF NOT EXISTS pgc;
COMMENT ON SCHEMA pgc IS 'The list of Principal Galaxy Catalog (PGC) numbers used as the primary identifier for objects in the database.';

CREATE TABLE pgc.data (
  object_id text REFERENCES rawdata.objects
, id integer
, PRIMARY KEY (object_id)
);
