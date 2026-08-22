BEGIN;

-----------------------------------------------
-------- Distance measurements schema ---------
-----------------------------------------------
CREATE SCHEMA IF NOT EXISTS distance;
SELECT meta.setpatarms( 'distance' , '{"description": "Catalog of the distance measurements"}'::json ) ;


CREATE TYPE distance.indicator_type AS ENUM ( 'direct', 'quasi-geometric', 'standard candle', 'standard ruler', 'standard siren', 'luminosity-based scaling relation', 'size-based scaling relation' ) ;
COMMENT ON TYPE distance.indicator_type IS '{
"description": "Classification of the indicators of the distance measurement",
"values": {
  "direct": "Direct distance measurements without assumptions about object nature",
  "quasi-geometric": "Geometric measurements based on additional model assumptions, i.e. atmosphere/radiative transfer models",
  "standard candle": "Luminosity based distance indicators (standard candle)",
  "standard ruler": "Phisical size based distance indicators (standard ruler)",
  "standard siren": "Gravitational waves indicators (standard siren)",
  "luminosity-based scaling relation": "Secondary distance indicators linking luminosity to galaxy properties",
  "size-based scaling relation": "Secondary distance indicators linking size to galaxy properties"
  }
}';


------------ Methods --------------
CREATE TABLE distance.methods (
  id	Text	PRIMARY KEY
, indicator	distance.indicator_type	NOT NULL	DEFAULT 'standard candle'
, title	Text	NOT NULL
, description	Text
) ;
SELECT meta.setparams( 'distance', 'methods', '{"description": "Distance determination methods"}'::json ) ;
SELECT meta.setparams( 'distance', 'methods', 'id', '{"description": "Method ID", "ucd": "meta.id;meta.main"}'::json ) ;
SELECT meta.setparams( 'distance', 'methods', 'indicator', '{"description": "Distance indicator type (direct, quasi-geometric, standard ruler, standard candle, standard siren, luminosity-based scaling relation, size-based scaling relation)", "ucd": "meta.code.class"}'::json ) ;
SELECT meta.setparams( 'distance', 'methods', 'title', '{"description": "Short description of the method", "ucd": "meta.title"}'::json ) ;
SELECT meta.setparams( 'distance', 'methods', 'description', '{"description": "Description of the method", "ucd": "meta.note"}'::json ) ;



---------- Calibration -----------
CREATE TABLE distance.calibrations (
  id	Serial	PRIMARY KEY
, method_id	Text	NOT NULL	REFERENCES distance.methods (id) ON DELETE restrict ON UPDATE cascade
, clarification	Text
, bib	Integer	REFERENCES common.bib(id) ON DELETE restrict ON UPDATE cascade
, description	json
, UNIQUE NULLS NOT DISTINCT (bib, method_id, clarification)
);
SELECT meta.setparams( 'distance', 'calibrations', '{"description": "Calibration of the distance method"}'::json ) ;
SELECT meta.setparams( 'distance', 'calibrations', 'id', '{"description": "Calibration ID"}'::json ) ;
SELECT meta.setparams( 'distance', 'calibrations', 'method', '{"description": "Distance method ID"}'::json ) ;
SELECT meta.setparams( 'distance', 'calibrations', 'bibcode', '{"description": "ADS bibcode"}'::json ) ;
SELECT meta.setparams( 'distance', 'calibrations', 'description', '{"description": "Distance calibration description"}'::json ) ;


------- Distance catalog -------
CREATE TABLE distance.data (
  record_id	Text	NOT NULL	REFERENCES layer0.records(id) ON UPDATE cascade ON DELETE restrict
, modulus	Real	NOT NULL
, em_modulus	Real
, ep_modulus	Real
, quality	common.QualityType	NOT NULL	DEFAULT 'regular'
, calib_id	Text	NOT NULL	REFERENCES distance.calibrations(id) ON UPDATE cascade ON DELETE restrict
, PRIMARY KEY (record_id, calib_id)
, CHECK ( (em_modulus IS NULL and ep_modulus IS NULL) or (em_modulus IS NOT NULL and ep_modulus IS NOT NULL) )
) ;
CREATE INDEX ON distance.data (record_id) ;
CREATE INDEX ON distance.data (calib_id) ;

SELECT meta.setparams( 'distance', 'data', '{"description": "Redshift independent distance catalog"}'::json ) ;
SELECT meta.setparams( 'distance', 'data', 'record_id', '{"description": "Record ID"}'::json ) ;
SELECT meta.setparams( 'distance', 'data', 'modulus', '{"description": "Distance modulus", "unit": "mag", "ucd": "phot.mag.distMod"}'::json ) ;
SELECT meta.setparams( 'distance', 'data', 'em_modulus', '{"description": "Statustucal plus uncertainty of the distance modulus", "unit": "mag", "ucd": "stat.error;phot.mag.distMod"}'::json ) ;
SELECT meta.setparams( 'distance', 'data', 'ep_modulus', '{"description": "Statustucal minus uncertainty of the distance modulus", "unit": "mag", "ucd": "stat.error;phot.mag.distMod"}'::json ) ;
SELECT meta.setparams( 'distance', 'data', 'calib_id', '{"description": "ID of the calibration of the distance method"}'::json ) ;

ROLLBACK ;
-- COMMIT ;
