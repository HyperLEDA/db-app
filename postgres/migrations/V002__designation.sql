/* pgmigrate-encoding: utf-8 */

BEGIN ;

DROP SCHEMA IF EXISTS designation CASCADE ;

-----------------------------------------------------------
-------- Designation --------------------------------------
CREATE SCHEMA designation ;

COMMENT ON SCHEMA designation IS 'Designation catalog' ;


-- Рекомендации по наименованию объектов: https://cdsweb.u-strasbg.fr/Dic/iau-spec.html
-- Общая форма: Acronym Sequence (Specifier)
-- К сожалению, они не всегда выполняются
-- Леда следует рекомендациям IAU, однако удаляет пробелы. Кроме того, все имена в Леда сохраняются в uppercase. Это было связано с индексацией, но выглядит излишним.
-- Есть случаи неоднозначности имен в старых каталогах, когда одно и тоже имя могло использоваться для разных объектов. Рещил вынести это в отдельную таблицу.
-- Важный момент использвание сокращений:
--    NGC 0123 <=> N 123
--    Andromeda XVIII <=> And XVIII <=> And 18
-- В Леда используется метод разработанный в NED парсинга имени и перекодирования его в стандартную форму.
CREATE TABLE designation.data (
  pgc	integer	NOT NULL	REFERENCES common.pgc(id) ON DELETE restrict ON UPDATE cascade
, design	text	NOT NULL	UNIQUE
, bib	integer	NOT NULL	REFERENCES common.bib(id) ON DELETE restrict ON UPDATE cascade
, modification_time	timestamp without time zone	NOT NULL	DEFAULT NOW()
, PRIMARY KEY (pgc,design)
) ;
CREATE UNIQUE INDEX ON designation.data (upper(replace(design,' ',''))) ;
CREATE INDEX ON designation.data (bib) ;

COMMENT ON TABLE designation.data IS 'List of unique object names' ;
COMMENT ON COLUMN designation.data.pgc IS '{"description" : "PGC number of the object" , "ucd" : "meta.id"}' ;
COMMENT ON COLUMN designation.data.design IS '{"description" : "Unique designation the object. It must follow the IAU recommendations: https://cdsweb.u-strasbg.fr/Dic/iau-spec.html" , "ucd" : "meta.id"}' ;
COMMENT ON COLUMN designation.data.bib IS '{"description" : "Bibliography reference" , "ucd" : "meta.bib"}' ;
COMMENT ON COLUMN designation.data.modification_time IS '{"description" : "Timestamp when the record was added to the database" , "ucd" : "time.creation"}' ;


CREATE TABLE designation.ambiguity (
  PRIMARY KEY (pgc,design)
, FOREIGN KEY (pgc)	REFERENCES common.pgc(id) ON DELETE restrict ON UPDATE cascade
, FOREIGN KEY (bib)	REFERENCES common.bib(id) ON DELETE restrict ON UPDATE cascade
) INHERITS (designation.data) ;
CREATE INDEX ON designation.ambiguity (upper(replace(design,' ',''))) ;
CREATE INDEX ON designation.ambiguity (bib) ;

-- CREATE TABLE designation.ambiguity (
--   pgc	integer	NOT NULL	REFERENCES common.pgc(id) ON DELETE restrict ON UPDATE cascade
-- , design	text	NOT NULL
-- , bib	integer	NOT NULL	REFERENCES common.bib(id) ON DELETE restrict ON UPDATE cascade
-- , modification_time	timestamp without time zone	NOT NULL	DEFAULT NOW()
-- , PRIMARY KEY (pgc,design)
-- ) ;
-- CREATE INDEX ON designation.ambiguity (upper(replace(design,' ',''))) ;
-- CREATE INDEX ON designation.ambiguity (bib) ;

COMMENT ON TABLE designation.ambiguity IS 'List of ambiguous designations' ;
COMMENT ON COLUMN designation.ambiguity.pgc IS 'PGC number of the object' ;
COMMENT ON COLUMN designation.ambiguity.design IS 'Ambiguous designation' ;
COMMENT ON COLUMN designation.ambiguity.bib IS 'Bibliography reference' ;
COMMENT ON COLUMN designation.ambiguity.modification_time IS 'Timestamp when the record was added to the database' ;


CREATE VIEW designation.list AS
SELECT 
  *
, tableoid::regclass::text~'(designation\.)?data$'	AS isunique
FROM designation.data
;

COMMENT ON VIEW designation.list IS 'List of designations' ;
COMMENT ON COLUMN designation.list.pgc IS 'PGC number of the object' ;
COMMENT ON COLUMN designation.list.design IS 'Designation' ;
COMMENT ON COLUMN designation.list.bib IS 'Bibliography reference' ;
COMMENT ON COLUMN designation.list.modification_time IS 'Timestamp when the record was added to the database' ;
COMMENT ON COLUMN designation.list.isunique IS 'True if designation is unique and False if it is ambiguous' ;



-- Костыль для выбора основного имени
CREATE VIEW designation.main AS
SELECT DISTINCT ON (pgc)
  d.*
FROM 
  ONLY designation.data AS d
  LEFT JOIN common.bib AS b ON (d.bib = b.id)
ORDER BY 
  pgc
, CASE WHEN d.design~'^M ' THEN 1   -- Messier
       WHEN d.design~'^NGC' THEN 2
       WHEN d.design~'^IC'  THEN 3
       WHEN d.design~'^DDO' THEN 4
       WHEN d.design~'^UGC' THEN 5
       WHEN d.design~'^PGC' and d.pgc<1000000 THEN 6
       WHEN b.bibcode IS NOT NULL THEN b.year-1800
       ELSE b.year
  END
;

COMMENT ON VIEW designation.main IS 'List of the principal object names' ;
COMMENT ON COLUMN designation.main.pgc IS 'PGC number of the object' ;
COMMENT ON COLUMN designation.main.design IS 'Principal designation' ;
COMMENT ON COLUMN designation.main.bib IS 'Bibliography reference' ;
COMMENT ON COLUMN designation.main.modification_time IS 'Timestamp when the record was added to the database' ;



-- -----------------------------------------------------------
-- -- Designations must follow the IAU recommendations
-- -- https://cdsweb.u-strasbg.fr/Dic/iau-spec.html
-- -- The designation must be in a form:  Acronym_Sequence_(Specifier)
-- -- were "_" denotes a blank " "
-- 
-- -- Acronym is an unique code that specifies the catalog or collection of sources.
-- CREATE TABLE designation.acronym (
--   id	text	PRIMARY KEY
-- , description	text	NOT NULL
-- ) ;
-- 
-- CREATE TABLE designation.synonym (
--   acronym	text	NOT NULL	REFERENCES designation.acronym (id) ON DELETE restrict ON UPDATE cascade
-- , analog	text	NOT NULL	UNIQUE
-- , PRIMARY KEY (acronym,analog)
-- ) ;
-- 
-- CREATE TABLE designation.acronymref (
--   acronym	text	NOT NULL	REFERENCES designation.acronym (id) ON DELETE restrict ON UPDATE cascade
-- , bib	integer	NOT NULL	REFERENCES common.bib (id) ON DELETE restrict ON UPDATE cascade
-- , PRIMARY KEY (acronym,bib)
-- ) ;


-----------------------------------------------------------
-- Constellations -----------------------------------------
CREATE TABLE designation.constellation (
  id	char(3)	PRIMARY KEY
, name	text	NOT NULL	UNIQUE
) ;

COMMENT ON TABLE designation.constellation IS 'List of constellations: http://vizier.cds.unistra.fr/vizier/VizieR/constellations.htx' ;
COMMENT ON COLUMN designation.constellation.id IS '3-letter official abbreviation of the constellation' ;
COMMENT ON COLUMN designation.constellation.name IS 'Constellation' ;


INSERT INTO designation.constellation (id,name) VALUES
  ( 'And' , 'Andromeda' )
, ( 'Ant' , 'Antlia' )
, ( 'Aps' , 'Apus' )
, ( 'Aqr' , 'Aquarius' )
, ( 'Aql' , 'Aquila' )
, ( 'Ara' , 'Ara' )
, ( 'Ari' , 'Aries' )
, ( 'Aur' , 'Auriga' )
, ( 'Boo' , 'Bootes' )
, ( 'Cae' , 'Caelum' )
, ( 'Cam' , 'Camelopardalis' )
, ( 'Cnc' , 'Cancer' )
, ( 'CVn' , 'Canes Venatici' )
, ( 'CMa' , 'Canis Major' )
, ( 'CMi' , 'Canis Minor' )
, ( 'Cap' , 'Capricornus' )
, ( 'Car' , 'Carina' )
, ( 'Cas' , 'Cassiopeia' )
, ( 'Cen' , 'Centaurus' )
, ( 'Cep' , 'Cepheus' )
, ( 'Cet' , 'Cetus' )
, ( 'Cha' , 'Chamaleon' )
, ( 'Cir' , 'Circinus' )
, ( 'Col' , 'Columba' )
, ( 'Com' , 'Coma Berenices' )
, ( 'CrA' , 'Corona Australis' )
, ( 'CrB' , 'Corona Borealis' )
, ( 'Crv' , 'Corvus' )
, ( 'Crt' , 'Crater' )
, ( 'Cru' , 'Crux' )
, ( 'Cyg' , 'Cygnus' )
, ( 'Del' , 'Delphinus' )
, ( 'Dor' , 'Dorado' )
, ( 'Dra' , 'Draco' )
, ( 'Equ' , 'Equuleus' )
, ( 'Eri' , 'Eridanus' )
, ( 'For' , 'Fornax' )
, ( 'Gem' , 'Gemini' )
, ( 'Gru' , 'Grus' )
, ( 'Her' , 'Hercules' )
, ( 'Hor' , 'Horologium' )
, ( 'Hya' , 'Hydra' )
, ( 'Hyi' , 'Hydrus' )
, ( 'Ind' , 'Indus' )
, ( 'Lac' , 'Lacerta' )
, ( 'Leo' , 'Leo' )
, ( 'LMi' , 'Leo Minor' )
, ( 'Lep' , 'Lepus' )
, ( 'Lib' , 'Libra' )
, ( 'Lup' , 'Lupus' )
, ( 'Lyn' , 'Lynx' )
, ( 'Lyr' , 'Lyra' )
, ( 'Men' , 'Mensa' )
, ( 'Mic' , 'Microscopium' )
, ( 'Mon' , 'Monoceros' )
, ( 'Mus' , 'Musca' )
, ( 'Nor' , 'Norma' )
, ( 'Oct' , 'Octans' )
, ( 'Oph' , 'Ophiucus' )
, ( 'Ori' , 'Orion' )
, ( 'Pav' , 'Pavo' )
, ( 'Peg' , 'Pegasus' )
, ( 'Per' , 'Perseus' )
, ( 'Phe' , 'Phoenix' )
, ( 'Pic' , 'Pictor' )
, ( 'Psc' , 'Pisces' )
, ( 'PsA' , 'Pisces Austrinus' )
, ( 'Pup' , 'Puppis' )
, ( 'Pyx' , 'Pyxis' )
, ( 'Ret' , 'Reticulum' )
, ( 'Sge' , 'Sagitta' )
, ( 'Sgr' , 'Sagittarius' )
, ( 'Sco' , 'Scorpius' )
, ( 'Scl' , 'Sculptor' )
, ( 'Sct' , 'Scutum' )
, ( 'Ser' , 'Serpens' )
, ( 'Sex' , 'Sextans' )
, ( 'Tau' , 'Taurus' )
, ( 'Tel' , 'Telescopium' )
, ( 'Tri' , 'Triangulum' )
, ( 'TrA' , 'Triangulum Australe' )
, ( 'Tuc' , 'Tucana' )
, ( 'UMa' , 'Ursa Major' )
, ( 'UMi' , 'Ursa Minor' )
, ( 'Vel' , 'Vela' )
, ( 'Vir' , 'Virgo' )
, ( 'Vol' , 'Volans' )
, ( 'Vul' , 'Vulpecula' )
;

COMMIT ;