/* pgmigrate-encoding: utf-8 */

ALTER TABLE layer0.crossmatch DROP CONSTRAINT IF EXISTS crossmatch_object_id_fkey;
ALTER TABLE icrs.data DROP CONSTRAINT IF EXISTS data_object_id_fkey;
ALTER TABLE designation.data DROP CONSTRAINT IF EXISTS designation_data_object_id_fkey;
ALTER TABLE cz.data DROP CONSTRAINT IF EXISTS data_object_id_fkey;
ALTER TABLE layer0.objects DROP CONSTRAINT IF EXISTS objects_table_id_fkey;

DROP TRIGGER IF EXISTS set_modification_time_on_pgc_update ON layer0.objects;

ALTER TABLE layer0.objects RENAME TO records;

ALTER TABLE layer0.crossmatch RENAME COLUMN object_id TO record_id;
ALTER TABLE icrs.data RENAME COLUMN object_id TO record_id;
ALTER TABLE designation.data RENAME COLUMN object_id TO record_id;
ALTER TABLE cz.data RENAME COLUMN object_id TO record_id;

ALTER TABLE layer0.crossmatch 
ADD FOREIGN KEY (record_id) REFERENCES layer0.records(id);

ALTER TABLE icrs.data 
ADD FOREIGN KEY (record_id) REFERENCES layer0.records(id);

ALTER TABLE designation.data 
ADD FOREIGN KEY (record_id) REFERENCES layer0.records(id);

ALTER TABLE cz.data 
ADD FOREIGN KEY (record_id) REFERENCES layer0.records(id) ON DELETE restrict ON UPDATE cascade;

ALTER TABLE layer0.records 
ADD FOREIGN KEY (table_id) REFERENCES layer0.tables(id);

CREATE TRIGGER set_modification_time_on_pgc_update
BEFORE UPDATE OF pgc ON layer0.records
FOR EACH ROW
EXECUTE FUNCTION rawdata_set_modification_time();

