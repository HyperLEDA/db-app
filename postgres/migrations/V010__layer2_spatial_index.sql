/* pgmigrate-encoding: utf-8 */

CREATE INDEX ON layer2.icrs USING GIST (ST_MakePoint(dec, ra-180));

COMMENT ON INDEX layer2.icrs_st_makepoint_idx IS 'Spatial index for efficient coordinate-based distance queries on layer2.icrs table'; 