/* pgmigrate-encoding: utf-8 */

-- Drop foreign key constraints that reference tables to be moved
ALTER TABLE rawdata.crossmatch DROP CONSTRAINT crossmatch_object_id_fkey;
ALTER TABLE icrs.data DROP CONSTRAINT data_object_id_fkey;
ALTER TABLE designation.data DROP CONSTRAINT data_object_id_fkey;
ALTER TABLE cz.data DROP CONSTRAINT data_object_id_fkey;
ALTER TABLE layer0.column_modifiers DROP CONSTRAINT column_modifiers_table_id_fkey;
ALTER TABLE rawdata.objects DROP CONSTRAINT objects_table_id_fkey;
DROP TRIGGER IF EXISTS set_modification_time_on_pgc_update ON rawdata.objects;

ALTER TABLE rawdata.tables SET SCHEMA layer0;
ALTER TABLE rawdata.objects SET SCHEMA layer0;
ALTER TYPE rawdata.crossmatch_status SET SCHEMA layer0;
ALTER TABLE rawdata.crossmatch SET SCHEMA layer0;

-- Recreate constraints
ALTER TABLE layer0.crossmatch 
ADD FOREIGN KEY (object_id) REFERENCES layer0.objects(id);

ALTER TABLE icrs.data 
ADD FOREIGN KEY (object_id) REFERENCES layer0.objects(id);

ALTER TABLE designation.data 
ADD FOREIGN KEY (object_id) REFERENCES layer0.objects(id);

ALTER TABLE cz.data 
ADD FOREIGN KEY (object_id) REFERENCES layer0.objects(id) ON DELETE restrict ON UPDATE cascade;

ALTER TABLE layer0.column_modifiers 
ADD FOREIGN KEY (table_id) REFERENCES layer0.tables(id);

ALTER TABLE layer0.objects 
ADD CONSTRAINT objects_table_id_fkey FOREIGN KEY (table_id) REFERENCES layer0.tables(id);

CREATE TRIGGER set_modification_time_on_pgc_update
BEFORE UPDATE OF pgc ON layer0.objects
FOR EACH ROW
EXECUTE FUNCTION rawdata_set_modification_time();

