BEGIN;

ALTER TYPE common.quality RENAME VALUE 'ok' TO 'regular' ;
ALTER TYPE common.quality RENAME VALUE 'lowsnr' TO 'low_snr' ;
ALTER TYPE common.quality RENAME VALUE 'sus' TO 'suspected' ;
ALTER TYPE common.quality RENAME VALUE '>' TO 'lower_limit' ;
ALTER TYPE common.quality RENAME VALUE '<' TO 'upper_limit' ;

ALTER TYPE common.quality RENAME TO qualityType ;

COMMENT ON TYPE common.QualityType	IS '{
"description": "Quality flag of the measurement", 
"values": {
  "regular": "regular measurement", 
  "low_snr": "low signal-to-noise", 
  "suspected": "suspected measurement", 
  "lower_limit": "lower limit", 
  "upper_limit": "upper limit", 
  "wrong": "wrong measurement"
  }
}' ;

COMMIT;
