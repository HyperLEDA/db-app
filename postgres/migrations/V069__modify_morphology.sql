/* pgmigrate-encoding: utf-8 */
BEGIN;

ALTER TYPE morphology.measurement_type	ADD VALUE IF NOT EXISTS 'average' ;
ALTER TYPE morphology.measurement_type	ADD VALUE IF NOT EXISTS 'unknown' ;

COMMENT ON TYPE morphology.measurement_type IS '{
"description": "Type of the morphology classification",
"values": {
  "expert": "Classical detailed visual classification of galaxy morphology (Hubble, de Vaucouleurs, etc.) made by experts",
  "citizen science": "Visual classification of galaxy morphology performed by citizen scientists (e.g. Galaxy Zoo)",
  "machine learning": "Image-based automatic classification based on machine learning algorithms (CNN, etc)",
  "parametric": "Parametric classification based on photometry and structural relations (bulge-to-total-type relation, etc.)",
  "nonparametric": "Nonparametric indices based on image statistics (Gini, M20, CAS, etc.)",
  "kinematic": "Classification based on galaxy kinematics (fast/slow rotators, dispersion-dominated systems, etc.)",
  "simplified": "Simple/coarse classification (early/late, disk/elliptical, etc.)",
  "average": "Average of several measurements",
  "unknown": "Unspecified measurement"
  }
}';

-- Remove the foreign key to the integer Hubble sequence.
ALTER TABLE morphology.t	DROP CONSTRAINT t_value_fkey ;

-- Change T-type from integer to real-valued.
ALTER TABLE morphology.t	ALTER COLUMN value TYPE Real ;

ALTER TABLE morphology.t	ADD CHECK (value>-6.5 and value<11.5) ;

COMMIT;
