/* pgmigrate-encoding: utf-8 */

/* Legacy normalized-name lookup; app search no longer uses upper(replace(...)). */
DROP INDEX IF EXISTS designation.data_upper_idx;

/* Layer1 ILIKE/trgm; pattern search goes through layer2.designations instead. */
DROP INDEX IF EXISTS designation.designation_data_design_trgm_idx;
