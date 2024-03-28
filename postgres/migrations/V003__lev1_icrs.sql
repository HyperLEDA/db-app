BEGIN ;

----------- Coordinate catalog (level 1) ---------------------
CREATE SCHEMA icrs ;

COMMENT ON SCHEMA icrs IS 'Catalog of coordinate in the International Celestial Reference System' ;


--  data - ICRS координаты в градусах
--  err  - ошибки координат
--  dataseterr - средняя ошибка измерения координат выборки
--         к сожалению, в старых каталогах редко указывалась индивидуальная точность измерения координат
--         в Леда для этого был введен класс точности http://atlas.obs-hp.fr/hyperleda/a113/ : 
--         -1 = 0.1 arcsec, 0 = 1 arcsec, 1 = 10 arcsec, 2 = 100 arcsec ~ 1 arcmin, 3 = 1000 arcsec ~ 10 arcmin, 9 - исключить из рассмотрения
--  obsoleted  - список устаревших наборов данных (поддержание этого списка - ответственность Леда)
--  excluded   - список ошибочных измерений (поддержание этого списка - ответственность Леда)
--  list - представление
--  mean - усредненные координаты (простое взвешенное среднее)
--
--  Для данного каталога создание специализированных наборов данных (dataset) представляется излишним. Ссылка на библиографию должна полностью решать эту проблему.
--
--  Для небесных координат разработан специализированный индекс, ускоряющий поиск близлежащих объектов. Нужно будет научиться его использовать.

CREATE TABLE icrs.data (
  id	serial	PRIMARY KEY
, pgc	integer	NOT NULL	REFERENCES common.pgc ( id ) ON DELETE restrict ON UPDATE cascade
, ra	double precision	NOT NULL
, dec	double precision	NOT NULL
, bib	integer	NOT NULL	REFERENCES common.bib ( id ) ON DELETE restrict ON UPDATE cascade
, modification_time	timestamp without time zone	NOT NULL	DEFAULT NOW()
, CHECK (ra>=0 and ra<=360 and dec>=-90 and dec<=90)
) ;
CREATE INDEX ON icrs.data (ra) ;
CREATE INDEX ON icrs.data (dec) ;
CREATE INDEX ON icrs.data (ra,dec) ;

COMMENT ON TABLE icrs.data IS 'The table contains collection of the coordinates in the International Celestial Reference System (ICRS)' ;
COMMENT ON COLUMN icrs.data.id IS 'ID of the coordinates' ;
COMMENT ON COLUMN icrs.data.pgc IS 'PGC number of an object' ;
COMMENT ON COLUMN icrs.data.ra IS 'Right Ascension (ICRS) in degrees' ;
COMMENT ON COLUMN icrs.data.dec IS 'Declination (ICRS) in degrees' ;
COMMENT ON COLUMN icrs.data.bib IS 'Bibliography reference' ;
COMMENT ON COLUMN icrs.data.modification_time IS 'Timestamp of adding or modification coordinates in the database' ;


-- По уму надо бы хранить ошибку, скорректированную за сколненеие err_ra*cos(dec), аналогично собственным движениям
CREATE TABLE icrs.err (
  id	integer	NOT NULL	REFERENCES icrs.data (id) ON DELETE restrict ON UPDATE cascade
, ra	double precision	NOT NULL
, dec	double precision	NOT NULL
) ;


CREATE TABLE icrs.dataseterr (
  bib	integer	NOT NULL	REFERENCES common.bib ( id ) ON DELETE restrict ON UPDATE cascade
, ra	double precision	NOT NULL
, dec	double precision	NOT NULL
) ;

COMMENT ON TABLE icrs.err IS 'The table of individual object errors' ;
COMMENT ON COLUMN icrs.err.id IS 'ID of the coordinates' ;
COMMENT ON COLUMN icrs.err.racosdec IS 'Right Ascension error (RAerr*cos(Des) in arcsec' ;
COMMENT ON COLUMN icrs.err.dec IS 'Declination error in degrees' ;


-- Надо бы добавить поле, обозначающее ответственного за добавление данных в этот список...
CREATE TABLE icrs.obsoleted (
  bib	integer	NOT NULL	REFERENCES common.bib ( id ) ON DELETE restrict ON UPDATE cascade
, renewed	integer	NOT NULL	REFERENCES common.bib ( id ) ON DELETE restrict ON UPDATE cascade
, modification_time	timestamp without time zone	NOT NULL	DEFAULT NOW()
) ;

-- Надо бы добавить поле, обозначающее ответственного за добавление данных в этот список...
CREATE TABLE icrs.excluded (
  id	bigint	NOT NULL	REFERENCES icrs.data (id) ON DELETE restrict ON UPDATE cascade
, bib	integer	NOT NULL	REFERENCES common.bib ( id ) ON DELETE restrict ON UPDATE cascade
, note	text	NOT NULL
, modification_time	timestamp without time zone	NOT NULL	DEFAULT NOW()
) ;

CREATE VIEW icrs.list AS 
SELECT
  d.id
, d.pgc
, d.ra
, d.dec
, COALESCE( err.ra, dserr.ra )	AS e_ra
, COALESCE( err.dec, dserr.dec)	AS e_dec
, b.id	AS bib
, b.bibcode
, b.year
, b.author
, b.title
, b.description
, obsol.bib IS NOT NULL and excl.id IS NOT NULL	AS isok
, GREATEST( d.modification_time, ob.modification_time, ex.modification_time )	AS modification_time
FROM
  icrs.data AS d
  LEFT JOIN icrs.err AS err USING (id)
  LEFT JOIN icrs.dataseterr AS dserr USING (bib)
  LEFT JOIN common.bib AS b ON (d.bib=b.id)
  LEFT JOIN icrs.obsoleted AS obsol ON (obsol.bib=d.bib)
  LEFT JOIN icrs.excluded AS excl ON (excl.id=d.id)
;

-- Есть более точный расчет ошибки взвешенного среднего
-- Важный вопрос: скорректирована ли ошибка в ra за склонение. По уму надо бы хранить e_ra*cos(dec), аналогично собственным движениям
CREATE VIEW icrs.mean AS
WITH 
  xyz AS (
    SELECT
      pgc
    , cosd(dec) * cosd(ra)	AS x
    , cosd(dec) * sind(ra)	AS y
    , sind(dec)	AS z
    , coalesce( 1/( (e_ra*cosd(dec))^2 + e_dec^2 ), 1 ) AS invvar
    FROM icrs.list
    WHERE isOk
  )
, mean AS (
    SELECT
      pgc
    , avg( x*invvar ) / avg( invvar )	AS x
    , avg( y*invvar ) / avg( invvar )	AS y
    , avg( z*invvar ) / avg( invvar )	AS z
    , sqrt( 1/sum(invvar) )	AS sig
    FROM xyz
    GROUP BY pgc
  )
SELECT
  pgc
, atan2d(y,x)	AS ra
, atan2d(z,sqrt(x^2+y^2))	AS dec
, sig	AS e_ra
, sig	AS e_dec
FROM mean
;

COMMIT ;