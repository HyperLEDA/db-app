/* pgmigrate-encoding: utf-8 */

CREATE SCHEMA IF NOT EXISTS pgc;
COMMENT ON SCHEMA pgc IS 'The list of Principal Galaxy Catalog (PGC) numbers used as the primary identifier for objects in the database.';

CREATE OR REPLACE FUNCTION pgc.next_id() RETURNS integer AS $$
DECLARE
  next_id integer;
BEGIN
  SELECT MAX(id) + 1 INTO next_id FROM pgc.data;
  RETURN COALESCE(next_id, 1);
END;
$$ LANGUAGE plpgsql;

CREATE TABLE pgc.data (
  object_id text REFERENCES rawdata.objects (id)
, id integer NOT NULL DEFAULT pgc.next_id()
, PRIMARY KEY (object_id)
);
