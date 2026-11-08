BEGIN;

CREATE TYPE common.velocity_reference_frame_type AS ENUM (
  'Solar'
, 'LSR'
, 'GSR'
, 'LG'
, 'LS'
, 'CMB'
);

COMMENT ON TYPE common.velocity_reference_frame_type IS
'{
"description": "Radial velocity reference frame",
"values": {
  "Solar": "Reference frames associated with the Solar System",
  "Barycentric": "Barycentric reference frame, with origin at the Solar System barycentre",
  "LSR": "Local Standard of Rest",
  "GSR": "Galactic Standard of Rest",
  "LG": "Local Group rest frame",
  "LS": "Local Sheet rest frame",
  "CMB": "Cosmic Microwave Background rest frame"
}
}' ;


CREATE TABLE common.velocity_reference_frames (
  id	Text	PRIMARY KEY
, frame_type	common.velocity_reference_frame_type	NOT NULL
, v	Real	CHECK (v>0)
, e_v	Real	CHECK (e_v>0)
, l	Real	CHECK (l>=0 and l<360)
, e_l	Real	CHECK (e_l>0)
, b	Real	CHECK (b>=-90 and b<=+90)
, e_b	Real	CHECK (e_b>0)
, description	Text
, bib	Integer	REFERENCES common.bib(id) ON DELETE restrict ON UPDATE cascade
, CHECK ( (v IS NULL AND l IS NULL AND b IS NULL) OR (v IS NOT NULL AND l IS NOT NULL AND b IS NOT NULL) )
);

SELECT meta.setparams( 'common' , 'velocity_reference_frames' , '{"description": "Radial velocity reference frames and parameters for conversion from the heliocentric reference frame", "ucd": "meta.table"}'::json ) ;

SELECT meta.setparams( 'common' , 'velocity_reference_frames' , 'id' , '{"description": "Reference frame definition ID", "ucd": "meta.id;meta.main"}'::json );
SELECT meta.setparams( 'common' , 'velocity_reference_frames' , 'frame_type' , '{"description": "Type of the radial velocity reference frame", "ucd": "meta.code.class"}'::json );
SELECT meta.setparams( 'common' , 'velocity_reference_frames' , 'v' , '{"description": "Velocity of the Sun relative to the adopted reference frame", "ucd": "phys.veloc", "unit": "km/s"}'::json );
SELECT meta.setparams( 'common' , 'velocity_reference_frames' , 'e_v' , '{"description": "Uncertainty in the velocity of the Sun relative to the adopted reference frame", "ucd": "stat.error;phys.veloc", "unit": "km/s"}'::json );
SELECT meta.setparams( 'common' , 'velocity_reference_frames' , 'l' , '{"description": "Galactic longitude of the solar apex defining the transformation from the heliocentric to the adopted reference frame", "ucd": "pos.galactic.lon", "unit": "deg"}'::json );
SELECT meta.setparams( 'common' , 'velocity_reference_frames' , 'e_l' , '{"description": "Uncertainty in the Galactic longitude of the solar apex", "ucd": "stat.error;pos.galactic.lon", "unit": "deg"}'::json );
SELECT meta.setparams( 'common' , 'velocity_reference_frames' , 'b' , '{"description": "Galactic latitude of the solar apex defining the transformation from the heliocentric to the adopted reference frame", "ucd": "pos.galactic.lat", "unit": "deg"}'::json );
SELECT meta.setparams( 'common' , 'velocity_reference_frames' , 'e_b' , '{"description": "Uncertainty in the Galactic latitude of the solar apex", "ucd": "stat.error;pos.galactic.lat", "unit": "deg"}'::json );
SELECT meta.setparams( 'common' , 'velocity_reference_frames' , 'description' , '{"description": "Description of the adopted reference frame definition and transformation parameters", "ucd": "meta.note"}'::json );
SELECT meta.setparams( 'common' , 'velocity_reference_frames' , 'bib' , '{"description": "Bibliographic reference for the adopted reference frame definition", "ucd": "meta.ref"}'::json );

INSERT INTO common.velocity_reference_frames (id, frame_type, description ) VALUES 
  ( 'Helio', 'Solar', 'Heliocentric reference frame' )
, ( 'Bary' , 'Solar', 'Barycentric reference frame' )
;

INSERT INTO common.velocity_reference_frames (id, frame_type, v, e_v, l, e_l, b, e_b, description, bib) VALUES
  ( 'LSR_SBD2010'   , 'LSR' , 18.04411538, 1.6, 47.79628626, 6.0, 23.69031811, 2.9, 'Local Standard of Rest: (U, V, W) = (11.1 +0.69-0.75, 12.24 +0.47-0.47, 7.25 +0.37-0.36) km/s, with additional systematic uncertainties (1, 2, 0.5) km/s', 88 )
, ( 'LG_KM1996'     , 'LG'  , 316   , 5 , 93 , 2 , -4 , 2 , 'Solar apex with respect to the LG galaxies' , 87 )
, ( 'LG_MMM2025'    , 'LG'  , 301.3 , 3.3 , 94.0 , 0.7 , -2.7 , 0.3 , 'Solar apex in the LG taking into account the approach velocity between the MW and M 31 and the motion of the Sun in the Galaxy: (Vx,Vy,Vz) = (-21.1 +-3.5, +300.3 +-3.4, -14.3 +-1.4) km/s' , 89 )
, ( 'CMB_Plank2018' , 'CMB' , 369.82 , 0.11 , 264.021 , 0.011 , 48.253 , 0.005 , 'Velocity of the Sun relative to the CMB (Planck 2018)' , 86 )
;


COMMIT ;