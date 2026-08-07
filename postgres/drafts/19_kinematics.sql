BEGIN;


----------------------------------------------------
-------------- Kinematics schema -------------------
----------------------------------------------------
CREATE SCHEMA IF NOT EXISTS kinematics ;
COMMENT ON SCHEMA kinematics IS 'Catalog of galaxy kinematics';


CREATE TYPE kinematics.WidthMethodType AS ENUM ( 'max', 'peak', 'w2p', 'mean', 'int', 'edge', 'model' ) ;
COMMENT ON TYPE kinematics.WidthMethodType	IS '{
"description": "Method of the line width measurement",
"values": {
  "max": "Width measured at a fixed fraction of the global maximum line profile intensity", 
  "peak": "Width measured at a fixed fraction of the intensity of each horn independently", 
  "w2p": "Width measured at a fixed fraction of the mean intensity of the two profile peaks", 
  "mean": "Width measured at a fixed fraction of the mean flux density over the line profile", 
  "int": "Width determined from the cumulative (integrated) flux distribution of the line profile", 
  "edge": "Width determined from the inferred profile edges", 
  "model": "Width derived from a fitted model of the spectral line profile"
  }
}' ;


------------- Line Width ---------------------
CREATE TABLE kinematics.line (
  record_id	Text	NOT NULL	REFERENCES layer0.records(id) ON UPDATE cascade ON DELETE restrict
, line_id	Text	NOT NULL	REFERENCES common.lines(id) ON UPDATE cascade ON DELETE restrict
, width	real	NOT NULL
, e_width	real
, method	kinematics.WidthMethodType	NOT NULL	DEFAULT 'peak'
, level	real	NOT NULL	DEFAULT 50
, resolution	real	NOT NULL
, PRIMARY KEY (record_id, line_id, method, level)
, CHECK (width > 0)
, CHECK (e_width IS NULL OR e_width >= 0)
, CHECK (resolution > 0)
);
CREATE INDEX ON kinematics.line (line_id, method, level) ;

COMMENT ON TABLE  kinematics.line	IS 'Catalog of spectral line width measurements' ;
COMMENT ON COLUMN kinematics.line.record_id	IS 'Record ID' ;
COMMENT ON COLUMN kinematics.line.line_id	IS 'Spectral line ID' ;
COMMENT ON COLUMN kinematics.line.width	IS '{"description":"Spectral line width", "unit":"km/s", "ucd":"spect.line.width"}' ;
COMMENT ON COLUMN kinematics.line.e_width	IS '{"description":"Error of the spectral line width", "unit":"km/s", "ucd":"stat.error"}' ;
COMMENT ON COLUMN kinematics.line.method	IS 'Width measurement method' ;
COMMENT ON COLUMN kinematics.line.level	IS 'Reference level expressed as a percentage of the adopted intensity measure' ;
COMMENT ON COLUMN kinematics.line.resolution	IS '{"description":"Effective velocity resolution after smoothing", "unit":"km/s", "ucd":"spect.resolution;phys.veloc"}' ;

COMMIT;
