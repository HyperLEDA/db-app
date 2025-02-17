------------------------------------------
-- List of obsoleted bibliography --------
CREATE TABLE common.obsoleted (
  bib	integer	PRIMARY KEY	REFERENCES common.bib ( id ) ON DELETE restrict ON UPDATE cascade
, renewed	integer	NOT NULL	REFERENCES common.bib ( id ) ON DELETE restrict ON UPDATE cascade
, modification_time	timestamp without time zone	NOT NULL	DEFAULT NOW()
) ;

COMMENT ON TABLE common.obsoleted	IS 'List of obsoleted bibliography' ;
COMMENT ON COLUMN common.obsoleted.bib	IS 'Obsoleted bibliography' ;
COMMENT ON COLUMN common.obsoleted.renewed	IS 'Bibliography that made the previous one obsolete' ;
COMMENT ON COLUMN common.obsoleted.modification_time	IS 'Timestamp when the record was added to the database' ;


------------------------------------------------
------ Notes -----------------------------------
CREATE TABLE common.notes (
  pgc	integer	NULL	REFERENCES common.pgc ( id ) ON DELETE restrict ON UPDATE cascade
, bib	integer	NOT NULL	REFERENCES common.bib ( id ) ON DELETE restrict ON UPDATE cascade
, note	text	NOT NULL
, modification_time	timestamp without time zone	NOT NULL	DEFAULT now()
, PRIMARY KEY (pgc,bib)
) ;

COMMENT ON TABLE common.notes IS 'List of important notes on object' ;
COMMENT ON COLUMN common.notes.pgc	IS '{"description" : "PGC number of the object" , "ucd" : "meta.id"}' ;
COMMENT ON COLUMN common.notes.bib	IS '{"description" : "Bibliography reference" , "ucd" : "meta.bib"}' ;
COMMENT ON COLUMN common.notes.note	IS '{"description" : "Important comments on the object" , "ucd" : "meta.note"}' ;
COMMENT ON COLUMN common.notes.modification_time	IS '{"description" : "Timestamp when the record was added to the database" , "ucd" : "time.creation"}' ;
