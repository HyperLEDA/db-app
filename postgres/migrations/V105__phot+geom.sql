BEGIN ;

-----------------------------------------------------
-- Percentage of the total flux
-- Methods:
--   Total
--   Model
--   Visual
-----------------------------------------------------

CREATE TABLE geometry.circFluxLevel (
  level	real	NOT NULL
, photid	integer	REFERENCES photometry.data (id)	ON DELETE restrict ON UPDATE cascade
, PRIMARY KEY (id)
, UNIQUE (pgc,quality,band,a,level,dataset)
) INHERITS (geometry.circle) ;
CREATE INDEX ON geometry.circFluxLevel (dataset) ;

COMMENT ON TABLE geometry.circFluxLevel	IS 'Equivalent diameter table at specific total flux level' ;
COMMENT ON COLUMN geometry.circFluxLevel.id	IS 'Measurement ID' ;
COMMENT ON COLUMN geometry.circFluxLevel.pgc	IS 'PGC number of the object' ;
COMMENT ON COLUMN geometry.circFluxLevel.band	IS 'Passband ID' ;
COMMENT ON COLUMN geometry.circFluxLevel.quality	IS 'Measurement quality' ;
COMMENT ON COLUMN geometry.circFluxLevel.dataset	IS 'Dataset of the measurements' ;
COMMENT ON COLUMN geometry.circFluxLevel.modification_time	IS 'Timestamp when the record was added to the database' ;
COMMENT ON COLUMN geometry.circFluxLevel.a	IS '{"description" : "Equivalent diameter", "unit" : "arcsec", "ucd" : "phys.angSize"}' ;
COMMENT ON COLUMN geometry.circFluxLevel.e_a	IS '{"description" : "Error of the equivalent diameter", "unit" : "arcsec", "ucd" : "stat.error"}' ; ;
COMMENT ON COLUMN geometry.circFluxLevel.level	IS 'Level of the total flux [%]. Effective or half-light levele is 50%' ;


CREATE TABLE geometry.fluxLevel (
  level	real	NOT NULL
, photid	integer	REFERENCES photometry.data (id)	ON DELETE restrict ON UPDATE cascade
, PRIMARY KEY (id)
, UNIQUE (pgc,quality,band,a,b,pa,level,dataset)
) INHERITS (geometry.ellipse) ;
CREATE INDEX ON geometry.fluxLevel (dataset) ;

COMMENT ON TABLE geometry.fluxLevel	IS 'Geometry table at specific total flux level' ;
COMMENT ON COLUMN geometry.fluxLevel.id	IS 'Measurement ID' ;
COMMENT ON COLUMN geometry.fluxLevel.pgc	IS 'PGC number of the object' ;
COMMENT ON COLUMN geometry.fluxLevel.band	IS 'Passband ID' ;
COMMENT ON COLUMN geometry.fluxLevel.quality	IS 'Measurement quality' ;
COMMENT ON COLUMN geometry.fluxLevel.dataset	IS 'Dataset of the measurements' ;
COMMENT ON COLUMN geometry.fluxLevel.modification_time	IS 'Timestamp when the record was added to the database' ;
COMMENT ON COLUMN geometry.fluxLevel.a	IS '{"description" : "Major axis diameter", "unit" : "arcsec", "ucd" : "phys.angSize"}' ;
COMMENT ON COLUMN geometry.fluxLevel.e_a	IS '{"description" : "Error of the major axis diameter", "unit" : "arcsec", "ucd" : "stat.error"}' ; ;
COMMENT ON COLUMN geometry.fluxLevel.b	IS '{"description" : "Minor axis diameter", "unit" : "arcsec", "ucd" : "phys.angSize"}' ;
COMMENT ON COLUMN geometry.fluxLevel.e_b	IS '{"description" : "Error of the minor exis diameter", "unit" : "arcsec", "ucd" : "stat.error"}' ; ;
COMMENT ON COLUMN geometry.fluxLevel.pa	IS 'Position angle from North to East from 0 to 180 [degrees]' ;
COMMENT ON COLUMN geometry.fluxLevel.e_pa	IS 'Error of the position angle [degrees]' ;
COMMENT ON COLUMN geometry.fluxLevel.level	IS 'Level of the total flux [%]. Effective or half-light level is 50%' ;


-- -----------------------------------------------------
-- -- Percentage of the Petrosian flux
-- -- Methods:
-- --   Petro
-- -----------------------------------------------------
-- 
-- CREATE TABLE geometry.circPetroFluxLevel (
--   PRIMARY KEY (id)
-- , UNIQUE (pgc,quality,band,a,level,dataset)
-- , FOREIGN KEY (photid)	REFERENCES photometry.circPetro (id)	ON DELETE restrict ON UPDATE cascade
-- ) INHERITS (geometry.circFluxLevel) ;
-- CREATE INDEX ON geometry.circPetroFluxLevel (dataset) ;
-- 
-- COMMENT ON TABLE geometry.fluxlevel	IS 'Equivalent diameter table at specific Petrosian flux level' ;
-- COMMENT ON COLUMN geometry.fluxlevel.id	IS 'Measurement ID' ;
-- COMMENT ON COLUMN geometry.fluxlevel.pgc	IS 'PGC number of the object' ;
-- COMMENT ON COLUMN geometry.fluxlevel.band	IS 'Passband ID' ;
-- COMMENT ON COLUMN geometry.fluxlevel.quality	IS 'Measurement quality' ;
-- COMMENT ON COLUMN geometry.fluxlevel.dataset	IS 'Dataset of the measurements' ;
-- COMMENT ON COLUMN geometry.fluxlevel.modification_time	IS 'Timestamp when the record was added to the database' ;
-- COMMENT ON COLUMN geometry.fluxlevel.a	IS '{"description" : "Equivalent diameter", "unit" : "arcsec", "ucd" : "phys.angSize"}' ;
-- COMMENT ON COLUMN geometry.fluxlevel.e_a	IS '{"description" : "Error of the equivalent diameter", "unit" : "arcsec", "ucd" : "stat.error"}' ; ;
-- COMMENT ON COLUMN geometry.fluxlevel.level	IS 'Level of the Petrocian flux [%]. Effective or half-light levele is 50%' ;
-- 
-- 
-- CREATE TABLE geometry.petroFluxLevel (
-- , PRIMARY KEY (id)
-- , UNIQUE (pgc,quality,band,a,b,pa,level,dataset)
-- , FOREIGN KEY photid	REFERENCES photometry.petro (id)	ON DELETE restrict ON UPDATE cascade
-- ) INHERITS (geometry.fluxLevel) ;
-- CREATE INDEX ON geometry.fluxLevel (dataset) ;
-- 
-- COMMENT ON TABLE geometry.fluxlevel	IS 'Geometry table at the specific Petrosian flux level' ;
-- COMMENT ON COLUMN geometry.fluxlevel.id	IS 'Measurement ID' ;
-- COMMENT ON COLUMN geometry.fluxlevel.pgc	IS 'PGC number of the object' ;
-- COMMENT ON COLUMN geometry.fluxlevel.band	IS 'Passband ID' ;
-- COMMENT ON COLUMN geometry.fluxlevel.quality	IS 'Measurement quality' ;
-- COMMENT ON COLUMN geometry.fluxlevel.dataset	IS 'Dataset of the measurements' ;
-- COMMENT ON COLUMN geometry.fluxlevel.modification_time	IS 'Timestamp when the record was added to the database' ;
-- COMMENT ON COLUMN geometry.fluxlevel.a	IS '{"description" : "Major axis diameter", "unit" : "arcsec", "ucd" : "phys.angSize"}' ;
-- COMMENT ON COLUMN geometry.fluxlevel.e_a	IS '{"description" : "Error of the major axis diameter", "unit" : "arcsec", "ucd" : "stat.error"}' ; ;
-- COMMENT ON COLUMN geometry.fluxlevel.b	IS '{"description" : "Minor axis diameter", "unit" : "arcsec", "ucd" : "phys.angSize"}' ;
-- COMMENT ON COLUMN geometry.fluxlevel.e_b	IS '{"description" : "Error of the minor exis diameter", "unit" : "arcsec", "ucd" : "stat.error"}' ; ;
-- COMMENT ON COLUMN geometry.fluxlevel.pa	IS 'Position angle from North to East from 0 to 180 [degrees]' ;
-- COMMENT ON COLUMN geometry.fluxlevel.e_pa	IS 'Error of the position angle [degrees]' ;
-- COMMENT ON COLUMN geometry.fluxlevel.level	IS 'Level of the Petrosian flux [%]. Effective or half-light level is 50%' ;



COMMIT ;