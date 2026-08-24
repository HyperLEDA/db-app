BEGIN;

-----------------------------------------------
-------- Galaxy Morphology Schema ---------
-----------------------------------------------
CREATE SCHEMA IF NOT EXISTS morphology ;
COMMENT ON SCHEMA morphology IS 'Catalog of the galaxy morphology';


CREATE TYPE morphology.measurement_type AS ENUM ( 'expert' , 'citizen science', 'machine learning', 'parametric', 'nonparametric', 'kinematic', 'simplified' ) ;
COMMENT ON TYPE morphology.measurement_type IS '{
"description": "Type of the morphology classification",
"values": {
  "expert": "Classical detailed visual classification of galaxy morphology (Hubble, de Vaucouleurs, etc.) made by experts",
  "citizen science": "Visual classification of galaxy morphology performed by citizen scientists (e.g. Galaxy Zoo)",
  "machine learning": "Image-based automatic classification based on machine learning algorithms (CNN, etc)",
  "parametric": "Parametric classification based on photometry and structural relations (bulge-to-total-type relation, etc.)",
  "nonparametric": "Nonparametric indices based on image statistics (Gini, M20, CAS, etc.)",
  "kinematic": "Classification based on galaxy kinematics (fast/slow rotators, dispersion-dominated systems, etc.)",
  "simplified": "Simple/coarse classification (early/late, disk/elliptical, etc.)"
  }
}';


CREATE TYPE morphology.class_type AS ENUM ('elliptical', 'lenticular', 'spiral', 'irregular', 'spheroidal') ;
COMMENT ON TYPE morphology.class_type IS '{
"description": "Galaxy class",
"values": {
  "elliptical": "Elliptical or spherical shape, structureless, smooth intensity distribution with relatively steep gradient." ,
  "lenticular": "Spheroidal bulge and disk but no visible spiral arms in the disk." ,
  "spiral": "Central bulge and disk with spiral arms." ,
  "irregular": "No arms, no bulge. Irregular profile. Low surface brightness. May host a bar.",
  "spheroidal": "Regular low surface brightness profile, no arms. May contain a tight nucleus."
  }
}';


CREATE TYPE morphology.extra_type AS ENUM ('UCD', 'cE', 'dE', 'dS0', 'dSph', 'UDG', 'UFD', 'Tr', 'Ir', 'Im', 'BCD', 'LSB', 'xLSB', 'nucleated') ;
COMMENT ON TYPE morphology.extra_type IS '{
"description": "Additional morphological and phenomenological galaxy types and classes",
"values": {
  "UCD": "Ultra-compact dwarf galaxy",
  "cE": "Compact elliptical galaxy",
  "dE": "Dwarf elliptical galaxy",
  "dS0": "Dwarf lenticular galaxy",
  "dSph": "Dwarf spheroidal galaxy",
  "UDG": "Ultra-diffuse galaxy",
  "UFD": "Ultra-faint dwarf galaxy",
  "Tr": "Transitional type galaxy",
  "Ir": "Irregular galaxy",
  "Im": "Magellanic irregular galaxy",
  "BCD": "Blue compact dwarf galaxy",
  "LSB": "Low surface brightness galaxy",
  "xLSB": "Extra low surface brightness galaxy",
  "nucleated": "Galaxy with a distinct central nucleus"
  }
}';


-------------- Hubble sequence --------------
CREATE TABLE IF NOT EXISTS morphology.hubble_sequence (
  t	SmallInt	PRIMARY KEY
, class	morphology.class_type	NOT NULL
, stage	Text	NOT NULL
, design	Text	NOT NULL
, description	Text	NOT NULL
) ;
SELECT meta.setparams( 'morphology' , 'hubble_sequence' , '{"description": "Extended Hubble-de Vaucouleurs morphological sequence", "ucd": "meta.table"}'::json ) ;
SELECT meta.setparams( 'morphology' , 'hubble_sequence' , 't' , '{"description": "de Vaucouleurs numerical morphological type", "ucd": "src.morph.type;meta.main"}'::json ) ;
SELECT meta.setparams( 'morphology' , 'hubble_sequence' , 'class' , '{"description": "Galaxy class: elliptical, lenticular, spiral, irregular, or spheroidal", "ucd": "meta.code.class"}'::json ) ;
SELECT meta.setparams( 'morphology' , 'hubble_sequence' , 'stage' , '{"description": "Intermediate stage or subtype within the classification sequence", "ucd": "meta.code.class;obs.sequence"}'::json ) ;
SELECT meta.setparams( 'morphology' , 'hubble_sequence' , 'design' , '{"description": "Hubble morphological type designation", "ucd": "src.morph.type"}'::json ) ;
SELECT meta.setparams( 'morphology' , 'hubble_sequence' , 'description' , '{"description": "Description", "ucd": "meta.note"}'::json ) ;

INSERT INTO morphology.hubble_sequence (t, class, stage, design, description) VALUES
  (-6, 'elliptical', 'compact', 'cE', 'Compact elliptical')
, (-5, 'elliptical', '0-6', 'E', 'Elliptical')
, (-4, 'elliptical', 'cD', 'cD', 'Giant elliptical. Sharp central profile and very extended low surface brightness halo')
, (-3, 'lenticular', 'early', 'S0^-', 'Lenticular. Dominant bulge, no sign of structure in disk nor dust')
, (-2, 'lenticular', 'intermediate', 'S0^0', 'Lenticular. Some structure in disk but no arms, low amounts of dust')
, (-1, 'lenticular', 'late', 'S0^+', 'Lenticular. Clear structure in disk but no arms, thin dust lanes')
, ( 0, 'spiral', '0/a', 'S0/a', 'Spiral. Very tightly wound arms, very prominent bulge, low amounts of dust')
, ( 1, 'spiral', 'a',  'Sa',  'Spiral. Tightly wound arms, very prominent bulge, low amounts of dust')
, ( 2, 'spiral', 'ab', 'Sab', 'Spiral. Quite tightly wound arms, prominent bulge, low amounts of dust')
, ( 3, 'spiral', 'b',  'Sb',  'Spiral. Quite tightly wound arms, prominent bulge, strong dust lanes')
, ( 4, 'spiral', 'bc', 'Sbc', 'Spiral. Quite loosely wound arms, medium bulge, dust lanes')
, ( 5, 'spiral', 'c',  'Sc',  'Spiral. Grand design spiral, fairly weak bulge, dust lanes')
, ( 6, 'spiral', 'cd', 'Scd', 'Spiral. Loosely wound and weak arms, weak bulge, scattered dust')
, ( 7, 'spiral', 'd',  'Sd',  'Spiral. Loosely wound and very weak arms, weak bulge, scattered dust')
, ( 8, 'spiral', 'dm', 'Sdm', 'Spiral. Very loosely wound arms, very weak bulge, low amounts of dust')
, ( 9, 'spiral', 'm',  'Sm',  'Spiral. Some indication of spiral arms, very weak bulge, low amounts of dust')
, (10, 'irregular',  'irregular', 'Ir',  'Irregular including Magellanic and non-Magellanic types. No arms, no bulge. Irregular profile. Low surface brightness. May host a bar')
, (11, 'spheroidal', 'spheroidal', 'dSph',  'Dwarf spheroidal/elliptical. Regular low-surface-brightness profile with no spiral arms. May contain a compact nucleus. LEDA extension of the standard Hubble sequence')
;


-------------- Morphology attributes --------------
CREATE TYPE morphology.attribute_group_type AS ENUM ( 'appearance' , 'environment' , 'bulge' , 'spiral pattern' , 'texture' , 'dynamics', 'interaction', 'peculiar') ;
COMMENT ON TYPE morphology.attribute_group_type IS '{
"description": "Groups of galaxy morphological attributes",
"values": {
  "appearance": "Global appearance, including inclination and elongation",
  "environment": "Local environment, including neighbouring galaxies and image contamination",
  "bulge": "Properties and morphology of the central bulge",
  "spiral pattern": "Properties of spiral arms, including their prominence and curvature",
  "texture": "Textural properties, including visible dust, dust patchiness, flocculence and high-surface-brightness regions",
  "dynamics": "Internal structural features associated with galaxy dynamics, including bars and rings",
  "interaction": "Morphological distortions and structures associated with galaxy interactions, including perturbations and tidal features",
  "peculiar": "Unusual geometric or structural configurations not adequately described by the standard Hubble classification"
  }
}';


CREATE TABLE IF NOT EXISTS morphology.attributes (
  id	Text	PRIMARY KEY
, attribute_group	morphology.attribute_group_type	NOT NULL
, description	JSON	NOT NULL
) ;
SELECT meta.setparams( 'morphology' , 'attributes' , '{"description": "Dictionary of attributes", "ucd": "meta.table"}'::json ) ;
SELECT meta.setparams( 'morphology' , 'attributes' , 'id' , '{"description": "Attribute ID", "ucd": "meta.id"}'::json ) ;
SELECT meta.setparams( 'morphology' , 'attributes' , 'attribute_group' , '{"description": "Attribute group", "ucd": "meta.code.class"}'::json ) ;
SELECT meta.setparams( 'morphology' , 'attributes' , 'description' , '{"description": "Attribute description", "ucd": "meta.note"}'::json ) ;

INSERT INTO morphology.attributes VALUES
  ( 'inclination/elongation' , 'appearance',
'{
"description": "Dimensionless inclination parameter, f=1−cosθ, for disk galaxies and apparent elongation, f=1−b/a, for galaxies with no evident disk (elliptical, irregular and spheroidal galaxies)",
"values": {
  "0": "0°–35° disk inclination angle (face-on) or very low elongation 0 ≤ f < 0.2",
  "0.25": "35°–50° disk inclination angle or low elongation 0.2 ≤ f < 0.4",
  "0.5": "50°–70° disk inclination angle or moderate elongation 0.4 ≤ f < 0.7",
  "0.75": "70°–80° disk inclination angle or strong elongation 0.7 ≤ f < 0.8",
  "1": "80°–90° disk inclination angle (edge-on) or very strong elongation 0.8 ≤ f ≤ 1"
  }
}'::JSON )

, ( 'contamination' , 'environment',
'{
"description": "Severity of the contamination by bright stars, overlapping galaxies or image artifacts",
"values": {
  "0": "no overlapping source on the galaxy",
  "0.25": "only faint sources overlapping the galaxy (negligible effect on photometry or morphology)",
  "0.5": "overlapping sources on the galaxy or faint light pollution (some impact on photometry and morphology)",
  "0.75": "bright sources overlapping the galaxy or strong light pollution (large impact on photometry and morphology)",
  "1": "most of the galaxy dominated by light from a very bright contaminant (unreliable photometry or morphology)"
  }
}'::JSON )

, ( 'bulge-to-total' , 'bulge',
'{
"description": "Bulge-to-total flux ratio: relative contribution of the bulge to the total flux of the galaxy",
"values": {
  "0": "no bulge",
  "0.25": "very weak bulge ~25% of the total flux",
  "0.5": "medium bulge ~50% of the total flux",
  "0.75": "strong bulge ~75% of the total flux",
  "1": "all flux within bulge, no disk nor spiral arms"
  }
}'::JSON )

, ( 'spiral' , 'spiral pattern',
'{
"description": "Relative prominence of the spiral pattern",
"values": {
  "0": "no visible spiral pattern",
  "0.25": "weak or barely visible spiral pattern",
  "0.5": "moderately prominent spiral pattern",
  "0.75": "strong and clearly defined spiral pattern",
  "1": "very prominent spiral pattern with dominant, well-defined arms"
  }
}'::JSON )
, ( 'spiral curvature' , 'spiral pattern',
'{
"description": "Intrinsic curvature of the spiral arms as if seen face-on",
"values": {
  "0": "wide open spiral arms, with pitch angles of 40° or more",
  "0.25": "open spiral arms: 30° ≤ pitch angle < 40°",
  "0.5": "moderately open spiral arms: 20° ≤ pitch angle < 30°",
  "0.75": "closed-in spiral arms: 10° ≤ pitch angle < 20°",
  "1": "tightly wound spiral arms, with pitch angles of 10° or less"
  }
}'::JSON )

, ( 'dust' , 'texture',
'{
"description": "Dust content",
"values": {
  "0": "no dust",
  "0.25": "indications of dust, but dust cannot be located",
  "0.5": "low to moderate amounts of dust, can be located",
  "0.75": "significant amounts of dust covering <50% of the surface of the galaxy",
  "1": "high amounts of dust covering ≥50% of the surface of the galaxy"
}
}'::JSON )
, ( 'dust patchiness' , 'texture',
'{
"description": "Patchiness of the dust distribution",
"values": {
  "0": "thin lane(s) of dust with smooth outline",
  "0.25": "thin lane(s) of dust with patchy outline",
  "0.5": "patchy lane(s) of dust and some other small patches",
  "0.75": "very patchy lane(s) of dust and many other patches",
  "1": "extremely patchy distribution of the dust"
  }
}'::JSON )
, ( 'flocculence' , 'texture',
'{
"description": "Flocculent features of scattered HII regions relative to the spiral arms and the underlying smooth profile components",
"values": {
  "0": "no visible flocculence",
  "0.25": "weak/barely visible flocculence/patchiness limited to small parts of the galaxy disk",
  "0.5": "some flocculence visible in parts of the galaxy disk",
  "0.75": "significant flocculence over most of the galaxy disk",
  "1": "strong flocculence over most of the galaxy disk"
  }
}'::JSON )
, ( 'hotspot' , 'texture',
'{"description": "Regions of very high surface brightness (giant regions of star formation, active nuclei, or stellar nuclei of dwarf galaxies)",
"values": {
  "0": "no hot spot",
  "0.25": "small part of the galaxy flux included in one or several hot spots",
  "0.5": "moderate part of the galaxy flux included in one or several hot spots",
  "0.75": "significant part of the galaxy flux included in one or several hot spots",
  "1": "one or several hot spots dominate the galaxy flux"
  }
}'::JSON )

, ( 'bar' , 'dynamics',
'{
"description": "Relative prominence and extent of the bar",
"values": {
  "0": "no visible bar",
  "0.25": "short, barely visible bar feature",
  "0.5": "short bar, with a length about one third of D25",
  "0.75": "long bar, extending over about half of D25",
  "1": "very long, prominent bar that extends over more than half of D25"
  }
}'::JSON )
, ( 'inner ring' , 'dynamics',
'{
"description": "Presence and relative prominence of an inner ring-like overdensity located within the disk and/or spiral pattern at the end of the bar (distinct from nuclear rings located well inside the bar)",
"values": {
  "0": "no inner ring",
  "0.25": "low ring contribution to the galaxy flux",
  "0.5": "intermediate ring contribution to the galaxy flux",
  "0.75": "significant ring contribution to the galaxy flux",
  "1": "highest ring contribution to the galaxy flux"
  }
}'::JSON )
, ( 'outer ring' , 'dynamics',
'{
"description": "Presence and relative prominence of a ring-like overdensity located mostly outside the main disk and spiral-arm pattern",
"values": {
  "0": "no outer ring",
  "0.25": "low ring contribution to the galaxy flux",
  "0.5": "intermediate ring contribution to the galaxy flux",
  "0.75": "significant ring contribution to the galaxy flux",
  "1": "highest ring contribution to the galaxy flux"
  }
}'::JSON )
, ( 'pseudo-ring' , 'dynamics',
'{
"description": "Presence and relative prominence of an outer pseudo-ring (Buta & Combes, 1996): R1 pseudo-ring having a dimpled eight shape due to a 180◦ winding of the spiral arms relative to the bar; R2 pseudo-ring with a winding of 270◦; and an intermediate R1-R2 pattern",
"values": {
  "0": "no visible pseudo-ring feature",
  "0.25": "R2 and R1-R2 pseudo-rings containing a low fraction of the galaxy flux",
  "0.5": "R2 and R1-R2 pseudo-rings containing a higher fraction of the galaxy flux",
  "0.75": "R1 pseudo-ring feature containing a low fraction of the galaxy flux",
  "1": "R1 pseudo-ring feature containing a higher fraction of the galaxy flux"
  }
}'::JSON )

, ( 'perturbation' , 'interaction',
'{
"description": "Amplitude of morphological distortions of the galaxy",
"values": {
  "0": "no distortion",
  "0.25": "slight distortion",
  "0.5": "moderate distortion",
  "0.75": "strong distortion; profile components (bulge, disk, spiral arms) still visible",
  "1": "completely distorted profile, components can be barely distinguished"
  }
}'::JSON )

, ( 'x-shape' , 'bulge',
'{
"description": "An X-shaped or peanut-shaped morphology of the central bulge, usually associated with a vertically thickened bar",
"values": {
  "0": "no X-structure",
  "0.5": "moderate X-structure",
  "1": "strong X-structure"
}
}'::JSON )
;


-------------- de Vaucouleurs numeric types --------------
CREATE TABLE IF NOT EXISTS morphology.t (
  record_id	Text	NOT NULL	REFERENCES layer0.records(id)	ON UPDATE cascade ON DELETE restrict
, value	SmallInt	NOT NULL	REFERENCES morphology.hubble_sequence (t)	ON UPDATE cascade ON DELETE restrict
, em_value	Real	CHECK (em_value>=0)
, ep_value	Real	CHECK (ep_value>=0)
, method	morphology.measurement_type	NOT NULL
, CHECK ( (em_value IS NULL and ep_value IS NULL) or (em_value IS NOT NULL and ep_value IS NOT NULL) )
, PRIMARY KEY (record_id, method)
) ;
CREATE INDEX ON morphology.t (value) ;
CREATE INDEX ON morphology.t (method) ;

SELECT meta.setparams( 'morphology' , 't' , '{"description": "Catalog of de Vaucouleurs numeric types", "ucd": "meta.table"}'::json ) ;
SELECT meta.setparams( 'morphology' , 't' , 'record_id' , '{"description": "Record ID", "ucd": "meta.id"}'::json ) ;
SELECT meta.setparams( 'morphology' , 't' , 'value' , '{"description": "de Vaucouleurs numerical morphological type", "ucd": "src.morph.type"}'::json ) ;
SELECT meta.setparams( 'morphology' , 't' , 'em_value' , '{"description": "Lower uncertainty", "ucd": "stat.error"}'::json ) ;
SELECT meta.setparams( 'morphology' , 't' , 'ep_value' , '{"description": "Upper uncertainty", "ucd": "stat.error"}'::json ) ;
SELECT meta.setparams( 'morphology' , 't' , 'method' , '{"description": "Method used to determine the morphological type", "ucd": "meta.code.class"}'::json ) ;



-------------- Catalog of galaxy features --------------
CREATE TABLE IF NOT EXISTS morphology.features (
  record_id	Text	NOT NULL	REFERENCES layer0.records(id)	ON UPDATE cascade ON DELETE restrict
, attribute_id	Text	NOT NULL	REFERENCES morphology.attributes (id)	ON UPDATE cascade ON DELETE restrict
, value	Real	NOT NULL
, em_value	Real	CHECK (em_value>=0)
, ep_value	Real	CHECK (ep_value>=0)
, method	morphology.measurement_type	NOT NULL
, CHECK (value >= 0 AND value <= 1)
, CHECK ( (em_value IS NULL and ep_value IS NULL) or (em_value IS NOT NULL and ep_value IS NOT NULL) )
, PRIMARY KEY (record_id, attribute_id, method)
) ;
CREATE INDEX ON morphology.features (attribute_id, method) ;
CREATE INDEX ON morphology.features (method) ;

SELECT meta.setparams( 'morphology' , 'features' , '{"description": "Catalog of morphological features", "ucd": "meta.table"}'::json ) ;
SELECT meta.setparams( 'morphology' , 'features' , 'record_id' , '{"description": "Record ID", "ucd": "meta.id"}'::json ) ;
SELECT meta.setparams( 'morphology' , 'features' , 'attribute_id' , '{"description": "Morphological attribute ID", "ucd": "meta.id"}'::json ) ;
SELECT meta.setparams( 'morphology' , 'features' , 'value' , '{"description": "Attribute value", "ucd": "stat.value;meta.main"}'::json ) ;
SELECT meta.setparams( 'morphology' , 'features' , 'em_value' , '{"description": "Lower uncertainty of the attribute", "ucd": "stat.error"}'::json ) ;
SELECT meta.setparams( 'morphology' , 'features' , 'ep_value' , '{"description": "Upper uncertainty of the attribute", "ucd": "stat.error"}'::json ) ;
SELECT meta.setparams( 'morphology' , 'features' , 'method' , '{"description": "Method used to determine the morphological attribute", "ucd": "meta.code.class"}'::json ) ;


-------------- Morphology of Dwarfs --------------
CREATE TABLE IF NOT EXISTS morphology.extra (
  record_id	Text	NOT NULL	REFERENCES layer0.records(id)	ON UPDATE cascade ON DELETE restrict
, type	morphology.extra_type	NOT NULL
, PRIMARY KEY (record_id, type)
) ;
CREATE INDEX ON morphology.extra (type) ;

SELECT meta.setparams( 'morphology' , 'extra' , '{"description": "Catalog of additional morphological and phenomenological types and classes", "ucd": "meta.table"}'::json ) ;
SELECT meta.setparams( 'morphology' , 'extra' , 'record_id' , '{"description": "Record ID", "ucd": "meta.id"}'::json ) ;
SELECT meta.setparams( 'morphology' , 'extra' , 'type' , '{"description": "Additional morphological or phenomenological type", "ucd": "src.morph.type"}'::json ) ;


-------------- Spiral pattern rotation --------------
CREATE TABLE IF NOT EXISTS morphology.spiral_winding (
  record_id	Text	NOT NULL	REFERENCES layer0.records(id)	ON UPDATE cascade ON DELETE restrict
, winding	Real	NOT NULL
, em_winding	Real	CHECK (em_winding>=0)
, ep_winding	Real	CHECK (ep_winding>=0)
, method	morphology.measurement_type NOT NULL
, CHECK (winding >= -1 AND winding <= 1)
, CHECK ( (em_winding IS NULL and ep_winding IS NULL) or (em_winding IS NOT NULL and ep_winding IS NOT NULL) )
, PRIMARY KEY (record_id, method)
);

SELECT meta.setparams( 'morphology' , 'spiral_winding' , '{"description": "Catalog of spiral pattern windings", "ucd": "meta.table"}'::json ) ;
SELECT meta.setparams( 'morphology' , 'spiral_winding' , 'record_id' , '{"description": "Record ID", "ucd": "meta.id"}'::json ) ;
SELECT meta.setparams( 'morphology' , 'spiral_winding' , 'winding' , '{
"description": "Apparent spiral winding direction on the sky",
"values": {
  "+1": "definitely clockwise",
  "+0.5": "probably clockwise",
  "0": "no preferred direction",
  "-0.5": "probably counter-clockwise",
  "-1": "definitely counter-clockwise"
  },
"ucd": "stat.value;meta.main"
}'::json ) ;
SELECT meta.setparams( 'morphology' , 'spiral_winding' , 'em_winding' , '{"description": "Lower uncertainty of the winding direction", "ucd": "stat.error"}'::json ) ;
SELECT meta.setparams( 'morphology' , 'spiral_winding' , 'ep_winding' , '{"description": "Upper uncertainty of the winding direction", "ucd": "stat.error"}'::json ) ;
SELECT meta.setparams( 'morphology' , 'spiral_winding' , 'method' , '{"description": "Method used to determine the spiral winding direction", "ucd": "meta.code.class"}'::json ) ;


COMMIT ;
