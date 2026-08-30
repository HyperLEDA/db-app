CREATE INDEX IF NOT EXISTS designation_data_design_trgm_idx
  ON designation.data USING GIN (design gin_trgm_ops);
