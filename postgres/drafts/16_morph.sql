BEGIN;

-----------------------------------------------
-------- Galaxy Morphology Schema ---------
-----------------------------------------------
CREATE SCHEMA IF NOT EXISTS morphology ;
COMMENT ON SCHEMA morphology IS 'Catalog of the galaxy morphology';


CREATE TYPE morphology.class AS ENUM ('elliptical','lenticular','spiral','dwarf') ;
COMMENT ON TYPE morphology.class IS '{
"description": "Class of galaxies",
"values": {
  "elliptical": "Elliptical or spherical shape, structureless, smooth intensity distribution with relatively steep gradient." ,
  "lenticular": "Spheroidal bulge and disk but no visible spiral arms in the disk." ,
  "spiral": "Central bulge and disk with spiral arms." ,
  "dwarf": "No arms, no bulge. Low surface brightness. Irregular may host a bar. May contain a tight nucleus."
  }
}';

CREATE TYPE morphology.MethodType AS ENUM ( 'expert' , 'citizen science', 'machine learning', 'parametric', 'kinematic', 'simplified' ) ;
COMMENT ON TYPE morphology.MethodType IS '{
"description": "Type of the morphological classification",
"values": {
  "expert": "Classical detailed visual classification of galaxy morphology (Hubble, de Vaucouleurs, etc.) made by experts" ,
  "citizen science": "Detailed visual classification of galaxy morphology (Galaxy Zoo) made by citizen scientists" ,
  "machine learning": "Image based automatic classification based on machine learning algorithms (CNN, etc)" ,
  "parametric": "Parametric classification based on photometry and structural relations (B/T-type relation, etc.)" ,
  "nonparametric": "Nonparametric indices based on image statistics (Gini, M20, CAS, etc.)" ,
  "kinematic": "Classification based on galaxy kinematics (fast/slow rotators, dispersion-dominated systems, etc.)" ,
  "simplified": "Simple/coarse classification (early/late, disk/elliptical, etc.)"
  }
}';


CREATE TYPE morphology.ExtraType AS ENUM ('UCD','cE','dE','UFD','dSph','dS0','UDG','Tr','Ir','BCD','Im','LSB','XLSB') ;
COMMENT ON TYPE morphology.ExtraType IS '{
"description": "Type of dwarf galaxies",
"values": {
  "UCD": "Ultra Compact Dwarf galaxy" ,
  "cE": "Compact Elliptical galaxy" ,
  "dE": "Dwarf Elliptical galaxy" ,
  "UFD": "Ultra Faint Dwarf galaxy" ,
  "dSph": "Dwarf Spheroidal galaxy" ,
  "dS0": "Dwarf Lenticular galaxy" ,
  "UDG": "Ultra Diffuse Galaxy" ,
  "Tr": "Transitional type galaxy" ,
  "Ir": "Irregular galaxy" ,
  "Im": "Magellanic type galaxy" ,
  "BCD": "Blue Compact Dwarf galaxy" ,
  "LSB": "Low Surface Brightness galaxy" ,
  "XLSB": "Extra Low Surface Brightness galaxy"
  }
}';


-------------- Hubble sequence --------------
CREATE TABLE IF NOT EXISTS morphology.hubble (
  t	SmallInt	PRIMARY KEY
, class	morphology.class	NOT NULL
, stage	Text	NOT NULL
, design	Text	NOT NULL
, description	Text	NOT NULL
) ;

COMMENT ON TABLE morphology.hubble	IS 'The Hubble sequence' ;
COMMENT ON COLUMN morphology.hubble.t	IS 'de Vaucouleurs numeric type' ;
COMMENT ON COLUMN morphology.hubble.class	IS 'Galaxy class: elliptical, lenticular, spiral, dwarf' ;
COMMENT ON COLUMN morphology.hubble.stage	IS 'Intermediate stage within each class' ;
COMMENT ON COLUMN morphology.hubble.design	IS '{"description": "Hubble morphological type", "ucd": "src.morph.type"}' ;
COMMENT ON COLUMN morphology.hubble.description	IS 'Description' ;

INSERT INTO morphology.hubble (t, class, stage, design, description) VALUES 
  (-6, 'elliptical', 'compact', 'cE', 'Compact elliptical')
, (-5, 'elliptical', '0-6', 'E', 'Elliptical')
, (-4, 'elliptical', 'cD', 'cD', 'Giant elliptical. Sharp central profile and very extended low surface brightness halo')
, (-3, 'lenticular', 'early', 'S0^-', 'Dominant bulge, no sign of structure in disk nor dust')
, (-2, 'lenticular', 'intermediate', 'S0^0', 'Some structure in disk but no arms, low amounts of dust')
, (-1, 'lenticular', 'late', 'S0^+', 'Clear structure in disk but no arms, thin dust lanes')
, ( 0, 'spiral', '0/a', 'S0/a', 'Very tightly wound arms, very prominent bulge, low amounts of dust')
, ( 1, 'spiral', 'a',  'Sa',  'Tightly wound arms, very prominent bulge, low amounts of dust')
, ( 2, 'spiral', 'ab', 'Sab', 'Quite tightly wound arms, prominent bulge, low amounts of dust')
, ( 3, 'spiral', 'b',  'Sb',  'Quite tightly wound arms, prominent bulge, strong dust lanes')
, ( 4, 'spiral', 'bc', 'Sbc', 'Quite loosely wound arms, medium bulge, dust lanes')
, ( 5, 'spiral', 'c',  'Sc',  'Grand design spiral, fairly weak bulge, dust lanes')
, ( 6, 'spiral', 'cd', 'Scd', 'Loosely wound and weak arms, weak bulge, scattered dust')
, ( 7, 'spiral', 'd',  'Sd',  'Loosely wound and very weak arms, weak bulge, scattered dust')
, ( 8, 'spiral', 'dm', 'Sdm', 'Very loosely wound arms, very weak bulge, low amounts of dust')
, ( 9, 'spiral', 'm',  'Sm',  'Some indication of spiral arms, very weak bulge, low amounts of dust')
, (10, 'dwarf',  'Magellanic', 'Im',  'No arms, no bulge. Irregular profile. Low surface brightness. May host a bar')
;


-------------- de Vaucouleurs numeric types --------------
CREATE TABLE IF NOT EXISTS morphology.t (
  record_id	Text	PRIMARY KEY	REFERENCES layer0.records(id)	ON UPDATE cascade ON DELETE restrict
, value	SmallInt	NOT NULL	REFERENCES morphology.hubble (t)	ON UPDATE cascade ON DELETE restrict
, em_value	Real
, ep_value	Real
, method	morphology.MethodType	NOT NULL
, CHECK ( (em_value IS NULL and ep_value IS NULL) or (em_value IS NOT NULL and ep_value IS NOT NULL) )
) ;

COMMENT ON TABLE morphology.t	IS 'Catalog of de Vaucouleurs numeric types' ;
COMMENT ON COLUMN morphology.t.record_id	IS 'Record ID';
COMMENT ON COLUMN morphology.t.value	IS '{"description": "de Vaucouleurs numeric type", "ucd": "src.morph.type"}' ;
COMMENT ON COLUMN morphology.t.em_value	IS 'Lower error' ;
COMMENT ON COLUMN morphology.t.ep_value	IS 'Upper error' ;
COMMENT ON COLUMN morphology.t.method	IS 'Morphology method ID';


-------------- Morphology attributes --------------
CREATE TABLE IF NOT EXISTS morphology.attributes (
  id	Text	PRIMARY KEY
, range	Real[2]
, description	JSON
) ;

COMMENT ON TABLE morphology.attributes	IS 'List of attributes' ;
COMMENT ON COLUMN morphology.attributes.id	IS 'Attribute ID' ;
COMMENT ON COLUMN morphology.attributes.range	IS 'Attribute value range' ;
COMMENT ON COLUMN morphology.attributes.description	IS 'Attribute description' ;

INSERT INTO morphology.attributes VALUES
  ( 'multiplicity' , {0,4}, '{"description": "Abundance of galaxies brighter than main+5mag within R<=0.75*D25", "values": {"0": "no other galaxy", "1": "one neighbour", "2": "two neighbours", "3": "three neighbours", "4": " four or more neighbours"}}'::JSON )
, ( 'contamination' , {0,1}, '{"description": "severity of the contamination by bright stars, overlapping galaxies or image artifacts", "values": {"0": "no overlapping source on the galaxy", "0.25": "only faint sources overlapping the galaxy (negligible effect on photometry or morphology)", "0.5": "overlapping sources on the galaxy or faint light pollution (some impact on photometry and morphology)", "0.75": "bright sources overlapping the galaxy or strong light pollution (large impact on photometry and morphology)", "1": "most of the galaxy dominated by light from a very bright contaminant (unreliable photometry or morphology)"}}'::JSON )
, ( 'perturbation' , {0,1}, '{"description": "amplitude of distortions in the galaxy profile", "values": {"0": "no distortion", "0.25": "slight distortion", "0.5": "moderate distortion", "0.75": "Strong distortion. Profile components (bulge, disk, spiral arms) still visible", "1": "Completely distorted profile, components can be barely distinguished"}}'::JSON )
, ( 'b/t' , {0,1}, '{"description": "Bulge/Total ratio: relative contribution of the bulge to the total flux of the galaxy", "values": {"0": "no bulge", "0.25": "very weak bulge ~25% of the total flux", "0.5": "medium bulge ~50% of the total flux", "0.75": "strong bulge ~75% of the total flux", "1": "all flux within bulge, no disk nor spiral arms"}}'::JSON )
, ( 'arm' , {0,1}, '{"description": "relative strength of spiral arms", "values": {"0": "very weak or no spiral arms", "0.25": "weak contribution to the galaxy flux", "0.5": "moderate contribution to the galaxy flux", "0.75": "significant contribution to the galaxy flux", "1": "highest contribution to the galaxy flux"}}'::JSON )
, ( 'arm curvature' , {0,90}, '{"description": "intrinsic curvature of the spiral arms as if seen face-on", "values": {"45": "wide open spiral arms, with pitch angles of 40 degrees or more", "35": "open spiral arms, with pitch angles of 30 to 40 degrees", "25": "moderately open spiral arms, with pitch angles of 20 to 30 degrees", "15": "closed-in spiral arms, with pitch angles of 10 to 20 degrees", "5": "tightly wound spiral arms, with pitch angles of 10 degrees or less"}}'::JSON )
, ( 'dust' , {0,1}, '{"description": "presence of dust", "values": {"0": "no dust", "0.25": "indications of dust, but dust cannot be located", "0.5": "low to moderate amounts of dust, can be located", "0.75": "significant amounts of dust covering <50% of the surface of the galaxy", "1": "high amounts of dust covering >50% of the surface of the galaxy"}}'::JSON )
, ( 'dust patchness' , {0,1}, '{"description": "patchiness of the dust distribution", "values": {"0": "thin lane(s) of dust with smooth outline", "0.25": "thin lane(s) of dust with patchy outline", "0.5": "patchy lane(s) of dust and some other small patches", "0.75": "very patchy lane(s) of dust and many other patches", "1": "extremely patchy distribution of the dust"}}'::JSON )
, ( 'flocculence' , {0,1}, '{"description": "flocculent features of scattered HII regions relative to the spiral arms and the underlying smooth profile components", "values": {"0": "no visible flocculence", "0.25": "weak/barely visible flocculence/patchiness limited to small parts of the galaxy disk", "0.5": "some flocculence visible in parts of the galaxy disk", "0.75": "significant flocculence over most of the galaxy disk", "1": "strong flocculence over most of the galaxy disk"}}'::JSON )
, ( 'hot spot' , {0,1}, '{"description": "regions of very high surface brightness (giant regions of star formation, active nuclei, or stellar nuclei of dwarf galaxies)", "values": {"0": "no hot spot", "0.25": "small part of the galaxy flux included in one or several hot spots", "0.5": "moderate part of the galaxy flux included in one or several hot spots", "0.75": "significant part of the galaxy flux included in one or several hot spots", "1": "one or several hot spots dominate the galaxy flux"}}'::JSON )
, ( 'bar' , {0,1}, '{"description": "presence of a central bar component", "values": {"0": "no visible bar", "0.25": "short, barely visible bar feature", "0.5": "short bar, with a length about one third of D25", "0.75": "long bar, that extends over about half of D25", "1": "very long, prominent bar that extends over more than half of D25"}}'::JSON )
, ( 'inner ring' , {0,1}, '{"description": "presence of a ring-like overdensity that is within the disk and/or spiral arm pattern, and at the end of the bar when present (contrary to nuclear rings that occur well within the bar)", "values": {"0": "no inner ring", "0.25": "low ring contribution to the galaxy flux", "0.5": "intermediate ring contribution to the galaxy flux", "0.75": "significant ring contribution to the galaxy flux", "1": "highest ring contribution to the galaxy flux"}}'::JSON )
, ( 'outer ring' , {0,1}, '{"description": "presence of a ring-like over-density that lies mostly outside the disk and/or spiral arm pattern", "values": {"0": "no outer ring", "0.25": "low ring contribution to the galaxy flux", "0.5": "intermediate ring contribution to the galaxy flux", "0.75": "significant ring contribution to the galaxy flux", "1": "highest ring contribution to the galaxy flux"}}'::JSON )
, ( 'pseudo-ring' , {0,1}, '{"description": "presence of a outer pseudo-rings (Buta & Combes, 1996): R1-ring having a dimpled eight shape due to a 180◦ winding of the spiral arms with respect to the end of a bar; R2-feature with a higher winding of 270◦ of the spiral arms with respect to the bar; and the intermediate R1-R2 pattern", "values": {"0": "no visible pseudo-ring feature", "0.25": "R2 and R1-R2 pseudo-rings containing a low fraction of the galaxy flux", "0.5": "R2 and R1-R2 pseudo-rings containing a higher fraction of the galaxy flux", "0.75": "R1 pseudo-ring feature containing a low fraction of the galaxy flux", "1": "R1 pseudo-ring feature containing a higher fraction of the galaxy flux"}}'::JSON )
;


CREATE TABLE IF NOT EXISTS morphology.features (
  record_id	Text	NOT NULL	REFERENCES layer0.records(id)	ON UPDATE cascade ON DELETE restrict
, attribute	Text	NOT NULL	REFERENCES morphology.attributes (id)	ON UPDATE cascade ON DELETE restrict
, value	Real	NOT NULL
, em_value	Real
, ep_value	Real
, method	morphology.MethodType	NOT NULL
, CHECK ( (em_value IS NULL and ep_value IS NULL) or (em_value IS NOT NULL and ep_value IS NOT NULL) )
, PRIMARY KEY (record_id, method)
) ;

COMMENT ON TABLE morphology.features	IS 'Catalog of morphology features' ;
COMMENT ON COLUMN distance.featires.record_id	IS 'Record ID';
COMMENT ON COLUMN morphology.features.id	IS 'Attribute ID' ;
COMMENT ON COLUMN morphology.features.value	IS 'Attribute strength' ;
COMMENT ON COLUMN morphology.features.em_value	IS 'Lower error of the attribute' ;
COMMENT ON COLUMN morphology.features.ep_value	IS 'Upper error of the attribute' ;
COMMENT ON COLUMN morphology.features.method	IS 'Morphology method ID';


-------------- Morphology of Dwarfs --------------
CREATE TABLE IF NOT EXISTS morphology.extra (
  record_id	Text	PRIMARY KEY	REFERENCES layer0.records(id)	ON UPDATE cascade ON DELETE restrict
, type	morphology.ExtraType	NOT NULL
) ;


COMMIT ;
