/* pgmigrate-encoding: utf-8 */

CREATE TABLE common.pgc_changes (
  pgc integer NOT NULL
, changed_at timestamp without time zone NOT NULL DEFAULT now()
);

CREATE INDEX pgc_changes_pgc_changed_at_idx
  ON common.pgc_changes (pgc, changed_at);

CREATE INDEX pgc_changes_changed_at_idx
  ON common.pgc_changes (changed_at);

COMMENT ON TABLE common.pgc_changes
  IS 'Append-only log of PGC objects whose underlying data changed. Layer 2 tasks read it incrementally and prune rows older than the oldest layer2.last_update watermark';

INSERT INTO common.pgc_changes (pgc, changed_at)
SELECT id, modification_time
FROM common.pgc
WHERE modification_time > (SELECT min(dt) FROM layer2.last_update);
