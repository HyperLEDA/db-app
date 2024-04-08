BEGIN ;

DROP SCHEMA IF EXISTS rawdata CASCADE ;

-----------------------------------------------------------
-------- Raw data -----------------------------------------
CREATE SCHEMA rawdata;

COMMENT ON SCHEMA rawdata IS 'Container for the orginal tables from different sources' ;


COMMIT ;