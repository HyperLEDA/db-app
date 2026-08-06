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


CREATE TYPE common.VelocityConventionType AS ENUM ( 'optical', 'radio', 'relativistic' ) ;

COMMENT ON TYPE common.VelocityConventionType IS '{
"description": "Velocity convention",
"values": {
  "optical": "Voptical=c(λ-λ0)/λ0=cz",
  "radio": "Vradio=c(ν0-ν)/ν0; cz=Vradio/(1-Vradio/c)",
  "relativistic": "Relativistic Doppler effect: V=c(ν0^2-ν^2)/(ν0^2+ν^2)=c(λ^2-λ0^2)/(λ^2+λ0^2)=c[(1+z)^2-1]/[(1+z)^2+1]"
  }
}' ;


COMMIT;
