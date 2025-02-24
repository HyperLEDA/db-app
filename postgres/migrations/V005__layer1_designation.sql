/* pgmigrate-encoding: utf-8 */
CREATE SCHEMA IF NOT EXISTS designation;

COMMENT ON SCHEMA designation IS 'Designation catalog';

CREATE TABLE designation.data (
  object_id text PRIMARY KEY REFERENCES rawdata.objects (id),
  design text NOT NULL,
  modification_time timestamp without time zone NOT NULL DEFAULT NOW()
);

CREATE INDEX ON designation.data (upper(replace(design, ' ', '')));

COMMENT ON TABLE designation.data IS 'List of unique object names';
COMMENT ON COLUMN designation.data.object_id IS 'ID of the object in original table';
COMMENT ON COLUMN designation.data.design IS '{"description" : "Unique designation the object. It must follow the IAU recommendations: https://cdsweb.u-strasbg.fr/Dic/iau-spec.html" , "ucd" : "meta.id"}';
COMMENT ON COLUMN designation.data.modification_time IS '{"description" : "Timestamp when the record was added to the database" , "ucd" : "time.creation"}';