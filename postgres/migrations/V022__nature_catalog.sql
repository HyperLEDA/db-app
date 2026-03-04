CREATE SCHEMA IF NOT EXISTS nature;
SELECT meta.setparams('nature', '{"description": "Nature of the object"}');

CREATE TYPE nature.ObjectClassType AS ENUM ('?','*','grp*','ism','G','grpG','src','reg','err');
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
}';



CREATE TABLE nature.objectType (
  objtype	Text	PRIMARY KEY
, objclass	nature.ObjectClassType	NOT NULL
, description	Text	NOT NULL
, PRIMARY KEY (objtype,objclass)
);
SELECT meta.setparams('nature', 'objectType', '{"description": "Object nature types"}');
SELECT meta.setparams('nature', 'objectType', 'objtype', '{"description": "Object type code"}');
SELECT meta.setparams('nature', 'objectType', 'objclass', '{"description": "Object nature code"}');
SELECT meta.setparams('nature', 'objectType', 'description', '{"description": "Description"}');

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
, ('M3', 'grpG', 'Triplet of Galaxies')
, ('M+', 'grpG', 'Group of galaxies')
, ('ClG', 'grpG', 'Cluster of galaxies')
, ('SCG', 'grpG', 'Supercluster of Galaxies')
, ('void', 'grpG', 'Underdense Region of the Universe')

, ('R', 'src', 'Radio Source')
, ('HI', 'src', 'HI (21cm) Source')

, ('!', 'err', 'Not an object (error in catalogue, artifact, plate defect, transient/moving object, etc.)')
, ('PoG', 'err', 'Part of a Galaxy');


CREATE TABLE nature.data (
  record_id	Text PRIMARY KEY REFERENCES layer0.records(id)
, objtype	Text NOT NULL REFERENCES nature.objectType(objtype)
);
SELECT meta.setparams('nature', 'data', 'record_id', '{"description": "Record identifier"}');
SELECT meta.setparams('nature', 'data', 'objtype', '{"description": "Object type (nature) code"}');
