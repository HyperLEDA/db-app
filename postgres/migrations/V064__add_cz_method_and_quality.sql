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

UPDATE cz.data SET method = 'average'  WHERE record_id IN (SELECT hyperleda_internal_id FROM rawdata.hyperleda_m000) ;
UPDATE cz.data SET method = 'best'     WHERE record_id IN (SELECT hyperleda_internal_id FROM rawdata."nearby_galaxy_catalog_2026-02-22") ;
UPDATE cz.data SET method = 'best'     WHERE record_id IN (SELECT hyperleda_internal_id FROM rawdata."priv_comm_Makarov_MGC43397") ;
UPDATE cz.data SET method = 'best'     WHERE record_id IN (SELECT hyperleda_internal_id FROM rawdata."50_mpc_2026-05-26") ;
UPDATE cz.data SET method = 'emission' WHERE record_id IN (SELECT hyperleda_internal_id FROM rawdata."VIII_73_hicat") ;
UPDATE cz.data SET method = 'emission' WHERE record_id IN (SELECT hyperleda_internal_id FROM rawdata."VIII_89_nhicat_2026-08-12") ;
UPDATE cz.data SET method = 'fit'      WHERE record_id IN (SELECT hyperleda_internal_id FROM rawdata."J_A+A_660_A2_Alcyoneus") ;

DELETE FROM cz.data WHERE record_id IN (SELECT hyperleda_internal_id FROM rawdata."manga_2026-02-28") ;

UPDATE cz.data SET quality = 'suspected' WHERE record_id = '7e2c9a55-8b2a-6c6e-0c3e-2f48dbe9be5a' ;

-- ROLLBACK ;
COMMIT;
