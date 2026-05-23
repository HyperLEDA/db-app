CREATE TABLE photometry.ellipse (
  record_id text NOT NULL REFERENCES layer0.records(id) ON UPDATE CASCADE ON DELETE RESTRICT,
  band text NOT NULL REFERENCES photometry.calib_bands(id) ON DELETE RESTRICT ON UPDATE CASCADE,
  method photometry.mag_method_type NOT NULL,
  level real CHECK (level > 0 AND level < 100),
  a real CHECK (a > 0),
  e_a real CHECK (e_a > 0),
  b real CHECK (b <= a),
  e_b real CHECK (e_b > 0),
  pa real CHECK (pa >= 0 AND pa < 180),
  e_pa real CHECK (e_pa > 0),
  isophote real CHECK (isophote > -1 AND isophote < 30),
  e_isophote real CHECK (e_isophote > 0 AND e_isophote < 0.5),
  CHECK (a IS NOT NULL OR b IS NOT NULL OR pa IS NOT NULL),
  CHECK (
    (method IN ('asymptotic', 'model', 'petrosian', 'kron') AND level IS NOT NULL AND isophote IS NULL)
    OR (method = 'isophotal' AND isophote IS NOT NULL AND level IS NULL)
  ),
  UNIQUE NULLS NOT DISTINCT (record_id, band, method, level, isophote)
);

CREATE INDEX ON photometry.ellipse (record_id);

SELECT meta.setparams('photometry', 'ellipse', '{"description": "Catalog of the isophotal photometry"}');
SELECT meta.setparams('photometry', 'ellipse', 'record_id', '{"description": "Record ID"}');
SELECT meta.setparams('photometry', 'ellipse', 'band', '{"description": "Calibrated passband ID", "ucd": "instr.filter"}');
SELECT meta.setparams('photometry', 'ellipse', 'method', '{"description": "Measurement method of the total magnitude"}');
SELECT meta.setparams('photometry', 'ellipse', 'level', '{"description": "Percent of the enclosed flux"}');
SELECT meta.setparams('photometry', 'ellipse', 'a', '{"description": "Semi-major axis length at the given isophote", "unit": "arcsec", "ucd": "phys.angSize.smajAxis"}');
SELECT meta.setparams('photometry', 'ellipse', 'e_a', '{"description": "Error of the semi-major axis length at the given isophote", "unit": "arcsec", "ucd": "stat.error;phys.angSize.smajAxis"}');
SELECT meta.setparams('photometry', 'ellipse', 'b', '{"description": "Semi-minor axis length at the given isophote", "unit": "arcsec", "ucd": "phys.angSize.sminAxis"}');
SELECT meta.setparams('photometry', 'ellipse', 'e_b', '{"description": "Error of the semi-minor axis length at the given isophote", "unit": "arcsec", "ucd": "stat.error;phys.angSize.sminAxis"}');
SELECT meta.setparams('photometry', 'ellipse', 'pa', '{"description": "Position angle (measured east of north)", "unit": "deg", "ucd": "pos.posAng"}');
SELECT meta.setparams('photometry', 'ellipse', 'e_pa', '{"description": "Error of the position angle", "unit": "deg", "ucd": "stat.error;pos.posAng"}');
SELECT meta.setparams('photometry', 'ellipse', 'isophote', '{"description": "Surface brightness at given level", "unit": "mag/arcmin2", "ucd": "phot.mag.sb"}');
SELECT meta.setparams('photometry', 'ellipse', 'e_isophote', '{"description": "Error fo the surface brightness at given level", "unit": "mag/arcmin2", "ucd": "stat.error;phot.mag.sb"}');
