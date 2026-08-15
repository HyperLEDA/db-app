/* pgmigrate-encoding: utf-8 */

CREATE INDEX IF NOT EXISTS layer2_designation_pgc_cover_idx ON layer2.designation (pgc) INCLUDE (design);
CREATE INDEX IF NOT EXISTS layer2_cz_pgc_cover_idx ON layer2.cz (pgc) INCLUDE (cz);
CREATE INDEX IF NOT EXISTS layer2_nature_pgc_cover_idx ON layer2.nature (pgc) INCLUDE (type_name);
