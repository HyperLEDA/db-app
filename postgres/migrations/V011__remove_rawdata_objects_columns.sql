/* pgmigrate-encoding: utf-8 */

DROP TRIGGER IF EXISTS update_modification_dt ON rawdata.objects;
DROP FUNCTION IF EXISTS rawdata.update_modification_dt();

ALTER TABLE rawdata.objects DROP COLUMN IF EXISTS data;
ALTER TABLE rawdata.objects DROP COLUMN IF EXISTS modification_dt;
