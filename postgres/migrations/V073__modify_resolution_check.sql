BEGIN;

ALTER TABLE kinematics.line_width	DROP CONSTRAINT line_width_resolution_check ;
ALTER TABLE kinematics.line_width	ADD CHECK (resolution >= 0) ;

COMMIT;
