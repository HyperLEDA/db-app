/* pgmigrate-encoding: utf-8 */

ALTER TABLE layer0.tables DROP COLUMN status;
DROP TYPE rawdata.status;
