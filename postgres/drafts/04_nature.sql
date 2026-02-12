BEGIN;

CREATE SCHEMA IF NOT EXISTS nature;
COMMENT ON SCHEMA nature IS 'Nature of the object';


CREATE TYPE nature.ObjectClassType AS ENUM ('?','*','grp*','ism','G','grpG','src','reg','err') ;
COMMENT ON TYPE nature.ObjectClassType IS '{
"?" : "Unknown Nature",
"*" : "Star",
"grp*" : "Group of stars",
"ism" : "Interstellar Medium",
"G" : "Galaxy",
"grpG" : "Group of Galaxies",
"src" : "Source",
"reg" : "Region defined in the Sky",
"err" : "Different errors in data"
}' ;


CREATE TABLE nature.objectType (
  objtype	Text	PRIMARY KEY
, objclass	nature.ObjectClassType	NOT NULL
, description	Text	NOT NULL
, PRIMARY KEY (objtype,objclass)
);
COMMENT ON TABLE nature.objectType IS 'Object nature types' ;
COMMENT ON COLUMN nature.objectType.objtype	IS 'Object type code' ;
COMMENT ON COLUMN nature.objectType.objclass	IS 'Object nature code' ;
COMMENT ON COLUMN nature.objectType.description	IS 'Description' ;

INSERT INTO nature.objectType VALUES
  ('?', '?', 'Object of unknown/uncertain nature')

, ('*', '*', 'Star')
, ('SN', '*', 'SuperNova')
, ('kN', '*', 'kiloNova')

, ('cl*', 'grp*', 'Star cluster')
, ('OC', 'grp*', 'Open Cluster')
, ('GC', 'grp*', 'Globular Cluster')
, ('as*', 'grp*', 'Stellar association')
, ('str*', 'grp*', 'Stellar Stream')
, ('***', 'grp*', 'Asterism')

, ('HII', 'ism', 'HII Region')
, ('HVC', 'ism', 'High-velocity Cloud')
, ('SNR', 'ism', 'SuperNova Remnant')

, ('G', 'G', 'Galaxy')
, ('QSO', 'G', 'Quasar')
, ('G*', 'G', 'Galaxy with superimposed star')

, ('M', 'grpG', 'Multiple galaxy')
, ('IG', 'grpG', 'Interacting Galaxies')
, ('M2', 'grpG', 'Pair of Galaxies')
, ('M3', 'grpG', 'Triplet of Ggalaxies')
, ('M+', 'grpG', 'Group of galaxies')
, ('ClG', 'grpG', 'Cluster of galaxies')
, ('SCG', 'grpG', 'Supercluster of Galaxies')
, ('void', 'grpG', 'Underdense Region of the Universe')

, ('R', 'src', 'Radio Source')
, ('HI', 'src', 'HI (21cm) Source')

, ('!', 'err', 'Not an object (error in catalogue, artefact, plate defect, transcient/moving object, etc.)')
, ('PoG', 'err', 'Part of a Galaxy')
;


CREATE TABLE nature.datasets (
  id Integer PRIMARY KEY; 
, table_id Integer NOT NULL REFERENCES layer0.tables (id) ON DELETE restrict ON UPDATE cascade
, column_name Text NOT NULL
, datatype Common.DataType NOT NULL
) ;


CREATE TABLE nature.data (
  record_id	Text PRIMARY KEY REFERENCES layer0.records(id) ON UPDATE cascade ON DELETE restrict
, objtype	Text NOT NULL REFERENCES nature.objectType(objtype) ON UPDATE cascade ON DELETE restrict
, dataset_id	Integer NOT NULL REFERENCES nature.datasets(id) ON DELETE restrict ON UPDATE cascade
) ;


CREATE VIEW nature.dataview AS
SELECT
  r.pgc
, d.objtype
, c.objclass
, c.description

, d.record_id
, d.dataset_id
, s.table_id
, t.table_name
, s.column_name

, b.code
, b.year 
, b.author
, b.title

, r.modification_time
FROM
  nature.data AS d 
  LEFT JOIN nature.objectType AS c ON (d.objtype = c.objtype) 
  LEFT JOIN nature.datasets  AS s ON (d.dataset_id = s.id )
  LEFT JOIN layer0.records AS r ON (d.record_id = r.id )
  LEFT JOIN layer0.tables  AS t ON (d.table_id = t.id )
  LEFT JOIN common.bib AS b ON (t.bib = b.id )
;

COMMIT;
