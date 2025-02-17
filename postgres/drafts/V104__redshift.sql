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
, datatype	common.datatype	NOT NULL
, srctab	text
, specregion	text	REFERENCES common.specregion (id )	ON DELETE restrict ON UPDATE cascade
, fovdim	smallint	REFERENCES common.fovdim (id )	ON DELETE restrict ON UPDATE cascade
, method	text	REFERENCES cz.method (id )	ON DELETE restrict ON UPDATE cascade
, resolution	real
) ;

COMMENT ON TABLE cz.dataset	IS 'Dataset' ;
COMMENT ON COLUMN cz.dataset.id	IS 'Dataset ID' ;
COMMENT ON COLUMN cz.dataset.datatype	IS 'Types of the data (regular,reprocessing,preliminary,compilation)' ;
COMMENT ON COLUMN cz.dataset.specregion	IS 'Spectral region (radio,opt)' ;
COMMENT ON COLUMN cz.dataset.fovdim	IS 'FoV dimension: 0 - fiber (beam), 1 - longslit, 2 - integral field spectroscopy' ;
COMMENT ON COLUMN cz.dataset.method	IS 'Measurement method' ;
COMMENT ON COLUMN cz.dataset.resolution	IS 'Spectral resolution in km/s (usually for radio measurements)' ;
COMMENT ON COLUMN cz.dataset.bib	IS 'Bibliography reference' ;
COMMENT ON COLUMN cz.dataset.srctab	IS 'Source table' ;  -- Maybe it is better to create the registry for all downloaded tables and refer to their src id?

