BEGIN;

ALTER TABLE kinematics.line_width	DROP CONSTRAINT line_width_width_check ;
ALTER TABLE kinematics.line_width	ADD CHECK (width >= 0) ;

COMMIT;
