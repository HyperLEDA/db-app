BEGIN;

CREATE TYPE common.velocity_reference_frame_type AS ENUM (
  'Heliocentric'
, 'Barycentric'
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
  "Heliocentric": "Heliocentric reference frame, with origin at the centre of the Sun",
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
  ( 'Helio', 'Heliocentric', 'Heliocentric reference frame' )
, ( 'Bary' , 'Barycentric', 'Barycentric reference frame' )
;


COMMIT ;