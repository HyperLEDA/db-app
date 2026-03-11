BEGIN ;

CREATE VIEW layer2.designations AS
SELECT
  -- можно еще добавить record_id - но я не представляю зачем это может понадобиться на этом уровне
  r.pgc
, d.design
, t.table_name  -- я не уверен, что это нужно
, t.bib
, b.code
, b.year
, b.author
, b.title
FROM
  designation.data AS d 
  LEFT JOIN layer0.records AS r ON (d.record_id = r.id)
  LEFT JOIN layer0.tables AS t ON (r.table_id = t.id)
  LEFT JOIN common.bib AS b ON (t.bib = b.id)
;

COMMIT ;