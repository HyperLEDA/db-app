/* pgmigrate-encoding: utf-8 */

CREATE INDEX ON layer2.icrs USING GIST (ST_MakePoint(dec, ra-180));
CREATE INDEX ON layer2.icrs (pgc);