BEGIN;

CREATE TABLE common.pgc (
  pgc Serial PRIMARY KEY
, modification_time Timestamp Without Time Zone
);

COMMENT ON TABLE common.pgc IS 'The list of existing PGC-numbers' ;
COMMENT ON COLUMN common.pgc.pgc IS 'The PGC-number' ;
COMMENT ON COLUMN common.pgc.modification_time IS 'The modification time' ;

------------------------------------
-- Тип Serial создает последовательность, по умолчанию common.pgc_pgc_seq, которую можно использовать для автоматического создания PGC-номеров командой
-- > INSERT INTO test_pgc ( modification_time ) VALUES ( now() ) ;
-- Новое значение можно получить функцией nextval('common.pgc_pgc_seq'::regclass)
-- SELECT nextval('common.pgc_pgc_seq'::regclass) ;
-- В принципе, это делает ненужным функцию next_pgc
------------------------------------



DROP TABLE rawdata.pgc ;
DROP FUNCTION rawdata.next_pgc ;

ALTER TABLE rawdata.objects RENAME TO rawdata.resords ;

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

