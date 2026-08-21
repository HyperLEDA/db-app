BEGIN;

SELECT meta.setparams( 'photometry', 'ellipse', '{"description": "Catalog of the object geometry"}'::json );

COMMIT;
