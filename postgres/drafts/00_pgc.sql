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


--------------------------
-- Ассоциация записей с PGC номерами переносится в таблицу objects
--------------------------

ALTER TABLE rawdata.objects 
ADD COLUMN pgc Integer REFERENCES common.pgc (id) ON DELETE restrict ON UPDATE cascade,
ADD COLUMN modification_time Timestamp Without Time Zone ;

COMMENT ON TABLE rawdata.objects IS 'The register of all objects in original data tables' ;
COMMENT ON COLUMN rawdata.objects.id  IS 'The record id' ;
COMMENT ON COLUMN rawdata.objects.table_id IS 'The table in which the record is located' ;
COMMENT ON COLUMN rawdata.objects.pgc IS 'Corssidentification of the record with the PGC-number' ;
COMMENT ON COLUMN rawdata.objects.modification_time IS 'Time of PGC-number assignment to the record' ;


---------------------------
-- Перенос данных
---------------------------

INSERT INTO common.pgc (id) 
SELECT id 
FROM rawdata.pgc 
ORDER BY rawdata.pgc.id 
;

UPDATE rawdata.objects
SET
  pgc=rawdata.pgc.id
FROM rawdata.pgc
WHERE 
  rawdata.pgc.object_id=rawdata.objects.id
;


---------------------------
-- Категория данных переносится в описание наборов данных
---------------------------

ALTER TABLE rawdata.tables DROP COLUMN datatype ;


--------------------------------------
-- В дальнейшем нужно будет
-- 1. Перенести связь между записями и PGC в таблицу objects
-- 2. Удалить таблицу rawdata.pgc
-- 3. Перименовать таблицу objects в records
-- 4. Перенести таблицы records и tables в схему layer0
--------------------------------------

ROLLBACK;
-- COMMIT;

