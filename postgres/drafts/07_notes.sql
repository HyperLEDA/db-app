BEGIN;

CREATE SCHEMA note ;

CREATE TABLE nature.data (
  record_id	Text PRIMARY KEY REFERENCES layer0.records(id) ON UPDATE cascade ON DELETE restrict
, note	Text NOT NULL
) ;

CREATE VIEW layer2.notes AS
SELECT
  r.pgc
, d.note
, t.bib
, b.code
, b.year
, b.author
, b.title
FROM
  note.data AS d 
  LEFT JOIN layer0.records AS r ON (d.record_id = r.id)
  LEFT JOIN layer0.tables AS t ON (r.table_id = t.id)
  LEFT JOIN common.bib AS b ON (t.bib = b.id)
;

COMMIT;