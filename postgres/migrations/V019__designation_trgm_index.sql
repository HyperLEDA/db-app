/* pgmigrate-encoding: utf-8 */

CREATE EXTENSION IF NOT EXISTS pg_trgm;

CREATE INDEX layer2_designation_design_trgm_idx
    ON layer2.designation USING GIN (design gin_trgm_ops);
