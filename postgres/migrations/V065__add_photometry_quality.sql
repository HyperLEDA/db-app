BEGIN;

ALTER TABLE photometry.ellipse ADD COLUMN quality	common.quality_type	NOT NULL	DEFAULT 'regular' ;
SELECT meta.setparams( 'photometry', 'ellipse', 'quality', '{"description": "Measurement quality flag"}'::json ) ;

ALTER TABLE photometry.total ADD COLUMN quality	common.quality_type	NOT NULL	DEFAULT 'regular' ;
SELECT meta.setparams( 'photometry', 'total', 'quality', '{"description": "Measurement quality flag"}'::json ) ;

ALTER TABLE photometry.isophotal ADD COLUMN quality	common.quality_type	NOT NULL	DEFAULT 'regular' ;
SELECT meta.setparams( 'photometry', 'isophotal', 'quality', '{"description": "Measurement quality flag"}'::json ) ;

COMMIT;
