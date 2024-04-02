BEGIN;

DROP SCHEMA IF EXISTS cz CASCADE ;

---------------------------------------------------
-------- Redshift catalog (level 1) ---------------

CREATE SCHEMA cz ;

COMMENT ON SCHEMA cz IS 'Heliocentric Redshift catalog' ;


CREATE TABLE cz.method (
, id	text	PRIMARY KEY
, description	text	NOT NULL
) ;

COMMENT ON TABLE cz.method IS 'Redshift measurement method' ;
COMMENT ON COLUMN cz.method.id IS 'Method ID' ;
COMMENT ON COLUMN cz.method.description IS 'Method description' ;

INSERT INTO cz.method (id,description) VALUES 
  ('average', 'Average of measurements of members')
, ('emission', 'Emission lines')
, ('absorption', 'Absorption lines')
, ('xcorr', 'Cross correlation')
, ('fit', 'Stellar populations fit')
, ('photoz', 'Photometric redshift')
;


CREATE TABLE cz.line (
, id	text	PRIMARY KEY
, description	text	NOT NULL
) ;

COMMENT ON TABLE cz.line IS 'Spectral line' ;
COMMENT ON COLUMN cz.line.id IS 'Spectral line ID' ;
COMMENT ON COLUMN cz.line.description IS 'Spectral line description' ;

INSERT INTO cz.line (id,description) VALUES 
  ('Halpha', 'Halpha')
, ('HI', 'HI 21cm line')
, ('CO', 'CO')
, ('OH', 'OH')
;


CREATE TABLE cz.dataset (
  id	serial	PRIMARY KEY
, method	text	REFERENCES cz.method (id )	ON DELETE restrict ON UPDATE cascade
, line	text	REFERENCES cz.line (id )	ON DELETE restrict ON UPDATE cascade
, resolution	real
, bib	integer	NOT NULL	REFERENCES common.bib ( id )	ON DELETE restrict ON UPDATE cascade
) ;


CREATE TABLE cz.data (
  id	serial	PRIMARY KEY
, pgc	integer	NOT NULL	REFERENCES common.pgc (id )	ON DELETE restrict ON UPDATE cascade
, cz	real	NOT NULL
, e_cz	real
, dataset	integer	NOT NULL	REFERENCES cz.dataset (id)	ON DELETE restrict ON UPDATE cascade
, modification_time	timestamp without time zone	NOT NULL	DEFAULT now()
) ;

COMMIT ;