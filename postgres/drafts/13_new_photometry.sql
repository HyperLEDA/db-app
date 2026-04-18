BEGIN;

----------------------------------
--  Geometry 
----------------------------------
CREATE TABLE IF NOT EXISTS photometry.ellipse (
  record_id     Text    NOT NULL        REFERENCES layer0.records(id) ON UPDATE cascade ON DELETE restrict
, band  text    NOT NULL        REFERENCES photometry.calib_bands (id) ON DELETE restrict ON UPDATE cascade
, method        photometry.MagMethodType        NOT NULL
, level real    CHECK (level>0 and level<100)
, a     real    CHECK (a>0)
, e_a   real    CHECK (e_a>0)
, b     real    CHECK (b<=a)
, e_b   real    CHECK (e_b>0)
, pa    real    CHECK (pa>=0 and pa<180)
, e_pa  real    CHECK (e_pa>0)
, isophote      real    CHECK (isophote>-1 and isophote<30)
, e_isophote    real    CHECK (e_isophote>0 and e_isophote<0.5)
, PRIMARY KEY (record_id, band, method, level)
, CHECK (a IS NOT NULL or b IS NOT NULL or pa IS NOT NULL)
, CHECK (method IN ('asymptotic','model','petrosian','kron') and level IS NOT NULL)
, CHECK (method='isophotal' and isophote IS NOT NULL)
);
CREATE INDEX ON photometry.ellipse (record_id) ;
CREATE INDEX ON photometry.ellipse (band) ;
CREATE INDEX ON photometry.ellipse (level) ;

SELECT meta.setparams('photometry', 'ellipse',  '{"description":"Catalog of the isophotal photometry"}') ;
SELECT meta.setparams('photometry', 'ellipse', 'record_id', '{"description":"Record ID"}') ;
SELECT meta.setparams('photometry', 'ellipse', 'band',      '{"description":"Calibrated passband ID", "ucd":"instr.filter"}') ;
SELECT meta.setparams('photometry', 'ellipse', 'method',    '{"description":"Measurement method of the total magnitude"}') ;
SELECT meta.setparams('photometry', 'ellipse', 'level',     '{"description":"Percent of the enclosed flux"}') ;
SELECT meta.setparams('photometry', 'ellipse', 'a',         '{"description":"Semi-major axis length at the given isophote", "unit":"arcsec", "ucd":"phys.angSize.smajAxis"}') ;
SELECT meta.setparams('photometry', 'ellipse', 'e_a',       '{"description":"Error of the semi-major axis length at the given isophote", "unit":"arcsec", "ucd":"stat.error;phys.angSize.smajAxis"}') ;
SELECT meta.setparams('photometry', 'ellipse', 'b',         '{"description":"Semi-minor axis length at the given isophote", "unit":"arcsec", "ucd":"phys.angSize.sminAxis"}') ;
SELECT meta.setparams('photometry', 'ellipse', 'e_b',       '{"description":"Error of the semi-minor axis length at the given isophote", "unit":"arcsec", "ucd":"stat.error;phys.angSize.sminAxis"}') ;
SELECT meta.setparams('photometry', 'ellipse', 'pa',        '{"description":"Position angle (measured east of north)", "unit":"deg", "ucd":"pos.posAng"}') ;
SELECT meta.setparams('photometry', 'ellipse', 'e_pa',      '{"description":"Error of the position angle", "unit":"deg", "ucd":"stat.error;pos.posAng"}') ;
SELECT meta.setparams('photometry', 'ellipse', 'isophote',  '{"description":"Surface brightness at given level", "unit":"mag/arcmin2", "ucd":"phot.mag.sb"}') ;
SELECT meta.setparams('photometry', 'ellipse', 'e_isophote','{"description":"Error fo the surface brightness at given level", "unit":"mag/arcmin2", "ucd":"stat.error;phot.mag.sb"}') ;


-- ROLLBACK ;
COMMIT;
