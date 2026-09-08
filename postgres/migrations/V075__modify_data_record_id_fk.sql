BEGIN;

ALTER TABLE designation.data DROP CONSTRAINT data_record_id_fkey;

ALTER TABLE designation.data
ADD CONSTRAINT data_record_id_fkey FOREIGN KEY (record_id) REFERENCES layer0.records(id) ON UPDATE CASCADE ON DELETE RESTRICT;

COMMIT;