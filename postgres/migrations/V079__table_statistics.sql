/* pgmigrate-encoding: utf-8 */

ALTER TABLE layer0.tables
ADD COLUMN statistics jsonb,
ADD COLUMN statistics_refresh_dt timestamp;

COMMENT ON COLUMN layer0.tables.statistics
  IS 'Cached table progress (funnel counts and per-catalog structured counts)';
COMMENT ON COLUMN layer0.tables.statistics_refresh_dt
  IS 'layer0.tables.modification_dt observed when statistics was computed';
