/* pgmigrate-encoding: utf-8 */
BEGIN;

/*
 * layer0.records only grows through batched inserts from adminapi, so there is no single point to vacuum after an
 * import. With the default 20% scale factors autovacuum effectively never runs on a table of this size.
 */
ALTER TABLE layer0.records SET (
  autovacuum_vacuum_insert_scale_factor = 0.01,
  autovacuum_analyze_scale_factor = 0.01
);

COMMIT;
