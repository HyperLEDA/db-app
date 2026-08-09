BEGIN;

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
