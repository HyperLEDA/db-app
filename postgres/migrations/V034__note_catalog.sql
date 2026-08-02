CREATE SCHEMA IF NOT EXISTS note;
SELECT meta.setparams('note', '{"description": "Notes for individual records"}');

CREATE TABLE note.data (
  record_id Text PRIMARY KEY REFERENCES layer0.records(id) ON UPDATE CASCADE ON DELETE RESTRICT
, note Text NOT NULL
);
SELECT meta.setparams('note', 'data', 'record_id', '{"description": "Record identifier"}');
SELECT meta.setparams('note', 'data', 'note', '{"description": "Note text"}');

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
