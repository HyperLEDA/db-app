/* pgmigrate-encoding: utf-8 */

BEGIN;

DROP SCHEMA IF EXISTS cz CASCADE ;

---------------------------------------------------
-------- Redshift catalog (level 1) ---------------

CREATE SCHEMA cz ;

COMMENT ON SCHEMA cz	IS 'Heliocentric Redshift catalog' ;


CREATE TABLE cz.method (
  id	text	PRIMARY KEY
, description	text	NOT NULL
) ;

COMMENT ON TABLE cz.method	IS 'Redshift measurement method' ;
COMMENT ON COLUMN cz.method.id	IS 'Method ID' ;
COMMENT ON COLUMN cz.method.description	IS 'Method description' ;

INSERT INTO cz.method (id,description) VALUES 
  ('average', 'Average of measurements of members')
, ('emission', 'Emission lines')
, ('absorption', 'Absorption lines')
, ('xcorr', 'Cross correlation')
, ('fit', 'Stellar populations fit')
, ('photoz', 'Photometric redshift')
;


---------------------------------------------------
-------- Dataset ----------------------------------
CREATE TABLE cz.dataset (
  id	serial	PRIMARY KEY
, bib	integer	NOT NULL	REFERENCES common.bib ( id )	ON DELETE restrict ON UPDATE cascade
, datatype	text	REFERENCES common.datatype (id )	ON DELETE restrict ON UPDATE cascade
, srctab	text
, specregion	text	REFERENCES common.specregion (id )	ON DELETE restrict ON UPDATE cascade
, fovdim	smallint	REFERENCES common.fovdim (id )	ON DELETE restrict ON UPDATE cascade
, method	text	REFERENCES cz.method (id )	ON DELETE restrict ON UPDATE cascade
, resolution	real
) ;

COMMENT ON TABLE cz.dataset	IS 'Dataset' ;
COMMENT ON COLUMN cz.dataset.id	IS 'Dataset ID' ;
COMMENT ON COLUMN cz.dataset.datatype	IS 'Types of the data (reguliar,reprocessing,preliminary,compilation)' ;
COMMENT ON COLUMN cz.dataset.specregion	IS 'Spectral region (radio,opt)' ;
COMMENT ON COLUMN cz.dataset.fovdim	IS 'FoV dimention: 0 - fiber (beam), 1 - longslit, 2 - integral field spectroscopy' ;
COMMENT ON COLUMN cz.dataset.method	IS 'Measurement method' ;
COMMENT ON COLUMN cz.dataset.resolution	IS 'Spectral resolution in km/s (usually for radio measurements)' ;
COMMENT ON COLUMN cz.dataset.bib	IS 'Bibliography reference' ;
COMMENT ON COLUMN cz.dataset.srctab	IS 'Source table' ;  -- Maybe it is better to create the registry for all downloaded tables and reffer ther src id?


CREATE TABLE cz.datasetGroup (
  id	serial	PRIMARY KEY
, description	text	NOT NULL
) ;

COMMENT ON TABLE cz.datasetGroup	IS 'Dataset group' ;
COMMENT ON COLUMN cz.datasetGroup.id	IS 'Dataset Group ID' ;
COMMENT ON COLUMN cz.datasetGroup.description	IS 'Dataset Group description' ;


CREATE TABLE cz.datasetGroupList (
  datasetGroup	integer	NOT NULL	REFERENCES cz.datasetGroup (id)	ON DELETE restrict ON UPDATE cascade
, dataset	integer	NOT NULL	REFERENCES cz.dataset (id)	ON DELETE restrict ON UPDATE cascade
, PRIMARY KEY (datasetGroup,dataset)
) ;

COMMENT ON TABLE cz.datasetGroupList	IS 'List of datasets of the same group' ;
COMMENT ON COLUMN cz.datasetGroupList.datasetGroup	IS 'Dataset Group ID' ;
COMMENT ON COLUMN cz.datasetGroupList.dataset	IS 'Dataset Group' ;



------------------------------------------
--- Redshift measurements table ----------

CREATE TABLE cz.data (
  id	serial	PRIMARY KEY
, pgc	integer	NOT NULL	REFERENCES common.pgc (id )	ON DELETE restrict ON UPDATE cascade
, cz	real	NOT NULL
, e_cz	real
, quality	smallint	NOT NULL	REFERENCES common.quality (id)	ON DELETE restrict ON UPDATE cascade
, dataset	integer	NOT NULL	REFERENCES cz.dataset (id)	ON DELETE restrict ON UPDATE cascade
, modification_time	timestamp without time zone	NOT NULL	DEFAULT now()
) ;
CREATE UNIQUE INDEX ON cz.data (pgc,quality,cz,dataset) ;
CREATE INDEX ON cz.data (dataset) ;

COMMENT ON TABLE cz.data	IS 'Redshift measurement catalog' ;
COMMENT ON COLUMN cz.data.id	IS 'ID of the measurement' ;
COMMENT ON COLUMN cz.data.pgc	IS 'PGC number of the object' ;
COMMENT ON COLUMN cz.data.cz	IS 'Heliocentric/Barycentric redshift (cz) in km/s in the optical convention: z = (λ-λ0)/λ0' ;
COMMENT ON COLUMN cz.data.e_cz	IS 'cz measurement error in km/s' ;
COMMENT ON COLUMN cz.data.quality	IS 'Measurement quality: 0 - reguliar, 1 - low S/N, 2 - suspected, 5 -wrong' ;
COMMENT ON COLUMN cz.data.dataset	IS 'Dataset of the measurements' ;
COMMENT ON COLUMN cz.data.modification_time	IS 'Timestamp when the record was added to the database' ;


---------------------------------------------
-- List of excluded measurements ------------
CREATE TABLE cz.excluded (
  id	integer	PRIMARY KEY	REFERENCES cz.data (id) ON DELETE restrict ON UPDATE cascade
, bib	integer	NOT NULL	REFERENCES common.bib ( id ) ON DELETE restrict ON UPDATE cascade
, note	text	NOT NULL
, modification_time	timestamp without time zone	NOT NULL	DEFAULT NOW()
) ;

COMMENT ON TABLE cz.excluded	IS 'List of measurements excluded from consideration' ;
COMMENT ON COLUMN cz.excluded.id	IS 'measurement ID' ;
COMMENT ON COLUMN cz.excluded.bib	IS 'Bibliography reference where given measurement was marked as wrong' ;
COMMENT ON COLUMN cz.excluded.note	IS 'Note on exclusion' ;
COMMENT ON COLUMN cz.excluded.modification_time	IS 'Timestamp when the record was added to the database' ;


------------------------------------------
--- List of redshift measurements --------
CREATE VIEW cz.list AS
SELECT
  d.id
, d.pgc
, d.cz
, d.e_cz
, d.quality
, d.dataset
, obsol.bib IS NULL and excl.id IS NULL	AS isok
, greatest( d.modification_time, obsol.modification_time, excl.modification_time )	AS modification_time
FROM
  cz.data AS d
  LEFT JOIN cz.dataset ON (cz.dataset.id=d.dataset)
  LEFT JOIN common.obsoleted AS obsol ON (obsol.bib=cz.dataset.bib)
  LEFT JOIN cz.excluded AS excl ON (excl.id=d.id)
;

COMMENT ON VIEW cz.list	IS 'Redshift measurement catalog' ;
COMMENT ON COLUMN cz.list.id	IS 'measurement ID' ;
COMMENT ON COLUMN cz.list.pgc	IS 'PGC number of the object' ;
COMMENT ON COLUMN cz.list.cz	IS 'Heliocentric/Barycentric redshift (cz) in km/s in the optical convention: z = (λ-λ0)/λ0' ;
COMMENT ON COLUMN cz.list.e_cz	IS 'cz measurement error in km/s' ;
COMMENT ON COLUMN cz.list.quality	IS 'Measurement quality: 0 - reguliar, 1 - low S/N, 2 - suspected, 5 -wrong' ;
COMMENT ON COLUMN cz.list.dataset	IS 'Dataset of the measurements' ;
COMMENT ON COLUMN cz.list.isok	IS 'True if the measurement is actual and False if it is obsoleted or excluded' ;
COMMENT ON COLUMN cz.list.modification_time	IS 'Timestamp when the record was added to the database' ;



COMMIT ;