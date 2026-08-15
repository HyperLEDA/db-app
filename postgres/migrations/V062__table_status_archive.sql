/* pgmigrate-encoding: utf-8 */

CREATE TYPE rawdata.status_new AS ENUM ('initiated', 'archived');

ALTER TABLE layer0.tables ALTER COLUMN status DROP DEFAULT;

ALTER TABLE layer0.tables
  ALTER COLUMN status TYPE rawdata.status_new
  USING 'initiated'::rawdata.status_new;

DROP TYPE rawdata.status;

ALTER TYPE rawdata.status_new RENAME TO status;

ALTER TABLE layer0.tables ALTER COLUMN status SET DEFAULT 'initiated';

COMMENT ON TYPE rawdata.status IS '{
  "initiated": "Table is active",
  "archived": "Table is archived"
}';

COMMENT ON COLUMN layer0.tables.status IS 'Table lifecycle status';
