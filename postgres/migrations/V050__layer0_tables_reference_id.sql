/* pgmigrate-encoding: utf-8 */

-- Add optional reference_id column to layer0.tables for external system linking
ALTER TABLE layer0.tables ADD COLUMN reference_id text;
COMMENT ON COLUMN layer0.tables.reference_id IS 'Optional external reference identifier for linking to external systems';

-- Add index for better query performance on reference_id
CREATE INDEX ON layer0.tables (reference_id);
