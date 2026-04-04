BEGIN;

-- CREATE TYPE cz.DimentionType AS ENUM (0, 1, 2) ;
-- COMMENT ON TYPE cz.DimentionType IS '0 corresponds to a beam/fiber, 1 corresponds to a long-slit, 2 corresponds to panoramic spectroscopy ' ;

CREATE TYPE cz.MethodType AS ENUM ('average','emission','absorption','xcorr','fit','photoz') ;

COMMENT ON TYPE cz.MethodType IS '{ 
"description": "Method of the cz measurement",
"values": {
  "average": "Average of measurements of membersi",
  "emission": "Emission lines",
  "absorption": "Absorption lines",
  "xcorr": "Cross correlation",
  "fit": "Stellar populations fit",
  "photoz": "Photometric redshift"
  }
}' ;


-- CREATE TABLE cz.datasets (
--   id Integer PRIMARY KEY; 
-- , table_id	Integer	NOT NULL	REFERENCES layer0.tables (id) ON DELETE restrict ON UPDATE cascade
-- , method cz.MethodType	NOT NULL
-- ) ;

ALTER TABLE cz.data
ADD COLUMN method	cz.MethodType	NOT NULL,
DROP COLUMN modification_time ;

UPDATE cz.data SET method = 'average' 
FROM layer0.records AS r
WHERE 
  cz.data.record_id = r.id
  and r.table_id = 1 -- hyperleda_m000
;

COMMIT;
