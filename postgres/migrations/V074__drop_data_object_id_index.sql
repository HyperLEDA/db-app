BEGIN;

ALTER TABLE designation.data DROP CONSTRAINT IF EXISTS data_object_id_fkey ;

COMMIT;