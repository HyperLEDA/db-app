BEGIN ;

DROP SCHEMA IF EXISTS photometry CASCADE ;

---------------------------------------------------
-------- Photometry catalog (level 1) ---------------

CREATE SCHEMA photometry ;

COMMENT ON SCHEMA photometry	IS 'Photometry catalog (visual magnitudes)' ;

---------------------------------------------------
-------- Photometry measurement method  -------------
CREATE TABLE photometry.method (
  id	text	PRIMARY KEY
, description	text	NOT NULL
) ;

COMMENT ON TABLE photometry.method	IS 'Photometry measurement method' ;
COMMENT ON COLUMN photometry.method.id	IS 'Method ID' ;
COMMENT ON COLUMN photometry.method.description	IS 'Method description' ;

INSERT INTO photometry.method (id,description) VALUES 
  ( 'Total' , 'Asymptotic (extrapolated) magnitude' )
, ( 'Kron' , 'Kron magnitude' )
, ( 'Petro' , 'Petrosian magnitude' )
, ( 'Model' , 'Model best fit magnitude' )
;


---------------------------------------------------
-------- Dataset ----------------------------------
CREATE TABLE photometry.dataset (
  id	serial	PRIMARY KEY
, bib	integer	NOT NULL	REFERENCES common.bib ( id )	ON DELETE restrict ON UPDATE cascade
, datatype	text	REFERENCES common.datatype (id )	ON DELETE restrict ON UPDATE cascade
, srctab	text
, method	text	NOT NULL	REFERENCES photometry.method (id )	ON DELETE restrict ON UPDATE cascade
) ;

COMMENT ON TABLE photometry.dataset	IS 'Dataset' ;
COMMENT ON COLUMN photometry.dataset.id	IS 'Dataset ID' ;
COMMENT ON COLUMN photometry.dataset.bib	IS 'Bibliography reference' ;
COMMENT ON COLUMN photometry.dataset.datatype	IS 'Type of the data (reguliar,reprocessing,preliminary,compilation)' ;
COMMENT ON COLUMN photometry.dataset.srctab	IS 'Source table' ;  -- Maybe it is better to create the registry for all downloaded tables and reffer ther src id?
COMMENT ON COLUMN photometry.dataset.method	IS 'Measurement method' ;


------------------------------------------
--- Photometry measurement table ---------
CREATE TABLE photometry.data (
  id	serial	PRIMARY KEY
, pgc	integer	NOT NULL	REFERENCES common.pgc (id )	ON DELETE restrict ON UPDATE cascade
, mag	real	NOT NULL
, e_mag	real
, band	integer	REFERENCES common.calibpassband (id)	ON DELETE restrict ON UPDATE cascade
, quality	smallint	NOT NULL	REFERENCES common.quality (id)	ON DELETE restrict ON UPDATE cascade	DEFAULT 0   -- default 0 = reguliar measurement
, dataset	integer	NOT NULL	REFERENCES cz.dataset (id)	ON DELETE restrict ON UPDATE cascade
, modification_time	timestamp without time zone	NOT NULL	DEFAULT now()
) ;
CREATE UNIQUE INDEX ON photometry.data (pgc,quality,band,mag,dataset) ;
CREATE INDEX ON photometry.data (dataset) ;

COMMENT ON TABLE photometry.data	IS 'photometry catalog' ;
COMMENT ON COLUMN photometry.data.id	IS 'Measurement ID' ;
COMMENT ON COLUMN photometry.data.pgc	IS 'PGC number of the object' ;
COMMENT ON COLUMN photometry.data.mag	IS 'Total apparent magnitude [mag]' ;
COMMENT ON COLUMN photometry.data.e_mag	IS 'Error of the total apparent magnitude [mag]' ;
COMMENT ON COLUMN photometry.data.quality	IS 'Measurement quality: 0 - reguliar, 1 - low S/N, 2 - suspected, 5 -wrong' ;
COMMENT ON COLUMN photometry.data.dataset	IS 'Dataset of the measurements' ;
COMMENT ON COLUMN photometry.data.modification_time	IS 'Timestamp when the record was added to the database' ;


---------------------------------------------
-- List of excluded measurements ------------
CREATE TABLE photometry.excluded (
  id	integer	PRIMARY KEY	REFERENCES photometry.data (id) ON DELETE restrict ON UPDATE cascade
, bib	integer	NOT NULL	REFERENCES common.bib ( id ) ON DELETE restrict ON UPDATE cascade
, note	text	NOT NULL
, modification_time	timestamp without time zone	NOT NULL	DEFAULT NOW()
) ;

COMMENT ON TABLE photometry.excluded	IS 'List of measurements excluded from consideration' ;
COMMENT ON COLUMN photometry.excluded.id	IS 'measurement ID' ;
COMMENT ON COLUMN photometry.excluded.bib	IS 'Bibliography reference where given measurement was marked as wrong' ;
COMMENT ON COLUMN photometry.excluded.note	IS 'Note on exclusion' ;
COMMENT ON COLUMN photometry.excluded.modification_time	IS 'Timestamp when the record was added to the database' ;






COMMIT ;