/* pgmigrate-encoding: utf-8 */

/*
 * Spatial index backing the cone search in /query/simple.
 *
 * The expression must stay byte-identical to the one built by
 * ICRSCoordinatesInRadiusFilter, otherwise the planner will not match it.
 *
 * IF NOT EXISTS because production already has an equivalent index that was
 * created by hand and never captured in a migration.
 */
CREATE INDEX IF NOT EXISTS icrs_geography_idx
    ON layer2.icrs USING GIST ((ST_MakePoint(ra, dec)::geography));
