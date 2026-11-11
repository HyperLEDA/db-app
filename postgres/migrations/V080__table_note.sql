/* pgmigrate-encoding: utf-8 */

ALTER TABLE layer0.tables
ADD COLUMN note text;

COMMENT ON COLUMN layer0.tables.note
  IS 'Longer free-form textual note about the table';
