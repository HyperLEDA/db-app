BEGIN;

-----------------------------------------------
-------- Distance measurements schema ---------
-----------------------------------------------
CREATE SCHEMA IF NOT EXISTS distance;
SELECT meta.setparams( 'distance' , '{"description": "Catalog of the distance measurements"}'::json ) ;


CREATE TYPE distance.indicator_type AS ENUM ( 'direct', 'quasi-geometric', 'standard candle', 'standard ruler', 'standard siren', 'luminosity scaling', 'size scaling' ) ;
COMMENT ON TYPE distance.indicator_type IS '{
"description": "Classification of distance indicators",
"values": {
  "direct": "Direct distance measurements without assumptions about object nature",
  "quasi-geometric": "Geometric distance measurements requiring additional physical model assumptions, such as atmosphere or radiative transfer models",
  "standard ruler": "Distance indicators based on physical size",
  "standard candle": "Distance indicators based on intrinsic luminosity",
  "standard siren": "Distance indicators based on gravitational-wave observations"
  "luminosity scaling": "Secondary distance indicators based on luminosity scaling relations",
  "size scaling": "Secondary distance indicators based on size scaling relations"
  }
}';


------------ Methods --------------
CREATE TABLE distance.methods (
  id	Text	PRIMARY KEY
, indicator	distance.indicator_type	NOT NULL	DEFAULT 'standard candle'
, title	Text	NOT NULL
, description	Text
) ;

SELECT meta.setparams( 'distance', 'methods', '{"description": "Distance determination methods", "ucd": "meta.table"}'::json ) ;
SELECT meta.setparams( 'distance', 'methods', 'id', '{"description": "Method ID", "ucd": "meta.id;meta.main"}'::json ) ;
SELECT meta.setparams( 'distance', 'methods', 'indicator', '{"description": "Distance indicator type (direct, standard ruler, standard candle, etc.)", "ucd": "meta.code.class"}'::json ) ;
SELECT meta.setparams( 'distance', 'methods', 'title', '{"description": "Short description of the method", "ucd": "meta.title"}'::json ) ;
SELECT meta.setparams( 'distance', 'methods', 'description', '{"description": "Description of the method", "ucd": "meta.note"}'::json ) ;



---------- Calibration -----------
CREATE TABLE distance.calibrations (
  id	Text	PRIMARY KEY
, method_id	Text	NOT NULL	REFERENCES distance.methods (id) ON DELETE restrict ON UPDATE cascade
, specification	Text
, bib	Integer	REFERENCES common.bib(id) ON DELETE restrict ON UPDATE cascade
, scatter	Real
, description	json
, UNIQUE NULLS NOT DISTINCT (bib, method_id, specification)
);
CREATE INDEX ON distance.calibrations (method_id) ;

SELECT meta.setparams( 'distance', 'calibrations', '{"description": "Calibrations of the distance method", "ucd": "meta.table"}'::json ) ;
SELECT meta.setparams( 'distance', 'calibrations', 'id',
  '{"description": "Calibration ID", "ucd": "meta.id;meta.main"}'::json ) ;
SELECT meta.setparams( 'distance', 'calibrations', 'method_id',
  '{"description": "Distance method ID", "ucd": "meta.id"}'::json ) ;
SELECT meta.setparams( 'distance', 'calibrations', 'specification', 
  '{"description": "Short specification distinguishing this calibration from other calibrations of the same method", "ucd": "meta.code"}'::json ) ;
SELECT meta.setparams( 'distance', 'calibrations', 'bib',
  '{"description": "Reference describing the distance calibration", "ucd": "meta.bib"}'::json ) ;
SELECT meta.setparams( 'distance', 'calibrations', 'scatter',
  '{"description": "Typical intrinsic scatter of the distance calibration in distance modulus", "unit": "mag", "ucd": "stat.stdev;phot.mag.distMod"}'::json ) ;
SELECT meta.setparams( 'distance', 'calibrations', 'description',
  '{"description": "Detailed description of the distance calibration", "ucd": "meta.note"}'::json ) ;


------- Distance catalog -------
CREATE TABLE distance.data (
  record_id	Text	NOT NULL	REFERENCES layer0.records(id) ON UPDATE cascade ON DELETE restrict
, modulus	Real	NOT NULL
, em_modulus	Real	CHECK (em_modulus>0)
, ep_modulus	Real	CHECK (ep_modulus>0)
, quality	common.quality_type	NOT NULL	DEFAULT 'regular'
, calib_id	Text	NOT NULL	REFERENCES distance.calibrations(id) ON UPDATE cascade ON DELETE restrict
, PRIMARY KEY (record_id, calib_id)
, CHECK ( (em_modulus IS NULL and ep_modulus IS NULL) or (em_modulus IS NOT NULL and ep_modulus IS NOT NULL) )
) ;
CREATE INDEX ON distance.data (calib_id) ;

SELECT meta.setparams( 'distance', 'data', '{"description": "Redshift-independent distance measurements", "ucd": "meta.table"}'::json ) ;
SELECT meta.setparams( 'distance', 'data', 'record_id',
  '{"description": "Record ID", "ucd": "meta.id;meta.main"}'::json ) ;
SELECT meta.setparams( 'distance', 'data', 'modulus',
  '{"description": "Distance modulus", "unit": "mag", "ucd": "phot.mag.distMod"}'::json ) ;
SELECT meta.setparams( 'distance', 'data', 'em_modulus',
  '{"description": "Lower uncertainty of the distance modulus", "unit": "mag", "ucd": "stat.error;phot.mag.distMod"}'::json ) ;
SELECT meta.setparams( 'distance', 'data', 'ep_modulus',
  '{"description": "Upper uncertainty of the distance modulus", "unit": "mag", "ucd": "stat.error;phot.mag.distMod"}'::json ) ;
SELECT meta.setparams( 'distance', 'data', 'calib_id',
  '{"description": "Calibration used for the distance determination", "ucd": "meta.id"}'::json ) ;
SELECT meta.setparams( 'distance', 'data', 'quality',
  '{"description": "Quality flag of the measurement", "ucd": "meta.code.qual"}'::json ) ;

COMMIT ;
