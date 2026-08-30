/* pgmigrate-encoding: utf-8 */

CREATE INDEX IF NOT EXISTS designation_data_design_trgm_idx
  ON designation.data USING GIN (design gin_trgm_ops);

DROP INDEX IF EXISTS layer2.layer2_designation_design_trgm_idx;
