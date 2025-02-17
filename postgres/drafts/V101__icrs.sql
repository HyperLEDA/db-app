-- Надо бы добавить поле, обозначающее ответственного за добавление данных в этот список...
CREATE TABLE icrs.excluded (
  id	integer	PRIMARY KEY	REFERENCES icrs.data (id) ON DELETE restrict ON UPDATE cascade
, bib	integer	NOT NULL	REFERENCES common.bib ( id ) ON DELETE restrict ON UPDATE cascade
, note	text	NOT NULL
, modification_time	timestamp without time zone	NOT NULL	DEFAULT NOW()
) ;

COMMENT ON TABLE icrs.excluded	IS 'List of individual positions excluded from consideration' ;
COMMENT ON COLUMN icrs.excluded.id	IS 'ID the position' ;
COMMENT ON COLUMN icrs.excluded.bib	IS 'Bibliography reference where given position was marked as wrong' ;
COMMENT ON COLUMN icrs.excluded.note	IS 'Note on exclusion' ;
COMMENT ON COLUMN icrs.excluded.modification_time	IS 'Timestamp when the record was added to the database' ;


CREATE VIEW icrs.list AS 
SELECT
  d.id
, d.pgc
, d.ra
, d.dec
, d.e_ra
, d.e_dec
, d.bib
, obsol.bib IS NULL and excl.id IS NULL	AS isok
, greatest( d.modification_time, obsol.modification_time, excl.modification_time )	AS modification_time
FROM
  icrs.data AS d
  LEFT JOIN common.obsoleted AS obsol ON (obsol.bib=d.bib)
  LEFT JOIN icrs.excluded AS excl ON (excl.id=d.id)
;

COMMENT ON VIEW icrs.list	IS 'Collection of the object positions in the International Celestial Reference System (ICRS)' ;
COMMENT ON COLUMN icrs.list.id	IS 'ID of the position' ;
COMMENT ON COLUMN icrs.list.pgc	IS 'PGC number of the object' ;
COMMENT ON COLUMN icrs.list.ra	IS 'Right Ascension (ICRS) in degrees' ;
COMMENT ON COLUMN icrs.list.dec	IS 'Declination (ICRS) in degrees' ;
COMMENT ON COLUMN icrs.list.e_ra	IS 'Right Ascension error (RAerr*cos(Des) in arcsec' ;
COMMENT ON COLUMN icrs.list.e_dec	IS 'Declination error in arcsec' ;
COMMENT ON COLUMN icrs.list.bib	IS 'Bibliography reference' ;
COMMENT ON COLUMN icrs.list.isok	IS 'True if the position is actual and False if it is obsoleted or excluded' ;
COMMENT ON COLUMN icrs.list.modification_time	IS 'Timestamp when the record was added to the database' ;



-- Возможно необходимо создать функцию для расчета взвешенного среднего и его ошибки
-- cos(Dec) * dAlpha/dx = cos( atan( z/sqrt(x^2+y^2) ) ) * d( atan(y/x) )/dx = -y / sqrt( (x^2+y^2) * (x^2+y^2+z^2) ) = -y/sqrt( (x^2+y^2) )
-- cos(Dec) * dAlpha/dy = cos( atan( z/sqrt(x^2+y^2) ) ) * d( atan(y/x) )/dx =  x / sqrt( (x^2+y^2) * (x^2+y^2+z^2) ) =  x/sqrt( (x^2+y^2) )
-- dDec/dz = d( atan(z/sqrt(1-z^2)) )/dz = 1/sqrt(1-z^2)
CREATE VIEW icrs.mean AS
WITH 
  xyz AS (
    SELECT
      pgc
    , cosd(dec) * cosd(ra)	AS x
    , cosd(dec) * sind(ra)	AS y
    , sind(dec)	AS z
    , coalesce( 1/( e_ra^2 + e_dec^2 ), 1.0/300^2 ) AS invvar
    , modification_time
    FROM icrs.list
    WHERE isOk
  )
, mean AS (
    SELECT
      pgc
    , public.wmean( x, invvar )	AS x
    , public.wmean( y, invvar )	AS y
    , public.wmean( z, invvar )	AS z
    , max( modification_time )	AS modification_time
    FROM xyz
    GROUP BY pgc
  )
  
SELECT
  pgc
, atan2d( y[1] , x[1] )	AS ra
, atan2d( z[1] , sqrt( x[1]^2+y[1]^2 ) )	AS dec
, sqrt( ( y[1]^2*x[2]^2 + x[1]^2*y[2]^2 ) / ( x[1]^2+y[1]^2 ) ) /pi()*180*3600	AS e_ra              -- dAlpha is corrected for cos(dec)
, sqrt( 1 / (1-z[1]^2) )*z[2] /pi()*180*3600	AS e_dec
, modification_time
FROM mean
;

COMMENT ON VIEW icrs.mean	IS 'Object position in the International Celestial Reference System (ICRS)' ;
COMMENT ON COLUMN icrs.mean.pgc	IS 'PGC number of the object' ;
COMMENT ON COLUMN icrs.mean.ra	IS 'Right Ascension (ICRS) in degrees' ;
COMMENT ON COLUMN icrs.mean.dec	IS 'Declination (ICRS) in degrees' ;
COMMENT ON COLUMN icrs.mean.e_ra	IS 'Right Ascension error (RAerr*cos(Des) in arcsec' ;
COMMENT ON COLUMN icrs.mean.e_dec	IS 'Declination error in arcsec' ;
COMMENT ON COLUMN icrs.mean.modification_time	IS 'Timestamp when the record was added to the database' ;
