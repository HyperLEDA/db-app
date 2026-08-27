/* pgmigrate-encoding: utf-8 */
BEGIN;

ALTER TYPE spectroscopy.flux_method_type  ADD VALUE IF NOT EXISTS 'average' ;
ALTER TYPE spectroscopy.flux_method_type  ADD VALUE IF NOT EXISTS 'unknown' ;

COMMENT ON TYPE spectroscopy.flux_method_type IS '{
"description": "Method of the integrated line flux measurement",
"values": {
  "sum": "Integrated flux density of the line determined by summing all spectral channels",
  "gauss": "Line flux approximated by gaussian profile",
  "busy": "Profile of the line approximated by busy function",
  "average": "Average of several measurements",
  "unknown": "Unspecified measurement"
  }
}';

ALTER TYPE spectroscopy.flux_method_type RENAME TO flux_measurement_type ;

COMMIT ;
