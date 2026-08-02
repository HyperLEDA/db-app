CREATE SCHEMA IF NOT EXISTS nature;
SELECT meta.setparams('nature', '{"description": "Nature of the object"}');

CREATE TYPE nature.object_class AS ENUM ('?','*','grp*','ism','G','grpG','src','reg','err');
COMMENT ON TYPE nature.object_class IS '{
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

CREATE TABLE nature.object_type (
  type_name	Text	PRIMARY KEY
, objclass	nature.object_class	NOT NULL
, description	Text	NOT NULL
);
SELECT meta.setparams('nature', 'object_type', '{"description": "Object nature types"}');
SELECT meta.setparams('nature', 'object_type', 'type_name', '{"description": "Object type code"}');
SELECT meta.setparams('nature', 'object_type', 'objclass', '{"description": "Object nature code"}');
SELECT meta.setparams('nature', 'object_type', 'description', '{"description": "Description"}');

INSERT INTO nature.object_type VALUES
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
, type_name	Text NOT NULL REFERENCES nature.object_type(type_name)
);
SELECT meta.setparams('nature', 'data', 'record_id', '{"description": "Record identifier"}');
SELECT meta.setparams('nature', 'data', 'type_name', '{"description": "Object type code"}');

CREATE TABLE layer2.nature (
  pgc integer PRIMARY KEY REFERENCES common.pgc(id) ON DELETE RESTRICT ON UPDATE CASCADE,
  type_name text NOT NULL REFERENCES nature.object_type(type_name)
);
SELECT meta.setparams('layer2', 'nature', 'pgc', '{"description": "PGC identifier"}');
SELECT meta.setparams('layer2', 'nature', 'type_name', '{"description": "Object type code"}');
