BEGIN;

-----------------------------------------------
-------- Distance measurements schema ---------
-----------------------------------------------
CREATE SCHEMA IF NOT EXISTS distance;
COMMENT ON SCHEMA distance IS 'Catalog of the distance measurements';

CREATE TYPE distance.IndicatorType AS ENUM ( 'direct', 'candle', 'ruler', 'siren' ) ;

COMMENT ON TYPE distance.IndicatorType IS '{
"description": "Classification of the standards used for the distance measurement",
"values": {
  "direct": "Direct distance measurements without assumptions about object nature",
  "candle": "Luminosity based distance indicators (standard candle)",
  "ruler": "Phisical size based distance indicators (standard ruler)",
  "siren": "Gravitational waves indicators (standard siren)"
  }
}';


------------ Methods --------------
CREATE TABLE distance.methods (
  id	Text	PRIMARY KEY
, indicator	distance.IndicatorType	NOT NULL	DEFAULT 'candle'
, short	Text	NOT NULL
, description	Text	NOT NULL
) ;

COMMENT ON TABLE distance.methods	IS 'Distance determination methods' ;
COMMENT ON COLUMN distance.methods.id	IS 'Method ID' ;
COMMENT ON COLUMN distance.methods.indicator	IS 'Distance indicator type (direct, candle, ruler, siren)' ;
COMMENT ON COLUMN distance.methods.short	IS 'Short description of the method';
COMMENT ON COLUMN distance.methods.description	IS 'Method description' ;


---------- Calibration -----------
CREATE TABLE distance.calibrations (
  id	Text	PRIMARY KEY
, method	Text	NOT NULL	REFERENCES distance.methods (id) ON DELETE restrict ON UPDATE cascade
, bibcode	Char(19)	NOT NULL	REFERENCES common.bib (id) ON DELETE restrict ON UPDATE cascade
, relation	Text	NOT NULL
, description	Text	NOT NULL
, UNIQUE (method, bibcode)
);

COMMENT ON TABLE distance.calib	IS 'Calibration of the distance method';
COMMENT ON COLUMN distance.calib.id	IS 'Calibration ID';
COMMENT ON COLUMN distance.calib.method	IS 'Distance method ID';
COMMENT ON COLUMN distance.calib.relation	IS 'Relation description';
COMMENT ON COLUMN distance.calib.bibcode	IS 'ADS bibcode';
COMMENT ON COLUMN distance.calib.description	IS 'Distance calibration description';


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

COMMENT ON TABLE distance.data	IS 'Redshift independent distance catalog' ;
COMMENT ON COLUMN distance.data.record_id	IS 'Record ID';
COMMENT ON COLUMN distance.data.modulus	IS '{"description": "Distance modulus", "unit": "mag", "ucd": "phot.mag.distMod"}' ;
COMMENT ON COLUMN distance.data.em_modulus	IS '{"description": "Statustucal plus uncertainty of the distance modulus", "unit": "mag", "ucd": "stat.error;phot.mag.distMod"}' ;
COMMENT ON COLUMN distance.data.ep_modulus	IS '{"description": "Statustucal minus uncertainty of the distance modulus", "unit": "mag", "ucd": "stat.error;phot.mag.distMod"}' ;
COMMENT ON COLUMN distance.data.calib_id	IS 'ID of the calibration of the distance method' ;


COMMIT ;
