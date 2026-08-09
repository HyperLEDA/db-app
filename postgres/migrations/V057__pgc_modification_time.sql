/* pgmigrate-encoding: utf-8 */

ALTER TABLE common.pgc
ADD COLUMN modification_time timestamp without time zone NOT NULL DEFAULT NOW();

COMMENT ON COLUMN common.pgc.modification_time
  IS 'Last time any parameter associated with this PGC may have changed';

UPDATE common.pgc AS p
SET modification_time = s.max_mt
FROM (
  SELECT pgc, MAX(modification_time) AS max_mt
  FROM layer0.records
  WHERE pgc IS NOT NULL
  GROUP BY pgc
) AS s
WHERE p.id = s.pgc;

CREATE INDEX pgc_modification_time_id_idx
  ON common.pgc (modification_time, id);

DROP TRIGGER IF EXISTS set_modification_time_on_pgc_update ON layer0.records;
DROP FUNCTION IF EXISTS rawdata_set_modification_time();

ALTER TABLE layer0.records
DROP COLUMN modification_time;

ALTER TABLE icrs.data
DROP COLUMN modification_time;

ALTER TABLE designation.data
DROP COLUMN modification_time;

ALTER TABLE cz.data
DROP COLUMN modification_time;
