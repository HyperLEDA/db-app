/* pgmigrate-encoding: utf-8 */

INSERT INTO layer2.last_update (dt, catalog) VALUES (to_timestamp(0), 'nature');

CREATE INDEX IF NOT EXISTS layer0_records_pgc_idx ON layer0.records (pgc);
