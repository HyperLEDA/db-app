ALTER TABLE layer2.cz
ADD CONSTRAINT cz_pgc_fkey FOREIGN KEY (pgc) REFERENCES common.pgc(id) ON DELETE RESTRICT ON UPDATE CASCADE;
ALTER TABLE layer2.designation
ADD CONSTRAINT cz_pgc_fkey FOREIGN KEY (pgc) REFERENCES common.pgc(id) ON DELETE RESTRICT ON UPDATE CASCADE;
ALTER TABLE layer2.icrs
ADD CONSTRAINT cz_pgc_fkey FOREIGN KEY (pgc) REFERENCES common.pgc(id) ON DELETE RESTRICT ON UPDATE CASCADE;

CREATE OR REPLACE FUNCTION rawdata_set_modification_time()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.pgc IS DISTINCT FROM OLD.pgc THEN
        NEW.modification_time := now();
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER set_modification_time_on_pgc_update
BEFORE UPDATE OF pgc ON rawdata.objects
FOR EACH ROW
EXECUTE FUNCTION rawdata_set_modification_time();

DROP TABLE rawdata.pgc;
