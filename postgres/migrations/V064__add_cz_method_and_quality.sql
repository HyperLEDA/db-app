BEGIN;

CREATE TYPE cz.method_type AS ENUM ('unknown', 'emission', 'absorption','xcorr','fit','photoz','best','average') ;
COMMENT ON TYPE cz.method_type IS '{ 
"description": "Redshift measurement method",
"values": {
  "unknown": "Unspecified method"
  "emission": "Emission lines",
  "absorption": "Absorption lines",
  "xcorr": "Cross correlation",
  "fit": "Stellar populations fit",
  "photoz": "Photometric redshift"
  "best": "Best measurement",
  "average": "Average of measurements",
  }
}' ;


ALTER TABLE cz.data
  ADD COLUMN method	cz.method_type	NOT NULL	DEFAULT 'unknown'
, ADD COLUMN quality	common.quality_type	NOT NULL	DEFAULT 'regular'
;
SELECT meta.setparams( 'cz', 'data', 'method', '{"description": "CZ measurement type (emission, absorption, xcorr, fit, photoz, best, average)"}'::json ) ;
SELECT meta.setparams( 'cz', 'data', 'quality', '{"description": "Measurement quality flag"}'::json ) ;

ALTER TABLE cz.data
  DROP CONSTRAINT data_pkey ;
ALTER TABLE cz.data
  ADD PRIMARY KEY (record_id, method) ;

COMMIT;
