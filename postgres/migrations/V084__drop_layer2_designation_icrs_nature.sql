/* pgmigrate-encoding: utf-8 */
BEGIN;

DROP TABLE IF EXISTS layer2.designation;
DROP TABLE IF EXISTS layer2.icrs;
DROP TABLE IF EXISTS layer2.nature;

DELETE FROM layer2.last_update WHERE catalog IN ('designation', 'icrs', 'nature');

CREATE INDEX IF NOT EXISTS layer2_objects_name_idx ON layer2.objects (name);

COMMIT;
