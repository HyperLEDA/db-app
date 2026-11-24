/* pgmigrate-encoding: utf-8 */

CREATE INDEX IF NOT EXISTS layer0_records_table_id_id_unsubmitted
ON layer0.records (table_id, id)
WHERE pgc IS NULL;
