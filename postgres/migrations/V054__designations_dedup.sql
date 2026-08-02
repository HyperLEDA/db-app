/* pgmigrate-encoding: utf-8 */

CREATE OR REPLACE VIEW layer2.designations AS
SELECT DISTINCT ON (r.pgc, d.design)
  r.pgc
, d.design
, t.bib
, b.code
, b.year
, b.author
, b.title
FROM
  designation.data AS d
  JOIN layer0.records AS r ON (d.record_id = r.id)
  LEFT JOIN layer0.tables AS t ON (r.table_id = t.id)
  LEFT JOIN common.bib AS b ON (t.bib = b.id)
WHERE r.pgc IS NOT NULL
  AND NOT EXISTS (
    SELECT 1 FROM layer2.designation AS ld
    WHERE ld.pgc = r.pgc AND ld.design = d.design
  )
ORDER BY r.pgc, d.design, b.year DESC NULLS LAST, b.code ASC NULLS LAST;
