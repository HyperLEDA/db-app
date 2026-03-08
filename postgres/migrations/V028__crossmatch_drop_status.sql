/* pgmigrate-encoding: utf-8 */

DROP INDEX IF EXISTS layer0.crossmatch_triage_status_status_idx;
DROP INDEX IF EXISTS layer0.crossmatch_status_idx;
ALTER TABLE layer0.crossmatch DROP COLUMN status;
DROP TYPE IF EXISTS layer0.crossmatch_status;
