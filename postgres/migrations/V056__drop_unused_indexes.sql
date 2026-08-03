/* pgmigrate-encoding: utf-8 */

/* Planar spatial index on layer 1: no code has ever queried icrs.data spatially. */
DROP INDEX IF EXISTS icrs.data_st_makepoint_idx;

/* Redundant with the unique constraint index tables_table_name_key. */
DROP INDEX IF EXISTS layer0.tables_table_name_idx;
