BEGIN;

-------------------------------------------------------------
-- Сохранять время модификации PGC нет необходимости, 
-- т.к. есть время привязки объекта с записями и этого достаточно для отслеживания модификаций
--
-- добавление нового PGC номера делается командой
-- INSERT INTO common.pgc DEFAULT VALUES ;
-------------------------------------------------------------

CREATE TABLE common.pgc (
  id Serial PRIMARY KEY
);

COMMENT ON TABLE common.pgc     IS 'The list of existing PGC-numbers' ;
COMMENT ON COLUMN common.pgc.id IS 'Unique PGC-number' ;





DROP TABLE rawdata.pgc ;
DROP FUNCTION rawdata.next_pgc ;

ALTER TABLE rawdata.objects RENAME TO rawdata.records ;

ALTER TABLE rawdata.records 
ADD COLUMN pgc Integer REFERENCES common.pgc (pgc) ON DELETE restrict ON UPDATE cascade,
ADD COLUMN modification_time Timestamp Without Time Zone ;

COMMENT ON TABLE rawdata.records IS 'The register of all records in original data tables' ;
COMMENT ON COLUMN rawdata.records.id  IS 'The record id' ;
COMMENT ON COLUMN rawdata.records.table_id IS 'The table in which the record is located' ;
COMMENT ON COLUMN rawdata.records.pgc IS 'Corssidentification of the record with the PGC-number' ;
COMMENT ON COLUMN rawdata.records.modification_time IS 'Time of PGC-number assignment to the record' ;

--------------------------
-- Ассоциация записей с PGC номерами переносится в таблицу records
--------------------------



ALTER TABLE rawdata.tables DROP COLUMN datatype ;

---------------------------
-- Категория данных переносится в описание наборов данных
---------------------------



ALTER TABLE rawdata.tables SET SCHEMA layer0 ;
ALTER TABLE rawdata.records SET SCHEMA layer0 ;

--------------------------
-- Служебные таблицы уровня 0 переносятся в схему laye0
--------------------------

COMMIT;

