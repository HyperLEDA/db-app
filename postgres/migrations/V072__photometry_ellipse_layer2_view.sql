CREATE VIEW layer2.photometry_ellipse AS
SELECT
  r.pgc
, e.band
, e.method
, e.level
, e.a
, e.e_a
, e.b
, e.e_b
, e.pa
, e.e_pa
, e.isophote
, e.e_isophote
, e.quality
, t.bib
, b.code
, b.year
, b.author
, b.title
FROM photometry.ellipse AS e
  JOIN layer0.records AS r ON e.record_id = r.id
  LEFT JOIN layer0.tables AS t ON r.table_id = t.id
  LEFT JOIN common.bib AS b ON t.bib = b.id
WHERE r.pgc IS NOT NULL;
